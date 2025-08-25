from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, List

logger = logging.getLogger("ace.event_bus")

# one list of subscriber queues per session id
_subscribers: Dict[str, List[asyncio.Queue]] = {}

def _now() -> float:
    return time.time()

async def publish(sid: str, event_type: str, payload: dict) -> None:
    """Publish an event to all subscribers of the session."""
    evt = {"type": event_type, "sid": sid, "ts": _now(), "payload": payload}
    queues = _subscribers.get(sid, [])
    logger.debug("publish sid=%s type=%s subs=%d", sid, event_type, len(queues))
    for q in list(queues):
        try:
            q.put_nowait(evt)
        except Exception:
            logger.exception("publish drop sid=%s type=%s", sid, event_type)

async def subscribe(sid: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted lines for the given session.
    Use with StreamingResponse.
    """
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(sid, []).append(q)
    logger.info("SSE subscriber added sid=%s total_subs=%d", sid, len(_subscribers[sid]))
    try:
        # initial comment to open the stream
        yield ":ok\n\n"
        last_ping = time.time()
        while True:
            try:
                evt = await asyncio.wait_for(q.get(), timeout=15.0)
                data = json.dumps(evt, ensure_ascii=False)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                # keep-alive ping every ~15s
                if time.time() - last_ping >= 15:
                    yield ": ping\n\n"
                    last_ping = time.time()
            except Exception:
                logger.exception("SSE loop error sid=%s", sid)
                raise
    finally:
        try:
            _subscribers[sid].remove(q)
            cnt = len(_subscribers.get(sid, []))
            if cnt == 0:
                _subscribers.pop(sid, None)
            logger.info("SSE subscriber removed sid=%s remaining=%d", sid, cnt)
        except Exception:
            logger.exception("cleanup error for sid=%s", sid)
