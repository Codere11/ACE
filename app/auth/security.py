import os
import time
import json
import jwt
import logging
from typing import Optional
from pathlib import Path

# Do NOT import/modify your config.py for secrets; keep it self-contained
SECRET_KEY = os.getenv("ACE_SECRET", "dev-secret-change-me")  # override in prod
JWT_EXPIRE_MIN = int(os.getenv("ACE_JWT_EXPIRE_MIN", "1440"))  # 1 day
ALGO = "HS256"

# Resolve repo root (ACE-Campaign/) and users seed path
HERE = Path(__file__).resolve()
APP_DIR = HERE.parents[1]          # .../ACE-Campaign/app
ROOT_DIR = APP_DIR.parent          # .../ACE-Campaign
USERS_FILE = ROOT_DIR / "app" / "auth" / "users_seed.json"

logger = logging.getLogger("ace.auth")


def load_users() -> dict:
    """
    Load test users from users_seed.json.
    Returns a dict keyed by username: { username: {...} }
    """
    if not USERS_FILE.exists():
        logger.error("Users seed file not found at %s", USERS_FILE)
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    users = {u["username"]: u for u in data.get("users", [])}
    logger.debug("Loaded %d users from seed", len(users))
    return users


def create_token(payload: dict) -> str:
    now = int(time.time())
    exp = now + JWT_EXPIRE_MIN * 60
    to_encode = {**payload, "iat": now, "exp": exp}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGO)
    return token


def verify_token(token: str) -> Optional[dict]:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        return data
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        return None
