from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nlu.deepseek_provider import DeepSeekProvider
from conversation_engine import ConversationEngine, flatten_json_to_prompt, detect_property_image
from classifiers.bert_classifier import classify_stage
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

provider = DeepSeekProvider()
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

@app.post("/chat")
def chat(req: ChatRequest):
    global chat_history, active_image
    user_input = req.message
    stage = classify_stage(user_input)

    chat_history.append({"role": "user", "content": user_input})

    image_name = detect_property_image(user_input, config)

    if image_name:
        active_image = image_name
        chat_history.append({
            "role": "system",
            "content": f"Uporabnik želi videti fotografijo: {image_name}."
        })

    try:
        reply = provider.get_response(chat_history)
    except Exception:
        return {"reply": "Napaka pri pridobivanju odgovora."}

    chat_history.append({"role": "assistant", "content": reply})

    return {
        "reply": reply,
        "stage": stage,
        "imageUrl": f"/{active_image}" if image_name else None
    }
