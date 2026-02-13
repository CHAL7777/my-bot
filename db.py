import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional

logger = logging.getLogger(__name__)

DATABASE_PATH = "/data/quizbot.db"

# Ensure the /data directory exists before connecting to the database
DATA_DIR = os.path.dirname(DATABASE_PATH)
if DATA_DIR and not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        logger.info(f"Created data directory: {DATA_DIR}")
    except Exception as e:
        logger.error(f"Failed to create data directory {DATA_DIR}: {e}")
        # Continue anyway - sqlite3.connect will fail with a clearer error

conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row


def init_db():
    """Initialize database tables"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_premium INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            chapter_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            chapter_name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
            UNIQUE(subject_id, chapter_name)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            chapter_id INTEGER NOT NULL,
            difficulty TEXT CHECK(difficulty IN ('simple', 'medium', 'hard')) NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT CHECK(correct_option IN ('A', 'B', 'C', 'D')) NOT NULL,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
            FOREIGN KEY (chapter_id) REFERENCES chapters(chapter_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            screenshot_file_id TEXT,
            status TEXT CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
            transaction_id TEXT,
            notes TEXT,
            approved_by INTEGER,
            approved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (approved_by) REFERENCES admin_users(admin_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_option TEXT,
            is_correct INTEGER,
            time_taken INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (question_id) REFERENCES questions(question_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            leaderboard_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            period TEXT CHECK(period IN ('daily', 'weekly', 'monthly', 'overall')) NOT NULL,
            total_score INTEGER DEFAULT 0,
            total_accuracy REAL DEFAULT 0.0,
            total_questions INTEGER DEFAULT 0,
            rank_position INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, period)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            status TEXT CHECK(status IN ('pending', 'completed', 'cancelled')) DEFAULT 'pending',
            reward_claimed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id),
            UNIQUE(referrer_id, referred_id)
        )
    """)

    conn.commit()


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections"""
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        raise e


def get_user(user_id: int) -> Optional[sqlite3.Row]:
    """Get user by ID"""
    cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()


def create_user(user_id: int, username: Optional[str] = None, 
                first_name: Optional[str] = None, last_name: Optional[str] = None):
    """Create a new user"""
    conn.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, first_name, last_name))
    conn.commit()


def update_user_premium(user_id: int, is_premium: bool, is_approved: bool):
    """Update user premium and approval status"""
    conn.execute("""
        UPDATE users SET is_premium = ?, is_approved = ? WHERE user_id = ?
    """, (1 if is_premium else 0, 1 if is_approved else 0, user_id))
    conn.commit()


def get_questions(subject_id: int, chapter_id: int, difficulty: str, limit: int = 10):
    """Get random questions for a quiz"""
    cursor = conn.execute("""
        SELECT * FROM questions
        WHERE subject_id = ? AND chapter_id = ? AND difficulty = ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (subject_id, chapter_id, difficulty, limit))
    return cursor.fetchall()


def get_subjects():
    """Get all subjects"""
    cursor = conn.execute("SELECT * FROM subjects")
    return cursor.fetchall()


def get_chapters(subject_id: int):
    """Get chapters for a subject"""
    cursor = conn.execute("SELECT * FROM chapters WHERE subject_id = ?", (subject_id,))
    return cursor.fetchall()


def record_attempt(user_id: int, question_id: int, selected_option: str, 
                   is_correct: bool, time_taken: int = 0):
    """Record a quiz attempt"""
    conn.execute("""
        INSERT INTO quiz_attempts (user_id, question_id, selected_option, is_correct, time_taken)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, question_id, selected_option, 1 if is_correct else 0, time_taken))
    conn.commit()


def get_leaderboard(period: str = 'overall', limit: int = 10):
    """Get leaderboard data"""
    cursor = conn.execute("""
        SELECT u.user_id, u.username, u.first_name, l.total_score, l.total_accuracy
        FROM leaderboard l
        JOIN users u ON l.user_id = u.user_id
        WHERE l.period = ?
        ORDER BY l.rank_position ASC
        LIMIT ?
    """, (period, limit))
    return cursor.fetchall()


def get_pending_payments():
    """Get pending payments for admin approval"""
    cursor = conn.execute("""
        SELECT p.*, u.username, u.first_name
        FROM payments p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.status = 'pending'
        ORDER BY p.created_at ASC
    """)
    return cursor.fetchall()


def approve_payment(payment_id: int, admin_id: int):
    """Approve a payment"""
    conn.execute("""
        UPDATE payments 
        SET status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP
        WHERE payment_id = ?
    """, (admin_id, payment_id))
    
    cursor = conn.execute("SELECT user_id FROM payments WHERE payment_id = ?", (payment_id,))
    payment = cursor.fetchone()
    if payment:
        update_user_premium(payment['user_id'], is_premium=True, is_approved=True)
    
    conn.commit()


def reject_payment(payment_id: int):
    """Reject a payment"""
    conn.execute("""
        UPDATE payments SET status = 'rejected' WHERE payment_id = ?
    """, (payment_id,))
    conn.commit()


def add_payment(user_id: int, amount: float, screenshot_file_id: Optional[str] = None,
                transaction_id: Optional[str] = None, notes: Optional[str] = None):
    """Add a new payment"""
    conn.execute("""
        INSERT INTO payments (user_id, amount, screenshot_file_id, transaction_id, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, screenshot_file_id, transaction_id, notes))
    conn.commit()


def get_user_stats(user_id: int):
    """Get user quiz statistics"""
    cursor = conn.execute("""
        SELECT 
            COUNT(*) as total_attempts,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_answers,
            AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) as accuracy
        FROM quiz_attempts
        WHERE user_id = ?
    """, (user_id,))
    return cursor.fetchone()


def generate_referral_code(user_id: int) -> str:
    """Generate unique referral code for user"""
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    cursor = conn.execute("SELECT referral_code FROM users WHERE referral_code = ?", (code,))
    if cursor.fetchone():
        return generate_referral_code(user_id)
    
    conn.execute("UPDATE users SET referral_code = ? WHERE user_id = ?", (code, user_id))
    conn.commit()
    return code


def get_referral_count(user_id: int) -> int:
    """Get referral count for user"""
    cursor = conn.execute("""
        SELECT COUNT(*) FROM referrals 
        WHERE referrer_id = ? AND status = 'completed'
    """, (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

