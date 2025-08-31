import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from .security import load_users, create_token, verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("ace.auth.routes")


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginIn):
    users = load_users()
    u = users.get(payload.username)
    if not u or u["password"] != payload.password:
        logger.info("Login failed for user '%s'", payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(
        {"sub": u["username"], "role": u["role"], "tenant_slug": u.get("tenant_slug")}
    )
    logger.info("Login success for user '%s' (role=%s)", u["username"], u["role"])
    return {
        "token": token,
        "user": {
            "username": u["username"],
            "role": u["role"],
            "tenant_slug": u.get("tenant_slug"),
        },
    }


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    data = verify_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "user": {
            "username": data["sub"],
            "role": data["role"],
            "tenant_slug": data.get("tenant_slug"),
        }
    }
