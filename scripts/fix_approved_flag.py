#!/usr/bin/env python3
"""
Fix Script: Set approved = 1 for all users with is_premium = 1

This script fixes the critical issue where users have is_premium=1 but approved=0.
Run this after applying the code fixes to clean up any existing inconsistent data.

Usage:
    python scripts/fix_approved_flag.py
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.base import db
from app.config import settings


async def fix_approved_flag():
    """
    Fix all users with is_premium=1 but approved=0.
    
    This is the GOLD STANDARD fix for the approval issue.
    """
    print("🔧 Starting approved flag fix...")
    
    async with db.async_session() as session:
        # First, check how many users need fixing
        result = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE is_premium = 1 AND approved = 0")
        )
        count = result.scalar()
        
        if count == 0:
            print("✅ No users need fixing. All premium users have approved=1.")
            return True
        
        print(f"🚨 Found {count} users with is_premium=1 but approved=0")
        
        # Get the list of affected users
        result = await session.execute(
            text("SELECT user_id, username, is_premium, approved FROM users WHERE is_premium = 1 AND approved = 0")
        )
        users = result.fetchall()
        
        print("\n📋 Affected users:")
        for user in users:
            print(f"   • user_id={user.user_id}, username={user.username}")
        
        # Fix all users
        print("\n🔧 Fixing users...")
        await session.execute(
            text("UPDATE users SET approved = 1 WHERE is_premium = 1 AND approved = 0")
        )
        await session.commit()
        print(f"✅ Fixed {count} users")
        
        # Verify the fix
        result = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE is_premium = 1 AND approved = 0")
        )
        remaining = result.scalar()
        
        if remaining == 0:
            print("✅ Verification passed: No inconsistent users remaining")
            return True
        else:
            print(f"❌ Verification failed: {remaining} users still inconsistent")
            return False


async def verify_approval_status(user_id: int = None):
    """
    Verify the approval status of users.
    
    Args:
        user_id: Optional specific user to check. If None, checks all.
    """
    print("\n🔍 Verifying approval status...")
    
    async with db.async_session() as session:
        if user_id:
            # Check specific user
            result = await session.execute(
                text("SELECT user_id, username, approved, is_premium FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            user = result.fetchone()
            
            if user:
                print(f"\n📋 User {user_id}:")
                print(f"   • username: {user.username}")
                print(f"   • approved: {user.approved}")
                print(f"   • is_premium: {user.is_premium}")
                
                if user.is_premium and not user.approved:
                    print("   ⚠️  INCONSISTENT: is_premium=1 but approved=0!")
                    return False
                elif user.approved:
                    print("   ✅ CONSISTENT: approved=1")
                    return True
            else:
                print(f"❌ User {user_id} not found")
                return False
        else:
            # Check all users
            result = await session.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(approved) as approved_count,
                        SUM(is_premium) as premium_count,
                        SUM(CASE WHEN is_premium = 1 AND approved = 0 THEN 1 ELSE 0 END) as inconsistent_count
                    FROM users
                """)
            )
            stats = result.fetchone()
            
            print(f"\n📊 Statistics:")
            print(f"   • Total users: {stats.total}")
            print(f"   • Approved users: {stats.approved_count}")
            print(f"   • Premium users: {stats.premium_count}")
            print(f"   • Inconsistent (is_premium=1, approved=0): {stats.inconsistent_count}")
            
            if stats.inconsistent_count == 0:
                print("\n✅ All users are consistent!")
                return True
            else:
                print(f"\n🚨 {stats.inconsistent_count} users need fixing!")
                return False


async def main():
    """Main entry point."""
    print("=" * 60)
    print("🔧 User Approval Fix Script")
    print("=" * 60)
    
    # Check if running in demo mode
    demo_mode = "--demo" in sys.argv or "-d" in sys.argv
    
    if demo_mode:
        print("\n📝 Demo mode: Showing what would be fixed without making changes")
        await verify_approval_status()
    else:
        print("\n🚀 Running fix...")
        success = await fix_approved_flag()
        
        if success:
            print("\n🔍 Verifying fix...")
            await verify_approval_status()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

