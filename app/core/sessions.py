# app/core/sessions.py

chat_logs = []  # simple in-memory log

def add_chat(role: str, text: str):
    """Append chat message to the log"""
    chat_logs.append({"role": role, "text": text})
