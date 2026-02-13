#!/usr/bin/env python3
"""
SQLite Query Reference Script for quizbot.db
Run this script to execute common database queries.
"""

import sqlite3
from pathlib import Path

DB_PATH = "/data/quizbot.db"


def query_users():
    """Query all users"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, approved, is_premium FROM users;")
    users = cursor.fetchall()
    print("\n=== ALL USERS ===")
    for u in users:
        print(f"ID: {u[0]}, Username: {u[1]}, Name: {u[2]}, Approved: {u[3]}, Premium: {u[4]}")
    conn.close()
    return users


def query_user_by_id(user_id):
    """Query specific user by ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,))
    user = cursor.fetchone()
    print(f"\n=== USER {user_id} ===")
    if user:
        print(f"Full data: {user}")
    else:
        print("User not found!")
    conn.close()
    return user


def query_users_count():
    """Count total users"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    print(f"\n=== TOTAL USERS: {count} ===")
    conn.close()
    return count


def query_approved_users():
    """Query approved users"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name FROM users WHERE approved = 1;")
    users = cursor.fetchall()
    print("\n=== APPROVED USERS ===")
    for u in users:
        print(f"ID: {u[0]}, Username: {u[1]}, Name: {u[2]}")
    conn.close()
    return users


def query_premium_users():
    """Query premium users"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, is_premium FROM users WHERE is_premium = 1;")
    users = cursor.fetchall()
    print("\n=== PREMIUM USERS ===")
    for u in users:
        print(f"ID: {u[0]}, Username: {u[1]}, Name: {u[2]}, Premium: {u[3]}")
    conn.close()
    return users


def query_payments():
    """Query all payments"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT payment_id, user_id, status, amount, created_at FROM payments;")
    payments = cursor.fetchall()
    print("\n=== ALL PAYMENTS ===")
    for p in payments:
        print(f"ID: {p[0]}, User: {p[1]}, Status: {p[2]}, Amount: {p[3]}, Date: {p[4]}")
    conn.close()
    return payments


def query_pending_payments():
    """Query pending payments"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT payment_id, user_id, amount, screenshot_file_id FROM payments WHERE status = 'pending';")
    payments = cursor.fetchall()
    print("\n=== PENDING PAYMENTS ===")
    for p in payments:
        print(f"Payment ID: {p[0]}, User: {p[1]}, Amount: {p[2]}, Screenshot: {p[3]}")
    conn.close()
    return payments


def query_tables():
    """List all tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\n=== TABLES ===")
    for t in tables:
        print(f"  - {t[0]}")
    conn.close()
    return tables


def query_schema(table_name):
    """Show table schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print(f"\n=== SCHEMA: {table_name} ===")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    conn.close()
    return columns


def query_leaderboard():
    """Query leaderboard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT leaderboard_id, user_id, period, total_score, rank_position FROM leaderboard ORDER BY period, rank_position;")
    entries = cursor.fetchall()
    print("\n=== LEADERBOARD ===")
    for e in entries:
        print(f"ID: {e[0]}, User: {e[1]}, Period: {e[2]}, Score: {e[3]}, Rank: {e[4]}")
    conn.close()
    return entries


def main():
    print("SQLite Database Query Tool for quizbot.db")
    print("=" * 50)
    
    # Run all queries
    query_tables()
    query_users_count()
    query_users()
    query_approved_users()
    query_premium_users()
    query_payments()
    query_pending_payments()
    query_leaderboard()
    
    # Show schemas
    print("\n=== TABLE SCHEMAS ===")
    for table in ['users', 'payments', 'leaderboard']:
        query_schema(table)


if __name__ == "__main__":
    main()

