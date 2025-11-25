# app/api/organizations.py
"""
Organization management API endpoints.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.orm import Organization
from app.models.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse
)
from app.auth.permissions import AuthContext, require_org_admin

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=List[OrganizationResponse])
def list_organizations(
    skip: int = 0,
    limit: int = 100,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    List all organizations.
    Only accessible by org admins (for now - later can add super admin).
    """
    # For now, users can only see their own organization
    # TODO: Add super admin role for cross-org access
    orgs = db.query(Organization).filter(
        Organization.id == auth.organization_id
    ).offset(skip).limit(limit).all()
    
    return orgs


@router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new organization.
    
    NOTE: This endpoint is currently unprotected for initial setup.
    In production, this should only be accessible by super admins.
    """
    # Check if slug already exists
    existing = db.query(Organization).filter(
        Organization.slug == payload.slug
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Organization with slug '{payload.slug}' already exists"
        )
    
    org = Organization(
        name=payload.name,
        slug=payload.slug,
        subdomain=payload.subdomain,
        active=payload.active
    )
    
    db.add(org)
    db.commit()
    db.refresh(org)
    
    return org


@router.get("/slug/{org_slug}", response_model=OrganizationResponse)
def get_organization_by_slug(
    org_slug: str,
    db: Session = Depends(get_db)
):
    """
    Get organization by slug (public endpoint for login page).
    No auth required - used for validating org before login.
    """
    org = db.query(Organization).filter(
        Organization.slug == org_slug,
        Organization.active == True
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: int,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """Get organization details"""
    # Users can only access their own organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own organization"
        )
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """Update organization details"""
    # Users can only update their own organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own organization"
        )
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Update fields
    if payload.name is not None:
        org.name = payload.name
    if payload.slug is not None:
        # Check slug uniqueness
        existing = db.query(Organization).filter(
            Organization.slug == payload.slug,
            Organization.id != org_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Organization with slug '{payload.slug}' already exists"
            )
        org.slug = payload.slug
    if payload.subdomain is not None:
        org.subdomain = payload.subdomain
    if payload.active is not None:
        org.active = payload.active
    
    db.commit()
    db.refresh(org)
    
    return org


@router.delete("/{org_id}", status_code=204)
def delete_organization(
    org_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an organization.
    
    NOTE: This endpoint is currently unprotected for testing.
    In production, this should only be accessible by super admins.
    WARNING: This will cascade delete all users, surveys, and responses!
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    db.delete(org)
    db.commit()
    
    return None
