from __future__ import annotations

import sys
from typing import List, Dict, Any
from fastapi import APIRouter, Query, Request
import pydantic  # type: ignore

from app.models import chat as chat_models
from app.services import chat_store
from app.services import event_bus  # ← added

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


@router.get("/store/messages")
def store_messages(sid: str = Query(..., min_length=1)):
    """Inspect exactly what's persisted for a SID."""
    return chat_store.list_messages(sid)


@router.get("/routes")
def list_routes(request: Request):
    """
    Introspect all registered routes to verify there are no collisions.
    Uses Request to access the FastAPI instance (correct pattern).
    """
    app = request.app
    out: List[Dict[str, Any]] = []
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        name = getattr(r, "name", None)
        if path and methods:
            out.append({"path": path, "methods": sorted(list(methods)), "name": name})
    out.sort(key=lambda x: (x["path"], ",".join(x["methods"])))
    return {"ok": True, "routes": out}


@router.get("/events")
def events_health():
    """
    Current SSE subscriber counts per topic.
    """
    s = event_bus.stats()
    total = s.pop("__total__", 0)
    topics = [{"topic": k, "subscribers": v} for k, v in sorted(s.items())]
    return {"ok": True, "total": total, "topics": topics}
