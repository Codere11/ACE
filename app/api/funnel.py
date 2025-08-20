from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger("ace")

@router.get("/")
async def get_funnel():
    funnel = {
        "awareness": 0,
        "interest": 0,
        "meeting": 0,
        "close": 0
    }
    logger.info(f"Returning funnel: {funnel}")
    return funnel
