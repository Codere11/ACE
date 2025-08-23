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
    """
    Save survey answers (industry, budget, experience, Q1, Q2) into lead,
    but do NOT call DeepSeek yet. DeepSeek runs later via flow node with action=deepseek_score.
    """
    sid = data.get("sid")
    industry = data.get("industry", "")
    budget = data.get("budget", "")
    experience = data.get("experience", "")
    question1 = data.get("question1", "")
    question2 = data.get("question2", "")

    existing = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
    if existing:
        existing.lastSeenSec = int(time.time())
        if question1 or question2:
            existing.lastMessage = f"{question1} | {question2}"

        # merge notes
        notes_parts = []
        if question1:
            notes_parts.append(f"Q1: {question1}")
        if question2:
            notes_parts.append(f"Q2: {question2}")
        existing.notes = " | ".join(notes_parts)

    else:
        # provisional lead if needed
        provisional = Lead(
            id=sid,
            name="Unknown",
            industry=industry or "Unknown",
            score=50,
            stage="Pogovori",
            compatibility=True,
            interest="Medium",
            phone=False,
            email=False,
            adsExp=False,
            lastMessage=f"{question1} | {question2}",
            lastSeenSec=int(time.time()),
            notes=f"Q1: {question1} | Q2: {question2}"
        )
        lead_service.add_lead(provisional)

    # reply just acknowledges answers
    reply = "Hvala za odgovore 🙏. Nadaljujmo..."

    sessions.add_chat(sid, "assistant", reply)

    return {
        "reply": reply,
        "ui": {"story_complete": False, "openInput": False},
        "chatMode": "guided",
        "storyComplete": False
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
