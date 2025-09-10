from __future__ import annotations

import asyncio
import logging
import random
import time
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.config import FLOW
from app.core import sessions  # legacy memory store
from app.models import chat as chat_models
from app.models.chat import ChatRequest, SurveyRequest, StaffMessage
from app.services import lead_service, chat_store, event_bus, takeover
from app.services import scoring_service

logger = logging.getLogger("ace.api.chat")
router = APIRouter()

logger.info(
    "Chat models: version=%s fingerprint=%s modules=%s",
    chat_models.SCHEMA_VERSION,
    chat_models.schema_fingerprint()[:12],
    chat_models.model_modules(),
)

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
        lastMessage="",
        lastSeenSec=_now(),
        notes=""
    )
    lead_service.add_lead(lead)
    logger.info("lead_created sid=%s (ensure)", sid)
    return lead

def _touch_lead_message(sid: str, message: str | None):
    lead = _ensure_lead(sid)
    if message:
        lead.lastMessage = message
    lead.lastSeenSec = _now()

def _append_lead_notes(sid: str, note: str):
    lead = _ensure_lead(sid)
    if not note:
        return
    lead.notes = (" | ".join([p for p in [lead.notes, note] if p])).strip(" |")

def _apply_score_to_lead(sid: str, result: dict | None, *, silent: bool = False):
    """
    Persist deterministic interest/score.
    If silent=True, do NOT overwrite lastMessage (to avoid visible noise).
    """
    if not result:
        return
    lead = _ensure_lead(sid)

    interest = (result or {}).get("interest")
    if isinstance(interest, str) and interest:
        lead.interest = interest

    comp = (result or {}).get("compatibility")
    try:
        if comp is not None:
            lead.score = max(0, min(100, int(round(float(comp)))))
    except Exception:
        pass

    pitch = (result or {}).get("pitch", "") or ""
    reasons = (result or {}).get("reasons", "") or ""

    # Only set lastMessage on final compute_fit (silent=False), and NEVER include reasons
    if not silent and pitch:
        lead.lastMessage = pitch

    # Keep internal breadcrumb for dashboard/audit
    try:
        _append_lead_notes(sid, f"Score: {lead.score} | interest: {lead.interest}" + (f" | reasons: {reasons}" if reasons else ""))
    except Exception:
        pass

def _set_node(flow_sessions: Dict[str, Dict[str, Any]], sid: str, node_id: str, **extra):
    fs = flow_sessions.setdefault(sid, {})
    fs["node"] = node_id
    if "waiting_input" not in extra:
        fs.pop("waiting_input", None)
    if "awaiting_node" not in extra:
        fs.pop("awaiting_node", None)
    fs.update(extra)
    return fs

def _realtime_score(sid: str, qual: Dict[str, Any]):
    try:
        result = scoring_service.score_from_qual(qual or {})
        _apply_score_to_lead(sid, result, silent=True)
    except Exception:
        logger.exception("realtime scoring failed sid=%s", sid)

# ---------------- Flow engine ----------------
def _execute_action_node(sid: str, node: Dict[str, Any], flow_sessions: Dict[str, Dict[str, Any]]) -> dict:
    action = (node.get("action") or "").strip()
    next_key = node.get("next")
    node_id = node.get("id")

    # Deterministic scoring (final)
    if action in ("compute_fit", "deepseek_score"):
        qual = (flow_sessions.get(sid, {}) or {}).get("qual", {})
        _ensure_lead(sid)

        qual_pairs = "; ".join(f"{k}={v}" for k, v in qual.items())
        if qual_pairs:
            _append_lead_notes(sid, f"qual: {qual_pairs}")

        result = scoring_service.score_from_qual(qual)
        _apply_score_to_lead(sid, result, silent=False)

        # USER-FACING reply: pitch only (no numbers, no reasons)
        reply = (result or {}).get("pitch") or \
                "Super — zdi se, da ustreza vašim željam. Lahko uskladimo termin za ogled ali pošljem več informacij."

        _set_node(flow_sessions, sid, node_id)
        if node.get("choices"):
            return make_response(
                reply,
                ui={"type": "choices", "buttons": node["choices"]},
                chat_mode="guided",
                story_complete=False,
            )
        if next_key:
            _set_node(flow_sessions, sid, next_key)
            nxt = get_node_by_id(next_key)
            base = format_node(nxt, story_complete=False)
            base["reply"] = (reply + "\n\n" + (base.get("reply") or "")).strip()
            return base
        return make_response(reply, ui={"openInput": True}, chat_mode="open", story_complete=False)

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
            # Capture structured signals
            choice_action = (chosen.get("action") or "").strip()
            if choice_action == "qualify_tag":
                payload = (chosen.get("payload") or {})
                q = flow_sessions.setdefault(sid, {}).setdefault("qual", {})
                q.update(payload)
                if payload:
                    pairs = "; ".join(f"{k}={v}" for k, v in payload.items())
                    _append_lead_notes(sid, f"qual: {pairs}")
                # Real-time scoring (silent)
                _realtime_score(sid, q)

            next_key = chosen.get("next")
            next_node = get_node_by_id(next_key) if next_key else None
            if not next_node:
                _set_node(flow_sessions, sid, next_key or "done")
                _trace(sid, "choice->missing_next", next_key, flow_sessions[sid], msg)
                return make_response("⚠️ Manjka naslednji korak.", ui={}, chat_mode="guided", story_complete=True)

            if next_node.get("openInput"):
                _set_node(flow_sessions, sid, next_key, waiting_input=True, awaiting_node=next_key)
                _trace(sid, "choice->openInput(armed)", next_key, flow_sessions[sid], msg)
                return format_node(next_node, story_complete=False)

            if next_node.get("action"):
                _set_node(flow_sessions, sid, next_key)
                _trace(sid, "choice->action(exec)", next_key, flow_sessions[sid], msg)
                return _execute_action_node(sid, next_node, flow_sessions)

            _set_node(flow_sessions, sid, next_key)
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
            _append_lead_notes(sid, msg)
            _touch_lead_message(sid, msg)

        if next_key:
            next_node = get_node_by_id(next_key)
            _set_node(flow_sessions, sid, next_key)

            if next_node and next_node.get("openInput"):
                _set_node(flow_sessions, sid, next_key, waiting_input=True, awaiting_node=next_key)
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
            _set_node(flow_sessions, sid, next_key)
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

    if node.get("openInput"):
        ui = {"openInput": True, "inputType": node.get("inputType", "single")}
        mode = "open"
    elif "choices" in node:
        ui = {"type": "choices", "buttons": node["choices"]}
        mode = "guided"
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

# ---------------- Route impls ----------------
async def _chat_impl(req: ChatRequest):
    sid = req.sid
    message = (req.message or "").strip()
    logger.info("POST /chat sid=%s len=%d", sid, len(message or ""))

    if message.startswith("/contact"):
        try:
            json_str = message[len("/contact"):].strip()
            data = json.loads(json_str) if json_str else {}
            name = (data.get("name") or "").strip()
            email = (data.get("email") or "").strip()
            phone = (data.get("phone") or "").strip()
            channel = (data.get("channel") or "email").strip()

            lead = lead_service.upsert_contact(sid, name=name, email=email, phone=phone, channel=channel)

            try:
                await event_bus.publish(sid, "lead.touched", {
                    "lastMessage": "Kontakt posodobljen",
                    "lastSeenSec": lead.lastSeenSec,
                    "phone": bool(lead.phone),
                    "email": bool(lead.email),
                    "phoneText": lead.phoneText,
                    "emailText": lead.emailText,
                })
            except Exception:
                logger.exception("lead.touched publish failed sid=%s", sid)

            curr = FLOW_SESSIONS.get(sid) or {}
            curr_node_id = curr.get("node")
            curr_node = get_node_by_id(curr_node_id) if curr_node_id else None
            if curr_node and curr_node.get("openInput") and curr_node.get("inputType") in ("dual-contact", "contact"):
                next_key = curr_node.get("next") or "done"
                _set_node(FLOW_SESSIONS, sid, next_key)
                next_node = get_node_by_id(next_key)
                if next_node and next_node.get("openInput"):
                    _set_node(FLOW_SESSIONS, sid, next_key, waiting_input=True, awaiting_node=next_key)
                _trace(sid, "contact->advance", next_key, FLOW_SESSIONS[sid], "advance after /contact")
                return format_node(next_node, story_complete=False)

            return make_response("Kontakt shranjen ✅ — nadaljujeva. 🔥", ui=None, chat_mode="guided", story_complete=False)
        except Exception:
            logger.exception("contact parse/save failed sid=%s", sid)
            return make_response("⚠️ Ni uspelo shraniti kontakta. Poskusi znova ali preskoči v klepet.", ui=None, chat_mode="guided", story_complete=False)

    if message.strip() == "/skip_to_human":
        try:
            takeover.enable(sid)
            await event_bus.publish(sid, "lead.touched", {
                "lastMessage": "Uporabnik želi 1-na-1 pogovor",
                "lastSeenSec": _now(),
            })
        except Exception:
            logger.exception("skip_to_human publish failed sid=%s", sid)
        return make_response(reply=None, ui={"openInput": True}, chat_mode="open", story_complete=False)

    _touch_lead_message(sid, message)

    try:
        user_msg = chat_store.append_message(sid, role="user", text=message)
        await event_bus.publish(sid, "message.created", user_msg)
    except Exception:
        logger.exception("persist/publish user message failed sid=%s", sid)
        raise

    if takeover.is_active(sid):
        logger.info("human-mode active sid=%s -> skipping bot", sid)
        return make_response(reply=None, ui={"openInput": True}, chat_mode="open", story_complete=False)

    try:
        result = handle_flow(req, FLOW_SESSIONS)
    except Exception:
        logger.exception("flow error sid=%s", sid)
        raise

    reply_text = (result.get("reply") or "").strip()
    if reply_text:
        try:
            assistant_msg = chat_store.append_message(sid, role="assistant", text=reply_text)
            await event_bus.publish(sid, "message.created", assistant_msg)
            _touch_lead_message(sid, reply_text)
        except Exception:
            logger.exception("persist/publish assistant message failed sid=%s", sid)

    logger.info("POST /chat sid=%s done reply_len=%d", sid, len(reply_text))
    return result

@router.post("/", name="chat")
async def chat(req: ChatRequest):
    return await _chat_impl(req)

@router.post("", include_in_schema=False, name="chat_no_slash")
async def chat_no_slash(req: ChatRequest):
    return await _chat_impl(req)

# ---- stream ----
async def _chat_stream_impl(req: ChatRequest):
    sid = req.sid
    message = (req.message or "").strip()
    logger.info("POST /chat/stream sid=%s len=%d", sid, len(message or ""))

    if message.startswith("/contact"):
        try:
            json_str = message[len("/contact"):].strip()
            data = json.loads(json_str) if json_str else {}
            name = (data.get("name") or "").strip()
            email = (data.get("email") or "").strip()
            phone = (data.get("phone") or "").strip()
            channel = (data.get("channel") or "email").strip()

            lead = lead_service.upsert_contact(sid, name=name, email=email, phone=phone, channel=channel)

            try:
                await event_bus.publish(sid, "lead.touched", {
                    "lastMessage": "Kontakt posodobljen",
                    "lastSeenSec": lead.lastSeenSec,
                    "phone": bool(lead.phone),
                    "email": bool(lead.email),
                    "phoneText": lead.phoneText,
                    "emailText": lead.emailText,
                })
            except Exception:
                logger.exception("lead.touched publish failed (stream) sid=%s", sid)

            curr = FLOW_SESSIONS.get(sid) or {}
            curr_node_id = curr.get("node")
            curr_node = get_node_by_id(curr_node_id) if curr_node_id else None
            if curr_node and curr_node.get("openInput") and curr_node.get("inputType") in ("dual-contact", "contact"):
                next_key = curr_node.get("next") or "done"
                _set_node(FLOW_SESSIONS, sid, next_key)
                next_node = get_node_by_id(next_key)
                if next_node and next_node.get("openInput"):
                    _set_node(FLOW_SESSIONS, sid, next_key, waiting_input=True, awaiting_node=next_key)
                _trace(sid, "contact->advance(stream)", next_key, FLOW_SESSIONS[sid], "advance after /contact")
                reply_text = (format_node(next_node, story_complete=False).get("reply") or "").strip()

                async def ok():
                    yield reply_text or "Nadaljujva. 🔥"
                return StreamingResponse(ok(), media_type="text/plain; charset=utf-8")

            async def ok_fallback():
                yield "Kontakt shranjen ✅ — nadaljujeva. 🔥"
            return StreamingResponse(ok_fallback(), media_type="text/plain; charset=utf-8")
        except Exception:
            logger.exception("contact parse/save failed (stream) sid=%s", sid)
            async def err():
                yield "⚠️ Ni uspelo shraniti kontakta. Poskusi znova ali preskoči v klepet."
            return StreamingResponse(err(), media_type="text/plain; charset=utf-8")

    if message.strip() == "/skip_to_human":
        try:
            takeover.enable(sid)
            await event_bus.publish(sid, "lead.touched", {
                "lastMessage": "Uporabnik želi 1-na-1 pogovor",
                "lastSeenSec": _now(),
            })
        except Exception:
            logger.exception("skip_to_human publish failed (stream) sid=%s", sid)

        async def human_notice():
            yield "Agent je prevzel pogovor. 🤝\n"
        return StreamingResponse(human_notice(), media_type="text/plain; charset=utf-8")

    _touch_lead_message(sid, message)

    try:
        user_msg = chat_store.append_message(sid, role="user", text=message)
        await event_bus.publish(sid, "message.created", user_msg)
    except Exception:
        logger.exception("persist/publish user message failed (stream) sid=%s", sid)

    if takeover.is_active(sid):
        logger.info("human-mode active sid=%s -> streaming notice", sid)
        async def human_notice2():
            yield "Agent je prevzel pogovor. 🤝\n"
        return StreamingResponse(human_notice2(), media_type="text/plain; charset=utf-8")

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

    if reply_text:
        try:
            assistant_msg = chat_store.append_message(sid, role="assistant", text=reply_text)
            await event_bus.publish(sid, "message.created", assistant_msg)
            _touch_lead_message(sid, reply_text)
        except Exception:
            logger.exception("persist/publish assistant failed (stream) sid=%s", sid)

    logger.info("POST /chat/stream sid=%s done reply_len=%d", sid, len(reply_text))
    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")

@router.post("/stream", name="chat_stream")
async def chat_stream(req: ChatRequest):
    return await _chat_stream_impl(req)

@router.post("/stream/", include_in_schema=False, name="chat_stream_slash")
async def chat_stream_slash(req: ChatRequest):
    return await _chat_stream_impl(req)

# ---- survey (notes only) ----
async def _survey_impl(body: SurveyRequest):
    sid = body.sid
    logger.info("POST /chat/survey sid=%s", sid)

    if takeover.is_active(sid):
        return {"ok": True, "human_mode": True}

    parts = []
    if getattr(body, "industry", None):   parts.append(f"Industry: {body.industry}")
    if getattr(body, "budget", None):     parts.append(f"Budget: {body.budget}")
    if getattr(body, "experience", None): parts.append(f"Experience: {body.experience}")
    if getattr(body, "question1", None):  parts.append(f"Q1: {body.question1}")
    if getattr(body, "question2", None):  parts.append(f"Q2: {body.question2}")
    survey_text = " | ".join(parts) if parts else "No answers provided."

    _ensure_lead(sid)
    _append_lead_notes(sid, survey_text)
    _touch_lead_message(sid, getattr(body, "question2", None) or getattr(body, "question1", None) or getattr(body, "industry", None) or "")

    try:
        user_msg = chat_store.append_message(sid, role="user", text=f"[Survey] {survey_text}")
        await event_bus.publish(sid, "message.created", user_msg)
    except Exception:
        logger.exception("persist/publish survey message failed sid=%s", sid)

    reply = "Hvala za odgovore! Nadaljujeva z naslednjimi koraki ali terminom ogleda."
    story_complete = True

    try:
        assistant_msg = chat_store.append_message(sid, role="assistant", text=reply)
        await event_bus.publish(sid, "message.created", assistant_msg)
        _touch_lead_message(sid, reply)
    except Exception:
        logger.exception("persist/publish survey assistant failed sid=%s", sid)

    logger.info("POST /chat/survey sid=%s done", sid)
    return make_response(
        reply=reply,
        ui={"openInput": True},
        chat_mode="open",
        story_complete=story_complete
    )

@router.post("/survey", name="survey")
async def survey(body: SurveyRequest):
    return await _survey_impl(body)

@router.post("/survey/", include_in_schema=False, name="survey_slash")
async def survey_slash(body: SurveyRequest):
    return await _survey_impl(body)

# ---- staff ----
async def _staff_impl(body: StaffMessage):
    sid = body.sid
    text = (body.text or "").strip()

    takeover.enable(sid)

    if not text:
        return {"ok": False}

    _touch_lead_message(sid, text)

    saved = None
    try:
        saved = chat_store.append_message(sid, role="staff", text=text)
        sessions.add_chat(sid, "staff", text)
        await event_bus.publish(sid, "message.created", saved)
    except Exception:
        logger.exception("persist/publish staff message failed sid=%s", sid)

    return {"ok": True, "message": saved}

@router.post("/staff", name="staff_message")
async def staff_message(body: StaffMessage):
    return await _staff_impl(body)

@router.post("/staff/", include_in_schema=False, name="staff_message_slash")
async def staff_message_slash(body: StaffMessage):
    return await _staff_impl(body)
