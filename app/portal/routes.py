import os
import json
import logging
import jwt
import time
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from app.core import config as user_config

logger = logging.getLogger("ace.portal")

# ----- Paths
ROOT_DIR = Path(user_config.ROOT_DIR)  # ACE-Campaign/
INSTANCES_DIR = ROOT_DIR / "instances"
USERS_FILE = ROOT_DIR / "app" / "portal" / "users_seed.json"

# ----- Auth settings
SECRET_KEY = os.getenv("ACE_SECRET", "dev-secret-change-me")
ALGO = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("ACE_JWT_EXPIRE_MIN", "1440"))  # 1 day

def _create_token(payload: dict) -> str:
    now = int(time.time())
    exp = now + JWT_EXPIRE_MIN * 60
    return jwt.encode({**payload, "iat": now, "exp": exp}, SECRET_KEY, algorithm=ALGO)

def _verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        return None

def _require_auth(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    data = _verify_token(authorization.split(" ", 1)[1])
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return data

# ----- User loading with safe fallback
_DEFAULT_USERS = {
    "users": [
        { "username": "admin", "password": "admin123", "role": "admin", "tenant_slug": None },
        { "username": "demo",  "password": "demo123",  "role": "manager", "tenant_slug": "demo-agency" }
    ]
}

def _load_users() -> dict:
    # Optional override via env (JSON string)
    env_json = os.getenv("ACE_DEFAULT_USERS_JSON")
    if env_json:
        try:
            data = json.loads(env_json)
            logger.warning("Using users from ACE_DEFAULT_USERS_JSON env var.")
            return {u["username"]: u for u in data.get("users", [])}
        except Exception as e:
            logger.error("Invalid ACE_DEFAULT_USERS_JSON: %s", e)

    # Load from seed file
    try:
        if USERS_FILE.exists():
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            users = {u["username"]: u for u in data.get("users", [])}
            logger.info("Loaded %d users from %s", len(users), USERS_FILE)
            return users
        else:
            logger.warning("users_seed.json not found at %s — using fallback users.", USERS_FILE)
    except Exception as e:
        logger.error("Failed to read users_seed.json: %s — using fallback users.", e)

    # Fallback users (dev)
    users = {u["username"]: u for u in _DEFAULT_USERS["users"]}
    return users

# ---------- Routers
router = APIRouter()
auth_router = APIRouter(prefix="/api/auth", tags=["PortalAuth"])
public_router = APIRouter(tags=["PortalPublic"])

# ----- Auth endpoints (login + me + debug)
@auth_router.post("/login")
def login(payload: dict):
    username = (payload or {}).get("username", "")
    password = (payload or {}).get("password", "")
    users = _load_users()
    u = users.get(username)
    if not u or u.get("password") != password:
        logger.info("Portal login failed for '%s'", username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_token({"sub": u["username"], "role": u["role"], "tenant_slug": u.get("tenant_slug")})
    logger.info("Portal login success for '%s' (role=%s)", u["username"], u["role"])
    return {"token": token, "user": {"username": u["username"], "role": u["role"], "tenant_slug": u.get("tenant_slug")}}

@auth_router.get("/me")
def me(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    return {"user": {"username": data["sub"], "role": data["role"], "tenant_slug": data.get("tenant_slug")}}

# DEV ONLY helper — returns list of usernames it sees (no passwords)
@auth_router.get("/debug-users")
def debug_users():
    users = _load_users()
    return {"usernames": sorted(list(users.keys())), "source": str(USERS_FILE)}

# ----- Admin / Manager endpoints using instances/* files
@router.get("/api/admin/customers", tags=["PortalAdmin"])
def list_customers(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    out = []
    if not INSTANCES_DIR.exists():
        return {"customers": out}
    for inst_dir in INSTANCES_DIR.glob("*"):
        if not inst_dir.is_dir():
            continue
        profile_file = inst_dir / "profile.json"
        profile = {}
        if profile_file.exists():
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    profile = json.load(f)
            except Exception as e:
                logger.error("Failed to read %s: %s", profile_file, e)
        out.append({
            "slug": inst_dir.name,
            "display_name": profile.get("display_name", inst_dir.name),
            "last_paid": profile.get("last_paid"),
            "contact": profile.get("contact", {}),
            "chatbot_url": f"/instances/{inst_dir.name}/chatbot/",
        })
    return {"customers": out}

@router.get("/api/manager/my-instance", tags=["PortalManager"])
def my_instance(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager or admin")
    slug = data.get("tenant_slug")
    if not slug:
        raise HTTPException(status_code=400, detail="No tenant assigned")
    inst = INSTANCES_DIR / slug
    if not inst.exists():
        raise HTTPException(status_code=404, detail="Instance not found")
    profile_file = inst / "profile.json"
    profile = {}
    if profile_file.exists():
        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except Exception as e:
            logger.error("Failed to read %s: %s", profile_file, e)
    return {"slug": slug, "display_name": profile.get("display_name", slug), "chatbot_url": f"/instances/{slug}/chatbot/"}

# Public: per-instance flow for static chatbot
@public_router.get("/api/instances/{slug}/conversation_flow")
def conversation_flow(slug: str):
    inst = INSTANCES_DIR / slug
    if not inst.exists():
        raise HTTPException(status_code=404, detail="Instance not found")
    flow_file = inst / "conversation_flow.json"
    if not flow_file.exists():
        raise HTTPException(status_code=404, detail="conversation_flow.json not found")
    try:
        with open(flow_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read %s: %s", flow_file, e)
        raise HTTPException(status_code=500, detail="Failed to read flow")

# helper to mount static chatbots, called from main
def mount_instance_chatbots(app):
    if not INSTANCES_DIR.exists():
        logger.warning("Instances dir not found: %s", INSTANCES_DIR)
        return
    for inst_dir in INSTANCES_DIR.glob("*"):
        chatbot_path = inst_dir / "chatbot"
        if chatbot_path.exists():
            mount_path = f"/instances/{inst_dir.name}/chatbot"
            app.mount(mount_path, StaticFiles(directory=str(chatbot_path), html=True), name=f"chatbot-{inst_dir.name}")
            logger.info("Mounted chatbot %s -> %s", mount_path, chatbot_path)
