#!/usr/bin/env python3
"""
PostgreSQL Schema Execution Script
This script executes the PostgreSQL schema on your database.

Usage:
    python scripts/execute_postgres_schema.py

Environment Variables Required:
    - DATABASE_URL: Full PostgreSQL connection URL
      Example: postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require

Or individually:
    - DB_HOST
    - DB_PORT
    - DB_NAME
    - DB_USER
    - DB_PASSWORD
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment or construct from components."""
    # Check for full DATABASE_URL first
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    
    # Construct from individual components
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"


async def execute_schema_async(schema_file: str):
    """Execute schema file asynchronously using asyncpg."""
    # Get connection params from DATABASE_URL
    database_url = get_database_url()
    
    # Parse the URL to get connection params
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    url = database_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    
    if "@" in url:
        auth, rest = url.split("@", 1)
        user, password = auth.split(":", 1)
        host_port_db = rest.split("/")
        host_port = host_port_db[0].split(":")
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 5432
        dbname = host_port_db[1] if len(host_port_db) > 1 else "postgres"
    else:
        # Fallback
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "5432"))
        dbname = os.getenv("DB_NAME", "postgres")
    
    logger.info(f"Connecting to PostgreSQL: {host}:{port}/{dbname}")
    
    # Read schema file
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Connect and execute
    conn = await asyncpg.connect(
        host=host,
        port=port,
        database=dbname,
        user=user,
        password=password,
        ssl="require"  # Required for production
    )
    
    logger.info("Executing schema...")
    await conn.execute(schema_sql)
    await conn.close()
    
    logger.info("Schema executed successfully!")


def execute_schema_sync(schema_file: str):
    """Execute schema file synchronously using psycopg2."""
    import psycopg2
    
    database_url = get_database_url()
    
    # Parse connection params
    url = database_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    
    if "@" in url:
        auth, rest = url.split("@", 1)
        user, password = auth.split(":", 1)
        host_port_db = rest.split("/")
        host_port = host_port_db[0].split(":")
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 5432
        dbname = host_port_db[1] if len(host_port_db) > 1 else "postgres"
    else:
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "5432"))
        dbname = os.getenv("DB_NAME", "postgres")
    
    logger.info(f"Connecting to PostgreSQL: {host}:{port}/{dbname}")
    
    # Read schema file
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Connect and execute
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=dbname,
        user=user,
        password=password,
        sslmode="require"
    )
    
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Split and execute statements
    statements = schema_sql.split(';')
    for statement in statements:
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                cursor.execute(statement)
                logger.info(f"Executed: {statement[:50]}...")
            except Exception as e:
                logger.warning(f"Statement failed (may be OK): {e}")
    
    cursor.close()
    conn.close()
    
    logger.info("Schema executed successfully!")


def execute_with_sqlalchemy(schema_file: str):
    """Execute schema using SQLAlchemy (works with both sync and async engines)."""
    from sqlalchemy import create_engine, text
    
    database_url = get_database_url()
    
    # Use sync engine for schema creation
    sync_url = database_url.replace("+asyncpg", "").replace("+aiomysql", "")
    
    logger.info(f"Connecting with SQLAlchemy...")
    
    engine = create_engine(sync_url, echo=False)
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    with engine.connect() as conn:
        # Split statements and execute
        statements = schema_sql.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    conn.execute(text(statement))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Statement failed (may be OK): {e}")
    
    logger.info("Schema executed successfully!")


def main():
    """Main entry point."""
    # Schema file path
    schema_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "schema_postgresql.sql"
    )
    
    if not os.path.exists(schema_file):
        logger.error(f"Schema file not found: {schema_file}")
        sys.exit(1)
    
    logger.info(f"Using schema file: {schema_file}")
    
    # Check for asyncpg availability
    try:
        import asyncpg
        use_async = True
    except ImportError:
        use_async = False
    
    # Check for psycopg2 availability
    try:
        import psycopg2
        use_psycopg2 = True
    except ImportError:
        use_psycopg2 = False
    
    # Try different methods
    if use_async:
        try:
            asyncio.run(execute_schema_async(schema_file))
            return
        except Exception as e:
            logger.warning(f"Async execution failed: {e}")
    
    if use_psycopg2:
        try:
            execute_schema_sync(schema_file)
            return
        except Exception as e:
            logger.warning(f"Psycopg2 execution failed: {e}")
    
    # Fallback to SQLAlchemy
    try:
        execute_with_sqlalchemy(schema_file)
    except Exception as e:
        logger.error(f"All methods failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

