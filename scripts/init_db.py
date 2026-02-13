#!/usr/bin/env python3
"""
Database Initialization Script for Telegram Quiz Bot

This script initializes the PostgreSQL database with all required enums and tables.
It is designed to work with Supabase and other PostgreSQL providers that don't
support DO $$ blocks directly.

Usage:
    python scripts/init_db.py

Environment Variables:
    DATABASE_URL - Full PostgreSQL connection URL
                  Example: postgresql+asyncpg://user:pass@host:5432/dbname

Or individually:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

For Supabase:
    - Get your connection string from: Supabase Dashboard -> Settings -> Database
    - Format: postgresql://user:password@host:5432/dbname
    - The script will automatically add sslmode=require
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUM DEFINITIONS (Python side for programmatic creation)
# ============================================================================
ENUM_DEFINITIONS = [
    ("user_role", ["student", "admin"]),
    ("question_difficulty", ["simple", "medium", "hard"]),
    ("correct_option", ["A", "B", "C", "D"]),
    ("selected_option", ["A", "B", "C", "D"]),
    ("payment_status", ["pending", "approved", "rejected"]),
    ("leaderboard_period", ["daily", "weekly", "monthly", "overall"]),
    ("progress_difficulty", ["simple", "medium", "hard"]),
    ("admin_role", ["superadmin", "moderator"]),
    ("contact_category", ["payment", "quiz_error", "access", "general", "feedback"]),
    ("contact_status", ["open", "replied", "closed"]),
    ("referral_status", ["pending", "completed", "cancelled"]),
    ("telegram_admin_role", ["superadmin", "admin"]),
    ("chapter_limit_difficulty", ["simple", "medium", "hard"]),
]

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_database_url() -> str:
    """Get database URL from environment or construct from components."""
    from urllib.parse import quote
    
    # Check for full DATABASE_URL first
    if os.getenv("DATABASE_URL"):
        raw_url = os.getenv("DATABASE_URL", "")
        
        # Handle special characters in password (like #)
        if "@" in raw_url and ":" in raw_url:
            # Parse and re-encode the password
            auth_part = raw_url.split("@")[0].split("://")[1] if "://" in raw_url else raw_url.split("@")[0]
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                # Encode the password
                encoded_password = quote(password, safe='')
                # Rebuild URL
                protocol = raw_url.split("://")[0] if "://" in raw_url else "postgresql"
                rest = raw_url.split("@", 1)[1]
                raw_url = f"{protocol}://{user}:{encoded_password}@{rest}"
        
        # Ensure we're using asyncpg driver
        if not raw_url.startswith("postgresql+asyncpg://"):
            if raw_url.startswith("postgresql://"):
                raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif "://" in raw_url:
                # Keep existing protocol (e.g., postgres://)
                pass
            else:
                # No protocol, add it
                raw_url = f"postgresql+asyncpg://{raw_url}"
        return raw_url
    
    # Construct from individual components
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    
    # URL encode the password
    encoded_password = quote(password, safe='')
    
    return f"postgresql+asyncpg://{user}:{encoded_password}@{host}:{port}/{dbname}"


def parse_connection_params(db_url: str) -> dict:
    """Parse database URL into connection parameters."""
    from urllib.parse import unquote
    
    # Remove the driver prefix
    clean_url = db_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    
    if "@" not in clean_url:
        raise ValueError("Invalid database URL format")
    
    auth, rest = clean_url.split("@", 1)
    user, password = auth.split(":", 1)
    
    # URL decode the password (to handle # and other special characters)
    password = unquote(password)
    
    if "/" in rest:
        host_port, dbname = rest.split("/", 1)
    else:
        host_port = rest
        dbname = "postgres"
    
    if ":" in host_port:
        host, port = host_port.split(":")
    else:
        host = host_port
        port = "5432"
    
    return {
        "host": host,
        "port": int(port),
        "database": dbname,
        "user": user,
        "password": password,
    }


# ============================================================================
# ENUM CREATION
# ============================================================================

async def create_enum_type(conn: asyncpg.Connection, enum_name: str, values: list) -> None:
    """Create an enum type if it doesn't exist."""
    # Check if enum already exists
    exists = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = $1)",
        enum_name
    )
    
    if exists:
        logger.info(f"  ✓ Enum '{enum_name}' already exists")
        return
    
    # Create the enum with proper quoting
    values_str = ", ".join(f"'{v}'" for v in values)
    await conn.execute(
        f"CREATE TYPE {enum_name} AS ENUM ({values_str})"
    )
    logger.info(f"  ✓ Created enum '{enum_name}' with values: {values}")


async def create_all_enums(conn: asyncpg.Connection) -> None:
    """Create all required enum types."""
    logger.info("Creating enum types...")
    for enum_name, values in ENUM_DEFINITIONS:
        await create_enum_type(conn, enum_name, values)
    logger.info("All enum types created successfully!")


# ============================================================================
# TABLE CREATION
# ============================================================================

TABLE_CREATION_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    role user_role DEFAULT 'student',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    blocked BOOLEAN DEFAULT FALSE,
    approved BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    referral_code VARCHAR(20) UNIQUE,
    referred_by BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    referral_count INTEGER DEFAULT 0
);

-- Subjects table
CREATE TABLE IF NOT EXISTS subjects (
    subject_id SERIAL PRIMARY KEY,
    subject_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chapters table
CREATE TABLE IF NOT EXISTS chapters (
    chapter_id SERIAL PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_name VARCHAR(100) NOT NULL,
    chapter_order INTEGER DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subject_id, chapter_name)
);

-- Questions table
CREATE TABLE IF NOT EXISTS questions (
    question_id SERIAL PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    difficulty question_difficulty NOT NULL,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option correct_option NOT NULL,
    explanation TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Progress table
CREATE TABLE IF NOT EXISTS user_progress (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    difficulty progress_difficulty,
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    total_time_spent INTEGER DEFAULT 0,
    last_attempt TIMESTAMP WITH TIME ZONE,
    accuracy FLOAT DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subject_id, chapter_id, difficulty)
);

-- Quiz Attempts table
CREATE TABLE IF NOT EXISTS quiz_attempts (
    attempt_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(question_id) ON DELETE CASCADE,
    selected_option selected_option,
    is_correct BOOLEAN,
    time_taken INTEGER DEFAULT 0,
    quiz_session_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    screenshot_file_id VARCHAR(255),
    screenshot_file_path VARCHAR(500),
    status payment_status DEFAULT 'pending',
    amount FLOAT NOT NULL,
    subscription_days INTEGER,
    transaction_id VARCHAR(100),
    notes TEXT,
    approved_by BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Leaderboard table
CREATE TABLE IF NOT EXISTS leaderboard (
    leaderboard_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    period leaderboard_period NOT NULL,
    total_score INTEGER DEFAULT 0,
    total_accuracy FLOAT DEFAULT 0.00,
    total_questions INTEGER DEFAULT 0,
    rank_position INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, period)
);

-- User Daily Limits table
CREATE TABLE IF NOT EXISTS user_daily_limits (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    quiz_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- User Chapter Daily Limits table
CREATE TABLE IF NOT EXISTS user_chapter_daily_limits (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_id INTEGER REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    difficulty chapter_limit_difficulty,
    date DATE NOT NULL,
    question_count INTEGER DEFAULT 0,
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subject_id, chapter_id, difficulty, date)
);

-- Admin Users table
CREATE TABLE IF NOT EXISTS admin_users (
    admin_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role admin_role DEFAULT 'moderator',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Admin Logs table
CREATE TABLE IF NOT EXISTS admin_logs (
    id SERIAL PRIMARY KEY,
    admin_user_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Contact Messages table
CREATE TABLE IF NOT EXISTS contact_messages (
    message_id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(20) UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    category contact_category NOT NULL,
    subject VARCHAR(200),
    message_text TEXT NOT NULL,
    status contact_status DEFAULT 'open',
    admin_reply TEXT,
    replied_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    replied_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Access Audit Log table
CREATE TABLE IF NOT EXISTS access_audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    access_granted BOOLEAN NOT NULL,
    reason VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Referrals table
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    referred_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    status referral_status DEFAULT 'pending',
    reward_claimed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(referrer_id, referred_id)
);

-- Telegram Admins table
CREATE TABLE IF NOT EXISTS telegram_admins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    role telegram_admin_role DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    added_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""


INDEX_CREATION_SQL = """
-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by);

-- Indexes for chapters
CREATE INDEX IF NOT EXISTS idx_subject_order ON chapters(subject_id, chapter_order);

-- Indexes for questions
CREATE INDEX IF NOT EXISTS idx_subject_chapter ON questions(subject_id, chapter_id);
CREATE INDEX IF NOT EXISTS idx_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_active ON questions(is_active);

-- Indexes for user_progress
CREATE INDEX IF NOT EXISTS idx_user_progress ON user_progress(user_id, accuracy);
CREATE INDEX IF NOT EXISTS idx_subject_progress ON user_progress(subject_id, chapter_id, difficulty);

-- Indexes for quiz_attempts
CREATE INDEX IF NOT EXISTS idx_user_attempts ON quiz_attempts(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_question_attempts ON quiz_attempts(question_id, is_correct);
CREATE INDEX IF NOT EXISTS idx_session ON quiz_attempts(quiz_session_id);

-- Indexes for payments
CREATE INDEX IF NOT EXISTS idx_payment_status ON payments(status, created_at);
CREATE INDEX IF NOT EXISTS idx_user_payments ON payments(user_id, created_at);

-- Indexes for leaderboard
CREATE INDEX IF NOT EXISTS idx_leaderboard_period ON leaderboard(period, rank_position);
CREATE INDEX IF NOT EXISTS idx_user_leaderboard ON leaderboard(user_id, period);

-- Indexes for user_daily_limits
CREATE INDEX IF NOT EXISTS idx_date_limit ON user_daily_limits(date, quiz_count);

-- Indexes for user_chapter_daily_limits
CREATE INDEX IF NOT EXISTS idx_chapter_limit_lookup ON user_chapter_daily_limits(user_id, chapter_id, difficulty, date);

-- Indexes for admin_users
CREATE INDEX IF NOT EXISTS idx_admin_username ON admin_users(username);
CREATE INDEX IF NOT EXISTS idx_admin_email ON admin_users(email);

-- Indexes for contact_messages
CREATE INDEX IF NOT EXISTS idx_contact_ticket_id ON contact_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_contact_user ON contact_messages(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_contact_status ON contact_messages(status, created_at);
CREATE INDEX IF NOT EXISTS idx_contact_category ON contact_messages(category);

-- Indexes for access_audit_log
CREATE INDEX IF NOT EXISTS idx_access_audit_user ON access_audit_log(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_access_audit_denied ON access_audit_log(access_granted, created_at);
CREATE INDEX IF NOT EXISTS idx_access_audit_resource ON access_audit_log(resource, action);

-- Indexes for referrals
CREATE INDEX IF NOT EXISTS idx_referral_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referral_referred ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referral_status ON referrals(status);

-- Indexes for telegram_admins
CREATE INDEX IF NOT EXISTS idx_telegram_admin_user_id ON telegram_admins(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_admin_role ON telegram_admins(role);
"""


TRIGGER_CREATION_SQL = """
-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
DO $$
DECLARE
    table_names TEXT[] := ARRAY['users', 'subjects', 'chapters', 
                                  'admin_users', 'telegram_admins'];
    t TEXT;
BEGIN
    FOREACH t IN ARRAY table_names
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS update_%I_updated_at ON %I', t, t);
        EXECUTE format('
            CREATE TRIGGER update_%I_updated_at
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()', t, t);
    END LOOP;
END $$;
"""


async def create_tables(conn: asyncpg.Connection) -> None:
    """Create all database tables."""
    logger.info("Creating tables...")
    
    # Execute table creation
    await conn.execute(TABLE_CREATION_SQL)
    logger.info("  ✓ Tables created")
    
    # Execute index creation
    await conn.execute(INDEX_CREATION_SQL)
    logger.info("  ✓ Indexes created")
    
    # Execute trigger creation
    await conn.execute(TRIGGER_CREATION_SQL)
    logger.info("  ✓ Triggers created")


# ============================================================================
# SQLALCHEMY SETUP (Optional - for ORM usage)
# ============================================================================

async def test_sqlalchemy_connection(db_url: str) -> bool:
    """Test the SQLAlchemy async engine connection."""
    logger.info("Testing SQLAlchemy async engine connection...")
    
    engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        future=True,
        pool_size=5,
        max_overflow=10,
    )
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("  ✓ SQLAlchemy async engine connected successfully!")
        await engine.dispose()
        return True
    except Exception as e:
        logger.error(f"  ✗ SQLAlchemy connection failed: {e}")
        await engine.dispose()
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def init_database() -> bool:
    """Initialize the complete database."""
    logger.info("=" * 60)
    logger.info("🗄️  DATABASE INITIALIZATION FOR KOYEB + SUPABASE")
    logger.info("=" * 60)
    
    try:
        # Get database URL
        db_url = get_database_url()
        logger.info(f"Database URL configured: {db_url.split('@')[0]}@...")
        
        # Parse connection params
        conn_params = parse_connection_params(db_url)
        logger.info(f"Connecting to: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
        
        # Connect to database
        logger.info("Connecting to PostgreSQL...")
        conn = await asyncpg.connect(
            host=conn_params["host"],
            port=conn_params["port"],
            database=conn_params["database"],
            user=conn_params["user"],
            password=conn_params["password"],
            ssl="require",  # Required for Supabase
            command_timeout=60,
        )
        logger.info("  ✓ Connected to PostgreSQL!")
        
        # Create enums
        await create_all_enums(conn)
        
        # Create tables
        await create_tables(conn)
        
        # Close connection
        await conn.close()
        logger.info("  ✓ Database connection closed")
        
        # Test SQLAlchemy connection
        await test_sqlalchemy_connection(db_url)
        
        logger.info("=" * 60)
        logger.info("✅ DATABASE INITIALIZATION COMPLETE!")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    # Check for required environment variables
    if not os.getenv("DATABASE_URL"):
        if not all([os.getenv("DB_HOST"), os.getenv("DB_NAME"), os.getenv("DB_USER")]):
            logger.error("Error: DATABASE_URL or individual DB_* environment variables required!")
            logger.info("\nSet one of the following:")
            logger.info("  export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
            logger.info("  Or:")
            logger.info("  export DB_HOST=host")
            logger.info("  export DB_PORT=5432")
            logger.info("  export DB_NAME=dbname")
            logger.info("  export DB_USER=user")
            logger.info("  export DB_PASSWORD=password")
            sys.exit(1)
    
    # Run initialization
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

