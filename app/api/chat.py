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
import uuid
import hashlib

router = APIRouter()

# ---------- Models ----------
class ChatRequestBody(BaseModel):
    sid: str | None = None
    message: str

# ---------- In-memory flow/session state ----------
SESSION_STATE: dict[str, dict] = {}

# ---------- Utils ----------
def _now() -> int:
    return int(time.time())

def _log(prefix: str, sid: str, rid: str, msg: str = "", extra: dict | None = None):
    base = f"[CHAT] {prefix} sid={sid} rid={rid}"
    if msg:
        base += f" msg='{msg}'"
    if extra is not None:
        base += f" {extra}"
    print(base)

def _normalize_sid(raw_sid: str | None) -> str | None:
    s = (raw_sid or "").strip()
    if not s or s.lower() in {"undefined", "null", "(null)", "(undefined)"}:
        return None
    if len(s) < 8:  # safety
        return None
    return s

def _fingerprint_sid(request: Request) -> str:
    # Stable per device/browser without cookies or storage.
    ip = (request.client.host if request.client else "") or ""
    ua = request.headers.get("user-agent", "")
    raw = f"{ip}|{ua}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def _resolve_sid_with_debug(request: Request, body_sid: str | None) -> tuple[str, dict]:
    """
    Return (final_sid, debug_info) without changing any existing behavior,
    but with full introspection so we can see what's happening.
    Rule:
      1) use valid body sid if provided
      2) else fingerprint(IP+UA)
      3) else random uuid (very rare)
    """
    cookie_sid = None  # we are not using cookies here, but log slot for clarity

    raw_body_sid = body_sid
    norm_body_sid = _normalize_sid(raw_body_sid)
    fp_sid = _fingerprint_sid(request)
    final_sid = norm_body_sid or fp_sid or str(uuid.uuid4())

    debug = {
        "raw_body_sid": raw_body_sid,
        "norm_body_sid": norm_body_sid,
        "cookie_sid": cookie_sid,
        "fingerprint_sid": fp_sid,
        "final_sid": final_sid,
        "client_ip": (request.client.host if request.client else None),
        "user_agent": request.headers.get("user-agent", None),
        "path": request.url.path,
        "method": request.method,
    }
    return final_sid, debug

def _lead_exists(sid: str) -> bool:
    return next((l for l in lead_service.get_all_leads() if l.id == sid), None) is not None

def _sid_snapshot(sid: str) -> dict:
    """Capture current state around this sid for debugging."""
    st = SESSION_STATE.get(sid, {})
    leads = lead_service.get_all_leads()
    exists = next((l for l in leads if l.id == sid), None)
    return {
        "session_state": st.copy(),
        "lead_exists": exists is not None,
        "leads_total": len(leads),
        "lead_lastMessage": getattr(exists, "lastMessage", None) if exists else None,
        "lead_notes": getattr(exists, "notes", None) if exists else None,
    }

# ---------- Endpoints ----------
@router.post("/")
def chat(req: ChatRequestBody, request: Request):
    rid = request.headers.get("x-req-id", "-")

    # Resolve SID + emit pre-processing debug
    sid_final, debug = _resolve_sid_with_debug(request, req.sid)
    _log("SID_DEBUG_IN", sid_final, rid, extra=debug)

    # Log user message into per-sid transcript
    sessions.add_chat(sid_final, "user", req.message)

    # Ensure lead exists / update lastMessage
    existing = next((l for l in lead_service.get_all_leads() if l.id == sid_final), None)
    if not existing:
        provisional = Lead(
            id=sid_final,
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
        _log("lead_created", sid_final, rid)
    else:
        existing.lastMessage = req.message
        existing.lastSeenSec = _now()
        _log("lead_updated", sid_final, rid, extra={"lastMessage": req.message})

    # Snapshot before flow
    _log("SID_SNAPSHOT_PRE_FLOW", sid_final, rid, extra=_sid_snapshot(sid_final))

    # Run conversation flow
    reply = handle_chat(ChatRequest(sid=sid_final, message=req.message), SESSION_STATE)

    # Log assistant reply
    if reply.get("reply") is not None:
        sessions.add_chat(sid_final, "assistant", reply["reply"])

    # Snapshot after flow
    post = _sid_snapshot(sid_final)
    post.update({"chatMode": reply.get("chatMode"), "ui": reply.get("ui")})
    _log("SID_SNAPSHOT_POST_FLOW", sid_final, rid, extra=post)

    _log("OUT", sid_final, rid, extra={"chatMode": reply.get("chatMode"), "ui": reply.get("ui")})
    return reply

@router.post("/survey")
def survey(data: dict, request: Request):
    rid = request.headers.get("x-req-id", "-")

    sid_final, debug = _resolve_sid_with_debug(request, data.get("sid"))
    _log("SID_DEBUG_SURVEY_IN", sid_final, rid, extra=debug)

    q1 = data.get("question1", "")
    q2 = data.get("question2", "")

    # Upsert + merge notes
    existing = next((l for l in lead_service.get_all_leads() if l.id == sid_final), None)
    if existing:
        existing.lastSeenSec = _now()
        if q1 or q2:
            existing.lastMessage = f"{q1} | {q2}".strip(" |")
        pieces = []
        if q1: pieces.append(f"Q1: {q1}")
        if q2: pieces.append(f"Q2: {q2}")
        if pieces:
            existing.notes = " | ".join([p for p in [existing.notes, " | ".join(pieces)] if p]).strip(" |")
    else:
        provisional = Lead(
            id=sid_final,
            name="Unknown",
            industry="Unknown",
            score=50,
            stage="Pogovori",
            compatibility=True,
            interest="Medium",
            phone=False,
            email=False,
            adsExp=False,
            lastMessage=f"{q1} | {q2}".strip(" |"),
            lastSeenSec=_now(),
            notes=" | ".join([p for p in [f"Q1: {q1}" if q1 else "", f"Q2: {q2}" if q2 else ""] if p])
        )
        lead_service.add_lead(provisional)
        _log("lead_created", sid_final, rid, extra={"source": "survey"})

    # Snapshot before action
    _log("SID_SNAPSHOT_PRE_DEEPSEEK", sid_final, rid, extra=_sid_snapshot(sid_final))

    # Move to action node and execute immediately (DeepSeek)
    SESSION_STATE[sid_final] = {"node": "survey_done"}
    reply = handle_chat(ChatRequest(sid=sid_final, message=""), SESSION_STATE)

    # Log assistant reply
    if reply.get("reply") is not None:
        sessions.add_chat(sid_final, "assistant", reply["reply"])

    # Snapshot after action
    post = _sid_snapshot(sid_final)
    post.update({"chatMode": reply.get("chatMode"), "ui": reply.get("ui")})
    _log("SID_SNAPSHOT_POST_DEEPSEEK", sid_final, rid, extra=post)

    _log("SURVEY_OUT", sid_final, rid, extra={"triggered": "deepseek", "ui": reply.get("ui")})
    return reply

@router.post("/stream")
def chat_stream(req: ChatRequestBody, request: Request):
    rid = request.headers.get("x-req-id", "-")

    sid_final, debug = _resolve_sid_with_debug(request, req.sid)
    _log("SID_DEBUG_STREAM_IN", sid_final, rid, extra=debug)

    sessions.add_chat(sid_final, "user", req.message)

    def event_generator():
        buffer = ""
        for chunk in deepseek_service.stream_deepseek(req.message, sid_final):
            buffer += chunk
            yield chunk
        sessions.add_chat(sid_final, "assistant", buffer)
        _log("STREAM_DONE", sid_final, rid)

    # Snapshot around stream start
    _log("SID_SNAPSHOT_STREAM_BEGIN", sid_final, rid, extra=_sid_snapshot(sid_final))

    return StreamingResponse(event_generator(), media_type="text/plain")
