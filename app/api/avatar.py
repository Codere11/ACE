# app/api/avatar.py
"""
User avatar upload endpoint.
"""

import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from PIL import Image
import io

from app.core.db import get_db
from app.models.orm import User
from app.auth.permissions import AuthContext, get_auth_context

router = APIRouter(prefix="/api/users", tags=["avatar"])

# Directory to store avatars
AVATAR_DIR = Path("static/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Upload profile picture for the current user.
    Accepts images up to 5MB.
    Returns the avatar URL.
    """
    # Validate file type
    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Validate it's actually an image
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file"
        )
    
    # Reopen image for processing (verify() closes it)
    img = Image.open(io.BytesIO(content))
    
    # Resize to max 512x512 while maintaining aspect ratio
    img.thumbnail((512, 512), Image.Resampling.LANCZOS)
    
    # Generate unique filename
    file_ext = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
    file_path = AVATAR_DIR / unique_filename
    
    # Save the resized image
    img.save(file_path, optimize=True, quality=85)
    
    # Delete old avatar if exists
    user = db.query(User).filter(User.id == auth.user_id).first()
    if user and user.avatar_url:
        old_path = Path(user.avatar_url.lstrip("/"))
        if old_path.exists():
            try:
                old_path.unlink()
            except Exception:
                pass  # Ignore deletion errors
    
    # Update user record
    avatar_url = f"/static/avatars/{unique_filename}"
    if user:
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
    
    return {
        "avatar_url": avatar_url,
        "message": "Avatar uploaded successfully"
    }


@router.delete("/me/avatar")
def delete_avatar(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Delete the current user's avatar.
    """
    user = db.query(User).filter(User.id == auth.user_id).first()
    
    if not user or not user.avatar_url:
        raise HTTPException(status_code=404, detail="No avatar to delete")
    
    # Delete file from disk
    avatar_path = Path(user.avatar_url.lstrip("/"))
    if avatar_path.exists():
        try:
            avatar_path.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete avatar file: {e}")
    
    # Remove from database
    user.avatar_url = None
    db.commit()
    
    return {"message": "Avatar deleted successfully"}
