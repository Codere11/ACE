from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Deque, Dict, List, Set, Tuple

logger = logging.getLogger("ace.event_bus")

# Live subscribers for SSE (topic = sid or "*")
_subscribers: Dict[str, Set[asyncio.Queue]] = {}
_lock = asyncio.Lock()

# -------- Event history (for long-polling) -----------------------------------
# Per-topic ring buffer of recent events: (seq, event_dict)
_hist: Dict[str, Deque[Tuple[int, dict]]] = {}
_seq: Dict[str, int] = {}
_notify = asyncio.Event()  # global notifier to wake long-pollers

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


# ----------------------------- Live subscribe API ----------------------------

async def subscribe(topic: str) -> asyncio.Queue:
    """
    Subscribe to a topic (sid or "*") for SSE.
    Returns an asyncio.Queue where events will be delivered.
    """
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


# ------------------------------ Publish API ----------------------------------

async def publish(sid: str, event_name: str, payload: Any) -> int:
    """
    Publish to sid-specific topic and to "*" topic.
    - Feeds SSE queues.
    - Stores in history for long-polling.
    """
    evt = {"type": event_name, "sid": sid, "ts": _now(), "payload": payload}

    # History first (sid + broadcast)
    _push_history(sid, evt)
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
    _push_history("*", evt)  # only broadcast topic gets it
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


# --------------------------- Long-poll helpers --------------------------------

def _collect_since_one(topic: str, since: int) -> List[dict]:
    """Collect events from a single topic with seq > since, tagging seq & topic."""
    out: List[dict] = []
    for seq, evt in _hist.get(topic, ()):
        if seq > since:
            out.append({**evt, "_seq": seq, "_topic": topic})
    return out


def collect_since(
    sid: str,
    since: int,
    limit: int = 200,
    include_broadcast: bool = False,
) -> List[dict]:
    """
    Immediate fetch of recent events.
    Option B (no duplicates): by default we do NOT merge '*' unless explicitly asked.
    - If sid == "*": read only broadcast topic.
    - Else: read only `sid` topic; include '*' only if include_broadcast=True.
    """
    if sid == "*":
        topics = ["*"]
    else:
        topics = [sid] + (["*"] if include_broadcast else [])

    items: List[dict] = []
    for t in topics:
        items.extend(_collect_since_one(t, since))

    items.sort(key=lambda e: e["_seq"])
    if len(items) > limit:
        items = items[-limit:]
    return items


async def long_poll(
    sid: str,
    since: int,
    timeout: float = 20.0,
    limit: int = 200,
    include_broadcast: bool = False,
) -> List[dict]:
    """
    Long-poll: waits up to `timeout` seconds for new events beyond `since`.
    Always returns (possibly empty) list of events.
    """
    items = collect_since(sid, since, limit=limit, include_broadcast=include_broadcast)
    if items:
        return items

    try:
        await asyncio.wait_for(_notify.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.info("event_bus: long_poll timeout sid=%s since=%d", sid, since)
        return []
    except Exception:
        logger.exception("event_bus: long_poll wait error sid=%s", sid)
        return []

    # After being notified, collect again
    return collect_since(sid, since, limit=limit, include_broadcast=include_broadcast)


# ------------------------------ Introspection --------------------------------

def stats() -> Dict[str, int]:
    """Current SSE subscriber counts per topic (live)."""
    per = {topic: len(qs) for topic, qs in _subscribers.items()}
    per["__total__"] = sum(per.values())
    return per
