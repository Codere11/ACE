#!/usr/bin/env python3
"""
Migration script from old schema (clients) to new schema (organizations + surveys)

This script:
1. Renames 'clients' table to 'organizations'
2. Creates new 'surveys' and 'survey_responses' tables
3. Migrates existing Leads to SurveyResponses (if needed)
4. Updates User roles from 'admin'/'manager' to 'org_admin'/'org_user'
5. Creates a default survey for each organization from conversation_flow.json

Run this after updating your ORM models but before starting the backend.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.core.db import engine, SessionLocal
from app.models.orm import Base, Organization, User, Survey, SurveyResponse, Lead
import json
from datetime import datetime


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    if not table_exists(table_name):
        return False
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_schema():
    """Main migration function"""
    print("🚀 Starting schema migration to v2...")
    
    db = SessionLocal()
    
    try:
        # Step 1: Rename clients table to organizations
        print("\n📦 Step 1: Migrating clients → organizations...")
        if table_exists('clients') and not table_exists('organizations'):
            print("  ✓ Renaming 'clients' table to 'organizations'...")
            db.execute(text("ALTER TABLE clients RENAME TO organizations"))
            
            # Update foreign key references
            if column_exists('users', 'tenant_id'):
                print("  ✓ Renaming users.tenant_id → organization_id...")
                db.execute(text("ALTER TABLE users RENAME COLUMN tenant_id TO organization_id"))
            
            if column_exists('conversations', 'client_id'):
                print("  ✓ Renaming conversations.client_id → organization_id...")
                db.execute(text("ALTER TABLE conversations RENAME COLUMN client_id TO organization_id"))
            
            if column_exists('leads', 'client_id'):
                print("  ✓ Renaming leads.client_id → organization_id...")
                db.execute(text("ALTER TABLE leads RENAME COLUMN client_id TO organization_id"))
            
            # SQLite automatically renames indexes when table is renamed
            print("  ✓ Indexes automatically renamed with table")
            
            # For SQLite, we need to handle constraints differently
            # Check database type
            db_type = engine.dialect.name
            if db_type == 'postgresql':
                # PostgreSQL: rename constraints
                db.execute(text("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS uq_conversations_client_sid"))
                db.execute(text("ALTER TABLE conversations ADD CONSTRAINT uq_conversations_org_sid UNIQUE (organization_id, sid)"))
            else:
                # SQLite: constraints are tied to table, already updated
                print("  ✓ Constraints automatically updated (SQLite)")
            
            db.commit()
            print("  ✅ Table rename complete!")
        elif table_exists('organizations'):
            print("  ℹ️  'organizations' table already exists, skipping rename.")
        else:
            print("  ⚠️  Neither 'clients' nor 'organizations' table exists. Creating fresh schema...")
        
        # Step 2: Update User roles
        print("\n👤 Step 2: Updating user roles...")
        if table_exists('users') and column_exists('users', 'role'):
            # Update role values
            db.execute(text("UPDATE users SET role = 'org_admin' WHERE role = 'admin'"))
            db.execute(text("UPDATE users SET role = 'org_user' WHERE role = 'manager'"))
            
            # SQLite doesn't support DROP/ADD CONSTRAINT - constraints will be enforced at application level
            # The ORM model already has the correct constraint definition
            print("  ✓ Updated user roles (org_admin/org_user)")
            
            # Make organization_id NOT NULL if it has NULL values
            if column_exists('users', 'organization_id'):
                null_org_users = db.execute(text("SELECT COUNT(*) FROM users WHERE organization_id IS NULL")).scalar()
                if null_org_users > 0:
                    print(f"  ⚠️  Found {null_org_users} users without organization_id. Assigning to first org...")
                    first_org = db.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
                    if first_org:
                        db.execute(text(f"UPDATE users SET organization_id = {first_org} WHERE organization_id IS NULL"))
            
            db.commit()
            print("  ✅ User roles updated!")
        else:
            print("  ℹ️  Users table not found or no role column, skipping.")
        
        # Step 3: Create new tables (surveys, survey_responses)
        print("\n📋 Step 3: Creating new tables...")
        if not table_exists('surveys'):
            print("  ✓ Creating 'surveys' table...")
        if not table_exists('survey_responses'):
            print("  ✓ Creating 'survey_responses' table...")
        
        # Use SQLAlchemy to create missing tables
        Base.metadata.create_all(bind=engine)
        print("  ✅ New tables created!")
        
        # Step 4: Create default survey for each organization
        print("\n🎯 Step 4: Creating default surveys for organizations...")
        
        # Load default conversation flow
        flow_path = Path(__file__).parent.parent / "data" / "conversation_flow.json"
        default_flow = None
        if flow_path.exists():
            with open(flow_path, 'r') as f:
                default_flow = json.load(f)
            print(f"  ✓ Loaded default flow from {flow_path}")
        
        # Get all organizations
        orgs = db.query(Organization).all()
        print(f"  ℹ️  Found {len(orgs)} organizations")
        
        for org in orgs:
            # Check if org already has a survey
            existing_survey = db.query(Survey).filter(Survey.organization_id == org.id).first()
            if existing_survey:
                print(f"  ℹ️  Organization '{org.name}' already has surveys, skipping.")
                continue
            
            # Use org's conversation_flow if it exists, otherwise use default
            flow = org.conversation_flow if org.conversation_flow else default_flow
            
            if flow:
                survey = Survey(
                    organization_id=org.id,
                    name=f"{org.name} - Default Survey",
                    slug=f"{org.slug}-default",
                    survey_type="regular",
                    status="draft",
                    flow_json=flow,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(survey)
                print(f"  ✓ Created default survey for '{org.name}'")
        
        db.commit()
        print("  ✅ Default surveys created!")
        
        # Step 5: Migrate existing Leads to SurveyResponses (optional)
        print("\n🔄 Step 5: Checking if Lead migration is needed...")
        
        # Check if leads table exists and has data
        if table_exists('leads'):
            lead_count = db.execute(text("SELECT COUNT(*) FROM leads")).scalar()
        else:
            lead_count = 0
        
        response_count = db.query(SurveyResponse).count()
        
        print(f"  ℹ️  Existing Leads: {lead_count}")
        print(f"  ℹ️  Existing SurveyResponses: {response_count}")
        
        if lead_count > 0 and response_count == 0:
            print("  ⚠️  Found leads but no survey responses. Migration recommended but not automated.")
            print("  ℹ️  You can manually migrate leads or continue using the Lead model for now.")
        elif lead_count > 0 and response_count > 0:
            print("  ℹ️  Both Leads and SurveyResponses exist. Using hybrid approach.")
        else:
            print("  ✅ No migration needed!")
        
        print("\n✅ Schema migration completed successfully!")
        print("\n📝 Next steps:")
        print("  1. Review the changes in your database")
        print("  2. Update your backend code to use Organization instead of Client")
        print("  3. Test the new survey management endpoints")
        print("  4. Update frontend to use new API schemas")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def rollback_migration():
    """Rollback migration (organizations → clients)"""
    print("⚠️  Rolling back migration...")
    db = SessionLocal()
    
    try:
        # Rename tables back
        if table_exists('organizations') and not table_exists('clients'):
            print("  ✓ Renaming 'organizations' back to 'clients'...")
            db.execute(text("ALTER TABLE organizations RENAME TO clients"))
            
            # Rename foreign keys back
            if column_exists('users', 'organization_id'):
                db.execute(text("ALTER TABLE users RENAME COLUMN organization_id TO tenant_id"))
            if column_exists('conversations', 'organization_id'):
                db.execute(text("ALTER TABLE conversations RENAME COLUMN organization_id TO client_id"))
            if column_exists('leads', 'organization_id'):
                db.execute(text("ALTER TABLE leads RENAME COLUMN organization_id TO client_id"))
            
            db.commit()
            print("  ✅ Rollback complete!")
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        migrate_schema()
