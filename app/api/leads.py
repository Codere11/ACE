from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger("ace")

@router.get("/")
async def get_leads():
    leads = []  # start blank for new clients
    logger.info(f"Returning {len(leads)} leads: {leads}")
    return leads
