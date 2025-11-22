import os
import time
import jwt
import logging
from typing import Optional
import bcrypt

# Do NOT import/modify your config.py for secrets; keep it self-contained
SECRET_KEY = os.getenv("ACE_SECRET", "dev-secret-change-me")  # override in prod
JWT_EXPIRE_MIN = int(os.getenv("ACE_JWT_EXPIRE_MIN", "1440"))  # 1 day
ALGO = "HS256"

logger = logging.getLogger("ace.auth")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.warning("Password verification failed: %s", e)
        return False


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
