# app/models/chat.py
from __future__ import annotations
from typing import Optional, Dict, Any, Mapping
import hashlib
import json

SCHEMA_VERSION: int = 1
SUPPORTED_SCHEMA_VERSIONS = {1}

def is_schema_supported(v: int | None) -> bool:
    return v in SUPPORTED_SCHEMA_VERSIONS if v is not None else True

def schema_fingerprint() -> str:
    layout = {
        "version": SCHEMA_VERSION,
        "models": {
            "ChatRequest": ["message", "sid", "tenant_slug", "context", "meta"],
            "SurveyRequest": ["answers", "sid", "form_id", "tenant_slug", "meta"],
            "StaffMessage": ["sid", "text", "tenant_slug", "meta"],
            "ChatMessage": ["role", "text", "timestamp", "sid", "meta"],
            "ChatEvent": ["type", "sid", "payload", "timestamp"],
        },
        "roles": ["user", "assistant", "staff", "system"],
    }
    raw = json.dumps(layout, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_STAFF = "staff"
ROLE_SYSTEM = "system"
MESSAGE_ROLES = {ROLE_USER, ROLE_ASSISTANT, ROLE_STAFF, ROLE_SYSTEM}
MESSAGE_TYPES = MESSAGE_ROLES

def sanitize_role(role: Optional[str]) -> str:
    return role if role in MESSAGE_ROLES else ROLE_USER

try:
    from pydantic import BaseModel, Field, ConfigDict  # type: ignore
    class _FlexibleModel(BaseModel):
        model_config = ConfigDict(extra="allow")
except Exception:
    from pydantic import BaseModel, Field  # type: ignore
    class _FlexibleModel(BaseModel):
        class Config:
            extra = "allow"

class ChatRequest(_FlexibleModel):
    message: str
    sid: Optional[str] = None
    tenant_slug: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

class SurveyRequest(_FlexibleModel):
    answers: Dict[str, Any] = {}
    sid: Optional[str] = None
    form_id: Optional[str] = None
    tenant_slug: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class SurveySubmitRequest(_FlexibleModel):
    """Submit survey answers with progress tracking"""
    sid: str
    node_id: str  # Current node being answered
    answer: Any  # Answer value (string, list, dict)
    progress: int = 0  # 0-100 percentage
    all_answers: Optional[Dict[str, Any]] = None  # Complete answers so far
    tenant_slug: Optional[str] = None
    org_slug: Optional[str] = None  # Organization slug for multi-tenant surveys
    survey_slug: Optional[str] = None  # Survey slug to identify which survey flow to use

class StaffMessage(_FlexibleModel):
    sid: str
    text: str
    tenant_slug: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class ChatMessage(_FlexibleModel):
    role: str = ROLE_USER
    text: str
    timestamp: Optional[int] = None
    sid: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class ChatEvent(_FlexibleModel):
    type: str
    sid: str
    payload: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None

def model_modules() -> Mapping[str, Any]:
    return {
        "ChatRequest": ChatRequest,
        "SurveyRequest": SurveyRequest,
        "StaffMessage": StaffMessage,
        "ChatMessage": ChatMessage,
        "ChatEvent": ChatEvent,
    }

from .core import Tenant, User, ConversationFlow  # noqa: E402,F401

__all__ = [
    "SCHEMA_VERSION","SUPPORTED_SCHEMA_VERSIONS","is_schema_supported","schema_fingerprint",
    "ROLE_USER","ROLE_ASSISTANT","ROLE_STAFF","ROLE_SYSTEM","MESSAGE_ROLES","MESSAGE_TYPES","sanitize_role",
    "ChatRequest","SurveyRequest","SurveySubmitRequest","StaffMessage","ChatMessage","ChatEvent",
    "model_modules",
    "Tenant","User","ConversationFlow",
]
