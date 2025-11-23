# app/api/org_avatar.py
"""
Public endpoint to get organization's avatar (for chatbot display).
Returns the avatar of the organization's primary admin.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.orm import Organization, User

router = APIRouter(prefix="/api/organizations", tags=["public"])


@router.get("/{org_slug}/avatar")
def get_organization_avatar(
    org_slug: str,
    db: Session = Depends(get_db)
):
    """
    Get the avatar URL for an organization's primary representative.
    This is public so chatbots can display the agent's photo.
    
    Returns the avatar_url of the first active admin user found,
    or null if no avatar is set.
    """
    # Find organization
    org = db.query(Organization).filter(
        Organization.slug == org_slug,
        Organization.active == True
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Find first active admin user with an avatar
    admin_with_avatar = db.query(User).filter(
        User.organization_id == org.id,
        User.role == "org_admin",
        User.is_active == True,
        User.avatar_url.isnot(None)
    ).first()
    
    if admin_with_avatar:
        return {
            "avatar_url": admin_with_avatar.avatar_url,
            "organization_name": org.name
        }
    
    # Fallback: return any admin even without avatar
    any_admin = db.query(User).filter(
        User.organization_id == org.id,
        User.role == "org_admin",
        User.is_active == True
    ).first()
    
    if any_admin:
        return {
            "avatar_url": None,
            "organization_name": org.name
        }
    
    raise HTTPException(
        status_code=404, 
        detail="No active administrator found for this organization"
    )
