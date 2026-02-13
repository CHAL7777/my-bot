#!/usr/bin/env python3
"""
Safe Database Migration Script for Telegram Quiz Bot

This script safely adds missing columns to MariaDB tables without causing
duplicate column errors. It checks for column existence before adding.

Usage:
    python scripts/run_migration.py              # Run migrations
    python scripts/run_migration.py --dry-run    # Preview only (no changes)
    python scripts/run_migration.py --verify     # Verify schema only

Compatible with:
    - MariaDB 10.x
    - MySQL 8.x
    - Python 3.14
    - SQLAlchemy async sessions
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import AsyncGenerator

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings


# Column definitions for safe addition
# Format: "column_name column_definition"
COLUMN_DEFINITIONS = {
    # subscriptions table
    'subscriptions': {
        'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
        'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
    },
    # user_progress table
    'user_progress': {
        'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
        'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
    },
    # quiz_attempts table
    'quiz_attempts': {
        'quiz_session_id': 'VARCHAR(50)',
    },
    # payments table
    'payments': {
        'subscription_days': 'INT NOT NULL DEFAULT 30',
        'transaction_id': 'VARCHAR(100)',
        'notes': 'TEXT',
    },
}


class SafeDatabaseMigration:
    """Handles safe database schema migration"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = True):
        self.dry_run = dry_run
        self.verbose = verbose
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=verbose
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def column_exists(self, conn, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
        result = await conn.execute(
            text(f"""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = '{table_name}'
                AND COLUMN_NAME = '{column_name}'
            """)
        )
        return (result.fetchone()[0]) > 0
    
    async def table_exists(self, conn, table_name: str) -> bool:
        """Check if a table exists"""
        result = await conn.execute(
            text(f"SHOW TABLES LIKE '{table_name}'")
        )
        return result.fetchone() is not None
    
    async def safe_add_column(self, conn, table_name: str, column_name: str, 
                              column_definition: str) -> bool:
        """
        Safely add a column if it doesn't exist.
        
        Returns:
            True if column was added or already exists
            False if there was an error
        """
        # Check if column already exists
        if await self.column_exists(conn, table_name, column_name):
            if self.verbose:
                print(f"  ✓ {table_name}.{column_name} already exists")
            return True
        
        # Column doesn't exist, try to add it
        sql = f"ALTER TABLE {table_name} ADD {column_name} {column_definition}"
        
        if self.dry_run:
            print(f"  [DRY-RUN] {sql}")
            return True
        
        try:
            await conn.execute(text(sql))
            if self.verbose:
                print(f"  ✓ Added {column_name} to {table_name}")
            return True
        except Exception as e:
            if self.verbose:
                print(f"  ✗ Error adding {column_name} to {table_name}: {e}")
            return False
    
    async def migrate_table(self, conn, table_name: str) -> int:
        """
        Migrate a single table by adding all missing columns.
        
        Returns:
            Number of columns added
        """
        if not await self.table_exists(conn, table_name):
            if self.verbose:
                print(f"  ⚠ Table {table_name} does not exist, skipping...")
            return 0
        
        columns = COLUMN_DEFINITIONS.get(table_name, {})
        if not columns:
            if self.verbose:
                print(f"  ✓ {table_name}: no columns to add")
            return 0
        
        added_count = 0
        for column_name, column_def in columns.items():
            if await self.safe_add_column(conn, table_name, column_name, column_def):
                added_count += 1
        
        return added_count
    
    async def migrate_all(self) -> dict:
        """
        Run all migrations.
        
        Returns:
            Dictionary with migration results
        """
        results = {
            'tables_checked': 0,
            'columns_added': 0,
            'errors': []
        }
        
        async with self.engine.begin() as conn:
            for table_name in COLUMN_DEFINITIONS.keys():
                results['tables_checked'] += 1
                columns_added = await self.migrate_table(conn, table_name)
                results['columns_added'] += columns_added
        
        return results
    
    async def verify_schema(self) -> dict:
        """
        Verify the database schema against expected columns.
        
        Returns:
            Dictionary with verification results
        """
        verification = {}
        
        async with self.engine.begin() as conn:
            for table_name, columns in COLUMN_DEFINITIONS.items():
                if not await self.table_exists(conn, table_name):
                    verification[table_name] = {
                        'exists': False,
                        'columns_found': 0,
                        'columns_expected': len(columns),
                        'missing_columns': list(columns.keys())
                    }
                    continue
                
                existing_cols = set()
                for col in columns.keys():
                    if await self.column_exists(conn, table_name, col):
                        existing_cols.add(col)
                
                verification[table_name] = {
                    'exists': True,
                    'columns_found': len(existing_cols),
                    'columns_expected': len(columns),
                    'missing_columns': [c for c in columns.keys() if c not in existing_cols],
                    'all_present': len(existing_cols) == len(columns)
                }
        
        return verification
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()


async def main():
    """Main entry point for the migration script"""
    parser = argparse.ArgumentParser(
        description='Safe database migration for Telegram Quiz Bot'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Preview changes without applying them'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify schema only, no changes'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Telegram Quiz Bot - Database Migration")
    print("=" * 60)
    
    if args.dry_run:
        print("Mode: DRY-RUN (preview only, no changes will be made)")
    else:
        print("Mode: LIVE (changes will be applied)")
    
    print()
    
    migration = SafeDatabaseMigration(
        dry_run=args.dry_run,
        verbose=not args.quiet
    )
    
    try:
        if args.verify:
            # Verify mode
            print("Verifying database schema...")
            print()
            
            verification = await migration.verify_schema()
            
            all_ok = True
            for table_name, info in verification.items():
                if info['exists']:
                    status = "✓" if info['all_present'] else "⚠"
                    print(f"  {status} {table_name}: {info['columns_found']}/{info['columns_expected']} columns")
                    
                    if not info['all_present']:
                        all_ok = False
                        print(f"      Missing: {', '.join(info['missing_columns'])}")
                else:
                    print(f"  ✗ {table_name}: table not found")
                    all_ok = False
            
            print()
            if all_ok:
                print("✓ All expected columns are present!")
            else:
                print("⚠ Some columns are missing. Run migration to fix.")
            
        else:
            # Migration mode
            print("Running migrations...")
            print()
            
            results = await migration.migrate_all()
            
            print()
            print(f"Summary:")
            print(f"  • Tables checked: {results['tables_checked']}")
            print(f"  • Columns added: {results['columns_added']}")
            
            if args.dry_run:
                print()
                print("[DRY-RUN] No changes were applied.")
                print("Run without --dry-run to apply changes.")
            else:
                if results['columns_added'] > 0:
                    print()
                    print("✓ Migration complete! Database schema is up to date.")
                else:
                    print()
                    print("✓ Database is already up to date. No changes needed.")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        return 1
    
    finally:
        await migration.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

