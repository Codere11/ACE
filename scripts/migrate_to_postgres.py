#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
This script will:
1. Create all tables in PostgreSQL
2. Copy data from SQLite to PostgreSQL (if SQLite DB exists)
3. Verify the migration
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect
from app.core.db import Base, DATABASE_URL
from app.models.orm import User, Client, Conversation, Message, Lead, Event

SQLITE_PATH = Path(__file__).parent.parent / "ace_dev.db"

def main():
    print("🔄 ACE Database Migration: SQLite → PostgreSQL")
    print("=" * 60)
    
    # Check if already using PostgreSQL
    if not DATABASE_URL.startswith("sqlite"):
        print(f"✅ Already using PostgreSQL: {DATABASE_URL.split('@')[-1]}")
        print("\n📋 Creating/updating tables...")
        
        # Create all tables
        from app.core.db import engine
        Base.metadata.create_all(engine)
        
        # Check what tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Tables created: {', '.join(tables)}")
        
        if SQLITE_PATH.exists():
            print(f"\n⚠️  Found SQLite database: {SQLITE_PATH}")
            print("Do you want to migrate data from SQLite? (y/n)")
            response = input().strip().lower()
            
            if response == 'y':
                migrate_data()
        else:
            print("\n✅ No SQLite database found - starting fresh!")
            print("🎉 PostgreSQL is ready to use!")
        
        return
    
    print("❌ ERROR: Still using SQLite!")
    print(f"Current DATABASE_URL: {DATABASE_URL}")
    print("\n📝 Please set DATABASE_URL environment variable:")
    print("   export DATABASE_URL=postgresql://ace_user:ace_dev_password_change_in_production@localhost:5432/ace_production")
    print("\nOr add it to your .env file")
    sys.exit(1)

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    print("\n🔄 Migrating data from SQLite...")
    
    # Create SQLite engine
    sqlite_url = f"sqlite:///{SQLITE_PATH}"
    sqlite_engine = create_engine(sqlite_url)
    
    # Create PostgreSQL engine
    from app.core.db import engine as pg_engine
    
    # Get session makers
    from sqlalchemy.orm import sessionmaker
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)
    
    sqlite_session = SqliteSession()
    pg_session = PgSession()
    
    try:
        # Migrate in order (respecting foreign keys)
        # User comes first, then Client (tenant), then rest
        models = [User, Client, Conversation, Lead, Message, Event]
        
        for model in models:
            print(f"\n📦 Migrating {model.__tablename__}...")
            
            # Get all records from SQLite
            records = sqlite_session.query(model).all()
            print(f"   Found {len(records)} records")
            
            if records:
                # Bulk insert to PostgreSQL
                for record in records:
                    # Create a dict of the record
                    record_dict = {c.name: getattr(record, c.name) 
                                   for c in record.__table__.columns}
                    
                    # Create new instance for PostgreSQL
                    pg_record = model(**record_dict)
                    pg_session.merge(pg_record)  # merge handles existing records
                
                pg_session.commit()
                print(f"   ✅ Migrated {len(records)} records")
        
        print("\n🎉 Migration complete!")
        print("\n📊 Summary:")
        for model in models:
            count = pg_session.query(model).count()
            print(f"   {model.__tablename__}: {count} records")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        pg_session.rollback()
        raise
    finally:
        sqlite_session.close()
        pg_session.close()
    
    print("\n💡 You can now delete the SQLite database:")
    print(f"   rm {SQLITE_PATH}")

if __name__ == "__main__":
    main()
