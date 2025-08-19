import os, json, requests
from app.core.config import ACE_CONFIG, DEEPSEEK_API_KEY, DEEPSEEK_URL, DEEPSEEK_MODEL
from app.core.logger import logger

def run_deepseek(user_text: str, sid: str) -> dict:
    """
    Blocking call to DeepSeek for lead classification.
    Returns structured dict {category, reasons, pitch}.
    """
    prompt = (
        f"ACE knowledge:\n{json.dumps(ACE_CONFIG, indent=2)}\n\n"
        f"Lead details:\nDescription: {user_text}\n\n"
        "Task: Classify this lead. Respond as JSON with keys: "
        "category (good_fit, could_fit, bad_fit), reasons (string), pitch (string)."
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are ACE qualification AI."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        resp = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=12)
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        try:
            parsed = json.loads(content)
        except Exception:
            logger.error(f"DeepSeek returned non-JSON: {content}")
            parsed = {}

        return {
            "category": parsed.get("category", "could_fit"),
            "reasons": parsed.get("reasons", ""),
            "pitch": parsed.get("pitch", "")
        }

    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return {"category": "error", "reasons": str(e), "pitch": ""}


def stream_deepseek(user_text: str, sid: str):
    """
    Generator that streams conversational tokens from DeepSeek API.
    """
    prompt = (
        f"ACE knowledge:\n{json.dumps(ACE_CONFIG, indent=2)}\n\n"
        f"Lead details:\nDescription: {user_text}\n\n"
        "Task: Respond conversationally in chunks."
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are ACE qualification AI."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "stream": True
    }

    try:
        with requests.post(DEEPSEEK_URL, headers=headers, json=body, stream=True) as r:
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
        logger.error(f"DeepSeek streaming error: {e}")
        yield "⚠️ Error streaming from DeepSeek."
