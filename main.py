from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from conversation_engine import ConversationEngine, flatten_json_to_prompt, detect_property_image
from classifiers.bert_classifier import classify_stage
from typing import Optional
import requests
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

engine = ConversationEngine()
config = engine.get_config()
grounding_prompt = flatten_json_to_prompt(config)

chat_history = [
    {
        "role": "system",
        "content": grounding_prompt + "\n\nOdgovarjaj v slovenščini. Vedno bodi prijazen, profesionalen in ne delaj napak. Tvoja naloga je pomagati uporabniku najti pravo nepremičnino tako, da odgovarjaš na vprašanja, postavljaš subtilna vprašanja o željah uporabnika (npr. proračun, lokacija, velikost) in povezuješ z nepremičninskimi svetovalci, če je potrebno. Kadar je primerno, lahko predlagaš prikaz slike ustrezne nepremičnine."
    }
]

active_image: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
RASA_PARSE_URL = "http://localhost:5005/model/parse"

@app.post("/chat")
def chat(req: ChatRequest):
    global chat_history, active_image
    user_input = req.message
    logger.info(f"Received user input: {user_input}")

    stage = classify_stage(user_input)
    logger.info(f"Classified stage: {stage}")

    chat_history.append({"role": "user", "content": user_input})

    image_name = detect_property_image(user_input, config)
    logger.info(f"Detected image: {image_name}")

    if image_name:
        active_image = image_name
        chat_history.append({
            "role": "system",
            "content": f"Uporabnik želi videti fotografijo: {image_name}."
        })

    # Ask Rasa for response
    reply = None
    try:
        rasa_response = requests.post(RASA_URL, json={"sender": "user", "message": user_input})
        logger.info(f"Rasa response status: {rasa_response.status_code}")
        logger.info(f"Rasa response body: {rasa_response.text}")
        rasa_reply_data = rasa_response.json()
        if rasa_reply_data and "text" in rasa_reply_data[0]:
            reply = rasa_reply_data[0]["text"]
    except Exception as e:
        logger.error(f"Rasa response failed: {e}")

    # Fallback to DeepSeek if Rasa gives no reply
    if not reply:
        logger.info("No Rasa reply — falling back to DeepSeek.")
        try:
            reply = engine.get_response(chat_history)
        except Exception as e:
            logger.error(f"DeepSeek failed: {e}")
            reply = "Napaka pri pridobivanju odgovora."

    chat_history.append({"role": "assistant", "content": reply})

    with open("chat_logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "user": user_input,
            "bot": reply,
            "stage": stage,
            "image": active_image
            }, ensure_ascii=False) + "\n")

    return {
        "reply": reply,
        "stage": stage,
        "imageUrl": f"/{active_image}" if image_name else None
    }
