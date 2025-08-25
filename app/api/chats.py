# app/api/chats.py
from fastapi import APIRouter, Query
from app.services import chat_store
from app.core import sessions  # legacy fallback
import logging

logger = logging.getLogger("ace.api.chats")
router = APIRouter()

def _get_chats(sid: str | None):
    """
    Core handler: returns JSON for both /chats and /chats/ routes.
    - If sid is provided: list messages for that sid (persistent first, legacy fallback).
    - If sid is missing: return a flat list across all sids (keeps previous UI behavior).
    """
    if sid:
        items = chat_store.list_messages(sid)
        if items:
            return items
        # fallback for legacy writers
        logger.info("chats: fallback to legacy sessions for sid=%s", sid)
        return sessions.get_chats_for_sid(sid)

    # flat list for 'All Chats' tab (previous behavior)
    flat = chat_store.list_all_flat()
    if flat:
        return flat
    logger.info("chats: flat fallback to legacy sessions (no persistent data yet)")
    return sessions.get_all_chats()

# Support BOTH /chats/ and /chats (no trailing slash) without 307 redirects.
@router.get("/", name="get_chats_slash")
def get_chats_slash(sid: str | None = Query(None)):
    return _get_chats(sid)

@router.get("", include_in_schema=False, name="get_chats_no_slash")
def get_chats_no_slash(sid: str | None = Query(None)):
    return _get_chats(sid)
