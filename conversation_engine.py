import json
import re
from nlu.deepseek_provider import DeepSeekProvider


class ConversationEngine:
    def __init__(self, config_path="data/conversation_config.json", rasa_responses_path="rasa/responses.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            self.llm = DeepSeekProvider()


        try:
            with open(rasa_responses_path, "r", encoding="utf-8") as f:
                self.rasa_responses = json.load(f)
        except FileNotFoundError:
            self.rasa_responses = {}

    def get_response(self, chat_history):
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history[-20:]]
        return self.llm.get_response(messages)


    def get_config(self):
        return self.config

    def get_reply_by_intent(self, intent_name: str) -> str | None:
        # First try to find a Rasa-defined utterance
        if intent_name in self.rasa_responses:
            return self.rasa_responses[intent_name]
        # Fallback to the static prompt config (DeepSeek JSON)
        for topic in self.config.get("topics", []):
            if topic["topic"] == intent_name:
                return topic["responses"][0]
        return None


def flatten_json_to_prompt(json_data):
    agency_name = json_data["metadata"]["agency_name"]
    contact_url = json_data["metadata"]["contact_url"]

    prompt = f"""
You are a friendly and knowledgeable real estate assistant working for "{agency_name}".
Use ONLY the information below to answer user questions. If you're not sure, say "I'm not sure" instead of guessing.
Never invent features or prices.

AGENCY INFO:
"""

    for topic in json_data["topics"]:
        prompt += f"\nTopic: {topic['topic'].capitalize()}\n"
        for example, response in zip(topic["examples"], topic["responses"]):
            prompt += f"- Q: {example}\n  A: {response}\n"

    prompt += f"""
Contact or inquire here: {contact_url}

IMPORTANT:
If a user asks to see a specific listing (e.g., 'apartma', 'vila', 'hiša'), do not describe the photo or apologize.
Simply say: "Tukaj je fotografija, ki vas zanima 👇"

The system automatically displays the correct image below your message. Do not comment on your ability to show images.
"""
    return prompt.strip()


def detect_property_image(text: str, config: dict) -> str | None:
    text = text.lower()
    for key, listing in config.get("listings", {}).items():
        base = key[:-1] if key.endswith("a") else key
        pattern = r"\b" + re.escape(base) + r"\w*\b"
        if re.search(pattern, text):
            return listing.get("image")
    return None

provider = ConversationEngine()
