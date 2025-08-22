from fastapi import APIRouter, Query
from app.core import sessions

router = APIRouter()

@router.get("/")
def get_chats(sid: str | None = Query(None)):
    """Return all chat logs, or only for a specific sid"""
    if sid:
        return sessions.get_chats_for_sid(sid)
    return sessions.get_all_chats()
