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

@router.delete("/{lead_id}")
async def delete_lead(lead_id: str):
    """Delete a lead by ID."""
    deleted = lead_service.delete_lead(lead_id)
    if deleted:
        logger.info(f"Deleted lead {lead_id}")
        return {"success": True, "message": f"Lead {lead_id} deleted"}
    else:
        logger.warning(f"Lead {lead_id} not found for deletion")
        return {"success": False, "message": f"Lead {lead_id} not found"}
