from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class Lead(BaseModel):
    id: str = Field(..., description="Session/lead id (sid)")
    name: str = "Unknown"
    industry: str = "Unknown"
    score: int = 0
    stage: str = "Awareness"
    compatibility: bool = False
    interest: str = "Low"  # "High" | "Medium" | "Low"

    # Legacy flags used across UI/metrics
    phone: bool = False
    email: bool = False
    adsExp: bool = False

    # NEW: actual strings to render on dashboard (clickable tel:/mailto:)
    phoneText: Optional[str] = ""
    emailText: Optional[str] = ""

    lastMessage: str = ""
    lastSeenSec: int = 0
    notes: str = ""

    # Survey tracking
    survey_started_at: Optional[str] = None  # ISO datetime string
    survey_completed_at: Optional[str] = None
    survey_answers: Optional[dict] = None  # {node_id: answer_value}
    survey_progress: int = 0  # 0-100 percentage

    class Config:
        extra = "ignore"
