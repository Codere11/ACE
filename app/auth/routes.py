import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .security import create_token, verify_token, verify_password
from app.core.db import get_db
from app.models.orm import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("ace.auth.routes")


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    # Find user by username
    user = db.query(User).filter(User.username == payload.username).first()
    
    if not user or not user.is_active:
        logger.info("Login failed for user '%s' (not found or inactive)", payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        logger.info("Login failed for user '%s' (invalid password)", payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Get organization info
    org_slug = user.organization.slug if user.organization else None
    
    # Create JWT token
    token = create_token(
        {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
            "organization_id": user.organization_id,
            "organization_slug": org_slug,
            # Backward compatibility
            "tenant_id": user.organization_id,
            "tenant_slug": org_slug
        }
    )
    
    logger.info("Login success for user '%s' (role=%s)", user.username, user.role)
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
            "organization_slug": org_slug,
            # Backward compatibility
            "tenant_id": user.organization_id,
            "tenant_slug": org_slug,
        },
    }


@router.get("/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    data = verify_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get full user info from database
    user_id = data.get("user_id")
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            org_slug = user.organization.slug if user.organization else None
            return {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "organization_id": user.organization_id,
                    "organization_slug": org_slug,
                }
            }
    
    # Fallback to token data only
    return {
        "user": {
            "username": data["sub"],
            "role": data["role"],
            "organization_id": data.get("organization_id") or data.get("tenant_id"),
            "organization_slug": data.get("organization_slug") or data.get("tenant_slug"),
        }
    }
