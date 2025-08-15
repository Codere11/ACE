# ACE-Campaign/main.py
import json, logging, socket, subprocess, time, re, os
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from conversation_engine import ConversationEngine, flatten_json_to_prompt, detect_property_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ace")

def is_rasa_running(host="localhost", port=5005):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

if not is_rasa_running():
    logger.info("Rasa not running. Starting Rasa server...")
    subprocess.Popen(["rasa", "run", "--enable-api", "--endpoints", "endpoints.yml"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(6)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------- Engine & config ----------------
engine = ConversationEngine()
config = engine.get_config()
grounding_prompt = flatten_json_to_prompt(config)

chat_history = [
    {
        "role": "system",
        "content": grounding_prompt + "\n\nOdgovarjaj v slovenščini. Vedno bodi prijazen, profesionalen in ne delaj napak. Tvoja naloga je pomagati uporabniku razumeti ACE (Omsoft AI Customer Engine), odgovoriti na vprašanja, nevsiljivo voditi do kvalifikacije in po potrebi povezati z Maksom."
    }
]
active_image: Optional[str] = None

# ---------------- Models ----------------
class ChatMeta(BaseModel):
    first_visit: Optional[bool] = False

class ChatRequest(BaseModel):
    message: str
    sid: str
    meta: Optional[ChatMeta] = None

class SurveyRequest(BaseModel):
    sid: str
    industry: str
    budget: str
    experience: str

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

# --- DeepSeek fallback (only used if the Rasa action didn't respond) ---
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-ac86f23b7a524c8cb0f42b4f62a010b2")
AGENT_PHONE = os.getenv("AGENT_PHONE", "069 735 957")

def _deepseek_fallback(industry: str, budget: str, experience: str) -> Tuple[str, bool]:
    """Return (final_message, qualified) when the action didn't fire."""
    fallback_text = (
        "Since your business is heavily lead-reliant and you have some advertising experience, "
        "I believe ACE would be the right fit for you!"
    )
    def heuristic() -> Tuple[str, bool]:
        qual = (budget in ("3k_10k", "gt_10k")) or bool(experience.strip())
        assessment = fallback_text
        if qual:
            msg = (f"{assessment} Our agent will contact you in a minute at-most.\n\n"
                   f"If it takes too long, he is probably on his lunch break — you can SMS or call him on {AGENT_PHONE}.")
        else:
            msg = f"{assessment} If you’d still like a quick human check, you can SMS or call {AGENT_PHONE}."
        return msg, qual

    if not DEEPSEEK_API_KEY:
        return heuristic()

    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        system = (
            "You are ACE, an advanced lead-generation assistant. "
            "Decide if ACE is a good fit (qualified). "
            "Respond ONLY as compact JSON with keys: qualified (boolean), short_reason (string), "
            "assistant_text (string; 1–2 sentences)."
        )
        user = (
            f"- Industry: {industry or 'unknown'}\n"
            f"- Budget: {budget or 'unknown'} (lt_1k, 1k_3k, 3k_10k, gt_10k)\n"
            f"- Experience: {experience or 'unknown'}"
        )
        body = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role":"system","content":system},{"role":"user","content":user}],
            "temperature": 0.2, "max_tokens": 160
        }
        r = requests.post(DEEPSEEK_API_URL, headers=headers, json=body, timeout=10)
        if not r.ok:
            return heuristic()
        data = r.json()
        txt = (data.get("choices",[{}])[0].get("message",{}) or {}).get("content","") or ""
        m = re.search(r"\{[\s\S]*\}", txt)
        parsed = json.loads(m.group(0)) if m else {}
        qualified = bool(parsed.get("qualified", False))
        assessment = (str(parsed.get("assistant_text") or fallback_text).strip() or fallback_text)
        if qualified:
            msg = (f"{assessment} Our agent will contact you in a minute at-most.\n\n"
                   f"If it takes too long, he is probably on his lunch break — you can SMS or call him on {AGENT_PHONE}.")
        else:
            msg = f"{assessment} If you’d still like a quick human check, you can SMS or call {AGENT_PHONE}."
        return msg, qualified
    except Exception:
        return heuristic()

# ---------------- Helpers ----------------
def log_turn(sid: str, user: str, bot: str):
    rec = {"sid": sid, "ts": datetime.utcnow().isoformat(), "user": user, "bot": bot}
    with open("chat_logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def enforce_one_question(text: str) -> str:
    if text.count("?") <= 1:
        return text
    parts = text.split("?")
    first_q = parts[0].strip() + "?"
    rest = "?".join(parts[1:]).strip().replace("?", ".")
    return (first_q + (" " + rest if rest else "")).strip()

def _extract_reply_and_buttons(events: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]], bool]:
    texts, buttons = [], []
    story_complete = False
    for ev in events or []:
        if isinstance(ev.get("text"), str):
            texts.append(ev["text"])
        if not buttons and isinstance(ev.get("buttons"), list):
            buttons = ev["buttons"]
        if isinstance(ev.get("custom"), dict) and ev["custom"].get("story_complete") is True:
            story_complete = True
    return "\n\n".join([t for t in texts if t]).strip(), buttons, story_complete

def _extract_last_text(events: List[Dict[str, Any]]) -> str:
    """Only the last text event (used to drop the survey preamble)."""
    last = ""
    for ev in events or []:
        if isinstance(ev.get("text"), str):
            last = ev["text"]
    return (last or "").strip()

def _form_ui() -> Dict[str, Any]:
    return {
        "type": "form",
        "form": {
            "title": "Mini-survey",
            "fields": [
                {"name":"industry","label":"1) What is your business' industry?","type":"text","required":True},
                {"name":"budget","label":"2) Monthly advertising budget","type":"select","required":True,
                 "options":[
                     {"label":"< €1k","value":"lt_1k"},
                     {"label":"€1k–€3k","value":"1k_3k"},
                     {"label":"€3k–€10k","value":"3k_10k"},
                     {"label":"> €10k","value":"gt_10k"},
                 ]},
                {"name":"experience","label":"3) Your previous online advertising experience (what you tried, results, satisfaction)","type":"textarea","required":True}
            ],
            "submitLabel":"Submit"
        }
    }

def _send_rasa(sid: str, message: str) -> List[Dict[str, Any]]:
    try:
        r = requests.post(RASA_URL, json={"sender": sid, "message": message}, timeout=8)
        if r.ok:
            return r.json() or []
    except Exception as e:
        logger.error(f"Rasa error: {e}")
    return []

# ---------------- Chat Endpoint ----------------
@app.post("/chat")
def chat(req: ChatRequest):
    global chat_history, active_image
    user_input = (req.message or "").strip()
    logger.info(f"[{req.sid}] user: {user_input}")

    # greet/start
    if (req.meta and req.meta.first_visit) or (user_input == "/start"):
        events = _send_rasa(req.sid, "/greet")
        reply, buttons, story_done = _extract_reply_and_buttons(events)
        if not buttons:
            buttons = [
                {"title":"Technology", "payload":"/choose_technology"},
                {"title":"Leads", "payload":"/choose_leads"}
            ]
        ui = {"type": "choices", "buttons": buttons}
        reply = reply or "Hey, I see you're interested in ACE! Are you more interested in the technology, or how it helps get leads?"
        chat_history.append({"role":"assistant","content": reply})
        log_turn(req.sid, user_input, reply)
        return {
            "reply": reply,
            "quickReplies": buttons,
            "ui": ui,
            "chatMode": "guided",
            "storyComplete": False,
            "imageUrl": None
        }

    # optional image detection (kept)
    image = detect_property_image(user_input, config)
    if image:
        active_image = image
        chat_history.append({"role":"system","content": f"User requested image: {image}."})

    # forward to rasa
    events = _send_rasa(req.sid, user_input)
    reply, buttons, story_done = _extract_reply_and_buttons(events)

    # --------- UI decision (restored logic) ---------
    ui: Optional[Dict[str, Any]] = None
    if buttons:
        ui = {"type": "choices", "buttons": buttons}
    pitch_marker = "Please fill out this mini-survey" in (reply or "")
    first_q_marker = "1) What is your business' industry" in (reply or "")
    if pitch_marker or first_q_marker:
        ui = _form_ui()

    chat_mode = "open" if story_done else "guided"

    if not reply:
        try:
            reply = engine.get_response(chat_history)
        except Exception:
            reply = "Sorry, I had trouble answering."

    reply = enforce_one_question(reply)
    chat_history.append({"role": "assistant", "content": reply})
    log_turn(req.sid, user_input, reply)

    return {
        "reply": reply,
        "quickReplies": (ui or {}).get("buttons") if (ui and ui.get("type")=="choices") else None,
        "ui": ui,
        "chatMode": chat_mode,
        "storyComplete": story_done,
        "imageUrl": f"/{active_image}" if image else None
    }

# ---------------- Survey Endpoint (ONLY FINAL TEXT) ----------------
@app.post("/survey")
def survey(req: SurveyRequest):
    # Step the Rasa form in a single HTTP call (as before)
    ev1 = _send_rasa(req.sid, req.industry.strip())
    ev2 = _send_rasa(req.sid, f'/provide_budget{{"budget":"{req.budget}"}}')
    ev3 = _send_rasa(req.sid, req.experience.strip())
    events = (ev1 or []) + (ev2 or []) + (ev3 or [])

    # We only want the **final** message from Rasa (the DeepSeek action’s line),
    # not the earlier survey prompts or "Thanks, analyzing..." preamble.
    _reply_all, _buttons, story_done = _extract_reply_and_buttons(events)
    reply = _extract_last_text(events) or _reply_all

    # If the action didn't fire, use DeepSeek fallback and DO NOT prepend preamble.
    if not story_done:
        reply, _qualified = _deepseek_fallback(req.industry, req.budget, req.experience)
        story_done = True  # unlock chat

    return {
        "reply": reply or "Thanks! A notification was sent to our agent and he’ll join shortly.",
        "quickReplies": None,
        "ui": None,
        "chatMode": "open" if story_done else "guided",
        "storyComplete": story_done,
        "imageUrl": None
    }

# -------- Health --------
@app.get("/health")
def health():
    return {"ok": True}
