# ACE-Campaign/utm_session.py
from datetime import datetime
from typing import Dict, Any

SESSIONS: Dict[str, Dict[str, Any]] = {}

def ensure_session(sid: str) -> Dict[str, Any]:
    if sid not in SESSIONS:
        SESSIONS[sid] = {
            "created_at": datetime.utcnow().isoformat(),
            "utm": {},
            "vertical": "",
            "page_path": "",
            "history": [],
        }
    return SESSIONS[sid]
