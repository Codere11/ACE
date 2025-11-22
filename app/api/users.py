# app/api/users.py
"""
User management API endpoints.
Organization admins can manage users within their organization.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.orm import User
from app.models.schemas import UserCreate, UserUpdate, UserResponse
from app.auth.permissions import AuthContext, require_org_admin
from app.auth.security import hash_password

router = APIRouter(prefix="/api/organizations/{org_id}/users", tags=["users"])


@router.get("", response_model=List[UserResponse])
def list_users(
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    List all users in an organization.
    Only accessible by org admins of that organization.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only manage users in your own organization"
        )
    
    users = db.query(User).filter(
        User.organization_id == org_id
    ).offset(skip).limit(limit).all()
    
    return users


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    org_id: int,
    payload: UserCreate,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user in the organization.
    Only accessible by org admins.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only create users in your own organization"
        )
    
    # Override organization_id from URL (ignore payload)
    if payload.organization_id != org_id:
        raise HTTPException(
            status_code=400,
            detail="Organization ID in payload must match URL"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(
        User.username == payload.username
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=400,
            detail=f"Username '{payload.username}' already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(
        User.email == payload.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail=f"Email '{payload.email}' already exists"
        )
    
    # Hash password
    hashed_pw = hash_password(payload.password)
    
    # Create user
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pw,
        role=payload.role,
        organization_id=org_id,
        is_active=payload.is_active
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    org_id: int,
    user_id: int,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """Get user details"""
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view users in your own organization"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    org_id: int,
    user_id: int,
    payload: UserUpdate,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Update user details.
    Only accessible by org admins.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update users in your own organization"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from demoting themselves (must be at least one admin)
    if user_id == auth.user_id and payload.role == "org_user":
        admin_count = db.query(User).filter(
            User.organization_id == org_id,
            User.role == "org_admin",
            User.is_active == True
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the last admin in the organization"
            )
    
    # Update fields
    if payload.username is not None:
        # Check username uniqueness
        existing = db.query(User).filter(
            User.username == payload.username,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Username '{payload.username}' already exists"
            )
        user.username = payload.username
    
    if payload.email is not None:
        # Check email uniqueness
        existing = db.query(User).filter(
            User.email == payload.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Email '{payload.email}' already exists"
            )
        user.email = payload.email
    
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    
    if payload.role is not None:
        user.role = payload.role
    
    if payload.is_active is not None:
        # Prevent admin from deactivating themselves
        if user_id == auth.user_id and not payload.is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate your own account"
            )
        user.is_active = payload.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    org_id: int,
    user_id: int,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user.
    Only accessible by org admins.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete users in your own organization"
        )
    
    # Prevent admin from deleting themselves
    if user_id == auth.user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if this is the last admin
    if user.role == "org_admin":
        admin_count = db.query(User).filter(
            User.organization_id == org_id,
            User.role == "org_admin",
            User.is_active == True
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last admin in the organization"
            )
    
    db.delete(user)
    db.commit()
    
    return None
