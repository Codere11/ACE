import json, os, logging, requests, random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ace")

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Load static config (ACE product data)
CONFIG_PATH = os.path.join(DATA_DIR, "conversation_config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    ACE_CONFIG = json.load(f)

# Load scripted flow
FLOW_PATH = os.path.join(BASE_DIR, "conversation_flow.json")
with open(FLOW_PATH, "r", encoding="utf-8") as f:
    FLOW = json.load(f)

# In-memory session store
sessions: Dict[str, Dict[str, Any]] = {}

# DeepSeek setup
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-ac86f23b7a524c8cb0f42b4f62a010b2")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def run_deepseek(user_text: str, sid: str) -> str:
    """Blocking call to DeepSeek with ACE knowledge + user description."""
    prompt = (
        f"ACE knowledge:\n{json.dumps(ACE_CONFIG, indent=2)}\n\n"
        f"Lead details:\nDescription: {user_text}\n\n"
        "Task: Classify this lead. Respond as JSON with keys: "
        "category (good_fit, could_fit, bad_fit), reasons (string), pitch (string)."
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are ACE qualification AI."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        resp = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=12)
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # try to extract JSON
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {}

        category = parsed.get("category", "could_fit")
        pitch = parsed.get("pitch", "")
        reasons = parsed.get("reasons", "")

        if category == "good_fit":
            return f"{pitch} I believe ACE would be a great fit because {reasons}. A notification has been sent to our staff and will contact you shortly."
        elif category == "could_fit":
            return f"{pitch} We can discuss partnership further. Our staff will reach out shortly."
        else:
            return f"Perhaps ACE wouldn't be the best fit because {reasons}. But if you think otherwise, feel free to reach out to maks.ponikvar@gmail.com."

    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "Sorry, something went wrong while scoring the lead."


def stream_deepseek(user_text: str, sid: str):
    """Generator that streams tokens from DeepSeek API."""
    prompt = (
        f"ACE knowledge:\n{json.dumps(ACE_CONFIG, indent=2)}\n\n"
        f"Lead details:\nDescription: {user_text}\n\n"
        "Task: Classify this lead. Respond conversationally in chunks."
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are ACE qualification AI."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "stream": True
    }

    try:
        with requests.post(DEEPSEEK_URL, headers=headers, json=body, stream=True) as r:
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith(b"data: "):
                    data_str = line[len(b"data: "):].decode("utf-8")
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data_json = json.loads(data_str)
                        delta = data_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue
    except Exception as e:
        logger.error(f"DeepSeek streaming error: {e}")
        yield "⚠️ Error streaming from DeepSeek."


# --- FastAPI app ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    sid: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    sid = req.sid
    msg = req.message.strip()

    # initialize session if new
    if sid not in sessions:
        sessions[sid] = {"node": "welcome"}
        node = FLOW["welcome"]
        return format_node(node, story_complete=False)

    state = sessions[sid]
    node_key = state["node"]
    node = FLOW[node_key]

    # Case 1: Node has choices
    if "choices" in node:
        chosen = next((c for c in node["choices"] if c["title"] == msg or c.get("payload") == msg), None)
        if chosen:
            next_key = chosen["next"]
            sessions[sid] = {"node": next_key}
            next_node = FLOW[next_key]
            return format_node(next_node, story_complete=False)
        else:
            return format_node(node, story_complete=False)

    # Case 2: Node expects free text → go DeepSeek (blocking version)
    if node.get("openInput") and node.get("next") == "deepseek":
        sessions[sid] = {"node": "deepseek"}
        deepseek_reply = run_deepseek(msg, sid)
        sessions[sid] = {"node": "done"}
        return {
            "reply": deepseek_reply,
            "ui": {"story_complete": True, "openInput": True},
            "chatMode": "open",
            "storyComplete": True
        }

    # Case 3: Node is deepseek action
    if node.get("action") == "deepseek_score":
        deepseek_reply = run_deepseek(msg, sid)
        sessions[sid] = {"node": "done"}
        return {
            "reply": deepseek_reply,
            "ui": {"story_complete": True, "openInput": True},
            "chatMode": "open",
            "storyComplete": True
        }

    return format_node(node, story_complete=False)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Streaming endpoint for DeepSeek (always streams, skips flow)."""
    sid = req.sid
    msg = req.message.strip()
    return StreamingResponse(stream_deepseek(msg, sid), media_type="text/plain")


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

    # handle texts vs text
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
