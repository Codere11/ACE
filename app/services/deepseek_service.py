import os
import json
import time
from typing import Dict, Generator, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import ACE_CONFIG, DEEPSEEK_API_KEY, DEEPSEEK_URL, DEEPSEEK_MODEL
from app.core.logger import logger

# ---------- Tunables ----------
CONNECT_TIMEOUT = float(os.getenv("DEEPSEEK_CONNECT_TIMEOUT", "5"))   # seconds
READ_TIMEOUT    = float(os.getenv("DEEPSEEK_READ_TIMEOUT", "35"))     # seconds (was 12 → too low)
TOTAL_RETRIES   = int(os.getenv("DEEPSEEK_TOTAL_RETRIES", "3"))       # 3 tries total
BACKOFF_FACTOR  = float(os.getenv("DEEPSEEK_BACKOFF", "0.6"))         # expo backoff
POOL_MAXSIZE    = int(os.getenv("DEEPSEEK_POOL_MAXSIZE", "20"))

# Retry on transient HTTP errors + 429
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


def _knowledge_head() -> str:
    """
    Keep the payload light: do NOT dump the whole config every time.
    Pull only essentials to prevent latency/size-related timeouts.
    """
    # If ACE_CONFIG is large, take just the parts we need.
    subset = {
        "brand": ACE_CONFIG.get("brand"),
        "lang": ACE_CONFIG.get("lang"),
        "goals": ACE_CONFIG.get("goals"),
        "offers": ACE_CONFIG.get("offers"),
    }
    return json.dumps(subset, ensure_ascii=False)


def run_deepseek(user_text: str, sid: str) -> Dict:
    """
    Blocking call with retries/timeouts. Never throws — returns a dict.
    On failure returns {"category": "error"} without leaking raw exception text.
    """
    prompt = (
        f"ACE knowledge:\n{_knowledge_head()}\n\n"
        f"Lead details:\nDescription: {user_text}\n\n"
        "Task: Classify this lead. Respond as JSON with keys: "
        "category (good_fit, could_fit, bad_fit), reasons (string), pitch (string). "
        "Answer in Slovenian."
    )

    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are ACE qualification AI. Always answer in Slovenian."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        s = _get_session()
        resp = s.post(
            DEEPSEEK_URL,
            headers=_headers(),
            json=body,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        # If DeepSeek is overloaded, Adapter will retry before we get here.
        # Still handle non-200s.
        if resp.status_code >= 400:
            logger.warning(f"DeepSeek HTTP {resp.status_code}: {resp.text[:300]}")
            return {"category": "error", "reasons": "", "pitch": ""}

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        try:
            parsed = json.loads(content)
        except Exception:
            logger.error(f"DeepSeek returned non-JSON content: {content[:300]}")
            return {"category": "error", "reasons": "", "pitch": ""}

        return {
            "category": parsed.get("category", "could_fit"),
            "reasons": parsed.get("reasons", ""),
            "pitch": parsed.get("pitch", ""),
        }
    except Exception as e:
        # Hide specifics from end-user; log internally
        logger.error(f"DeepSeek error (sid={sid}): {repr(e)}")
        return {"category": "error", "reasons": "", "pitch": ""}


def stream_deepseek(user_text: str, sid: str) -> Generator[str, None, None]:
    """
    Streaming generator with timeouts/retries.
    If it fails mid-stream, yield a short warning and stop.
    """
    prompt = (
        f"ACE knowledge:\n{_knowledge_head()}\n\n"
        f"Lead details:\nDescription: {user_text}\n\n"
        "Task: Respond conversationally in chunks. Slovenian."
    )

    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are ACE qualification AI. Answer in Slovenian."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "stream": True,
    }

    try:
        s = _get_session()
        with s.post(
            DEEPSEEK_URL,
            headers=_headers(),
            json=body,
            stream=True,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        ) as r:
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
                        # swallow malformed SSE chunk
                        continue
    except Exception as e:
        logger.error(f"DeepSeek streaming error (sid={sid}): {repr(e)}")
        yield "⚠️ Težava z živim pretokom. Pošlji sporočilo še enkrat ali nadaljujva z navadnim odgovorom."
