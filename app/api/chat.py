# app/api/chat.py
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import FLOW
from app.services import deepseek_service, lead_service
from app.services import session_service as takeover
from app.services import chat_store, event_bus

logger = logging.getLogger("ace.api.chat")
router = APIRouter()

# ---------------- Models ----------------
class ChatRequest(BaseModel):
    sid: str = Field(min_length=3)
    message: Optional[str] = ""

class SurveyRequest(BaseModel):
    sid: str = Field(min_length=3)
    industry: Optional[str] = ""
    budget: Optional[str] = ""
    experience: Optional[str] = ""
    question1: Optional[str] = ""
    question2: Optional[str] = ""

# ---------------- Helpers ----------------
def _now() -> int:
    return int(time.time())

def make_response(
    reply: Optional[str],
    ui: Dict[str, Any] | None = None,
    chat_mode: str = "guided",
    story_complete: bool = False,
    image_url: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "reply": reply,
        "ui": ui or {},
        "chatMode": chat_mode,
        "storyComplete": story_complete,
        "imageUrl": image_url,
    }

def get_node_by_id(node_id: str) -> Dict[str, Any] | None:
    return next((n for n in FLOW["nodes"] if n["id"] == node_id), None)

def _trace(sid: str, stage: str, node_id: str | None, state: dict, msg: str = ""):
    logger.info("[FLOW] sid=%s %s node=%s waiting_input=%s awaiting_node=%s msg='%s'",
                sid, stage, node_id, state.get("waiting_input"), state.get("awaiting_node"), msg)

def _ensure_lead(sid: str):
    leads = lead_service.get_all_leads()
    lead = next((l for l in leads if l.id == sid), None)
    if lead:
        return lead
    # create placeholder, but DO NOT write AI text into lastMessage
    from app.models.lead import Lead
    lead = Lead(
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
        lastMessage="",        # keep empty; will be filled by real user msg
        lastSeenSec=_now(),
        notes=""
    )
    lead_service.add_lead(lead)
    logger.info("lead_created sid=%s (ensure)", sid)
    return lead

def _touch_lead_message(sid: str, message: str | None):
    """Update lastMessage/lastSeenSec on real user messages; never with AI output."""
    lead = _ensure_lead(sid)
    if message:
        lead.lastMessage = message
    lead.lastSeenSec = _now()

def _append_lead_notes(sid: str, note: str):
    lead = _ensure_lead(sid)
    if not note:
        return
    lead.notes = (" | ".join([p for p in [lead.notes, note] if p])).strip(" |")

def _update_lead_with_deepseek(sid: str, prompt: str, result: dict | None):
    """
    Store AI output in notes (prefixed 'AI:'), do NOT overwrite lastMessage.
    Also add the prompt context to notes for traceability.
    """
    pitch = (result or {}).get("pitch", "") if result else ""
    reasons = (result or {}).get("reasons", "") if result else ""
    summary = pitch.strip()
    if reasons:
        summary = f"{summary} Razlogi: {reasons}".strip()

    if prompt:
        _append_lead_notes(sid, f"Prompt: {prompt}")
    if summary:
        _append_lead_notes(sid, f"AI: {summary}")

# ---------------- Flow engine ----------------
def _execute_action_node(sid: str, node: Dict[str, Any], flow_sessions: Dict[str, Dict[str, Any]]) -> dict:
    action = node.get("action")
    next_key = node.get("next")
    node_id = node.get("id")

    if action == "deepseek_score":
        _trace(sid, "deepseek(start)", node_id, flow_sessions.get(sid, {}))

        lead = _ensure_lead(sid)
        prompt_parts = []
        if getattr(lead, "notes", None):
            prompt_parts.append(f"Notes: {lead.notes}")
        if getattr(lead, "lastMessage", None):
            prompt_parts.append(f"Last: {lead.lastMessage}")
        prompt = "\n".join(prompt_parts).strip() or \
                 "No structured answers were captured. Score fit and generate a short pitch."

        try:
            result = deepseek_service.run_deepseek(prompt, sid)
        except Exception:
            logger.exception("deepseek error sid=%s", sid)
            _update_lead_with_deepseek(sid, prompt, {"pitch": "", "reasons": ""})
            flow_sessions[sid] = {"node": next_key or "done"}
            return make_response(
                "⚠️ Prišlo je do težave pri ocenjevanju z DeepSeek. Predlagam, da rezervirava kratek termin.",
                ui={"story_complete": True, "openInput": True},
                chat_mode="open",
                story_complete=True,
            )

        _update_lead_with_deepseek(sid, prompt, result)
        flow_sessions[sid] = {"node": next_key or "done"}

        pitch = (result or {}).get("pitch", "") or ""
        reasons = (result or {}).get("reasons", "") or ""
        reply = (f"{pitch} Razlogi: {reasons}").strip() or \
                "Hitra ocena je pripravljena. Predlagam kratek test ACE ali termin za posvet."
        return make_response(
            reply,
            ui={"story_complete": True, "openInput": True},
            chat_mode="open",
            story_complete=True,
        )

    return format_node(node, story_complete=False)

def handle_flow(req: ChatRequest, flow_sessions: Dict[str, Dict[str, Any]]) -> dict:
    sid = req.sid
    msg = (req.message or "").strip()

    if sid not in flow_sessions:
        flow_sessions[sid] = {"node": "welcome"}
        node = get_node_by_id("welcome")
        _trace(sid, "init", "welcome", flow_sessions[sid], msg)
        return format_node(node, story_complete=False)

    state = flow_sessions[sid]
    node_key = state.get("node")
    node = get_node_by_id(node_key) if node_key else None
    _trace(sid, "enter", node_key, state, msg)

    if not node:
        logger.error("Flow node missing sid=%s node_key=%s", sid, node_key)
        return make_response("⚠️ Napaka v pogovornem toku.", ui={}, chat_mode="guided", story_complete=True)

    if "choices" in node:
        chosen = next((c for c in node["choices"]
                       if c.get("title") == msg or c.get("payload") == msg), None)
        if chosen:
            next_key = chosen.get("next")
            next_node = get_node_by_id(next_key) if next_key else None
            if not next_node:
                flow_sessions[sid] = {"node": next_key or "done"}
                _trace(sid, "choice->missing_next", next_key, flow_sessions[sid], msg)
                return make_response("⚠️ Manjka naslednji korak.", ui={}, chat_mode="guided", story_complete=True)

            if next_node.get("openInput"):
                flow_sessions[sid] = {"node": next_key, "waiting_input": True, "awaiting_node": next_key}
                _trace(sid, "choice->openInput(armed)", next_key, flow_sessions[sid], msg)
                return format_node(next_node, story_complete=False)

            if next_node.get("action"):
                flow_sessions[sid] = {"node": next_key}
                _trace(sid, "choice->action(exec)", next_key, flow_sessions[sid], msg)
                return _execute_action_node(sid, next_node, flow_sessions)

            flow_sessions[sid] = {"node": next_key}
            _trace(sid, "choice->next", next_key, flow_sessions[sid], msg)
            return format_node(next_node, story_complete=False)

        _trace(sid, "choice->repeat", node_key, state, msg)
        return format_node(node, story_complete=False)

    if node.get("openInput"):
        next_key = node.get("next")
        current_id = node.get("id")

        if state.get("waiting_input") is None:
            state["waiting_input"] = True
            state["awaiting_node"] = current_id
            _trace(sid, "ask", current_id, state)
            return format_node(node, story_complete=False)

        state.pop("waiting_input", None)
        _trace(sid, "answer", current_id, state, msg)

        if state.get("awaiting_node") == current_id:
            state.pop("awaiting_node", None)

            if node.get("action") == "store_answer":
                _append_lead_notes(sid, msg)         # store as notes
                _touch_lead_message(sid, msg)        # but keep lastMessage = real answer

            if next_key:
                next_node = get_node_by_id(next_key)
                flow_sessions[sid] = {"node": next_key}

                if next_node and next_node.get("openInput"):
                    flow_sessions[sid]["waiting_input"] = True
                    flow_sessions[sid]["awaiting_node"] = next_key
                    _trace(sid, "armed_next_openInput", next_key, flow_sessions[sid])
                    return format_node(next_node, story_complete=False)

                if next_node and next_node.get("action"):
                    _trace(sid, "goto_next->action(exec)", next_key, flow_sessions[sid])
                    return _execute_action_node(sid, next_node, flow_sessions)

                _trace(sid, "goto_next", next_key, flow_sessions[sid])
                return format_node(next_node, story_complete=False)

        _trace(sid, "dup_or_mismatch", current_id, state, msg)
        if next_key:
            next_node = get_node_by_id(next_key)
            flow_sessions[sid] = {"node": next_key}
            if next_node and next_node.get("action"):
                _trace(sid, "dup_or_mismatch->action(exec)", next_key, flow_sessions[sid])
                return _execute_action_node(sid, next_node, flow_sessions)
            return format_node(next_node, story_complete=False)

        return make_response("", ui={}, chat_mode="guided", story_complete=False)

    if node.get("action"):
        _trace(sid, "action(exec at enter)", node_key, state, msg)
        return _execute_action_node(sid, node, flow_sessions)

    _trace(sid, "default", node_key, state)
    return format_node(node, story_complete=False)

def format_node(node: Dict[str, Any] | None, story_complete: bool) -> Dict[str, Any]:
    if not node:
        return make_response("⚠️ Manjka vozlišče v pogovornem toku.", ui={}, chat_mode="guided", story_complete=True)

    if "choices" in node:
        ui = {"type": "choices", "buttons": node["choices"]}
        mode = "guided"
    elif node.get("openInput"):
        ui = {"openInput": True, "inputType": node.get("inputType", "single")}
        mode = "open"
    else:
        ui = {}
        mode = "guided"

    if isinstance(node.get("texts"), list) and node["texts"]:
        reply = random.choice(node["texts"])
    else:
        reply = node.get("text", "")

    return make_response(reply or "", ui=ui, chat_mode=mode, story_complete=story_complete)

# ---------------- In-memory flow sessions ----------------
FLOW_SESSIONS: Dict[str, Dict[str, Any]] = {}

# ---------------- Routes ----------------
@router.post("/")
async def chat(req: ChatRequest):
    sid = req.sid
    message = (req.message or "").strip()
    logger.info("POST /chat sid=%s len=%d", sid, len(message or ""))

    # Ensure lead exists + update last message/seen immediately
    _touch_lead_message(sid, message)

    # Persist & publish user message
    try:
        user_msg = chat_store.append_message(sid, role="user", text=message)
        await event_bus.publish(sid, "message.created", user_msg)
    except Exception:
        logger.exception("persist/publish user message failed sid=%s", sid)
        raise

    # Human takeover short-circuit
    if takeover.is_human_mode(sid):
        logger.info("human-mode active sid=%s -> skipping bot", sid)
        return make_response(reply=None, ui={"openInput": True}, chat_mode="open", story_complete=False)

    # Bot flow
    try:
        result = handle_flow(req, FLOW_SESSIONS)
    except Exception:
        logger.exception("flow error sid=%s", sid)
        raise

    # Persist & publish assistant message (if any)
    reply_text = (result.get("reply") or "").strip()
    if reply_text:
        try:
            assistant_msg = chat_store.append_message(sid, role="assistant", text=reply_text)
            await event_bus.publish(sid, "message.created", assistant_msg)
            # assistant also counts as "activity" for last seen (optional)
            _touch_lead_message(sid, reply_text)
        except Exception:
            logger.exception("persist/publish assistant message failed sid=%s", sid)

    logger.info("POST /chat sid=%s done reply_len=%d", sid, len(reply_text))
    return result

@router.post("/stream")
async def chat_stream(req: ChatRequest):
    sid = req.sid
    message = (req.message or "").strip()
    logger.info("POST /chat/stream sid=%s len=%d", sid, len(message or ""))

    # Ensure lead exists + update last message/seen
    _touch_lead_message(sid, message)

    # Persist & publish user message
    try:
        user_msg = chat_store.append_message(sid, role="user", text=message)
        await event_bus.publish(sid, "message.created", user_msg)
    except Exception:
        logger.exception("persist/publish user message failed (stream) sid=%s", sid)
        raise

    # Human takeover -> stream a tiny notice and exit
    if takeover.is_human_mode(sid):
        logger.info("human-mode active sid=%s -> streaming notice", sid)
        async def human_notice():
            yield "Agent je prevzel pogovor. 🤝\n"
        return StreamingResponse(human_notice(), media_type="text/plain; charset=utf-8")

    # Bot flow
    try:
        result = handle_flow(req, FLOW_SESSIONS)
    except Exception:
        logger.exception("flow error (stream) sid=%s", sid)
        raise

    reply_text = (result.get("reply") or "").strip()

    async def streamer():
        try:
            if not reply_text:
                return
            step = 24
            for i in range(0, len(reply_text), step):
                yield reply_text[i:i+step]
                await asyncio.sleep(0.02)
        except Exception:
            logger.exception("stream send error sid=%s", sid)
            raise

    # Persist & publish after we know full text
    if reply_text:
        try:
            assistant_msg = chat_store.append_message(sid, role="assistant", text=reply_text)
            await event_bus.publish(sid, "message.created", assistant_msg)
            _touch_lead_message(sid, reply_text)
        except Exception:
            logger.exception("persist/publish assistant failed (stream) sid=%s", sid)

    logger.info("POST /chat/stream sid=%s done reply_len=%d", sid, len(reply_text))
    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")

@router.post("/survey")
async def survey(body: SurveyRequest):
    sid = body.sid
    logger.info("POST /chat/survey sid=%s", sid)

    # Merge survey answers
    parts = []
    if body.industry:   parts.append(f"Industry: {body.industry}")
    if body.budget:     parts.append(f"Budget: {body.budget}")
    if body.experience: parts.append(f"Experience: {body.experience}")
    if body.question1:  parts.append(f"Q1: {body.question1}")
    if body.question2:  parts.append(f"Q2: {body.question2}")
    survey_text = " | ".join(parts) if parts else "No answers provided."

    # Ensure lead and update last message/seen with the last meaningful answer
    _ensure_lead(sid)
    _append_lead_notes(sid, survey_text)
    _touch_lead_message(sid, body.question2 or body.question1 or body.industry or "")

    # Persist & publish the survey as a user message
    try:
        user_msg = chat_store.append_message(sid, role="user", text=f"[Survey] {survey_text}")
        await event_bus.publish(sid, "message.created", user_msg)
    except Exception:
        logger.exception("persist/publish survey message failed sid=%s", sid)

    # DeepSeek classification (safe)
    try:
        lead = _ensure_lead(sid)
        prompt_parts = []
        if getattr(lead, "notes", None):
            prompt_parts.append(f"Notes: {lead.notes}")
        if getattr(lead, "lastMessage", None):
            prompt_parts.append(f"Last: {lead.lastMessage}")
        prompt_parts.append(f"Survey: {survey_text}")
        prompt = "\n".join(prompt_parts).strip() or survey_text

        result = deepseek_service.run_deepseek(prompt, sid)
    except Exception:
        logger.exception("deepseek error in survey sid=%s", sid)
        result = {"category": "error", "reasons": "", "pitch": ""}

    # Store AI output in notes only
    _update_lead_with_deepseek(sid, prompt, result)

    # Build reply
    if result and result.get("category") != "error":
        pitch = (result or {}).get("pitch", "") or ""
        reasons = (result or {}).get("reasons", "") or ""
        reply = (f"{pitch} Razlogi: {reasons}").strip() or \
                "Hitra ocena je pripravljena. Predlagam kratek test ACE ali termin za posvet."
        story_complete = True
    else:
        reply = (
            "Hvala za odgovore! Trenutno ne morem pripraviti hitre ocene. "
            "Lahko nadaljujeva z odprtim pogovorom ali urediva kratek termin."
        )
        story_complete = False

    # Persist & publish assistant reply
    try:
        assistant_msg = chat_store.append_message(sid, role="assistant", text=reply)
        await event_bus.publish(sid, "message.created", assistant_msg)
        _touch_lead_message(sid, reply)
    except Exception:
        logger.exception("persist/publish survey assistant failed sid=%s", sid)

    logger.info("POST /chat/survey sid=%s done (deepseek=%s)",
                sid, "ok" if result and result.get("category") != "error" else "fail")

    return make_response(
        reply=reply,
        ui={"openInput": True},
        chat_mode="open",
        story_complete=story_complete
    )
