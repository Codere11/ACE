import random
from typing import Dict, Any
from app.core.config import FLOW
from app.services import deepseek_service, lead_service
from app.models.chat import ChatRequest


def get_node_by_id(node_id: str) -> Dict[str, Any] | None:
    return next((n for n in FLOW["nodes"] if n["id"] == node_id), None)


def _trace(sid: str, stage: str, node_id: str | None, state: dict, msg: str = ""):
    # lightweight console tracing
    print(f"[FLOW] sid={sid} {stage} node={node_id} waiting_input={state.get('waiting_input')} "
          f"awaiting_node={state.get('awaiting_node')} msg='{msg}'")


def _execute_action_node(sid: str, node: Dict[str, Any], sessions: Dict[str, Dict[str, Any]]) -> dict:
    """
    Execute 'action' nodes immediately (no extra user message needed).
    Currently supports: deepseek_score
    """
    action = node.get("action")
    next_key = node.get("next")
    node_id = node.get("id")

    if action == "deepseek_score":
        _trace(sid, "deepseek(start)", node_id, sessions.get(sid, {}))

        # Use aggregated answers saved on the lead (via store_answer)
        lead = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
        prompt = ""
        if lead:
            # Build a concise prompt/context for DeepSeek
            parts = []
            if getattr(lead, "notes", None):
                parts.append(f"Notes: {lead.notes}")
            if getattr(lead, "lastMessage", None):
                parts.append(f"Last: {lead.lastMessage}")
            prompt = "\n".join(parts).strip()

        # Fallback so we never send an empty string
        if not prompt:
            prompt = "No structured answers were captured. Score fit and generate a short pitch."

        # Run DeepSeek once, ingest, and advance
        try:
            result = deepseek_service.run_deepseek(prompt, sid)
        except Exception as e:
            _trace(sid, f"deepseek(error={e})", node_id, sessions.get(sid, {}))
            sessions[sid] = {"node": next_key or "done"}
            return {
                "reply": "⚠️ Prišlo je do težave pri ocenjevanju z DeepSeek. Poskusiva zaključiti ročno.",
                "ui": {"story_complete": True, "openInput": True},
                "chatMode": "open",
                "storyComplete": True,
                "imageUrl": None
            }

        # Persist DeepSeek output alongside the lead
        try:
            lead_service.ingest_from_deepseek(prompt, result)
        except Exception as e:
            _trace(sid, f"deepseek(ingest_error={e})", node_id, sessions.get(sid, {}))

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

    # Default: if an unknown action appears, just render it as a normal node
    return format_node(node, story_complete=False)


def handle_chat(req: ChatRequest, sessions: Dict[str, Dict[str, Any]]) -> dict:
    """
    Scripted flow handler:
    - Choices -> jump to next node (execute action nodes immediately)
    - Open-input: ask ONCE, then consume next user message (store if configured)
    - 'deepseek_score' runs exactly once automatically at the end
    """
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

    # 3) CHOICES
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

            # If next is openInput, arm it
            if next_node.get("openInput"):
                sessions[sid] = {
                    "node": next_key,
                    "waiting_input": True,
                    "awaiting_node": next_key
                }
                _trace(sid, "choice->openInput(armed)", next_key, sessions[sid], msg)
                return format_node(next_node, story_complete=False)

            # If next is an action node, execute immediately
            if next_node.get("action"):
                sessions[sid] = {"node": next_key}
                _trace(sid, "choice->action(exec)", next_key, sessions[sid], msg)
                return _execute_action_node(sid, next_node, sessions)

            # Normal (non-open, non-action) node
            sessions[sid] = {"node": next_key}
            _trace(sid, "choice->next", next_key, sessions[sid], msg)
            return format_node(next_node, story_complete=False)

        # no matching choice: repeat
        _trace(sid, "choice->repeat", node_key, state, msg)
        return format_node(node, story_complete=False)

    # 4) OPEN-INPUT
    if node.get("openInput"):
        next_key = node.get("next")
        current_id = node.get("id")

        # Ask once
        if state.get("waiting_input") is None:
            state["waiting_input"] = True
            state["awaiting_node"] = current_id
            _trace(sid, "ask", current_id, state)
            return format_node(node, story_complete=False)

        # user answered
        state.pop("waiting_input", None)
        _trace(sid, "answer", current_id, state, msg)

        if state.get("awaiting_node") == current_id:
            state.pop("awaiting_node", None)

            # store answer if required
            if node.get("action") == "store_answer":
                lead = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
                if lead:
                    lead.notes = f"{lead.notes} | {msg}".strip(" |") if lead.notes else msg
                    lead.lastMessage = msg

            # go next
            if next_key:
                next_node = get_node_by_id(next_key)
                sessions[sid] = {"node": next_key}

                # If the next node is also openInput, arm it
                if next_node and next_node.get("openInput"):
                    sessions[sid]["waiting_input"] = True
                    sessions[sid]["awaiting_node"] = next_key
                    _trace(sid, "armed_next_openInput", next_key, sessions[sid])
                    return format_node(next_node, story_complete=False)

                # If the next node has an action (e.g., deepseek_score), execute immediately
                if next_node and next_node.get("action"):
                    _trace(sid, "goto_next->action(exec)", next_key, sessions[sid])
                    return _execute_action_node(sid, next_node, sessions)

                _trace(sid, "goto_next", next_key, sessions[sid])
                return format_node(next_node, story_complete=False)

            # no next
            _trace(sid, "no_next", current_id, state)
            return {"reply": "", "ui": {}, "chatMode": "guided", "storyComplete": False, "imageUrl": None}

        # mismatched/duplicate — push forward if possible
        _trace(sid, "dup_or_mismatch", current_id, state, msg)
        if next_key:
            next_node = get_node_by_id(next_key)
            sessions[sid] = {"node": next_key}
            # Execute action immediately if needed
            if next_node and next_node.get("action"):
                _trace(sid, "dup_or_mismatch->action(exec)", next_key, sessions[sid])
                return _execute_action_node(sid, next_node, sessions)
            return format_node(next_node, story_complete=False)
        return {"reply": "", "ui": {}, "chatMode": "guided", "storyComplete": False, "imageUrl": None}

    # 5) ACTIONS (node with action but no openInput) — execute immediately
    if node.get("action"):
        _trace(sid, "action(exec at enter)", node_key, state, msg)
        return _execute_action_node(sid, node, sessions)

    # 6) DEFAULT
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

    # UI/mode
    if "choices" in node:
        ui = {"type": "choices", "buttons": node["choices"]}
        mode = "guided"
    elif node.get("openInput"):
        ui = {"openInput": True, "inputType": node.get("inputType", "single")}
        mode = "open"
    else:
        ui = {}
        mode = "guided"

    # reply text
    if isinstance(node.get("texts"), list) and node["texts"]:
        reply = random.choice(node["texts"])
    else:
        reply = node.get("text", "")

    return {
        "reply": reply or "",
        "ui": ui,
        "chatMode": mode,
        "storyComplete": story_complete,
        "imageUrl": None
    }
