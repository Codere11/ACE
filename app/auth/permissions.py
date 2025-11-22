# app/auth/permissions.py
"""
Authentication and authorization dependencies for protected routes.
"""

from typing import Optional, Literal
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .security import verify_token
from app.core.db import get_db
from app.models.orm import User, Organization


class AuthContext:
    """User authentication context"""
    def __init__(
        self,
        user_id: int,
        username: str,
        organization_id: int,
        role: Literal["org_admin", "org_user"],
        db: Session
    ):
        self.user_id = user_id
        self.username = username
        self.organization_id = organization_id
        self.role = role
        self.db = db
        self._user: Optional[User] = None
        self._organization: Optional[Organization] = None
    
    @property
    def user(self) -> User:
        """Lazy load user from database"""
        if self._user is None:
            self._user = self.db.query(User).filter(User.id == self.user_id).first()
            if not self._user:
                raise HTTPException(status_code=404, detail="User not found")
        return self._user
    
    @property
    def organization(self) -> Organization:
        """Lazy load organization from database"""
        if self._organization is None:
            self._organization = self.db.query(Organization).filter(
                Organization.id == self.organization_id
            ).first()
            if not self._organization:
                raise HTTPException(status_code=404, detail="Organization not found")
        return self._organization
    
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == "org_admin"
    
    def require_admin(self):
        """Raise exception if user is not admin"""
        if not self.is_admin():
            raise HTTPException(
                status_code=403,
                detail="Admin privileges required"
            )


def get_auth_context(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
) -> AuthContext:
    """
    Dependency to get authenticated user context.
    Validates JWT token and returns user information.
    
    Usage:
        @router.get("/protected")
        def protected_route(auth: AuthContext = Depends(get_auth_context)):
            print(f"User: {auth.username}, Org: {auth.organization_id}")
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.split(" ", 1)[1]
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Extract data from token
    user_id = token_data.get("user_id")
    username = token_data.get("sub")
    organization_id = token_data.get("organization_id") or token_data.get("tenant_id")
    role = token_data.get("role")
    
    if not all([user_id, username, organization_id, role]):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Verify user exists and is active
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return AuthContext(
        user_id=user_id,
        username=username,
        organization_id=organization_id,
        role=role,
        db=db
    )


def require_org_admin(
    auth: AuthContext = Depends(get_auth_context)
) -> AuthContext:
    """
    Dependency to require organization admin role.
    
    Usage:
        @router.post("/organizations/{org_id}/users")
        def create_user(auth: AuthContext = Depends(require_org_admin)):
            # Only org admins can reach here
    """
    auth.require_admin()
    return auth


def require_org_user(
    auth: AuthContext = Depends(get_auth_context)
) -> AuthContext:
    """
    Dependency to require any authenticated organization user.
    Both org_admin and org_user roles can access.
    
    Usage:
        @router.get("/leads")
        def list_leads(auth: AuthContext = Depends(require_org_user)):
            # Any authenticated user can reach here
    """
    return auth


def require_same_org(
    org_id: int,
    auth: AuthContext = Depends(get_auth_context)
) -> AuthContext:
    """
    Helper to verify user belongs to the organization they're accessing.
    
    Usage:
        @router.get("/organizations/{org_id}/surveys")
        def list_surveys(org_id: int, auth: AuthContext = Depends(get_auth_context)):
            require_same_org(org_id, auth)
            # User can only access their own org's surveys
    """
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: you can only access your own organization"
        )
    return auth
