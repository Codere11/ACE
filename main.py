import requests, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ace")

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    sid: str

def _send_rasa(sid: str, message: str) -> List[Dict[str, Any]]:
    try:
        r = requests.post(RASA_URL, json={"sender": sid, "message": message}, timeout=8)
        if r.ok:
            return r.json() or []
    except Exception as e:
        logger.error(f"Rasa error: {e}")
    return []

@app.post("/chat")
def chat(req: ChatRequest):
    events = _send_rasa(req.sid, req.message)

    reply = None
    ui_block = None
    story_done = False

    for ev in events:
        if ev.get("text"):
            reply = ev["text"]
        if ev.get("custom"):
            ui_block = ev["custom"]
        if ev.get("buttons") and not ui_block:
            ui_block = {"type": "choices", "buttons": ev["buttons"]}
        if ev.get("custom", {}).get("story_complete"):
            story_done = True

    return {
        "reply": reply,
        "quickReplies": ui_block.get("buttons") if ui_block and ui_block.get("type") == "choices" else None,
        "ui": ui_block,
        "chatMode": "open" if story_done else "guided",
        "storyComplete": story_done,
        "imageUrl": None
    }
