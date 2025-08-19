import random
from typing import Dict, Any
from app.core.config import FLOW
from app.services import deepseek_service, lead_service
from app.models.chat import ChatRequest

def handle_chat(req: ChatRequest, sessions: Dict[str, Dict[str, Any]]) -> dict:
    """
    Main chat handler:
    - Navigates scripted flow (conversation_flow.json)
    - Calls DeepSeek when needed
    - Logs leads into lead_service
    """
    sid = req.sid
    msg = req.message.strip()

    # init new session
    if sid not in sessions:
        sessions[sid] = {"node": "welcome"}
        node = FLOW["welcome"]
        return format_node(node, story_complete=False)

    state = sessions[sid]
    node_key = state["node"]
    node = FLOW[node_key]

    # Case 1: choices
    if "choices" in node:
        chosen = next(
            (c for c in node["choices"] if c["title"] == msg or c.get("payload") == msg),
            None
        )
        if chosen:
            next_key = chosen["next"]
            sessions[sid] = {"node": next_key}
            next_node = FLOW[next_key]
            return format_node(next_node, story_complete=False)
        else:
            return format_node(node, story_complete=False)

    # Case 2: open input -> DeepSeek classification
    if node.get("openInput") and node.get("next") == "deepseek":
        sessions[sid] = {"node": "deepseek"}
        result = deepseek_service.run_deepseek(msg, sid)

        # Convert DeepSeek classification into lead record
        lead_service.ingest_from_deepseek(msg, result)

        sessions[sid] = {"node": "done"}
        return {
            "reply": f"{result['pitch']} Reasoning: {result['reasons']}",
            "ui": {"story_complete": True, "openInput": True},
            "chatMode": "open",
            "storyComplete": True
        }

    # Case 3: action = deepseek_score
    if node.get("action") == "deepseek_score":
        result = deepseek_service.run_deepseek(msg, sid)
        lead_service.ingest_from_deepseek(msg, result)
        sessions[sid] = {"node": "done"}
        return {
            "reply": f"{result['pitch']} Reasoning: {result['reasons']}",
            "ui": {"story_complete": True, "openInput": True},
            "chatMode": "open",
            "storyComplete": True
        }

    return format_node(node, story_complete=False)


def format_node(node: Dict[str, Any], story_complete: bool) -> Dict[str, Any]:
    ui = {}
    if "choices" in node:
        ui = {"type": "choices", "buttons": node["choices"]}
        mode = "guided"
    elif node.get("openInput"):
        ui = {"openInput": True}
        mode = "open"
    else:
        mode = "guided"

    if "texts" in node and isinstance(node["texts"], list):
        reply = random.choice(node["texts"])
    else:
        reply = node.get("text")

    return {
        "reply": reply,
        "ui": ui,
        "chatMode": mode,
        "storyComplete": story_complete,
        "imageUrl": None
    }
