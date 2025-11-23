#!/usr/bin/env python3
"""
Migration script: Add avatar_url column to users table
Run this after updating the User model to add avatar_url field.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.db import engine

def migrate():
    """Add avatar_url column to users table if it doesn't exist"""
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result]
        
        if 'avatar_url' not in columns:
            print("Adding avatar_url column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255)"))
            conn.commit()
            print("✅ Migration complete: avatar_url column added")
        else:
            print("✅ avatar_url column already exists, no migration needed")

if __name__ == "__main__":
    migrate()
