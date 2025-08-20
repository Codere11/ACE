from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger("ace")

@router.get("/")
async def get_kpis():
    kpis = {
        "visitors": 0,
        "interactions": 0,
        "contacts": 0,
        "avgResponseSec": 0,
        "activeLeads": 0
    }
    logger.info(f"Returning KPIs: {kpis}")
    return kpis
