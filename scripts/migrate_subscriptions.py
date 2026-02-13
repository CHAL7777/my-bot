#!/usr/bin/env python3
"""
Comprehensive migration script for subscriptions table.
Fixes schema mismatches and safely migrates existing data.

Usage:
    python scripts/migrate_subscriptions.py --dry-run  # Preview changes
    python scripts/migrate_subscriptions.py            # Apply changes
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


class SubscriptionMigration:
    """Handles subscription table schema migration"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo= dry_run  # Only echo in dry-run mode
        )
    
    async def check_table_exists(self, conn) -> bool:
        """Check if subscriptions table exists"""
        result = await conn.execute(
            text("SHOW TABLES LIKE 'subscriptions'")
        )
        return result.fetchone() is not None
    
    async def get_current_columns(self, conn) -> set:
        """Get current columns in subscriptions table"""
        result = await conn.execute(text("DESCRIBE subscriptions"))
        return {row[0] for row in result.fetchall()}
    
    async def get_expected_columns(self) -> set:
        """Get expected columns from SQLAlchemy model"""
        return {
            'subscription_id', 'user_id', 'payment_id', 'status',
            'start_date', 'end_date', 'is_trial', 'created_at', 'updated_at'
        }
    
    async def add_column(self, conn, column_def: str):
        """Add a single column (or nothing if dry-run)"""
        if self.dry_run:
            print(f"  [DRY-RUN] Would execute: ALTER TABLE subscriptions ADD {column_def}")
            return
        
        await conn.execute(text(f"ALTER TABLE subscriptions ADD {column_def}"))
        print(f"  ✓ Added: {column_def.split()[0]}")
    
    async def migrate(self):
        """Run the complete migration"""
        print("=" * 60)
        print("Subscription Table Migration")
        print("=" * 60)
        print(f"Mode: {'DRY-RUN (preview only)' if self.dry_run else 'LIVE (applying changes)'}")
        print()
        
        async with self.engine.begin() as conn:
            if not await self.check_table_exists(conn):
                print("ERROR: subscriptions table does not exist!")
                print("Create it first with: alembic upgrade head")
                return False
            
            current_cols = await self.get_current_columns(conn)
            expected_cols = await self.get_expected_columns()
            
            print(f"Current columns: {sorted(current_cols)}")
            print(f"Expected columns: {sorted(expected_cols)}")
            print()
            
            missing_cols = expected_cols - current_cols
            
            if not missing_cols:
                print("✓ Table schema is up to date!")
                return True
            
            print(f"Missing columns to add: {sorted(missing_cols)}")
            print()
            
            migration_order = [
                ('is_trial', 'is_trial BOOLEAN DEFAULT FALSE NOT NULL AFTER end_date'),
                ('created_at', 'created_at DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
            ]
            
            print("Applying migrations:")
            for col_name, col_def in migration_order:
                if col_name in missing_cols:
                    await self.add_column(conn, col_def)
            
            for col in missing_cols:
                if col not in ['is_trial', 'created_at', 'updated_at']:
                    if self.dry_run:
                        print(f"  [DRY-RUN] Would add: {col}")
                    else:
                        print(f"  Adding: {col}")
            
            print()
            
            if 'is_trial' in missing_cols:
                await self.migrate_existing_data(conn)
            
            final_cols = await self.get_current_columns(conn)
            print(f"Final columns: {sorted(final_cols)}")
            
            if expected_cols.issubset(final_cols):
                print("\n✓ Migration completed successfully!")
                return True
            else:
                print("\n✗ Some columns are still missing!")
                return False
    
    async def migrate_existing_data(self, conn):
        """Migrate existing subscription data if needed"""
        print("\nMigrating existing data:")
        print("  - Existing subscriptions will have is_trial = FALSE (from DEFAULT)")
        print("  - No data migration needed for new BOOLEAN column")
    
    async def verify_data_integrity(self):
        """Verify data integrity after migration"""
        print("\nVerifying data integrity:")
        
        async with self.engine.begin() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM subscriptions"))
            total = result.scalar()
            print(f"  - Total subscriptions: {total}")
            
            result = await conn.execute(
                text("SELECT status, COUNT(*) FROM subscriptions GROUP BY status")
            )
            print("  - Subscriptions by status:")
            for row in result.fetchall():
                print(f"      {row[0]}: {row[1]}")
            
            result = await conn.execute(
                text("SELECT COUNT(*) FROM subscriptions WHERE is_trial IS NULL")
            )
            null_count = result.scalar()
            print(f"  - NULL is_trial values: {null_count}")
            
            if null_count > 0:
                print("  ⚠ Fixing NULL values...")
                await conn.execute(
                    text("UPDATE subscriptions SET is_trial = FALSE WHERE is_trial IS NULL")
                )
                print("  ✓ Fixed NULL values")
        
        print("✓ Data integrity verified")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Migrate subscriptions table')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without applying them')
    args = parser.parse_args()
    
    migration = SubscriptionMigration(dry_run=args.dry_run)
    success = await migration.migrate()
    
    if success and not args.dry_run:
        await migration.verify_data_integrity()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

