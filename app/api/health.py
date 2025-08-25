# app/api/health.py
from __future__ import annotations

import sys
from fastapi import APIRouter
import pydantic  # type: ignore

from app.models import chat as chat_models
from app.services import chat_store

router = APIRouter()

@router.get("/ping")
def ping():
    return {"ok": True}

@router.get("/models")
def models_health():
    return {
        "ok": True,
        "schemaVersion": chat_models.SCHEMA_VERSION,
        "fingerprint": chat_models.schema_fingerprint(),
        "modules": chat_models.model_modules(),
        "python": sys.version.split()[0],
        "pydantic": getattr(pydantic, "__version__", "unknown"),
    }

@router.get("/store")
def store_health():
    s = chat_store.stats()
    return {
        "ok": True,
        "path": s["path"],
        "sessions": s["sessions"],
        "messages": s["messages"],
    }
