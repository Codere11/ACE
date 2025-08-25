from pydantic import BaseModel
from typing import Any

class ChatEvent(BaseModel):
    type: str
    sid: str
    ts: float
    payload: Any
