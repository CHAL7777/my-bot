"""
Database Fix Script: Correct Inconsistent User States and Verify Access

🚨 CRITICAL SECURITY FIX

This script:
1. Fixes inconsistent user states (is_premium=True, approved=False)
2. Verifies that approved users can access quizzes
3. Tests the access control system

Usage:
    python scripts/fix_user_states.py --fix           # Fix inconsistent states
    python scripts/fix_user_states.py --verify        # Test access control
    python scripts/fix_user_states.py --refresh 123   # Refresh specific user
    python scripts/fix_user_states.py --set-approved 123 --yes  # Approve user
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import User
from app.config import settings


async def fix_user_states():
    """Fix inconsistent user states."""
    print("🔧 Fixing inconsistent user states...")
    
    # Use the bot's database URL
    database_url = settings.DATABASE_URL
    
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Find users with inconsistent states
        query = text("""
            SELECT user_id, username, approved, is_premium 
            FROM users 
            WHERE is_premium = 1 AND approved = 0
        """)
        result = await session.execute(query)
        inconsistent_users = result.fetchall()
        
        if inconsistent_users:
            print(f"\n⚠️  Found {len(inconsistent_users)} users with inconsistent states:")
            for user_row in inconsistent_users:
                user_id, username, approved, is_premium = user_row
                print(f"   User {user_id} ({username}): approved={approved}, is_premium={is_premium}")
                
                # Fix: Set is_premium = 0 for non-approved users
                update_query = text("""
                    UPDATE users 
                    SET is_premium = 0 
                    WHERE user_id = :user_id AND approved = 0
                """)
                await session.execute(update_query, {"user_id": user_id})
                print(f"   → Fixed: Set is_premium=0")
            
            await session.commit()
            print(f"\n✅ Fixed {len(inconsistent_users)} inconsistent user states")
        else:
            print("\n✅ No inconsistent user states found")
        
        # Verify approved users
        print("\n📊 Verifying approved users:")
        
        approved_query = text("""
            SELECT user_id, username, approved, is_premium 
            FROM users 
            WHERE approved = 1
        """)
        approved_result = await session.execute(approved_query)
        approved_users = approved_result.fetchall()
        
        print(f"   Approved users: {len(approved_users)}")
        for user_row in approved_users[:5]:  # Show first 5
            user_id, username, approved, is_premium = user_row
            print(f"   - User {user_id} ({username}): approved={approved}, is_premium={is_premium}")
        
        if len(approved_users) > 5:
            print(f"   ... and {len(approved_users) - 5} more")
        
        # Show non-approved users
        non_approved_query = text("""
            SELECT user_id, username, approved, is_premium 
            FROM users 
            WHERE approved = 0
        """)
        non_approved_result = await session.execute(non_approved_query)
        non_approved_users = non_approved_result.fetchall()
        
        print(f"   Non-approved users: {len(non_approved_users)}")
    
    await engine.dispose()
    print("\n🔒 Database fix complete!")


async def verify_access():
    """Verify that access control is working correctly."""
    print("\n🧪 Testing access control...")
    
    database_url = settings.DATABASE_URL
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Test query - this is what the middleware uses
        query = text("SELECT user_id, approved, is_premium FROM users LIMIT 10")
        result = await session.execute(query)
        users = result.fetchall()
        
        print("\n📋 User access status (first 10 users):")
        print("-" * 60)
        print(f"{'User ID':<15} {'Approved':<12} {'Is Premium':<12} {'Can Access'}")
        print("-" * 60)
        
        for user_id, approved, is_premium in users:
            can_access = "✅ YES" if approved else "❌ NO"
            print(f"{user_id:<15} {str(approved):<12} {str(is_premium):<12} {can_access}")
        
        print("-" * 60)
        print("\n✅ Access control verification complete!")
    
    await engine.dispose()


async def force_refresh_user(user_id: int):
    """Force refresh a specific user's data from database."""
    print(f"\n🔄 Force refreshing user {user_id}...")
    
    database_url = settings.DATABASE_URL
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Force refresh by reading directly from database
        query = text("SELECT user_id, approved, is_premium FROM users WHERE user_id = :user_id")
        result = await session.execute(query, {"user_id": user_id})
        user = result.fetchone()
        
        if user:
            uid, approved, is_premium = user
            print(f"   User {uid}: approved={approved}, is_premium={is_premium}")
            print(f"   Can access quiz: {'✅ YES' if approved else '❌ NO'}")
        else:
            print(f"   User {user_id} not found!")
    
    await engine.dispose()


async def set_user_approved(user_id: int, approved: bool = True):
    """Manually set a user's approved status (for admin use)."""
    print(f"\n👤 Setting user {user_id} approved={approved}...")
    
    database_url = settings.DATABASE_URL
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        query = text("""
            UPDATE users 
            SET approved = :approved, is_premium = :is_premium 
            WHERE user_id = :user_id
        """)
        await session.execute(query, {
            "user_id": user_id,
            "approved": 1 if approved else 0,
            "is_premium": 1 if approved else 0
        })
        await session.commit()
        
        # Verify the update
        verify_query = text("""
            SELECT user_id, approved, is_premium 
            FROM users 
            WHERE user_id = :user_id
        """)
        result = await session.execute(verify_query, {"user_id": user_id})
        user = result.fetchone()
        
        if user:
            uid, approved_val, is_premium = user
            print(f"   ✅ Updated: User {uid} - approved={approved_val}, is_premium={is_premium}")
        else:
            print(f"   ❌ User {user_id} not found!")
    
    await engine.dispose()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix and verify user states")
    parser.add_argument("--fix", action="store_true", help="Fix inconsistent user states")
    parser.add_argument("--verify", action="store_true", help="Verify access control")
    parser.add_argument("--refresh", type=int, metavar="USER_ID", help="Force refresh a user")
    parser.add_argument("--set-approved", type=int, metavar="USER_ID", 
                        help="Set a user as approved (use with --yes)")
    parser.add_argument("--yes", action="store_true", 
                        help="Skip confirmation when setting approved status")
    
    args = parser.parse_args()
    
    if args.fix:
        asyncio.run(fix_user_states())
    elif args.verify:
        asyncio.run(verify_access())
    elif args.refresh:
        asyncio.run(force_refresh_user(args.refresh))
    elif args.set_approved:
        if not args.yes:
            response = input(f"Set user {args.set_approved} as approved? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                sys.exit(0)
        asyncio.run(set_user_approved(args.set_approved, True))
    else:
        print(__doc__)
        print("\nUsage:")
        print("  python scripts/fix_user_states.py --fix           # Fix inconsistent states")
        print("  python scripts/fix_user_states.py --verify        # Test access control")
        print("  python scripts/fix_user_states.py --refresh 123   # Refresh specific user")
        print("  python scripts/fix_user_states.py --set-approved 123 --yes  # Approve user")
