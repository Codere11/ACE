#!/usr/bin/env python3
"""
Create initial users in the database.
Run this after database migration to set up admin and test accounts.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.db import SessionLocal
from app.models.orm import User, Client
from app.auth.security import hash_password

def create_initial_users():
    """Create default admin and demo users"""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("⚠️  Admin user already exists")
        else:
            # Create admin user
            admin = User(
                username="admin",
                email="admin@acesurvey.local",
                hashed_password=hash_password("admin123"),
                role="admin",
                tenant_id=None,  # Admin has no tenant restriction
                is_active=True
            )
            db.add(admin)
            print("✅ Created admin user (username: admin, password: admin123)")
        
        # Create demo tenant if doesn't exist
        demo_tenant = db.query(Client).filter(Client.slug == "demo-agency").first()
        if not demo_tenant:
            demo_tenant = Client(
                slug="demo-agency",
                name="Demo Real Estate Agency",
                active=True
            )
            db.add(demo_tenant)
            db.flush()  # Get the ID
            print("✅ Created demo tenant: demo-agency")
        
        # Check if demo manager exists
        existing_demo = db.query(User).filter(User.username == "demo").first()
        if existing_demo:
            print("⚠️  Demo manager already exists")
        else:
            # Create demo manager
            demo_user = User(
                username="demo",
                email="demo@demo-agency.local",
                hashed_password=hash_password("demo123"),
                role="manager",
                tenant_id=demo_tenant.id,
                is_active=True
            )
            db.add(demo_user)
            print("✅ Created demo manager (username: demo, password: demo123)")
        
        db.commit()
        
        print("\n" + "="*60)
        print("🎉 User setup complete!")
        print("="*60)
        print("\n📝 Login Credentials:")
        print("\n  Admin Account:")
        print("    Username: admin")
        print("    Password: admin123")
        print("    Access: Full system access")
        print("\n  Manager Account:")
        print("    Username: demo")
        print("    Password: demo123")
        print("    Access: demo-agency tenant only")
        print("\n⚠️  IMPORTANT: Change these passwords in production!")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_users()
