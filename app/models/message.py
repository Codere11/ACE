from pydantic import BaseModel
from typing import Literal

Role = Literal["user", "assistant", "agent", "system"]

class ChatMessage(BaseModel):
    id: str
    sid: str
    role: Role
    text: str
    ts: float
