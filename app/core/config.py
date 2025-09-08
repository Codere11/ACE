import os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Configs
CONFIG_PATH = os.path.join(DATA_DIR, "conversation_config.json")
FLOW_PATH = os.path.join(DATA_DIR, "conversation_flow.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    ACE_CONFIG = json.load(f)

with open(FLOW_PATH, "r", encoding="utf-8") as f:
    FLOW = json.load(f)

# --- Minimal, safe patch: ensure FIRST NODE is a dual contact prompt.
#     - Keeps everything else intact (choices remain but won't render because openInput takes precedence)
#     - Auto-sets 'next' to existing next/first-choice/second-node fallback
def _ensure_dual_contact_first_node(flow: dict) -> dict:
    try:
        nodes = flow.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            return flow

        # Prefer node with id='welcome', else the very first node
        idx = 0
        for i, n in enumerate(nodes):
            if isinstance(n, dict) and n.get("id") == "welcome":
                idx = i
                break

        node = dict(nodes[idx])  # shallow copy to avoid side effects

        # Determine the best 'next' target:
        # 1) existing node.next
        # 2) first choice.next
        # 3) fallback to the ID of the second node (if any)
        primary_next = node.get("next")
        if not primary_next:
            for c in node.get("choices", []):
                nxt = c.get("next")
                if nxt:
                    primary_next = nxt
                    break
        if not primary_next and len(nodes) >= 2 and isinstance(nodes[1], dict):
            primary_next = nodes[1].get("id")

        # Enforce dual-contact open input
        node["openInput"] = True
        node["inputType"] = "dual-contact"
        if primary_next:
            node["next"] = primary_next

        # Replace/ensure text is a clear contact ask (keep minimal, no variables)
        node["texts"] = [
            "Preden začnemo – prosim vnesite kontakt (e-pošta in/ali telefon) za povratni info."
        ]

        nodes[idx] = node
        flow["nodes"] = nodes
    except Exception:
        # Silent fail: never break boot if something unexpected is in the JSON
        pass
    return flow

# Toggle via env; default ON
if os.getenv("ACE_ENFORCE_DUAL_CONTACT", "1") not in ("0", "false", "False"):
    FLOW = _ensure_dual_contact_first_node(FLOW)

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-ac86f23b7a524c8cb0f42b4f62a010b2")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
