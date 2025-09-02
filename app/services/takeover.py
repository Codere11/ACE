# app/services/takeover.py
from __future__ import annotations
import time
import threading
from typing import Optional

# default takeover window (seconds). Adjust if you like.
DEFAULT_TTL = 15 * 60

_lock = threading.Lock()
# sid -> expires_at (unix seconds)
_registry: dict[str, int] = {}

def enable(sid: str, ttl: int = DEFAULT_TTL) -> None:
    """Enter human mode for this sid."""
    now = int(time.time())
    with _lock:
        _registry[sid] = now + ttl

def is_active(sid: Optional[str]) -> bool:
    """Return True if this sid is in human mode (not expired)."""
    if not sid:
        return False
    now = int(time.time())
    with _lock:
        exp = _registry.get(sid)
        if not exp:
            return False
        if exp < now:
            # expired, clean up
            try:
                del _registry[sid]
            except KeyError:
                pass
            return False
        return True

def touch(sid: str, ttl: int = DEFAULT_TTL) -> None:
    """Refresh the takeover window for this sid."""
    enable(sid, ttl=ttl)

def disable(sid: str) -> None:
    """Exit human mode for this sid."""
    with _lock:
        _registry.pop(sid, None)

def clear_all() -> None:
    """Utility for tests."""
    with _lock:
        _registry.clear()
