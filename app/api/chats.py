# app/api/chats.py
from fastapi import APIRouter
from app.core import sessions

router = APIRouter()

@router.get("/")
def get_chats():
    return sessions.chat_logs
