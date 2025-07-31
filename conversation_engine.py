import json
import re

class ConversationEngine:
    def __init__(self, config_path="data/conversation_config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get_config(self):
        return self.config


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
        # Match variants of each listing name (e.g., vila, vilo, vile, hiša, hišo, etc.)
        base = key[:-1] if key.endswith("a") else key  # crude fallback stem
        pattern = r"\b" + re.escape(base) + r"\w*\b"

        if re.search(pattern, text):
            return listing.get("image")

    return None