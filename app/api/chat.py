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

SESSION_STATE = {}

@router.post("/")
def chat(req: ChatRequest):
    # log user message
    sessions.add_chat(req.sid, "user", req.message)

    # ensure lead exists
    leads = lead_service.get_all_leads()
    existing = next((l for l in leads if l.id == req.sid), None)

    if not existing:
        provisional = Lead(
            id=req.sid,
            name="Unknown",
            industry="Unknown",
            score=50,
            stage="Pogovori",
            compatibility=True,
            interest="Medium",
            phone=False,
            email=False,
            adsExp=False,
            lastMessage=req.message,
            lastSeenSec=int(time.time()),
            notes=""
        )
        lead_service.add_lead(provisional)
        print(f"[DEBUG] Provisional lead created for sid={req.sid}")
    else:
        # always update lastMessage with the user message
        existing.lastMessage = req.message
        existing.lastSeenSec = int(time.time())

    # run conversation flow
    reply = handle_chat(req, SESSION_STATE)

    if reply.get("reply"):
        sessions.add_chat(req.sid, "assistant", reply["reply"])

    return reply

@router.post("/survey")
def survey(data: dict):
    sid = data.get("sid")
    industry = data.get("industry", "")
    budget = data.get("budget", "")
    experience = data.get("experience", "")
    question1 = data.get("question1", "")
    question2 = data.get("question2", "")

    combined = (
        f"Industrija: {industry} | "
        f"Proračun: {budget} | "
        f"Izkušnje: {experience} | "
        f"Kako pridobivate stranke: {question1} | "
        f"Kdo odgovarja leadom: {question2}"
    )

    result = deepseek_service.run_deepseek(combined, sid)

    existing = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
    if existing:
        existing.score = 90 if result["category"] == "good_fit" else 70 if result["category"] == "could_fit" else 40
        existing.stage = (
            "Interested" if result["category"] == "good_fit"
            else "Discovery" if result["category"] == "could_fit"
            else "Cold"
        )
        existing.interest = (
            "High" if result["category"] == "good_fit"
            else "Medium" if result["category"] == "could_fit"
            else "Low"
        )
        existing.lastSeenSec = int(time.time())

        # ✅ set lastMessage so dashboard shows Q1/Q2
        if question1 or question2:
            existing.lastMessage = f"{question1} | {question2}"
        else:
            existing.lastMessage = combined

        # ✅ merge notes
        notes_parts = []
        if question1:
            notes_parts.append(f"Q1: {question1}")
        if question2:
            notes_parts.append(f"Q2: {question2}")
        if result.get("reasons"):
            notes_parts.append(f"Reasons: {result['reasons']}")
        existing.notes = " | ".join(notes_parts)

    else:
        lead_service.ingest_from_deepseek(combined, result, sid)

    reply = f"{result['pitch']} Razlogi: {result['reasons']}"
    sessions.add_chat(sid, "assistant", reply)

    return {
        "reply": reply,
        "ui": {"story_complete": True, "openInput": True},
        "chatMode": "open",
        "storyComplete": True
    }

@router.post("/stream")
def chat_stream(req: ChatRequest):
    sessions.add_chat(req.sid, "user", req.message)

    def event_generator():
        buffer = ""
        for chunk in deepseek_service.stream_deepseek(req.message, req.sid):
            buffer += chunk
            yield chunk
        sessions.add_chat(req.sid, "assistant", buffer)

    return StreamingResponse(event_generator(), media_type="text/plain")
