import random
from typing import Dict, Any, Optional

from app.core.config import FLOW
from app.services import deepseek_service, lead_service
from app.models.chat import ChatRequest
from app.models.lead import Lead  # used when creating a missing lead

# ---------- helpers ----------
def get_node_by_id(node_id: str) -> Dict[str, Any] | None:
    return next((n for n in FLOW["nodes"] if n["id"] == node_id), None)

def _trace(sid: str, stage: str, node_id: str | None, state: dict, msg: str = ""):
    print(f"[FLOW] sid={sid} {stage} node={node_id} waiting_input={state.get('waiting_input')} "
          f"awaiting_node={state.get('awaiting_node')} msg='{msg}'")

def _ensure_lead(sid: str) -> Lead:
    leads = lead_service.get_all_leads()
    lead = next((l for l in leads if l.id == sid), None)
    if lead:
        return lead
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
        lastSeenSec=0,
        notes=""
    )
    lead_service.add_lead(lead)
    return lead

def _apply_ai_to_lead(sid: str, result: dict | None):
    lead = _ensure_lead(sid)
    if not result:
        return
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
    summary = (f"{pitch} Razlogi: {reasons}").strip()
    if summary:
        lead.lastMessage = summary
        lead.notes = (" | ".join([p for p in [lead.notes, f"AI: {summary}"] if p])).strip(" |")

def _update_lead_with_deepseek(sid: str, prompt: str, result: dict | None):
    if prompt:
        lead = _ensure_lead(sid)
        lead.notes = (" | ".join([p for p in [lead.notes, f"Prompt: {prompt}"] if p])).strip(" |")
    _apply_ai_to_lead(sid, result)

# ---------- engine ----------
def _execute_action_node(sid: str, node: Dict[str, Any], sessions: Dict[str, Dict[str, Any]]) -> dict:
    action = (node.get("action") or "").strip()
    next_key = node.get("next")
    node_id = node.get("id")

    if action in ("compute_fit", "deepseek_score"):
        # Build prompt from stored lead answers/notes
        lead = _ensure_lead(sid)
        parts = []
        if getattr(lead, "notes", None):       parts.append(f"Notes: {lead.notes}")
        if getattr(lead, "lastMessage", None): parts.append(f"Last: {lead.lastMessage}")
        prompt = "\n".join(parts).strip() or "ni signalov; konzervativna ocena"

        result = deepseek_service.run_deepseek(prompt, sid)
        _update_lead_with_deepseek(sid, prompt, result)

        # Keep current node active so its choices show (summary node)
        sessions[sid] = {"node": node_id}

        pitch = (result or {}).get("pitch", "") or ""
        reasons = (result or {}).get("reasons", "") or ""
        comp = (result or {}).get("compatibility", "")
        interest = (result or {}).get("interest", "")
        prefix = f"Ujemanje: {interest} ({comp}/100)." if interest or comp != "" else ""
        reply = (" ".join([prefix, f"{pitch} Razlogi: {reasons}".strip()])).strip() or \
                "Ocena je pripravljena. Kako naprej?"

        ui = {"type": "choices", "buttons": node.get("choices", [])} if node.get("choices") else {"openInput": True}
        return {
            "reply": reply,
            "ui": ui,
            "chatMode": "guided" if node.get("choices") else "open",
            "storyComplete": False,
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
            lead = _ensure_lead(sid)
            lead.notes = (" | ".join([p for p in [lead.notes, msg] if p])).strip(" |")
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

    return {"reply": reply or "", "ui": ui, "chatMode": mode, "storyComplete": story_complete, "imageUrl": None}
