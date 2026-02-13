#!/usr/bin/env python3
"""
Migration script to add missing is_trial column to subscriptions table.
Run this script to fix the schema mismatch between SQLAlchemy model and database.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def add_missing_columns():
    """Add missing columns to subscriptions table"""
    
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True
    )
    
    async with engine.begin() as conn:
        # Check current table structure
        result = await conn.execute(
            text("DESCRIBE subscriptions")
        )
        columns = {row[0] for row in result.fetchall()}
        print(f"Current columns in subscriptions table: {columns}")
        
        # Add missing is_trial column
        if 'is_trial' not in columns:
            print("Adding is_trial column...")
            await conn.execute(text("""
                ALTER TABLE subscriptions 
                ADD COLUMN is_trial BOOLEAN DEFAULT FALSE NOT NULL AFTER end_date
            """))
            print("✓ Added is_trial column")
        else:
            print("✓ is_trial column already exists")
        
        # Add missing updated_at column if needed
        if 'updated_at' not in columns:
            print("Adding updated_at column...")
            await conn.execute(text("""
                ALTER TABLE subscriptions 
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """))
            print("✓ Added updated_at column")
        else:
            print("✓ updated_at column already exists")
        
        # Add missing created_at column if needed
        if 'created_at' not in columns:
            print("Adding created_at column...")
            await conn.execute(text("""
                ALTER TABLE subscriptions 
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """))
            print("✓ Added created_at column")
        else:
            print("✓ created_at column already exists")
        
        # Verify the fix
        result = await conn.execute(text("DESCRIBE subscriptions"))
        columns = {row[0] for row in result.fetchall()}
        print(f"\nUpdated columns in subscriptions table: {columns}")
        print("\n✓ Migration completed successfully!")


def main():
    """Run the migration"""
    print("Starting migration to fix subscription table schema...\n")
    asyncio.run(add_missing_columns())


if __name__ == "__main__":
    main()

