from __future__ import annotations

import time
import threading
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Optional, List

logger = logging.getLogger("ace.session")

class SessionMode(str, Enum):
    BOT = "bot"
    HUMAN = "human"
    HYBRID = "hybrid"

@dataclass
class SessionState:
    sid: str
    mode: SessionMode = SessionMode.BOT
    claimed_by: Optional[str] = None
    claimed_at: Optional[float] = None
    updated_at: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d

_SESSIONS: Dict[str, SessionState] = {}
_LOCK = threading.Lock()

def _now() -> float:
    return time.time()

def _ensure(sid: str) -> SessionState:
    with _LOCK:
        st = _SESSIONS.get(sid)
        if st is None:
            st = SessionState(sid=sid)
            _SESSIONS[sid] = st
            logger.debug("session created sid=%s", sid)
        return st

def status(sid: str) -> SessionState:
    st = _ensure(sid)
    logger.debug("status sid=%s mode=%s claimed_by=%s", sid, st.mode.value, st.claimed_by)
    return st

def claim(sid: str, agent_id: str, *, force: bool = False) -> SessionState:
    if not agent_id:
        raise ValueError("agent_id is required")
    with _LOCK:
        st = _ensure(sid)
        if st.claimed_by and st.claimed_by != agent_id and not force:
            logger.warning("claim conflict sid=%s current=%s requester=%s", sid, st.claimed_by, agent_id)
            raise RuntimeError(f"session {sid} already claimed by {st.claimed_by}")
        st.mode = SessionMode.HUMAN
        st.claimed_by = agent_id
        st.claimed_at = _now()
        st.updated_at = st.claimed_at
        logger.info("claimed sid=%s by=%s", sid, agent_id)
        return st

def release(sid: str, *, agent_id: Optional[str] = None, force: bool = False) -> SessionState:
    with _LOCK:
        st = _ensure(sid)
        if st.claimed_by and agent_id and st.claimed_by != agent_id and not force:
            logger.warning("release denied sid=%s owner=%s requester=%s", sid, st.claimed_by, agent_id)
            raise RuntimeError(f"cannot release session {sid}: owned by {st.claimed_by}")
        st.mode = SessionMode.BOT
        st.claimed_by = None
        st.claimed_at = None
        st.updated_at = _now()
        logger.info("released sid=%s", sid)
        return st

def is_human_mode(sid: str) -> bool:
    human = status(sid).mode == SessionMode.HUMAN
    logger.debug("is_human_mode sid=%s -> %s", sid, human)
    return human

def list_active() -> List[SessionState]:
    with _LOCK:
        lst = list(_SESSIONS.values())
    logger.debug("list_active count=%d", len(lst))
    return lst
