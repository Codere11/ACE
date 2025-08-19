from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.chat import ChatRequest
from app.services import deepseek_service, flow_service
from app.core import sessions

router = APIRouter()

@router.post("/")
def chat(req: ChatRequest):
    return flow_service.handle_chat(req, sessions.sessions)

@router.post("/stream")
def chat_stream(req: ChatRequest):
    return StreamingResponse(
        deepseek_service.stream_deepseek(req.message, req.sid),
        media_type="text/plain"
    )
