from __future__ import annotations

import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, Query
from app.services import chat_store

logger = logging.getLogger("ace.api.chats")
router = APIRouter()

def _to_chatlog(m: Dict) -> Dict:
    return {
        "sid": m.get("sid", ""),
        "role": m.get("role", ""),
        "text": m.get("text", ""),
        "timestamp": float(m.get("ts") or m.get("timestamp") or 0.0),
    }

@router.get("")
@router.get("/")
def get_chats(sid: Optional[str] = Query(default=None)) -> List[Dict]:
    logger.info("GET /chats sid=%s", sid)
    msgs = chat_store.list_messages(sid=sid)
    out = [_to_chatlog(m) for m in msgs]
    logger.info("GET /chats sid=%s -> count=%d", sid, len(out))
    return out
