# app/api/tags.py
from __future__ import annotations

import json
import os
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

TAGS_PATH = os.environ.get("ACE_TAGS_PATH", "conversation_tags.json")


class TagsPayload(BaseModel):
    tags: List[str] = Field(default_factory=list)


router = APIRouter(prefix="/api/tags", tags=["tags"])


def _read_tags() -> List[str]:
    if not os.path.exists(TAGS_PATH):
        return []
    try:
        with open(TAGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(t).strip() for t in data if str(t).strip()]
            if isinstance(data, dict) and "tags" in data and isinstance(data["tags"], list):
                return [str(t).strip() for t in data["tags"] if str(t).strip()]
    except Exception:
        pass
    return []


def _write_tags(tags: List[str]) -> None:
    with open(TAGS_PATH, "w", encoding="utf-8") as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)


@router.get("", response_model=TagsPayload)
def get_tags():
    return TagsPayload(tags=_read_tags())


@router.put("", response_model=TagsPayload)
def put_tags(payload: TagsPayload):
    tags = sorted({t.strip() for t in payload.tags if t.strip()})
    if len(tags) > 64:
        raise HTTPException(status_code=400, detail="Too many tags (max 64).")
    _write_tags(list(tags))
    return TagsPayload(tags=list(tags))
