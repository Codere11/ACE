import random
from typing import Dict, Any
from app.core.config import FLOW
from app.services import deepseek_service, lead_service
from app.models.chat import ChatRequest


def get_node_by_id(node_id: str) -> Dict[str, Any] | None:
    """Return a node dict from FLOW by its id, or None if missing."""
    return next((n for n in FLOW["nodes"] if n["id"] == node_id), None)


def handle_chat(req: ChatRequest, sessions: Dict[str, Dict[str, Any]]) -> dict:
    """
    Main chat handler.
    - Drives the scripted flow defined in conversation_flow.json (FLOW)
    - Open-input nodes ask once, then consume the next user message
    - action=="store_answer" saves the user's message to the lead (notes + lastMessage)
    - action=="deepseek_score" runs DeepSeek ONCE at the end
    """
    sid = req.sid
    msg = (req.message or "").strip()

    # DEBUG (optional):
    # print(f"[FLOW] sid={sid} msg='{msg}' state={sessions.get(sid)}")

    # 1) First message in a session -> start at welcome
    if sid not in sessions:
        sessions[sid] = {"node": "welcome"}
        node = get_node_by_id("welcome")
        return format_node(node, story_complete=False)

    # 2) Resolve current node
    state = sessions[sid]
    node_key = state.get("node")
    node = get_node_by_id(node_key) if node_key else None
    if not node:
        # Fallback if flow is misconfigured
        return {
            "reply": "⚠️ Napaka v pogovornem toku.",
            "ui": {},
            "chatMode": "guided",
            "storyComplete": True,
            "imageUrl": None,
        }

    # 3) Handle CHOICES nodes
    if "choices" in node:
        chosen = next(
            (c for c in node["choices"] if c.get("title") == msg or c.get("payload") == msg),
            None
        )
        if chosen:
            next_key = chosen.get("next")
            if next_key:
                sessions[sid] = {"node": next_key}
                next_node = get_node_by_id(next_key)
                return format_node(next_node, story_complete=False)
        # No valid choice -> repeat same node
        return format_node(node, story_complete=False)

    # 4) Handle OPEN-INPUT nodes (single or dual)
    if node.get("openInput"):
        next_key = node.get("next")
        current_id = node.get("id")

        # First visit to this node: show the question ONCE
        if state.get("waiting_input") is None:
            state["waiting_input"] = True
            state["awaiting_node"] = current_id
            return format_node(node, story_complete=False)

        # Second visit: we have the user's answer
        state.pop("waiting_input", None)

        # Only accept answer if it's for the same node we asked
        if state.get("awaiting_node") == current_id:
            state.pop("awaiting_node", None)

            # If this node should STORE the answer, do it now
            if node.get("action") == "store_answer":
                lead = next((l for l in lead_service.get_all_leads() if l.id == sid), None)
                if lead:
                    lead.notes = f"{lead.notes} | {msg}".strip(" |") if lead.notes else msg
                    lead.lastMessage = msg

            # Move to the next scripted node (DO NOT re-emit current question)
            if next_key:
                sessions[sid] = {"node": next_key}
                next_node = get_node_by_id(next_key)
                return format_node(next_node, story_complete=False)

            # No next? return empty (no repeat)
            return {
                "reply": "",
                "ui": {},
                "chatMode": "guided",
                "storyComplete": False,
                "imageUrl": None,
            }

        # If here, client resent / node changed; push forward if possible
        if next_key:
            sessions[sid] = {"node": next_key}
            next_node = get_node_by_id(next_key)
            return format_node(next_node, story_complete=False)

        return {
            "reply": "",
            "ui": {},
            "chatMode": "guided",
            "storyComplete": False,
            "imageUrl": None,
        }

    # 5) Handle ACTION nodes (no openInput)
    action = node.get("action")
    if action == "deepseek_score":
        # Run DeepSeek ONCE at the END. Use the latest user message (msg).
        result = deepseek_service.run_deepseek(msg, sid)
        lead_service.ingest_from_deepseek(msg, result)

        # After classification, route to "closing" if present, else finish.
        next_key = node.get("next")
        if next_key:
            sessions[sid] = {"node": next_key}
        else:
            sessions[sid] = {"node": "done"}

        return {
            "reply": f"{result.get('pitch', '')} Razlogi: {result.get('reasons', '')}",
            "ui": {"story_complete": True, "openInput": True},
            "chatMode": "open",
            "storyComplete": True,
            "imageUrl": None,
        }

    # 6) Default: render node
    return format_node(node, story_complete=False)


def format_node(node: Dict[str, Any] | None, story_complete: bool) -> Dict[str, Any]:
    """Render a node into the ChatResponse payload."""
    if not node:
        return {
            "reply": "⚠️ Manjka vozlišče v pogovornem toku.",
            "ui": {},
            "chatMode": "guided",
            "storyComplete": True,
            "imageUrl": None,
        }

    # Determine UI and mode
    if "choices" in node:
        ui = {"type": "choices", "buttons": node["choices"]}
        mode = "guided"
    elif node.get("openInput"):
        ui = {"openInput": True, "inputType": node.get("inputType", "single")}
        mode = "open"
    else:
        ui = {}
        mode = "guided"

    # Pick a reply text
    if isinstance(node.get("texts"), list) and node["texts"]:
        reply = random.choice(node["texts"])
    else:
        reply = node.get("text", "")

    return {
        "reply": reply or "",
        "ui": ui,
        "chatMode": mode,
        "storyComplete": story_complete,
        "imageUrl": None,
    }
