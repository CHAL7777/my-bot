"""
Database connection and session management for Telegram Quiz Bot.

This module provides async database connectivity using SQLAlchemy with asyncpg driver.
Designed to work with Supabase, Koyeb, and other PostgreSQL providers.

Key Features:
- Async SQLAlchemy engine with asyncpg driver
- Proper SSL handling for Supabase (sslmode=require via connect_args)
- Connection pooling optimized for production
- Context-aware session management
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from urllib.parse import urlparse, parse_qs, quote, unquote
import os
import logging
import ssl

logger = logging.getLogger(__name__)

from app.config import settings

Base = declarative_base()


def _build_database_url() -> str:
    """
    Build database URL with proper driver and SSL for asyncpg.
    
    For Supabase and other PostgreSQL providers:
    - Use postgresql+asyncpg:// driver (NOT postgresql://)
    - Remove sslmode from URL (it's handled via connect_args)
    - Properly handle special characters in password (#, @, etc.)
    
    Returns:
        str: Properly formatted async database URL without sslmode in query
    """
    raw_db_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    
    if not raw_db_url:
        raise ValueError("DATABASE_URL is not set")
    
    # Ensure we're using asyncpg driver
    if "postgresql" in raw_db_url.lower() or "postgres" in raw_db_url.lower():
        # Parse the URL properly to handle special characters
        # The issue: passwords like "9.f3hHDyDY#Furj" have # which breaks URL parsing
        
        # Remove existing driver prefix
        clean_url = raw_db_url
        for prefix in ["postgresql+asyncpg://", "postgresql://", "postgres+asyncpg://", "postgres://"]:
            if clean_url.lower().startswith(prefix.lower()):
                clean_url = clean_url[len(prefix):]
                break
        
        # Now split into user:password@host:port/db
        if '@' in clean_url:
            user_pass, rest = clean_url.split('@', 1)
            if ':' in user_pass:
                user, password = user_pass.split(':', 1)
                # URL encode the password (especially # character)
                encoded_password = quote(password, safe='')
                clean_url = f"{user}:{encoded_password}@{rest}"
        
        # Reconstruct with asyncpg driver (NO sslmode in URL)
        db_url = f"postgresql+asyncpg://{clean_url}"
        
        logger.info(f"PostgreSQL URL configured for asyncpg")
    else:
        db_url = raw_db_url
        logger.info(f"Using database URL as-is: {db_url.split('://')[0]}")
    
    # Remove sslmode from URL query string (handled via connect_args)
    # Important: Also remove any other query params that shouldn't be in the URL
    if "?" in db_url:
        base_url, query = db_url.split("?", 1)
        # Filter out sslmode and other driver-incompatible params
        params = [p for p in query.split("&") if not p.startswith("sslmode")]
        if params:
            db_url = f"{base_url}?{'&'.join(params)}"
        else:
            db_url = base_url
    
    # Double-check: ensure db_url doesn't have malformed database name
    # Handle edge case where URL might look like: postgres:password@host/db?param=value
    # The '?' should only be a query string delimiter, not part of the path
    if "?" in db_url and "/" not in db_url.split("?", 1)[1]:
        # Malformed: db name has ? in it
        # This can happen with URLs like: user:pass@host?sslmode=require (missing database name)
        logger.warning(f"Malformed database URL detected: {db_url}")
    
    # Log connection info (mask password)
    if '@' in db_url:
        display_url = db_url.split('@')[0] + '@...'
    else:
        display_url = db_url[:30] + '...'
    logger.info(f"Database URL: {display_url}")
    
    return db_url


class Database:
    """
    Database connection manager.
    
    Provides:
    - Async SQLAlchemy engine with connection pooling
    - Session factory for creating async sessions
    - Health check capabilities
    """
    
    def __init__(self):
        """Initialize database engine and session factory."""
        # Build the database URL first
        DATABASE_URL = _build_database_url()
        
        # Build engine kwargs
        # Note: For asyncpg with SQLAlchemy, SSL is passed via connect_args
        engine_kwargs = {
            "echo": False,  # Set to True for debugging SQL
            "pool_pre_ping": True,  # Verify connections before use
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "future": True,  # Use SQLAlchemy 2.0 features
            "connect_args": {
                "ssl": "require",  # Required for Supabase/Railway/etc.
            },
        }
        
        # Add SQLite-specific settings if needed
        if "sqlite" in DATABASE_URL.lower():
            # Remove pool settings for SQLite
            engine_kwargs.pop("pool_size", None)
            engine_kwargs.pop("max_overflow", None)
            engine_kwargs.pop("connect_args", None)
            logger.info("SQLite detected - using in-memory pool settings")
        
        logger.info(f"Creating async database engine...")
        logger.info(f"  Pool size: {engine_kwargs.get('pool_size', 'default')}")
        logger.info(f"  Max overflow: {engine_kwargs.get('max_overflow', 'default')}")
        logger.info(f"  SSL: required")
        
        self.engine = create_async_engine(
            DATABASE_URL,
            **engine_kwargs
        )
        
        logger.info("Database engine created successfully")
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            future=True
        )
        
        logger.info("Async session factory configured")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session (generator style for dependency injection)."""
        async with self.async_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self) -> None:
        """Close the database engine gracefully."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine disposed")
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            async with self.async_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database instance
db = Database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.
    
    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session
            pass
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async for session in db.get_session():
        yield session


async def init_db() -> None:
    """
    Initialize database tables using SQLAlchemy metadata.
    
    This creates all tables defined in models.py if they don't exist.
    Note: Enum types must be created separately via init_db.py script.
    """
    from app.db.models import Base
    
    logger.info("Initializing database tables...")
    try:
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database tables: {e}")
        # This often happens if enum types don't exist yet
        logger.info("Hint: Run 'python scripts/init_db.py' to create enum types first")
        raise


async def close_db() -> None:
    """Close database connections on application shutdown."""
    await db.close()

