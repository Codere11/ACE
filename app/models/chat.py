from pydantic import BaseModel

class ChatRequest(BaseModel):
    sid: str
    message: str
