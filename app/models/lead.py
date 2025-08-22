from pydantic import BaseModel

class Lead(BaseModel):
    id: str   # unique identifier (sid)
    name: str
    industry: str
    score: int
    stage: str
    compatibility: bool
    interest: str
    phone: bool
    email: bool
    adsExp: bool
    lastMessage: str
    lastSeenSec: int
    notes: str
