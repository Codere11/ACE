#!/usr/bin/env python3
"""
Migration script to add survey tracking fields to existing database.
Run this to update the database schema without losing existing data.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.db import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """Add survey columns to leads table if they don't exist."""
    
    print("🔄 Starting survey fields migration...")
    
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('leads')
            WHERE name IN ('survey_started_at', 'survey_completed_at', 'survey_answers', 'survey_progress')
        """))
        existing_count = result.fetchone()[0]
        
        if existing_count == 4:
            print("✅ Survey fields already exist. No migration needed.")
            return
        
        print(f"📊 Found {existing_count}/4 survey fields. Adding missing columns...")
        
        # Add columns if they don't exist
        try:
            # SQLite doesn't support IF NOT EXISTS in ALTER TABLE, so we try-catch
            if existing_count < 4:
                try:
                    conn.execute(text("ALTER TABLE leads ADD COLUMN survey_started_at DATETIME"))
                    print("  ✓ Added survey_started_at")
                except Exception:
                    pass
                
                try:
                    conn.execute(text("ALTER TABLE leads ADD COLUMN survey_completed_at DATETIME"))
                    print("  ✓ Added survey_completed_at")
                except Exception:
                    pass
                
                try:
                    conn.execute(text("ALTER TABLE leads ADD COLUMN survey_answers TEXT"))  # JSON stored as TEXT in SQLite
                    print("  ✓ Added survey_answers")
                except Exception:
                    pass
                
                try:
                    conn.execute(text("ALTER TABLE leads ADD COLUMN survey_progress INTEGER DEFAULT 0"))
                    print("  ✓ Added survey_progress")
                except Exception:
                    pass
            
            conn.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
            raise

if __name__ == '__main__':
    migrate()
