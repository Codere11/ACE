# app/api/chats.py
from fastapi import APIRouter
from app.core import sessions

router = APIRouter()

@router.get("/")
def get_chats():
    """Return all chat logs"""
    return sessions.chat_logs
