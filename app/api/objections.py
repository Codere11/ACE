from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger("ace")

@router.get("/")
async def get_objections():
    objections = []
    logger.info(f"Returning objections: {objections}")
    return objections
