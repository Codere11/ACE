import os, json, requests, re
from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

# DeepSeek settings
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-ac86f23b7a524c8cb0f42b4f62a010b2")
AGENT_PHONE = "069 735 957"

# Load ACE config JSON
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../data/conversation_config.json")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        ACE_CONFIG = json.load(f)
except Exception as e:
    ACE_CONFIG = {"error": f"Could not load config: {e}"}

def _json_from_text(txt: str) -> Dict[str, Any]:
    """Tries to extract JSON object from DeepSeek response."""
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

        # Prompt includes ACE config JSON
        prompt = (
            f"ACE knowledge:\n{json.dumps(ACE_CONFIG, indent=2)}\n\n"
            f"Lead details:\nBudget: {budget}\nPlatform: {platform}\nCompany: {company_desc}\n\n"
            "Task: Based on ACE knowledge and the lead details, classify the lead. "
            "Respond as JSON with keys: category (good_fit, could_fit, bad_fit), reasons (string), pitch (string)."
        )

        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "You are ACE qualification AI."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        parsed = {}
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=body, timeout=12)
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = _json_from_text(content)
        except Exception as e:
            parsed = {"category": "could_fit", "reasons": str(e), "pitch": "Sorry, something went wrong."}

        category = parsed.get("category", "could_fit")
        pitch = parsed.get("pitch", "")
        reasons = parsed.get("reasons", "")

        if category == "good_fit":
            final_msg = (
                f"{pitch} I believe ACE would be a great fit because {reasons}. "
                f"A notification has been sent to our staff and will speak to you in 2 minutes at most! "
                f"If for some reason they don't, you can contact me directly at {AGENT_PHONE}."
            )
        elif category == "could_fit":
            final_msg = (
                f"{pitch} We can discuss partnership. "
                f"A notification has been sent to our staff and will speak to you in 2 minutes at most! "
                f"If for some reason they don't, you can contact me directly at {AGENT_PHONE}."
            )
        else:  # bad_fit
            final_msg = (
                f"Perhaps ACE wouldn't be a good fit for you because {reasons}. "
                f"But if you believe I've made an error you can tell me or contact maks.ponikvar@gmail.com "
                f"and he will see it first thing in the morning!"
            )

        # ✅ Force story_complete flag so frontend unlocks typing
        dispatcher.utter_message(
            text=final_msg,
            custom={"story_complete": True}
        )

        return []
