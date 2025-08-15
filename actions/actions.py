import os, json, re, time, requests
from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import EventType

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-ac86f23b7a524c8cb0f42b4f62a010b2")  # set your key in env
AGENT_NOTIFY_URL = os.getenv("AGENT_NOTIFY_URL")
AGENT_PHONE = os.getenv("AGENT_PHONE", "069 735 957")

def _notify_agent(payload: Dict[str, Any]) -> None:
    try:
        if AGENT_NOTIFY_URL:
            requests.post(AGENT_NOTIFY_URL, json=payload, timeout=4)
        else:
            with open("agent_notifications.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _json_from_text(txt: str) -> Dict[str, Any]:
    if not txt:
        return {}
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", txt)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
    return {}

def _deepseek_verdict(industry: str, budget: str, experience: str) -> Dict[str, Any]:
    """Return { qualified: bool, assistant_text: str, short_reason: str }"""
    fallback_text = (
        "Since your business is heavily lead-reliant and you have some advertising experience, "
        "I believe ACE would be the right fit for you!"
    )
    def heuristic() -> Dict[str, Any]:
        qual = (budget in ("3k_10k", "gt_10k")) or bool(experience.strip())
        return {"qualified": qual, "assistant_text": fallback_text, "short_reason": "heuristic"}

    if not DEEPSEEK_API_KEY:
        return heuristic()

    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        system = (
            "You are ACE, an advanced lead-generation assistant. "
            "Decide if ACE is a good fit (qualified). "
            "Respond ONLY as compact JSON with keys: qualified (boolean), short_reason (string), "
            "assistant_text (string; 1–2 sentences)."
        )
        user = (
            f"- Industry: {industry or 'unknown'}\n"
            f"- Budget: {budget or 'unknown'} (lt_1k, 1k_3k, 3k_10k, gt_10k)\n"
            f"- Experience: {experience or 'unknown'}"
        )
        body = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role":"system","content":system},{"role":"user","content":user}],
            "temperature": 0.2, "max_tokens": 160
        }
        r = requests.post(DEEPSEEK_API_URL, headers=headers, json=body, timeout=10)
        if not r.ok:
            return heuristic()
        data = r.json()
        text = (data.get("choices",[{}])[0].get("message",{}) or {}).get("content","") or ""
        parsed = _json_from_text(text)
        if "qualified" not in parsed:
            return heuristic()
        return {
            "qualified": bool(parsed.get("qualified")),
            "assistant_text": (str(parsed.get("assistant_text") or fallback_text).strip() or fallback_text),
            "short_reason": str(parsed.get("short_reason") or ""),
        }
    except Exception:
        return heuristic()

class ActionDeepseekAssessAndNotify(Action):
    def name(self) -> Text:
        return "action_deepseek_assess_and_notify"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:
        industry = (tracker.get_slot("industry") or "").strip()
        budget = (tracker.get_slot("budget") or "").strip()
        experience = (tracker.get_slot("experience") or "").strip()

        verdict = _deepseek_verdict(industry, budget, experience)
        qualified = bool(verdict.get("qualified"))
        assessment = verdict.get("assistant_text") or ""

        _notify_agent({
            "ts": int(time.time()),
            "sid": tracker.sender_id,
            "industry": industry,
            "budget": budget,
            "experience": experience,
            "assessment": assessment,
            "qualified": qualified,
            "source": "rasa_action_deepseek_assess_and_notify",
        })

        # Signal FE story completion (keeps normal text separate)
        dispatcher.utter_message(json_message={"story_complete": True, "qualified": qualified})

        if qualified:
            final_msg = (
                f"{assessment} Our agent will contact you in a minute at-most.\n\n"
                f"If it takes too long, he is probably on his lunch break — you can SMS or call him on {AGENT_PHONE}."
            )
        else:
            final_msg = f"{assessment} If you’d still like a quick human check, you can SMS or call {AGENT_PHONE}."

        dispatcher.utter_message(text=final_msg)
        return []
