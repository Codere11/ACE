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


def handle_chat(req: ChatRequest, sessions: Dict[str, Dict[str, Any]]) -> dict:
    """
    Scripted flow handler:
    - Choices -> jump to next node
    - Open-input: ask ONCE, then consume next user message
    - action='store_answer' saves user's message into lead (notes/lastMessage)
    - action='deepseek_score' runs DeepSeek exactly once at the end
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

            if next_node and next_node.get("openInput"):
                # ✅ CRITICAL FIX:
                # when entering an open-input node, mark that we're waiting for input NOW
                sessions[sid] = {
                    "node": next_key,
                    "waiting_input": True,
                    "awaiting_node": next_key
                }
                _trace(sid, "choice->openInput(armed)", next_key, sessions[sid], msg)
                return format_node(next_node, story_complete=False)

            # normal (non-open) node
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

        # If we didn't already arm waiting_input (e.g., direct entry),
        # show the question once and arm now.
        if state.get("waiting_input") is None:
            state["waiting_input"] = True
            state["awaiting_node"] = current_id
            _trace(sid, "ask", current_id, state)
            return format_node(node, story_complete=False)

        # user answered
        state.pop("waiting_input", None)
        _trace(sid, "answer", current_id, state, msg)

        # accept only if answering the same node we asked
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
                sessions[sid] = {"node": next_key}
                _trace(sid, "goto_next", next_key, sessions[sid])
                next_node = get_node_by_id(next_key)
                # If the next node is also openInput, arm it now so the *next* request is consumed
                if next_node and next_node.get("openInput"):
                    sessions[sid]["waiting_input"] = True
                    sessions[sid]["awaiting_node"] = next_key
                    _trace(sid, "armed_next_openInput", next_key, sessions[sid])
                return format_node(next_node, story_complete=False)

            # no next
            _trace(sid, "no_next", current_id, state)
            return {"reply": "", "ui": {}, "chatMode": "guided", "storyComplete": False, "imageUrl": None}

        # mismatched/duplicate — push forward if possible
        _trace(sid, "dup_or_mismatch", current_id, state, msg)
        if next_key:
            sessions[sid] = {"node": next_key}
            next_node = get_node_by_id(next_key)
            return format_node(next_node, story_complete=False)
        return {"reply": "", "ui": {}, "chatMode": "guided", "storyComplete": False, "imageUrl": None}

    # 5) ACTIONS (no openInput)
    action = node.get("action")
    if action == "deepseek_score":
        _trace(sid, "deepseek", node_key, state, msg)
        result = deepseek_service.run_deepseek(msg, sid)
        lead_service.ingest_from_deepseek(msg, result)
        next_key = node.get("next")
        sessions[sid] = {"node": next_key or "done"}
        return {
            "reply": f"{result.get('pitch','')} Razlogi: {result.get('reasons','')}",
            "ui": {"story_complete": True, "openInput": True},
            "chatMode": "open",
            "storyComplete": True,
            "imageUrl": None
        }

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
