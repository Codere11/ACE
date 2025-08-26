from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.services import event_bus

logger = logging.getLogger("ace.api.chat_events")
router = APIRouter()

HEARTBEAT_SECS = 15.0


class EmitRequest(BaseModel):
    sid: str = "*"           # "*" broadcasts to everyone
    event: str               # e.g., "message.created"
    payload: Any | None = None


# ------------------------ SSE (kept, optional) -------------------------------

async def _sse_stream(topic: str):
    q = await event_bus.subscribe(topic)
    logger.info("SSE connect topic=%s", topic)
    try:
        yield ":ok\n\n"
        last_hb = time.time()
        while True:
            try:
                evt = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_SECS)
                data = json.dumps(evt, ensure_ascii=False)
                name = evt.get("type", "message")
                yield f"event: {name}\n"
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                now = time.time()
                if now - last_hb >= HEARTBEAT_SECS:
                    hb = {"ts": now, "topic": topic}
                    yield "event: heartbeat\n"
                    yield f"data: {json.dumps(hb)}\n\n"
                    last_hb = now
    finally:
        await event_bus.unsubscribe(topic, q)
        logger.info("SSE disconnect topic=%s", topic)


@router.get("/events", name="chat_events_stream")
async def chat_events_stream(sid: str = Query("*", min_length=1)):
    logger.info("GET /chat-events/events sid=%s (open)", sid)
    return StreamingResponse(
        _sse_stream(sid),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/events/", include_in_schema=False, name="chat_events_stream_slash")
async def chat_events_stream_slash(sid: str = Query("*", min_length=1)):
    return await chat_events_stream(sid=sid)


# ------------------------ LONG-POLL (no duplicates) --------------------------

@router.get("/since", name="chat_events_since")
def chat_events_since(
    sid: str = Query(..., min_length=1),
    since: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    """
    Immediate fetch of events with seq > since.
    Option B: returns ONLY the SID topic (no '*' merge) unless sid='*'.
    """
    include_broadcast = (sid == "*")
    items = event_bus.collect_since(sid, since, limit=limit, include_broadcast=include_broadcast)
    next_seq = max([e.get("_seq", since) for e in items], default=since)
    for e in items:
        e.pop("_topic", None)
    logger.info("GET /chat-events/since sid=%s since=%d -> %d ev, next=%d", sid, since, len(items), next_seq)
    return {"ok": True, "events": items, "next": next_seq}


@router.get("/poll", name="chat_events_poll")
async def chat_events_poll(
    sid: str = Query(..., min_length=1),
    since: int = Query(0, ge=0),
    timeout: float = Query(20.0, ge=0.0, le=60.0),
    limit: int = Query(200, ge=1, le=500),
):
    """
    Long-poll: waits up to `timeout` seconds for new events with seq > since.
    Option B: returns ONLY the SID topic (no '*' merge) unless sid='*'.
    Always completes quickly and never 'hangs the page'.
    """
    include_broadcast = (sid == "*")
    items = await event_bus.long_poll(
        sid, since, timeout=timeout, limit=limit, include_broadcast=include_broadcast
    )
    next_seq = max([e.get("_seq", since) for e in items], default=since)
    for e in items:
        e.pop("_topic", None)
    logger.info("GET /chat-events/poll sid=%s since=%d timeout=%.1f -> %d ev, next=%d",
                sid, since, timeout, len(items), next_seq)
    return {"ok": True, "events": items, "next": next_seq}


# ------------------------ Utilities & Debug ----------------------------------

@router.get("/test", name="chat_events_test")
async def chat_events_test(sid: str = Query(..., min_length=1)):
    payload = {"sid": sid, "note": "test", "ts": time.time()}
    sent = await event_bus.publish(sid, "message.test", payload)
    logger.info("SSE/LP test sid=%s published=%d", sid, sent)
    return {"ok": True, "published": sent}


@router.post("/emit", name="chat_events_emit")
async def chat_events_emit(body: EmitRequest):
    if body.sid == "*":
        sent = await event_bus.publish_all(body.event, body.payload)
    else:
        sent = await event_bus.publish(body.sid, body.event, body.payload)
    logger.info("SSE/LP emit sid=%s event=%s published=%d", body.sid, body.event, sent)
    return {"ok": True, "published": sent}


@router.get("/tick", name="chat_events_tick")
async def chat_events_tick():
    sent = await event_bus.publish_all("heartbeat", {"ts": time.time()})
    logger.info("heartbeat published=%d", sent)
    return {"ok": True, "published": sent}


@router.get("/debug", name="chat_events_debug")
def chat_events_debug(sid: str = Query("*", min_length=1)):
    # This debug page uses long-polling (so it never blocks page load)
    html = f"""<!doctype html>
<meta charset="utf-8"/>
<title>ACE Live Debug</title>
<body style="font:14px/1.4 system-ui, sans-serif">
  <h3>Live Debug — topic: <code>{sid}</code></h3>
  <p>This page uses <b>long-polling</b> (not SSE) to avoid hanging issues.</p>
  <pre id="log" style="max-height:70vh;overflow:auto;border:1px solid #ccc;padding:8px"></pre>
  <script>
    const log = document.getElementById('log');
    function line(s) {{
      log.textContent += s + '\\n';
      log.scrollTop = log.scrollHeight;
    }}
    let next = 0;
    async function poll() {{
      try {{
        const r = await fetch(`/chat-events/poll?sid={sid}&since=${{next}}&timeout=20`);
        const j = await r.json();
        if (j.ok) {{
          for (const e of j.events) {{
            line(`[${{e.type}}] ` + JSON.stringify(e));
            next = Math.max(next, e._seq || 0);
          }}
        }} else {{
          line('! bad response');
        }}
      }} catch (err) {{
        line('! error ' + err);
      }} finally {{
        setTimeout(poll, 200); // short gap
      }}
    }}
    line('starting long-poll… sid={sid}');
    poll();
  </script>
</body>"""
    return HTMLResponse(html)


@router.get("/debug/", include_in_schema=False, name="chat_events_debug_slash")
def chat_events_debug_slash(sid: str = Query("*", min_length=1)):
    return chat_events_debug(sid=sid)
