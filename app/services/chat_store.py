from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ace.chat_store")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "chats.json"

_LOCK = threading.Lock()

def _load() -> Dict[str, List[Dict]]:
    if not DB_PATH.exists():
        logger.debug("DB file not found, initializing empty store at %s", DB_PATH)
        return {}
    try:
        with DB_PATH.open("r", encoding="utf-8") as f:
            db = json.load(f)
            return db if isinstance(db, dict) else {}
    except Exception:
        logger.exception("Failed to load DB file %s", DB_PATH)
        return {}

def _save(db: Dict[str, List[Dict]]) -> None:
    tmp = DB_PATH.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        tmp.replace(DB_PATH)
        logger.debug("DB saved %s (sessions=%d)", DB_PATH, len(db))
    except Exception:
        logger.exception("Failed to save DB file %s", DB_PATH)

def append_message(sid: str, role: str, text: str) -> Dict:
    msg = {
        "id": str(uuid.uuid4()),
        "sid": sid,
        "role": role,
        "text": text,
        "ts": time.time(),
    }
    with _LOCK:
        db = _load()
        db.setdefault(sid, []).append(msg)
        _save(db)
    logger.info("message appended sid=%s role=%s id=%s len=%d",
                sid, role, msg["id"], len(text or ""))
    return msg

def list_messages(sid: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
    with _LOCK:
        db = _load()
    if sid:
        msgs = db.get(sid, [])
        logger.debug("list_messages sid=%s count=%d", sid, len(msgs))
    else:
        msgs = []
        for arr in db.values():
            msgs.extend(arr)
        logger.debug("list_messages all_sessions total=%d", len(msgs))
    msgs.sort(key=lambda m: m.get("ts", 0))
    if limit:
        return msgs[-limit:]
    return msgs
