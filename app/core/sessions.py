# app/core/sessions.py
import time

# simple in-memory log
chat_logs = []


def add_chat(role: str, text: str):
    """Append chat message with timestamp to the log"""
    chat_logs.append({
        "role": role,
        "text": text,
        "timestamp": int(time.time())
    })
