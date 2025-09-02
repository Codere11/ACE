import os
import json
import logging
import jwt
import time
import shutil
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core import config as user_config
from app.services.db import SessionLocal
from app.models import User, Tenant, ConversationFlow
from app.services.security import hash_password, verify_password

logger = logging.getLogger("ace.portal")

# ----- Paths
ROOT_DIR = Path(user_config.ROOT_DIR)   # ACE-Campaign/
INSTANCES_DIR = ROOT_DIR / "instances"

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

router = APIRouter()
auth_router = APIRouter(prefix="/api/auth", tags=["PortalAuth"])
public_router = APIRouter(tags=["PortalPublic"])

# -------------------- AUTH (DB-backed) --------------------
@auth_router.post("/login")
def login(payload: dict):
    username = (payload or {}).get("username", "")
    password = (payload or {}).get("password", "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")

    with SessionLocal() as db:
        u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not u or not verify_password(password, u.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        tenant_slug = None
        if u.tenant_id:
            t = db.get(Tenant, u.tenant_id)
            tenant_slug = t.slug if t else None

        token = _create_token({"sub": u.username, "role": u.role, "tenant_slug": tenant_slug})
        logger.info("Portal login success for '%s' (role=%s)", u.username, u.role)
        return {"token": token, "user": {"username": u.username, "role": u.role, "tenant_slug": tenant_slug}}

@auth_router.get("/me")
def me(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    return {"user": {"username": data["sub"], "role": data["role"], "tenant_slug": data.get("tenant_slug")}}

# -------------------- Admin: CUSTOMERS (DB-backed Tenants) --------------------
@router.get("/api/admin/customers", tags=["PortalAdmin"])
def list_customers(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    out = []
    with SessionLocal() as db:
        tenants = db.execute(select(Tenant)).scalars().all()
        users = db.execute(select(User)).scalars().all()

        users_by_tenant: dict[int, list[str]] = {}
        for u in users:
            if u.tenant_id:
                users_by_tenant.setdefault(u.tenant_id, []).append(u.username)

        for t in tenants:
            out.append({
                "slug": t.slug,
                "display_name": t.display_name or t.slug,
                "last_paid": t.last_paid.isoformat() if t.last_paid else None,
                "contact": {"name": t.contact_name, "email": t.contact_email, "phone": t.contact_phone},
                "users": sorted(users_by_tenant.get(t.id, [])),
                "chatbot_url": f"/instances/{t.slug}/chatbot/",
            })
    return {"customers": out}

@router.post("/api/admin/customers", tags=["PortalAdmin"])
def create_customer(payload: dict, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    slug = (payload or {}).get("slug")
    if not slug:
        raise HTTPException(status_code=400, detail="slug is required")
    slug = slug.strip().lower()

    display_name = (payload or {}).get("display_name") or slug
    last_paid_str = (payload or {}).get("last_paid")
    contact = (payload or {}).get("contact") or {}

    lp = None
    if last_paid_str:
        try:
            y, m, d = [int(x) for x in last_paid_str.split("-")]
            lp = date(y, m, d)
        except Exception:
            raise HTTPException(status_code=400, detail="last_paid must be YYYY-MM-DD")

    with SessionLocal() as db:
        t = Tenant(
            slug=slug,
            display_name=display_name,
            last_paid=lp,
            contact_name=contact.get("name"),
            contact_email=contact.get("email"),
            contact_phone=contact.get("phone"),
        )
        db.add(t)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Tenant slug already exists")

        # optional manager user
        cu = (payload or {}).get("create_user")
        if isinstance(cu, dict) and cu.get("username") and cu.get("password"):
            u = User(
                username=cu["username"],
                password_hash=hash_password(cu["password"]),
                role=cu.get("role", "manager"),
                tenant_id=t.id
            )
            db.add(u)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=409, detail="Username already exists")

        # default flow in DB
        default_flow = {"greetings": ["Živjo! Kako vam lahko pomagam danes?"], "intents": [], "responses": {}}
        db.add(ConversationFlow(tenant_id=t.id, flow=default_flow))
        db.commit()

    _ensure_instance_static(slug)  # keep static chatbot folder so link works
    return {"ok": True}

@router.patch("/api/admin/customers/{slug}/profile", tags=["PortalAdmin"])
def update_customer_profile(slug: str, payload: dict, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    with SessionLocal() as db:
        t = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if "display_name" in payload:
            t.display_name = payload.get("display_name")
        if "last_paid" in payload:
            val = payload.get("last_paid")
            if val:
                try:
                    y, m, d = [int(x) for x in val.split("-")]
                    t.last_paid = date(y, m, d)
                except Exception:
                    raise HTTPException(status_code=400, detail="last_paid must be YYYY-MM-DD")
            else:
                t.last_paid = None
        if "contact" in payload and isinstance(payload["contact"], dict):
            c = payload["contact"]
            if "name" in c: t.contact_name = c.get("name")
            if "email" in c: t.contact_email = c.get("email")
            if "phone" in c: t.contact_phone = c.get("phone")
        db.commit()

    return {"ok": True}

@router.delete("/api/admin/customers/{slug}", tags=["PortalAdmin"])
def delete_customer(slug: str, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    with SessionLocal() as db:
        t = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Tenant not found")
        db.delete(t)  # cascades to users/flows
        db.commit()

    inst_dir = INSTANCES_DIR / slug
    if inst_dir.exists():
        shutil.rmtree(inst_dir)
    return {"ok": True}

# -------------------- Admin: USERS (DB-backed) --------------------
@router.get("/api/admin/users", tags=["PortalAdmin"])
def admin_list_users(authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    with SessionLocal() as db:
        rows = db.execute(select(User)).scalars().all()
        out = []
        for u in rows:
            slug = None
            if u.tenant_id:
                t = db.get(Tenant, u.tenant_id)
                slug = t.slug if t else None
            out.append({"username": u.username, "role": u.role, "tenant_slug": slug})
        return {"users": out}

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

    with SessionLocal() as db:
        tenant_id = None
        if tenant_slug:
            t = db.execute(select(Tenant).where(Tenant.slug == tenant_slug)).scalar_one_or_none()
            if not t:
                raise HTTPException(status_code=404, detail="tenant_slug not found")
            tenant_id = t.id

        u = User(username=username, password_hash=hash_password(password), role=role, tenant_id=tenant_id)
        db.add(u)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Username already exists")

    return {"ok": True}

@router.patch("/api/admin/users/{username}", tags=["PortalAdmin"])
def admin_update_user(username: str, payload: dict, authorization: str | None = Header(default=None)):
    data = _require_auth(authorization)
    if data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    with SessionLocal() as db:
        u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")

        if "password" in payload and payload["password"]:
            u.password_hash = hash_password(payload["password"])
        if "role" in payload:
            if payload["role"] not in ("admin", "manager"):
                raise HTTPException(status_code=400, detail="role must be 'admin' or 'manager'")
            u.role = payload["role"]
        if "tenant_slug" in payload:
            slug = payload["tenant_slug"]
            if slug:
                t = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
                if not t:
                    raise HTTPException(status_code=404, detail="tenant_slug not found")
                u.tenant_id = t.id
            else:
                u.tenant_id = None
        db.commit()

    return {"ok": True}

# -------------------- Public: per-instance flow from FS (unchanged) --------------------
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

# -------------------- Static mounting helpers --------------------
def _ensure_instance_static(slug: str):
    inst = INSTANCES_DIR / slug
    (inst / "chatbot").mkdir(parents=True, exist_ok=True)
    index = inst / "chatbot" / "index.html"
    if not index.exists():
        index.write_text(
            f"<!doctype html><html><body><h3>ACE Chatbot for {slug}</h3></body></html>", encoding="utf-8"
        )

def mount_instance_chatbots(app):
    if not INSTANCES_DIR.exists():
        return
    for inst_dir in INSTANCES_DIR.glob("*"):
        chatbot_path = inst_dir / "chatbot"
        if chatbot_path.exists():
            mount_path = f"/instances/{inst_dir.name}/chatbot"
            app.mount(mount_path, StaticFiles(directory=str(chatbot_path), html=True), name=f"chatbot-{inst_dir.name}")
            logger.info("Mounted chatbot %s -> %s", mount_path, chatbot_path)
