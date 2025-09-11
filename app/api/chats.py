# app/api/chats.py
from fastapi import APIRouter, Query
from app.services import chat_store
from app.core import sessions  # legacy fallback
import logging

logger = logging.getLogger("ace.api.chats")
router = APIRouter()

def _get_chats(sid: str | None):
    """
    Core handler for both /chats and /chats/.
    - If sid is provided: list messages for that sid (persistent first, legacy fallback).
    - If sid is missing: flat list across all sids (keeps previous UI behavior).
    """
    if sid:
        items = chat_store.list_messages(sid)
        if items:
            return items
        logger.info("chats: fallback to legacy sessions for sid=%s", sid)
        return sessions.get_chats_for_sid(sid)

    flat = chat_store.list_all_flat()
    if flat:
        return flat
    logger.info("chats: flat fallback to legacy sessions (no persistent data yet)")
    return sessions.get_all_chats()

@router.get("/", name="get_chats_slash")
def get_chats_slash(sid: str | None = Query(None)):
    """
    Returns ONLY messages for the given sid.
    If sid is missing, returns an empty list (no global history).
    """
    if not sid:
        logger.info("chats: sid missing -> return [] (no flat history)")
        return []
    return chat_store.list_messages(sid)

@router.get("", include_in_schema=False, name="get_chats_no_slash")
def get_chats_no_slash(sid: str | None = Query(None)):
    if not sid:
        logger.info("chats: sid missing (no-slash) -> []")
        return []
    return chat_store.list_messages(sid)
