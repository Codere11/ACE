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
        # Fallback to the static config
        for topic in self.config.get("topics", []):
            if topic["topic"] == intent_name:
                return topic["responses"][0]
        return None


def flatten_json_to_prompt(json_data):
    agency_name = json_data["metadata"]["agency_name"]

    prompt = f"""
You are a friendly, smart AI agent working for \"{agency_name}\" — a tech-first agency that installs intelligent sales agents (like yourself) on client websites.

Your job is to explain how Omsoft ACE works, why it’s better than traditional landing pages, and help guide potential clients through their questions, doubts, and interest in using the product.

RULES:
- Never make up information.
- Use the responses below as your source of truth.
- If you're unsure, say \"I'm not sure about that.\"
- Never discuss pricing unless it's included below.
- If the user asks for a demo, tell them they are already speaking to the demo agent.
- You should behave as if the campaign manager (e.g. Maks) will read the chat.
- If someone wants to be contacted, say: \"V redu, posredujem Maksu.\" — no extra explanation needed.

TOPICS:
"""

    for topic in json_data.get("topics", []):
        prompt += f"\nTopic: {topic['topic'].capitalize()}\n"
        for example, response in zip(topic["examples"], topic["responses"]):
            prompt += f"- Q: {example}\n  A: {response}\n"

    prompt += """

IMPORTANT:
If a user asks to see a specific feature (like a dashboard, chat popup, or campaign view), say:  
\"Tukaj je fotografija, ki vas zanima 👇\"  
The system will automatically display the correct image below your message. Never describe the image or say what you can't do.
"""
    return prompt.strip()


def detect_property_image(text: str, config: dict) -> str | None:
    """Detect if the user is asking to see a particular visual (dashboard, chat popup, etc)."""
    text = text.lower()
    for key, asset in config.get("visuals", {}).items():
        base = key[:-1] if key.endswith("a") else key
        pattern = r"\b" + re.escape(base) + r"\w*\b"
        if re.search(pattern, text):
            return asset.get("image")
    return None
