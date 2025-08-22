import time
from collections import defaultdict

# chats grouped by sid
chat_logs = defaultdict(list)

def add_chat(sid: str, role: str, text: str):
    """Append chat message with timestamp to the log for this sid"""
    chat_logs[sid].append({
        "sid": sid,
        "role": role,
        "text": text,
        "timestamp": int(time.time())
    })

def get_all_chats():
    """Return all chat logs (flattened)"""
    return [msg for msgs in chat_logs.values() for msg in msgs]

def get_chats_for_sid(sid: str):
    """Return chats for a specific sid"""
    return chat_logs.get(sid, [])
