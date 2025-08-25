import random
from typing import Dict, Any
from app.core.config import FLOW
from app.services import deepseek_service, lead_service
from app.models.chat import ChatRequest
from app.models.lead import Lead  # used when creating a missing lead


def get_node_by_id(node_id: str) -> Dict[str, Any] | None:
    return next((n for n in FLOW["nodes"] if n["id"] == node_id), None)


def _trace(sid: str, stage: str, node_id: str | None, state: dict, msg: str = ""):
    print(f"[FLOW] sid={sid} {stage} node={node_id} waiting_input={state.get('waiting_input')} "
          f"awaiting_node={state.get('awaiting_node')} msg='{msg}'")


def _update_lead_with_deepseek(sid: str, prompt: str, result: dict | None):
    """Update existing lead with DeepSeek output; if missing, create with SAME sid."""
    leads = lead_service.get_all_leads()
    lead = next((l for l in leads if l.id == sid), None)

    pitch = (result or {}).get("pitch", "") if result else ""
    reasons = (result or {}).get("reasons", "") if result else ""
    summary = pitch.strip()
    if reasons:
        summary = f"{summary} Razlogi: {reasons}".strip()

    if not lead:
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
            lastMessage=summary or (prompt[:200] if prompt else ""),
            lastSeenSec=0,
            notes=f"Notes: {prompt}" if prompt else ""
        )
        lead_service.add_lead(lead)
        return

    # Update existing
    if prompt:
        lead.notes = f"{lead.notes} | {prompt}".strip(" |") if lead.notes else prompt
    if summary:
        lead.lastMessage = summary


def _execute_action_node(sid: str, node: Dict[str, Any], sessions: Dict[str, Dict[str, Any]]) -> dict:
    action = node.get("action")
    next_key = node.get("next")
    node_id = node.get("id")

    if action == "deepseek_score":
        _trace(sid, "deepseek(start)", node_id, sessions.get(sid, {}))

        # Build prompt from stored lead answers
        lead = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
        prompt = ""
        if lead:
            parts = []
            if getattr(lead, "notes", None):
                parts.append(f"Notes: {lead.notes}")
            if getattr(lead, "lastMessage", None):
                parts.append(f"Last: {lead.lastMessage}")
            prompt = "\n".join(parts).strip()
        if not prompt:
            prompt = "No structured answers were captured. Score fit and generate a short pitch."

        # Run DeepSeek safely
        result = deepseek_service.run_deepseek(prompt, sid)

        # Treat explicit error category like an exception (do not show raw error to user)
        if not result or result.get("category") == "error":
            _update_lead_with_deepseek(sid, prompt, {"pitch": "", "reasons": ""})
            sessions[sid] = {"node": next_key or "done"}
            return {
                "reply": "⚠️ Trenutno ne morem oceniti. Predlagam kratek termin ali hiter test ACE.",
                "ui": {"story_complete": True, "openInput": True},
                "chatMode": "open",
                "storyComplete": True,
                "imageUrl": None
            }

        # Persist DeepSeek output
        _update_lead_with_deepseek(sid, prompt, result)

        sessions[sid] = {"node": next_key or "done"}
        pitch = (result or {}).get("pitch", "")
        reasons = (result or {}).get("reasons", "")
        reply = f"{pitch} Razlogi: {reasons}".strip()
        if not reply:
            reply = "Hitra ocena je pripravljena. Predlagam kratek test ACE ali termin za posvet."

        return {
            "reply": reply,
            "ui": {"story_complete": True, "openInput": True},
            "chatMode": "open",
            "storyComplete": True,
            "imageUrl": None
        }

    # Unknown action: render as normal
    return format_node(node, story_complete=False)


def handle_chat(req: ChatRequest, sessions: Dict[str, Dict[str, Any]]) -> dict:
    sid = req.sid
    msg = (req.message or "").strip()

    # 1) init
    if sid not in sessions:
        sessions[sid] = {"node": "welcome"}
        node = get_node_by_id("welcome")
        _trace(sid, "init", "welcome", sessions[sid], msg)
        return format_node(node, story_complete=False)

    # 2) resolve node
    state = sessions[sid]
    node_key = state.get("node")
    node = get_node_by_id(node_key) if node_key else None
    _trace(sid, "enter", node_key, state, msg)

    if not node:
        return {
            "reply": "⚠️ Napaka v pogovornem toku.",
            "ui": {},
            "chatMode": "guided",
            "storyComplete": True,
            "imageUrl": None
        }

    # 3) choices
    if "choices" in node:
        chosen = next((c for c in node["choices"]
                       if c.get("title") == msg or c.get("payload") == msg), None)
        if chosen:
            next_key = chosen.get("next")
            next_node = get_node_by_id(next_key) if next_key else None

            if not next_node:
                sessions[sid] = {"node": next_key or "done"}
                _trace(sid, "choice->missing_next", next_key, sessions[sid], msg)
                return {
                    "reply": "⚠️ Manjka naslednji korak.",
                    "ui": {},
                    "chatMode": "guided",
                    "storyComplete": True,
                    "imageUrl": None
                }

            if next_node.get("openInput"):
                sessions[sid] = {"node": next_key, "waiting_input": True, "awaiting_node": next_key}
                _trace(sid, "choice->openInput(armed)", next_key, sessions[sid], msg)
                return format_node(next_node, story_complete=False)

            if next_node.get("action"):
                sessions[sid] = {"node": next_key}
                _trace(sid, "choice->action(exec)", next_key, sessions[sid], msg)
                return _execute_action_node(sid, next_node, sessions)

            sessions[sid] = {"node": next_key}
            _trace(sid, "choice->next", next_key, sessions[sid], msg)
            return format_node(next_node, story_complete=False)

        _trace(sid, "choice->repeat", node_key, state, msg)
        return format_node(node, story_complete=False)

    # 4) open-input
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
                lead = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
                if lead:
                    lead.notes = f"{lead.notes} | {msg}".strip(" |") if lead.notes else msg
                    lead.lastMessage = msg

            if next_key:
                next_node = get_node_by_id(next_key)
                sessions[sid] = {"node": next_key}

                if next_node and next_node.get("openInput"):
                    sessions[sid]["waiting_input"] = True
                    sessions[sid]["awaiting_node"] = next_key
                    _trace(sid, "armed_next_openInput", next_key, sessions[sid])
                    return format_node(next_node, story_complete=False)

                if next_node and next_node.get("action"):
                    _trace(sid, "goto_next->action(exec)", next_key, sessions[sid])
                    return _execute_action_node(sid, next_node, sessions)

                _trace(sid, "goto_next", next_key, sessions[sid])
                return format_node(next_node, story_complete=False)

        _trace(sid, "dup_or_mismatch", current_id, state, msg)
        if next_key:
            next_node = get_node_by_id(next_key)
            sessions[sid] = {"node": next_key}
            if next_node and next_node.get("action"):
                _trace(sid, "dup_or_mismatch->action(exec)", next_key, sessions[sid])
                return _execute_action_node(sid, next_node, sessions)
            return format_node(next_node, story_complete=False)

        return {"reply": "", "ui": {}, "chatMode": "guided", "storyComplete": False, "imageUrl": None}

    # 5) actions (execute immediately on enter)
    if node.get("action"):
        _trace(sid, "action(exec at enter)", node_key, state, msg)
        return _execute_action_node(sid, node, sessions)

    # 6) default
    _trace(sid, "default", node_key, state)
    return format_node(node, story_complete=False)


def format_node(node: Dict[str, Any] | None, story_complete: bool) -> Dict[str, Any]:
    if not node:
        return {
            "reply": "⚠️ Manjka vozlišče v pogovornem toku.",
            "ui": {},
            "chatMode": "guided",
            "storyComplete": True,
            "imageUrl": None
        }

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

    return {"reply": reply or "", "ui": ui, "chatMode": mode, "storyComplete": story_complete, "imageUrl": None}
