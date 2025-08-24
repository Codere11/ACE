import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services import event_bus

logger = logging.getLogger("ace.api.chat_events")
router = APIRouter()

@router.get("/events")
async def chat_events(sid: str):
    logger.info("GET /chat/events sid=%s (open)", sid)
    async def wrapper():
        try:
            async for chunk in event_bus.subscribe(sid):
                yield chunk
        except Exception:
            logger.exception("SSE public stream error sid=%s", sid)
            raise
        finally:
            logger.info("GET /chat/events sid=%s (closed)", sid)
    return StreamingResponse(wrapper(), media_type="text/event-stream")
