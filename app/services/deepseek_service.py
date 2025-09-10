import os
import json
from typing import Dict, Generator, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import ACE_CONFIG, DEEPSEEK_API_KEY, DEEPSEEK_URL, DEEPSEEK_MODEL
from app.core.logger import logger

# ---------- Tunables ----------
CONNECT_TIMEOUT = float(os.getenv("DEEPSEEK_CONNECT_TIMEOUT", "5"))   # seconds
READ_TIMEOUT    = float(os.getenv("DEEPSEEK_READ_TIMEOUT", "35"))     # seconds
TOTAL_RETRIES   = int(os.getenv("DEEPSEEK_TOTAL_RETRIES", "3"))
BACKOFF_FACTOR  = float(os.getenv("DEEPSEEK_BACKOFF", "0.6"))
POOL_MAXSIZE    = int(os.getenv("DEEPSEEK_POOL_MAXSIZE", "20"))

_RETRY = Retry(
    total=TOTAL_RETRIES,
    connect=TOTAL_RETRIES,
    read=TOTAL_RETRIES,
    backoff_factor=BACKOFF_FACTOR,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("POST",),
    raise_on_status=False,
)

_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        adapter = HTTPAdapter(max_retries=_RETRY, pool_maxsize=POOL_MAXSIZE)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _session = s
    return _session


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }


# ------------ Config helpers (prompt + thresholds from conversation config) ------------
def _qual_cfg() -> Dict:
    llm = (ACE_CONFIG.get("llm") or {}).get("qualification") or {}
    return {
        "system_prompt": llm.get(
            "system_prompt",
            "Ti si ACE kvalifikacijski AI. Odgovarjaj vedno v slovenščini in vrni strogo JSON."
        ),
        "user_prompt_template": llm.get(
            "user_prompt_template",
            (
                "Kontekst:\n- Produkt: {product}\n- Opis: {description}\n"
                "- Idealni kupci: {ideal_clients}\n- Slab fit kupci: {bad_fit_clients}\n"
                "- Jedro vrednosti: {core_value}\n\nVhod:\n{lead_text}\n\n"
                "Vrni JSON s ključi category, interest, compatibility, reasons, pitch, tags."
            )
        ),
        "interest_thresholds": llm.get("interest_thresholds", {"High": 70, "Medium": 40, "Low": 0}),
    }


def _cfg_product_block() -> Dict:
    # Only pick what we actually need
    return {
        "product": ACE_CONFIG.get("product"),
        "description": ACE_CONFIG.get("description"),
        "ideal_clients": ACE_CONFIG.get("ideal_clients"),
        "bad_fit_clients": ACE_CONFIG.get("bad_fit_clients"),
        "core_value": ACE_CONFIG.get("core_value"),
    }


def _render_user_prompt(lead_text: str) -> str:
    cfg = _qual_cfg()
    pb = _cfg_product_block()
    # Make lists pretty for template
    def list_to_text(v):
        if isinstance(v, list):
            return "; ".join([str(x) for x in v])
        return str(v) if v is not None else ""
    return cfg["user_prompt_template"].format(
        product=str(pb.get("product") or ""),
        description=str(pb.get("description") or ""),
        ideal_clients=list_to_text(pb.get("ideal_clients")),
        bad_fit_clients=list_to_text(pb.get("bad_fit_clients")),
        core_value=list_to_text(pb.get("core_value")),
        lead_text=str(lead_text or "").strip()
    )


def _coerce_output(parsed: Dict) -> Dict:
    """
    Normalize model output to a fixed shape for the dashboard.
    Fills interest from thresholds if missing; clamps compatibility.
    """
    cfg = _qual_cfg()
    thresholds = cfg["interest_thresholds"]

    cat = (parsed.get("category") or "could_fit").strip()
    reasons = str(parsed.get("reasons") or "")
    pitch = str(parsed.get("pitch") or "")
    tags = parsed.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]

    # compatibility → int 0..100
    try:
        comp = int(float(parsed.get("compatibility")))
    except Exception:
        comp = 50
    comp = max(0, min(100, comp))

    # interest: model value wins; else derive from thresholds
    m_interest = (parsed.get("interest") or "").strip().title()
    if m_interest not in ("High", "Medium", "Low"):
        # derive from thresholds
        # sort thresholds by value desc and pick first match
        derived = "Low"
        try:
            ordered = sorted(thresholds.items(), key=lambda x: int(x[1]), reverse=True)
            for name, min_v in ordered:
                if comp >= int(min_v):
                    derived = name
                    break
            if derived not in ("High", "Medium", "Low"):
                derived = "Low"
        except Exception:
            derived = "Medium" if comp >= 50 else "Low"
        m_interest = derived

    return {
        "category": cat,               # good_fit | could_fit | bad_fit
        "interest": m_interest,        # High | Medium | Low
        "compatibility": comp,         # 0..100
        "reasons": reasons,
        "pitch": pitch,
        "tags": tags
    }


# ------------ Public API ------------
def run_deepseek(user_text: str, sid: str) -> Dict:
    """
    Blocking call with retries/timeouts. Never throws — returns a dict.
    On failure returns a minimal error shape the dashboard can handle.
    """
    cfg = _qual_cfg()
    system_prompt = cfg["system_prompt"]
    user_prompt = _render_user_prompt(user_text)

    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    try:
        s = _get_session()
        resp = s.post(DEEPSEEK_URL, headers=_headers(), json=body, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        if resp.status_code >= 400:
            logger.warning(f"DeepSeek HTTP {resp.status_code}: {resp.text[:300]}")
            return {"category": "error", "interest": "Low", "compatibility": 0, "reasons": "", "pitch": "", "tags": []}

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        try:
            parsed = json.loads(content)
        except Exception:
            logger.error(f"DeepSeek returned non-JSON content: {content[:300]}")
            return {"category": "error", "interest": "Low", "compatibility": 0, "reasons": "", "pitch": "", "tags": []}

        return _coerce_output(parsed)
    except Exception as e:
        logger.error(f"DeepSeek error (sid={sid}): {repr(e)}")
        return {"category": "error", "interest": "Low", "compatibility": 0, "reasons": "", "pitch": "", "tags": []}


def stream_deepseek(user_text: str, sid: str) -> Generator[str, None, None]:
    """
    Streaming generator with timeouts/retries. Uses the same config-driven prompts.
    If it fails mid-stream, yield a short warning and stop.
    """
    cfg = _qual_cfg()
    system_prompt = cfg["system_prompt"]
    user_prompt = _render_user_prompt(user_text)

    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "stream": True,
    }

    try:
        s = _get_session()
        with s.post(DEEPSEEK_URL, headers=_headers(), json=body, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)) as r:
            if r.status_code >= 400:
                logger.warning(f"DeepSeek stream HTTP {r.status_code}: {r.text[:300]}")
                yield "⚠️ Prišlo je do prekinjene povezave. Nadaljujeva brez streaminga."
                return

            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith(b"data: "):
                    data_str = line[len(b"data: "):].decode("utf-8")
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data_json = json.loads(data_str)
                        delta = data_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue
    except Exception as e:
        logger.error(f"DeepSeek streaming error (sid={sid}): {repr(e)}")
        yield "⚠️ Težava z živim pretokom. Pošlji sporočilo še enkrat ali nadaljujva z navadnim odgovorom."
