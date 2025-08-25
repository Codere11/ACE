# app/models/chat.py
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field
import json, hashlib

# ---- Version this schema bundle so we can detect drift in logs/health
SCHEMA_VERSION = "1.0.1-step1-pydantic-compat"

# Roles we persist and render
ChatRole = Literal["user", "assistant", "staff"]


class ChatRequest(BaseModel):
    """Standard chat message coming from the visitor/browser."""
    sid: str = Field(min_length=3)
    message: Optional[str] = ""


class SurveyRequest(BaseModel):
    """Structured answers submitted via the survey form."""
    sid: str = Field(min_length=3)
    industry: Optional[str] = ""
    budget: Optional[str] = ""
    experience: Optional[str] = ""
    question1: Optional[str] = ""
    question2: Optional[str] = ""


class StaffMessage(BaseModel):
    """Message sent by an internal agent via the dashboard takeover UI."""
    sid: str = Field(min_length=3)
    text: str = Field(min_length=1)


class ChatMessage(BaseModel):
    """Canonical stored chat message (what chat_store returns)."""
    sid: str
    role: ChatRole
    text: str
    timestamp: int  # epoch seconds


# ---- Pydantic v1/v2 compatibility helpers
def _model_schema(model_cls: type[BaseModel]) -> dict:
    """
    Return a JSON-serializable schema for a Pydantic model across v1/v2.
    - v2: model_json_schema()
    - v1: schema()
    """
    getter = getattr(model_cls, "model_json_schema", None)
    if callable(getter):  # pydantic v2
        return getter()
    return model_cls.schema()  # pydantic v1


def schema_fingerprint() -> str:
    """Stable fingerprint of these models for quick integrity checks."""
    payload = {
        "version": SCHEMA_VERSION,
        "roles": ["user", "assistant", "staff"],
        "ChatRequest": _model_schema(ChatRequest),
        "SurveyRequest": _model_schema(SurveyRequest),
        "StaffMessage": _model_schema(StaffMessage),
        "ChatMessage": _model_schema(ChatMessage),
        # include whether v2 API exists to avoid collisions across installs
        "pydantic_v2": hasattr(BaseModel, "model_json_schema"),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def model_modules() -> dict:
    """Where each model is actually being imported from (should be app.models.chat)."""
    return {
        "ChatRequest": ChatRequest.__module__,
        "SurveyRequest": SurveyRequest.__module__,
        "StaffMessage": StaffMessage.__module__,
        "ChatMessage": ChatMessage.__module__,
    }


__all__ = [
    "SCHEMA_VERSION",
    "ChatRole",
    "ChatRequest",
    "SurveyRequest",
    "StaffMessage",
    "ChatMessage",
    "schema_fingerprint",
    "model_modules",
]
