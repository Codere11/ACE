import os
import json
import logging
import jwt
import time
import threading
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

# ----- Locks
_users_lock = threading.Lock()

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

# ----- Users helpers (file-based)
_DEFAULT_USERS = {
    "users": [
        { "username": "admin", "password": "admin123", "role": "admin", "tenant_slug": None },
        { "username": "demo",  "password": "demo123",  "role": "manager", "tenant_slug": "demo-agency" }
    ]
}

def _read_users_list() -> list[dict]:
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            users = data.get("users", [])
            if isinstance(users, list):
                return users
        except Exception as e:
            logger.error("Failed to read %s: %s", USERS_FILE, e)
    logger.warning("Using fallback users (no users_seed.json found or invalid).")
    return _DEFAULT_USERS["users"].copy()

def _write_users_list(users: list[dict]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".json.tmp")
    with _users_lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({ "users": users }, f, ensure_ascii=False, indent=2)
        os.replace(tmp, USERS_FILE)  # atomic on POSIX
    logger.info("Wrote %d users to %s", len(users), USERS_FILE)

def _load_users_map() -> dict:
    users = _read_users_list()
    return {u["username"]: u for u in users}

# ---------- Routers
router = APIRouter()
auth_router = APIRouter(prefix="/api/auth", tags=["PortalAuth"])
public_router = APIRouter(tags=["PortalPublic"])

# ----- Auth endpoints (login + me + debug)
@auth_router.post("/login")
def login(payload: dict):
    username = (payload or {}).get("username", "")
    password = (payload or {}).get("password", "")
    users = _load_users_map()
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

@auth_router.get("/debug-users")
def debug_users():
    users = _read_users_list()
    return {"usernames": [u.get("username") for u in users], "source": str(USERS_FILE)}

# ----- Admin: customers list (extended to include usernames bound to tenant_slug)
@router.get("/api/admin/customers", tags=["PortalAdmin"])
def list_customers(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    out = []
    users_map = _load_users_map()
    users_by_tenant: dict[str, list[str]] = {}
    for u in users_map.values():
        slug = u.get("tenant_slug")
        if slug:
            users_by_tenant.setdefault(slug, []).append(u["username"])
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
            "users": sorted(users_by_tenant.get(inst_dir.name, [])),
            "chatbot_url": f"/instances/{inst_dir.name}/chatbot/",
        })
    return {"customers": out}

# ----- Admin: update customer profile (business name, contact, last_paid)
@router.patch("/api/admin/customers/{slug}/profile", tags=["PortalAdmin"])
def update_customer_profile(slug: str, payload: dict, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
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

    # Merge updates
    display_name = payload.get("display_name")
    last_paid = payload.get("last_paid")
    contact = payload.get("contact") or {}

    if display_name is not None:
        profile["display_name"] = display_name
    if last_paid is not None:
        profile["last_paid"] = last_paid
    if "contact" not in profile or not isinstance(profile.get("contact"), dict):
        profile["contact"] = {}
    for k in ("name", "email", "phone"):
        if k in contact:
            profile["contact"][k] = contact[k]

    # Write back
    inst.mkdir(parents=True, exist_ok=True)
    with open(profile_file, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    logger.info("Updated profile for %s", slug)
    return {"ok": True, "profile": profile}

# ----- Admin: users CRUD
@router.get("/api/admin/users", tags=["PortalAdmin"])
def admin_list_users(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    users = _read_users_list()
    # Do not return passwords
    sanitized = [{"username": u["username"], "role": u.get("role"), "tenant_slug": u.get("tenant_slug")} for u in users]
    return {"users": sanitized}

@router.post("/api/admin/users", tags=["PortalAdmin"])
def admin_create_user(payload: dict, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    username = (payload or {}).get("username")
    password = (payload or {}).get("password")
    role = (payload or {}).get("role", "manager")
    tenant_slug = (payload or {}).get("tenant_slug")

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")
    if role not in ("admin", "manager"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'manager'")

    users = _read_users_list()
    if any(u["username"] == username for u in users):
        raise HTTPException(status_code=409, detail="Username already exists")

    users.append({"username": username, "password": password, "role": role, "tenant_slug": tenant_slug})
    _write_users_list(users)
    logger.info("Created user '%s' (role=%s, tenant=%s)", username, role, tenant_slug)
    return {"ok": True}

@router.patch("/api/admin/users/{username}", tags=["PortalAdmin"])
def admin_update_user(username: str, payload: dict, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    users = _read_users_list()
    for u in users:
        if u["username"] == username:
            if "password" in payload and payload["password"]:
                u["password"] = payload["password"]
            if "role" in payload:
                if payload["role"] not in ("admin", "manager"):
                    raise HTTPException(status_code=400, detail="role must be 'admin' or 'manager'")
                u["role"] = payload["role"]
            if "tenant_slug" in payload:
                u["tenant_slug"] = payload["tenant_slug"]
            _write_users_list(users)
            logger.info("Updated user '%s'", username)
            return {"ok": True}
    raise HTTPException(status_code=404, detail="User not found")

@router.delete("/api/admin/users/{username}", tags=["PortalAdmin"])
def admin_delete_user(username: str, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete built-in admin")

    users = _read_users_list()
    new_users = [u for u in users if u["username"] != username]
    if len(new_users) == len(users):
        raise HTTPException(status_code=404, detail="User not found")
    _write_users_list(new_users)
    logger.info("Deleted user '%s'", username)
    return {"ok": True}

# ----- Public: per-instance flow for static chatbot
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
