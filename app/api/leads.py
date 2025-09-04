from __future__ import annotations
from fastapi import APIRouter
import logging
from app.services import lead_service
from app.models.lead import Lead
from typing import List

router = APIRouter()
logger = logging.getLogger("ace")

@router.get("/", response_model=List[Lead])
async def get_leads():
    leads = lead_service.get_all_leads()
    logger.info(f"Returning {len(leads)} leads")
    return leads
