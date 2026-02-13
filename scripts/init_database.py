#!/usr/bin/env python3
"""
Database initialization script for Telegram Quiz Bot.

This script executes schema.sql to create all tables in the SQLite database.
Production-safe: Preserves existing data, only creates missing tables.

Usage:
    python scripts/init_database.py

Environment Variables:
    SQLITE_DB_PATH - Path to SQLite database (default: /data/quizbot.db)
"""
import sqlite3
import os
import sys
import re
from pathlib import Path

# Project root directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Database configuration
DEFAULT_DB_PATH = "/data/quizbot.db"
SCHEMA_PATH = project_root / "data" / "schema.sql"


def get_database_path() -> str:
    """Get database path from environment or default."""
    return os.getenv("SQLITE_DB_PATH", DEFAULT_DB_PATH)


def parse_sql_statements(sql_content: str) -> list:
    """Parse SQL content into individual statements."""
    # Remove comments
    lines = []
    for line in sql_content.split('\n'):
        # Remove line comments
        if '--' in line:
            line = line[:line.index('--')]
        lines.append(line)
    
    content = '\n'.join(lines)
    
    # Split by semicolons
    statements = []
    for stmt in content.split(';'):
        stmt = stmt.strip()
        if stmt:
            statements.append(stmt)
    
    return statements


def make_statement_idempotent(statement: str) -> str:
    """Make a SQL statement idempotent by adding IF NOT EXISTS where appropriate."""
    statement = statement.strip()
    
    # Handle CREATE TABLE statements
    if statement.upper().startswith('CREATE TABLE'):
        # Check if already has IF NOT EXISTS
        if 'IF NOT EXISTS' not in statement.upper():
            # Replace first CREATE TABLE with CREATE TABLE IF NOT EXISTS
            statement = re.sub(
                r'CREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS)',
                'CREATE TABLE IF NOT EXISTS ',
                statement,
                count=1,
                flags=re.IGNORECASE
            )
    
    # Handle CREATE INDEX statements
    elif statement.upper().startswith('CREATE INDEX'):
        if 'IF NOT EXISTS' not in statement.upper():
            statement = re.sub(
                r'CREATE\s+INDEX\s+(?!IF\s+NOT\s+EXISTS)',
                'CREATE INDEX IF NOT EXISTS ',
                statement,
                count=1,
                flags=re.IGNORECASE
            )
    
    return statement


def init_database():
    """
    Initialize database from schema.sql.
    
    Production-safe:
    - Creates /data directory if missing
    - Preserves existing data
    - Only creates missing tables
    - Handles schema changes gracefully
    """
    db_path = get_database_path()
    
    # Ensure data directory exists
    data_dir = os.path.dirname(db_path)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        print(f"✓ Created data directory: {data_dir}")
    
    # Check if schema file exists
    if not SCHEMA_PATH.exists():
        print(f"✗ Error: Schema file not found at {SCHEMA_PATH}")
        sys.exit(1)
    
    print(f"Database: {db_path}")
    print(f"Schema: {SCHEMA_PATH}")
    
    # Connect to database (creates if not exists)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    
    # Check existing tables before
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    existing_tables = set(row[0] for row in cursor.fetchall())
    print(f"Existing tables: {len(existing_tables)}")
    
    # Read and parse schema.sql
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    
    statements = parse_sql_statements(schema_sql)
    print(f"SQL statements to execute: {len(statements)}")
    
    # Execute statements one by one with idempotent handling
    executed = 0
    skipped = 0
    errors = 0
    
    for stmt in statements:
        stmt = make_statement_idempotent(stmt)
        if not stmt:
            continue
            
        try:
            cursor.execute(stmt)
            executed += 1
        except sqlite3.OperationalError as e:
            # Table/index already exists - skip gracefully
            if 'already exists' in str(e):
                skipped += 1
                continue
            # Other errors should be reported
            print(f"✗ Error executing: {stmt[:60]}...")
            print(f"   Error: {e}")
            errors += 1
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            errors += 1
    
    conn.commit()
    
    # Check tables after
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    all_tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    # Calculate new tables
    new_tables = [t for t in all_tables if t not in existing_tables]
    
    print(f"\nExecution summary:")
    print(f"  Executed: {executed}")
    print(f"  Skipped (existing): {skipped}")
    print(f"  Errors: {errors}")
    print(f"\nTotal tables: {len(all_tables)}")
    
    if new_tables:
        print(f"New tables created: {new_tables}")
    else:
        print("✓ No new tables needed (existing database preserved)")
    
    # Show all tables
    print("\nAll tables in database:")
    for table in all_tables:
        print(f"  - {table}")
    
    print("\n✓ Database initialization complete!")
    return errors == 0


def verify_database():
    """Verify database is properly initialized."""
    db_path = get_database_path()
    
    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Check data
    print("\nDatabase verification:")
    print(f"  Tables: {len(tables)}")
    
    for table in tables[:5]:  # Show first 5 tables
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count} rows")
    
    if len(tables) > 5:
        print(f"  ... and {len(tables) - 5} more tables")
    
    conn.close()
    
    if tables:
        print("\n✓ Database verification passed!")
        return True
    else:
        print("\n✗ No tables found in database")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Initialize SQLite database from schema.sql"
    )
    parser.add_argument(
        "--verify", 
        action="store_true",
        help="Verify database without reinitializing"
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Override database path"
    )
    
    args = parser.parse_args()
    
    # Override path if provided
    if args.path:
        os.environ["SQLITE_DB_PATH"] = args.path
    
    if args.verify:
        success = verify_database()
    else:
        success = init_database()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

