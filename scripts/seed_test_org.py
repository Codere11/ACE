#!/usr/bin/env python3
"""
Seed test organization with users for development.

Creates:
- 1 test organization (Test Company)
- 1 admin user (admin@test.com)
- 2 regular users (user1@test.com, user2@test.com)

All passwords: test123
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.db import SessionLocal
from app.models.orm import Organization, User
from app.auth.security import hash_password


def seed_test_data():
    """Seed test organization and users"""
    print("🌱 Seeding test data...")
    
    db = SessionLocal()
    
    try:
        # Check if test org already exists
        existing_org = db.query(Organization).filter(
            Organization.slug == "test-company"
        ).first()
        
        if existing_org:
            print(f"  ℹ️  Organization 'Test Company' already exists (ID: {existing_org.id})")
            org = existing_org
        else:
            # Create test organization
            org = Organization(
                name="Test Company",
                slug="test-company",
                subdomain="test.ace.local",
                active=True
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"  ✅ Created organization: {org.name} (ID: {org.id})")
        
        # Create admin user
        admin_email = "admin@test.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        
        if existing_admin:
            print(f"  ℹ️  Admin user already exists: {admin_email}")
        else:
            admin = User(
                username="admin",
                email=admin_email,
                hashed_password=hash_password("test123"),
                role="org_admin",
                organization_id=org.id,
                is_active=True
            )
            db.add(admin)
            print(f"  ✅ Created admin user: {admin_email} (password: test123)")
        
        # Create user 1
        user1_email = "user1@test.com"
        existing_user1 = db.query(User).filter(User.email == user1_email).first()
        
        if existing_user1:
            print(f"  ℹ️  User 1 already exists: {user1_email}")
        else:
            user1 = User(
                username="user1",
                email=user1_email,
                hashed_password=hash_password("test123"),
                role="org_user",
                organization_id=org.id,
                is_active=True
            )
            db.add(user1)
            print(f"  ✅ Created user 1: {user1_email} (password: test123)")
        
        # Create user 2
        user2_email = "user2@test.com"
        existing_user2 = db.query(User).filter(User.email == user2_email).first()
        
        if existing_user2:
            print(f"  ℹ️  User 2 already exists: {user2_email}")
        else:
            user2 = User(
                username="user2",
                email=user2_email,
                hashed_password=hash_password("test123"),
                role="org_user",
                organization_id=org.id,
                is_active=True
            )
            db.add(user2)
            print(f"  ✅ Created user 2: {user2_email} (password: test123)")
        
        db.commit()
        
        # Print summary
        print("\n✅ Test data seeded successfully!")
        print("\n📋 Login credentials:")
        print("  Admin:")
        print("    Email: admin@test.com")
        print("    Password: test123")
        print("    Role: org_admin")
        print("\n  User 1:")
        print("    Email: user1@test.com")
        print("    Password: test123")
        print("    Role: org_user")
        print("\n  User 2:")
        print("    Email: user2@test.com")
        print("    Password: test123")
        print("    Role: org_user")
        print("\n🔗 Test login:")
        print(f"  POST http://localhost:8000/api/auth/login")
        print(f"  Body: {{\"username\": \"admin\", \"password\": \"test123\"}}")
        
    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_data()
