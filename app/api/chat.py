# app/api/chat.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.core import sessions
from app.services.flow_service import handle_chat
from app.services import deepseek_service, lead_service
from app.models.lead import Lead
import time

router = APIRouter()


class ChatRequest(BaseModel):
    sid: str
    message: str


# in-memory state per session for scripted flow
SESSION_STATE = {}


@router.post("/")
def chat(req: ChatRequest):
    # log user message
    sessions.add_chat("user", req.message)

    # ✅ create provisional lead if not already present
    leads = lead_service.get_all_leads()
    if not any(l.id == req.sid for l in leads):
        provisional = Lead(
            id=req.sid,                      # unique id tied to session
            name="Unknown",
            industry="Unknown",
            score=50,
            stage="Pogovori",                # provisional stage
            compatibility=True,
            interest="Medium",
            phone=False,
            email=False,
            adsExp=False,
            lastMessage=req.message,
            lastSeenSec=int(time.time()),
            notes=""
        )
        lead_service.add_lead(provisional)   # ✅ use service method instead of importing _leads
        print(f"[DEBUG] Provisional lead created for sid={req.sid}")

    # run conversation flow (guided JSON + DeepSeek trigger)
    reply = handle_chat(req, SESSION_STATE)

    # log assistant reply
    if reply.get("reply"):
        sessions.add_chat("assistant", reply["reply"])

    return reply


@router.post("/survey")
def survey(data: dict):
    sid = data.get("sid")
    industry = data.get("industry", "")
    budget = data.get("budget", "")
    experience = data.get("experience", "")

    combined = f"Kako pridobivate stranke: {industry} | Kdo odgovarja leadom: {experience} | Proračun: {budget}"

    # Run DeepSeek classification
    result = deepseek_service.run_deepseek(combined, sid)

    # ✅ update existing provisional lead if found
    existing = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
    if existing:
        existing.score = 90 if result["category"] == "good_fit" else 70 if result["category"] == "could_fit" else 40
        existing.stage = "Interested" if result["category"] == "good_fit" else "Discovery" if result["category"] == "could_fit" else "Cold"
        existing.interest = "High" if result["category"] == "good_fit" else "Medium" if result["category"] == "could_fit" else "Low"
        existing.lastMessage = combined
        existing.lastSeenSec = int(time.time())
        existing.notes = result.get("reasons", "")
    else:
        # fallback: ingest normally
        lead_service.ingest_from_deepseek(combined, result, sid)

    reply = f"{result['pitch']} Razlogi: {result['reasons']}"

    # log assistant reply
    sessions.add_chat("assistant", reply)

    return {
        "reply": reply,
        "ui": {"story_complete": True, "openInput": True},
        "chatMode": "open",
        "storyComplete": True
    }


@router.post("/stream")
def chat_stream(req: ChatRequest):
    # log user message
    sessions.add_chat("user", req.message)

    def event_generator():
        buffer = ""
        for chunk in deepseek_service.stream_deepseek(req.message, req.sid):
            buffer += chunk
            yield chunk
        # log the full streamed reply once done
        sessions.add_chat("assistant", buffer)

    return StreamingResponse(event_generator(), media_type="text/plain")
