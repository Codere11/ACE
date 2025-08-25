# app/services/chat_store.py
from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List, Optional, TypedDict, Literal
import logging

logger = logging.getLogger("ace.chat_store")

Role = Literal["user", "assistant", "staff"]

class ChatMessage(TypedDict):
    sid: str
    role: Role
    text: str
    timestamp: int  # epoch seconds


# Store path (configurable)
STORE_PATH = os.getenv(
    "ACE_CHAT_STORE_PATH",
    os.path.join(os.getcwd(), "data", "chat_store.jsonl")
)

_index: Dict[str, List[ChatMessage]] = {}
_lock = threading.RLock()


def _ensure_store_dir():
    d = os.path.dirname(STORE_PATH)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _load_once() -> None:
    if _index:  # already loaded
        return
    _ensure_store_dir()
    if not os.path.exists(STORE_PATH):
        logger.info("chat_store: no file, starting empty path=%s", STORE_PATH)
        return
    loaded = 0
    bad = 0
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    sid = msg.get("sid")
                    role = msg.get("role")
                    text = msg.get("text")
                    ts = msg.get("timestamp")
                    if not (sid and role and isinstance(text, str) and isinstance(ts, int)):
                        bad += 1
                        continue
                    _index.setdefault(sid, []).append({
                        "sid": sid, "role": role, "text": text, "timestamp": ts
                    })  # type: ignore
                    loaded += 1
                except Exception:
                    bad += 1
                    continue
        logger.info("chat_store: loaded=%d bad=%d path=%s", loaded, bad, STORE_PATH)
    except Exception as e:
        logger.exception("chat_store: load error: %s", e)


_load_once()


def append_message(sid: str, role: Role, text: str, *, ts: Optional[int] = None) -> ChatMessage:
    if not sid or not text or role not in ("user", "assistant", "staff"):
        raise ValueError("invalid message")

    msg: ChatMessage = {
        "sid": sid,
        "role": role,
        "text": text,
        "timestamp": int(ts if ts is not None else time.time()),
    }

    _ensure_store_dir()
    with _lock:
        _index.setdefault(sid, []).append(msg)
        with open(STORE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    logger.info("WRITE chat_store sid=%s role=%s len=%d ts=%d", sid, role, len(text), msg["timestamp"])
    return msg


def list_messages(sid: str) -> List[ChatMessage]:
    with _lock:
        return list(_index.get(sid, []))


def list_all(limit_per_sid: int = 1000) -> Dict[str, List[ChatMessage]]:
    out: Dict[str, List[ChatMessage]] = {}
    with _lock:
        for k, v in _index.items():
            out[k] = v[-limit_per_sid:]
    return out


def list_all_flat(limit: int = 10000) -> List[ChatMessage]:
    with _lock:
        all_msgs: List[ChatMessage] = []
        for arr in _index.values():
            all_msgs.extend(arr)
        all_msgs.sort(key=lambda m: m["timestamp"])
        return all_msgs[-limit:]


def stats() -> dict:
    with _lock:
        total = sum(len(v) for v in _index.values())
        return {
            "path": STORE_PATH,
            "sessions": len(_index),
            "messages": total,
        }
