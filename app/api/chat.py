# app/api/chat.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.core import sessions
from app.services.flow_service import handle_chat
from app.services import deepseek_service, lead_service
from app.models.lead import Lead
from app.models.chat import ChatRequest
import time

router = APIRouter()

class ChatRequestBody(BaseModel):
    sid: str
    message: str

SESSION_STATE = {}

def _now():
    return int(time.time())

def _log(prefix: str, sid: str, rid: str, msg: str = "", extra: dict | None = None):
    base = f"[CHAT] {prefix} sid={sid} rid={rid}"
    if msg:
        base += f" msg='{msg}'"
    if extra:
        base += f" {extra}"
    print(base)

@router.post("/")
def chat(req: ChatRequestBody, request: Request):
    rid = request.headers.get("x-req-id", "-")
    _log("IN", req.sid, rid, req.message)

    # log user message (per-sid)
    sessions.add_chat(req.sid, "user", req.message)

    # ensure lead exists / update lastMessage
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
            lastSeenSec=_now(),
            notes=""
        )
        lead_service.add_lead(provisional)
        _log("lead_created", req.sid, rid)
    else:
        existing.lastMessage = req.message
        existing.lastSeenSec = _now()
        _log("lead_updated", req.sid, rid, extra={"lastMessage": req.message})

    # run conversation flow
    reply = handle_chat(ChatRequest(sid=req.sid, message=req.message), SESSION_STATE)

    # log assistant reply
    if reply.get("reply") is not None:
        sessions.add_chat(req.sid, "assistant", reply["reply"])

    _log("OUT", req.sid, rid, extra={"chatMode": reply.get("chatMode"), "ui": reply.get("ui")})
    return reply

@router.post("/survey")
def survey(data: dict, request: Request):
    """
    This endpoint is presumably called by your UI after collecting 'dual' inputs.
    Previously it just returned a static 'Hvala...' and never hit the flow.

    Change: push the session directly to the 'survey_done' action node and invoke
    the flow handler so DeepSeek executes immediately using the saved answers.
    """
    rid = request.headers.get("x-req-id", "-")
    sid = data.get("sid")
    question1 = data.get("question1", "")
    question2 = data.get("question2", "")

    _log("SURVEY_IN", sid, rid, extra={"q1": question1, "q2": question2})

    # upsert + merge notes
    existing = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
    if existing:
        existing.lastSeenSec = _now()
        # keep lastMessage as a compact summary of both answers
        if question1 or question2:
            existing.lastMessage = f"{question1} | {question2}".strip(" |")
        # merge notes in a readable way
        pieces = []
        if question1:
            pieces.append(f"Q1: {question1}")
        if question2:
            pieces.append(f"Q2: {question2}")
        if pieces:
            existing.notes = " | ".join([p for p in [existing.notes, " | ".join(pieces)] if p]).strip(" |")
    else:
        provisional = Lead(
            id=sid,
            name="Unknown",
            industry="Unknown",
            score=50,
            stage="Pogovori",
            compatibility=True,
            interest="Medium",
            phone=False,
            email=False,
            adsExp=False,
            lastMessage=f"{question1} | {question2}".strip(" |"),
            lastSeenSec=_now(),
            notes=" | ".join([p for p in [f"Q1: {question1}" if question1 else "", f"Q2: {question2}" if question2 else ""] if p])
        )
        lead_service.add_lead(provisional)

    # 🔴 Critical: move the flow to the action node and execute it now
    SESSION_STATE[sid] = {"node": "survey_done"}
    reply = handle_chat(ChatRequest(sid=sid, message=""), SESSION_STATE)

    # Log assistant reply to chat history (the root '/' route also logs, but this endpoint is separate)
    if reply.get("reply") is not None:
        sessions.add_chat(sid, "assistant", reply["reply"])

    _log("SURVEY_OUT", sid, rid, extra={"triggered": "deepseek", "ui": reply.get("ui")})
    return reply

@router.post("/stream")
def chat_stream(req: ChatRequestBody, request: Request):
    rid = request.headers.get("x-req-id", "-")
    _log("STREAM_IN", req.sid, rid, req.message)

    sessions.add_chat(req.sid, "user", req.message)

    def event_generator():
        buffer = ""
        for chunk in deepseek_service.stream_deepseek(req.message, req.sid):
            buffer += chunk
            yield chunk
        sessions.add_chat(req.sid, "assistant", buffer)
        _log("STREAM_DONE", req.sid, rid)

    return StreamingResponse(event_generator(), media_type="text/plain")
