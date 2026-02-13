#!/usr/bin/env python3
"""
Comprehensive database migration script.
Fixes all schema mismatches between SQLAlchemy models and MySQL database.

Usage:
    python scripts/migrate_db.py --dry-run  # Preview changes
    python scripts/migrate_db.py            # Apply changes
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


class DatabaseMigration:
    """Handles database schema migration for all tables"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=dry_run
        )
    
    async def check_table_exists(self, conn, table_name: str) -> bool:
        result = await conn.execute(
            text(f"SHOW TABLES LIKE '{table_name}'")
        )
        return result.fetchone() is not None
    
    async def get_current_columns(self, conn, table_name: str) -> set:
        result = await conn.execute(text(f"DESCRIBE {table_name}"))
        return {row[0] for row in result.fetchall()}
    
    async def add_column(self, conn, table_name: str, column_def: str):
        if self.dry_run:
            print(f"  [DRY-RUN] ALTER TABLE {table_name} ADD {column_def}")
        else:
            await conn.execute(text(f"ALTER TABLE {table_name} ADD {column_def}"))
            print(f"  ✓ Added {column_def.split()[0]} to {table_name}")
    
    async def migrate_table(self, conn, table_name: str, expected_columns: dict):
        """Migrate a single table"""
        if not await self.check_table_exists(conn, table_name):
            print(f"  ⚠ Table {table_name} does not exist, skipping...")
            return False
        
        current_cols = await self.get_current_columns(conn, table_name)
        missing = expected_columns - current_cols
        
        if not missing:
            print(f"  ✓ {table_name}: up to date")
            return True
        
        print(f"  ⚠ {table_name}: adding {sorted(missing)}")
        
        for col in missing:
            col_def = expected_columns.get(col)
            if col_def:
                await self.add_column(conn, table_name, col_def)
        
        return True
    
    async def migrate_all(self):
        """Run all migrations"""
        print("=" * 60)
        print("Database Schema Migration")
        print("=" * 60)
        print(f"Mode: {'DRY-RUN (preview only)' if self.dry_run else 'LIVE'}")
        print()
        
        async with self.engine.begin() as conn:
            # Define expected columns for each table (based on models.py)
            tables = {
                'users': {
                    'user_id', 'username', 'first_name', 'last_name',
                    'role', 'created_at', 'updated_at', 'blocked', 'approved', 'is_premium'
                },
                'subjects': {
                    'subject_id', 'subject_name', 'description',
                    'is_active', 'created_at'
                },
                'chapters': {
                    'chapter_id', 'subject_id', 'chapter_name', 'chapter_order',
                    'description', 'is_active', 'created_at'
                },
                'questions': {
                    'question_id', 'subject_id', 'chapter_id', 'difficulty',
                    'question_text', 'option_a', 'option_b', 'option_c', 'option_d',
                    'correct_option', 'explanation', 'is_active', 'created_at'
                },
                'user_progress': {
                    'id', 'user_id', 'subject_id', 'chapter_id', 'difficulty',
                    'total_attempts', 'correct_attempts', 'total_time_spent',
                    'last_attempt', 'accuracy', 'created_at', 'updated_at'
                },
                'quiz_attempts': {
                    'attempt_id', 'user_id', 'question_id', 'selected_option',
                    'is_correct', 'time_taken', 'quiz_session_id', 'created_at'
                },
                'payments': {
                    'payment_id', 'user_id', 'screenshot_file_id', 'screenshot_file_path',
                    'status', 'amount', 'subscription_days', 'transaction_id', 'notes',
                    'approved_by', 'approved_at', 'rejected_reason', 'created_at'
                },
                'subscriptions': {
                    'subscription_id', 'user_id', 'payment_id', 'status',
                    'start_date', 'end_date', 'is_trial', 'created_at', 'updated_at'
                },
                'leaderboard': {
                    'leaderboard_id', 'user_id', 'period', 'total_score',
                    'total_accuracy', 'total_questions', 'rank_position', 'last_updated'
                },
                'user_daily_limits': {
                    'id', 'user_id', 'date', 'quiz_count', 'question_count', 'last_reset'
                }
            }
            
            # Column definitions for adding missing columns
            column_defs = {
                # user_progress table
                'total_time_spent': 'total_time_spent INT DEFAULT 0',
                'updated_at': 'updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
                
                # subscriptions table
                'is_trial': 'is_trial BOOLEAN DEFAULT FALSE',
                'created_at': 'created_at DATETIME DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
                
                # payments table
                'screenshot_file_id': 'screenshot_file_id VARCHAR(255)',
                'screenshot_file_path': 'screenshot_file_path VARCHAR(500)',
                'rejected_reason': 'rejected_reason TEXT',
                
                # users table
                'blocked': 'blocked BOOLEAN DEFAULT FALSE',
                'approved': 'approved BOOLEAN DEFAULT FALSE',
                'is_premium': 'is_premium BOOLEAN DEFAULT FALSE',
                'updated_at': 'updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
                
                # questions table
                'explanation': 'explanation TEXT',
                
                # leaderboard table
                'last_updated': 'last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
            }
            
            print("Checking tables:")
            for table_name, expected_cols in tables.items():
                await self.migrate_table(conn, table_name, expected_cols)
            
            print("\n✓ Migration check complete!")
            
            if self.dry_run:
                print("\n[DRY-RUN] No changes were applied.")
                print("Run without --dry-run to apply changes.")
            
            return True
    
    async def verify_all(self):
        """Verify all tables have expected columns"""
        print("\n" + "=" * 60)
        print("Verification")
        print("=" * 60)
        
        async with self.engine.begin() as conn:
            tables = ['users', 'user_progress', 'subscriptions', 'payments']
            for table in tables:
                if await self.check_table_exists(conn, table):
                    cols = await self.get_current_columns(conn, table)
                    print(f"  {table}: {len(cols)} columns")
                else:
                    print(f"  {table}: NOT FOUND")
            
            print("✓ Verification complete")


async def main():
    parser = argparse.ArgumentParser(description='Database schema migration')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--verify', action='store_true', help='Verify schema')
    args = parser.parse_args()
    
    migration = DatabaseMigration(dry_run=args.dry_run)
    
    await migration.migrate_all()
    
    if not args.dry_run or args.verify:
        await migration.verify_all()
    
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

