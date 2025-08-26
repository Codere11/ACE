from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Deque, Dict, List, Set, Tuple

logger = logging.getLogger("ace.event_bus")

# Subscribers for live SSE (topic = sid or "*")
_subscribers: Dict[str, Set[asyncio.Queue]] = {}
_lock = asyncio.Lock()

# --- Event history (enables long-polling) ------------------------------------
# Per-topic ring buffer of recent events: (seq, event_dict)
_hist: Dict[str, Deque[Tuple[int, dict]]] = {}
_seq: Dict[str, int] = {}
# Simple global notifier (avoids complex per-topic conditions)
_notify = asyncio.Event()

HIST_MAX = 500  # keep the last N events per topic


def _now() -> float:
    return time.time()


def _next_seq(topic: str) -> int:
    _seq[topic] = _seq.get(topic, 0) + 1
    return _seq[topic]


def _push_history(topic: str, evt: dict) -> int:
    seq = _next_seq(topic)
    dq = _hist.setdefault(topic, deque(maxlen=HIST_MAX))
    dq.append((seq, evt))
    return seq


async def subscribe(topic: str) -> asyncio.Queue:
    """Subscribe to live events (for SSE)."""
    q: asyncio.Queue = asyncio.Queue(maxsize=1024)
    async with _lock:
        _subscribers.setdefault(topic, set()).add(q)
        logger.info("event_bus: subscribe topic=%s subs=%d", topic, len(_subscribers[topic]))
    return q


async def unsubscribe(topic: str, q: asyncio.Queue) -> None:
    try:
        async with _lock:
            if topic in _subscribers and q in _subscribers[topic]:
                _subscribers[topic].remove(q)
                if not _subscribers[topic]:
                    _subscribers.pop(topic, None)
            logger.info("event_bus: unsubscribe topic=%s subs=%d", topic, len(_subscribers.get(topic, set())))
    except Exception:
        logger.exception("event_bus: unsubscribe failed topic=%s", topic)


async def publish(sid: str, event_name: str, payload: Any) -> int:
    """
    Publish to sid-specific topic and to "*" topic.
    - Feeds SSE queues.
    - Stores in history for long-polling.
    """
    evt = {"type": event_name, "sid": sid, "ts": _now(), "payload": payload}

    # History first (sid)
    _push_history(sid, evt)
    # History for broadcast topic
    _push_history("*", {**evt, "sid": sid})

    # Wake long-pollers
    _notify.set()
    _notify.clear()

    # Fan-out to live subscribers
    targets: Set[asyncio.Queue] = set()
    async with _lock:
        for topic in (sid, "*"):
            targets.update(_subscribers.get(topic, set()))

    sent = 0
    if targets:
        logger.info("event_bus: publish sid=%s event=%s targets=%d", sid, event_name, len(targets))
    for q in list(targets):
        try:
            q.put_nowait(evt)
            sent += 1
        except asyncio.QueueFull:
            logger.warning("event_bus: queue full sid=%s event=%s (drop)", sid, event_name)
        except Exception:
            logger.exception("event_bus: publish error sid=%s event=%s", sid, event_name)
    return sent


async def publish_all(event_name: str, payload: Any) -> int:
    evt = {"type": event_name, "sid": "*", "ts": _now(), "payload": payload}
    _push_history("*", evt)  # only on broadcast topic
    _notify.set()
    _notify.clear()

    targets: Set[asyncio.Queue] = set()
    async with _lock:
        for qs in _subscribers.values():
            targets.update(qs)

    sent = 0
    if targets:
        logger.info("event_bus: publish_all event=%s targets=%d", event_name, len(targets))
    for q in list(targets):
        try:
            q.put_nowait(evt)
            sent += 1
        except asyncio.QueueFull:
            logger.warning("event_bus: publish_all queue full event=%s (drop)", event_name)
        except Exception:
            logger.exception("event_bus: publish_all error event=%s", event_name)
    return sent


def _collect_since_one(topic: str, since: int) -> List[dict]:
    """Collect events from a single topic with seq > since, tagging seq."""
    out: List[dict] = []
    for seq, evt in _hist.get(topic, ()):
        if seq > since:
            out.append({**evt, "_seq": seq, "_topic": topic})
    return out


def collect_since(sid: str, since: int, limit: int = 200) -> List[dict]:
    """
    Immediate (non-blocking) fetch of recent events for:
      - the sid topic
      - the broadcast '*' topic
    """
    items = _collect_since_one(sid, since) + _collect_since_one("*", since)
    items.sort(key=lambda e: e["_seq"])
    if len(items) > limit:
        items = items[-limit:]
    return items


async def long_poll(sid: str, since: int, timeout: float = 20.0, limit: int = 200) -> List[dict]:
    """
    Long-poll: waits up to `timeout` seconds for new events beyond `since`.
    Always returns (possibly empty) list of events.
    """
    items = collect_since(sid, since, limit=limit)
    if items:
        return items

    try:
        await asyncio.wait_for(_notify.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        return []
    except Exception:
        logger.exception("event_bus: long_poll wait error sid=%s", sid)
        return []

    # After being notified, collect again
    return collect_since(sid, since, limit=limit)


def stats() -> Dict[str, int]:
    per = {topic: len(qs) for topic, qs in _subscribers.items()}
    per["__total__"] = sum(per.values())
    return per
