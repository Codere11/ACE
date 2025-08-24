from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services import session_service as sessions
from app.services import event_bus
from app.services import chat_store

logger = logging.getLogger("ace.api.agent")
router = APIRouter()

class ClaimBody(BaseModel):
    sid: str = Field(min_length=3)

class AgentMsgBody(BaseModel):
    sid: str = Field(min_length=3)
    text: str = Field(min_length=1, max_length=8000)

def get_agent_id(x_agent_id: Optional[str] = Header(default=None, alias="X-Agent-Id")) -> str:
    if not x_agent_id:
        logger.warning("Missing X-Agent-Id header")
        raise HTTPException(status_code=401, detail="Missing X-Agent-Id")
    return x_agent_id

@router.post("/claim")
async def claim_session(body: ClaimBody, agent_id: str = Depends(get_agent_id)):
    logger.info("POST /agent/claim sid=%s agent=%s", body.sid, agent_id)
    try:
        st = sessions.claim(body.sid, agent_id)
    except RuntimeError as e:
        logger.warning("claim conflict sid=%s agent=%s err=%s", body.sid, agent_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        logger.exception("claim error sid=%s agent=%s", body.sid, agent_id)
        raise
    await event_bus.publish(body.sid, "session.claimed", {"claimed_by": agent_id, "mode": "human"})
    await event_bus.publish(body.sid, "bot.paused", {"sid": body.sid})
    return st.to_dict()

@router.post("/release")
async def release_session(body: ClaimBody, agent_id: str = Depends(get_agent_id)):
    logger.info("POST /agent/release sid=%s agent=%s", body.sid, agent_id)
    try:
        st = sessions.release(body.sid, agent_id=agent_id)
    except RuntimeError as e:
        logger.warning("release conflict sid=%s agent=%s err=%s", body.sid, agent_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        logger.exception("release error sid=%s agent=%s", body.sid, agent_id)
        raise
    await event_bus.publish(body.sid, "session.released", {"released_by": agent_id, "mode": "bot"})
    await event_bus.publish(body.sid, "bot.resumed", {"sid": body.sid})
    return st.to_dict()

@router.post("/message")
async def send_message(body: AgentMsgBody, agent_id: str = Depends(get_agent_id)):
    logger.info("POST /agent/message sid=%s agent=%s len=%d", body.sid, agent_id, len(body.text or ""))
    try:
        msg = chat_store.append_message(body.sid, role="agent", text=body.text)
        await event_bus.publish(body.sid, "message.created", msg)
        return msg
    except Exception:
        logger.exception("agent message error sid=%s agent=%s", body.sid, agent_id)
        raise

@router.get("/stream")
async def agent_stream(sid: str):
    logger.info("GET /agent/stream sid=%s (open)", sid)
    async def wrapper():
        try:
            async for chunk in event_bus.subscribe(sid):
                yield chunk
        except Exception:
            logger.exception("SSE stream error sid=%s", sid)
            raise
        finally:
            logger.info("GET /agent/stream sid=%s (closed)", sid)
    return StreamingResponse(wrapper(), media_type="text/event-stream")
