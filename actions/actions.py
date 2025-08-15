import os, json, requests, re, time
from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-ac86f23b7a524c8cb0f42b4f62a010b2")
AGENT_PHONE = "069 735 957"

def _json_from_text(txt: str) -> Dict[str, Any]:
    try:
        return json.loads(txt)
    except:
        match = re.search(r"\{[\s\S]*\}", txt)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                return {}
    return {}

class ActionDeepseekScore(Action):
    def name(self) -> Text:
        return "action_deepseek_score"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List[Dict]:
        budget = tracker.get_slot("budget") or ""
        platform = tracker.get_slot("platform") or ""
        company_desc = tracker.get_slot("company_description") or ""

        prompt = (
            f"Budget: {budget}\n"
            f"Platform: {platform}\n"
            f"Company: {company_desc}\n\n"
            "Decide: is ACE a good fit? Respond as JSON with keys: category (good_fit, could_fit, bad_fit), reasons (string), pitch (string)."
        )

        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "system", "content": "You are ACE qualification AI."},
                         {"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=body, timeout=10)
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = _json_from_text(content)
        except:
            parsed = {}

        category = parsed.get("category", "could_fit")
        pitch = parsed.get("pitch", "")
        reasons = parsed.get("reasons", "")

        if category == "good_fit":
            final_msg = f"{pitch} I believe ACE would be a great fit because {reasons}. A notification has been sent to our staff and will speak to you in 2 minutes at most! If for some reason they don't, you can contact me directly at {AGENT_PHONE}."
        elif category == "could_fit":
            final_msg = f"{pitch} We can discuss partnership. A notification has been sent to our staff and will speak to you in 2 minutes at most! If for some reason they don't, you can contact me directly at {AGENT_PHONE}."
        else:
            final_msg = f"Perhaps ACE wouldn't be a good fit for you because {reasons}. But if you believe I've made an error you can tell me or contact maks.ponikvar@gmail.com and he will see it first thing in the morning!"

        dispatcher.utter_message(text=final_msg)
        dispatcher.utter_message(json_message={"story_complete": True})
        return []
