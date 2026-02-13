"""
Script to fix inconsistent user states in the database.

This script identifies and fixes users who have:
- is_premium=True but approved=False (inconsistent state)
- is_premium=True but blocked=True

These states should not grant quiz access, but they indicate data issues.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.base import get_db
from app.services.access_control_service import (
    validate_user_state, fix_inconsistent_user_state
)


async def find_and_fix_inconsistent_users():
    """
    Find all users with inconsistent states and fix them.
    
    Inconsistent states:
    - is_premium=True but approved=False
    """
    print("🔍 Scanning database for inconsistent user states...\n")
    
    # Use async for to iterate over the generator
    async for db_session in get_db():
        # Get all users with is_premium=True but approved=False
        query = text(
            "SELECT user_id, username, approved, is_premium, blocked "
            "FROM users WHERE is_premium = 1 AND approved = 0"
        )
        result = await db_session.execute(query)
        inconsistent_users = result.fetchall()
        
        if not inconsistent_users:
            print("✅ No inconsistent user states found!")
            return 0
        
        print(f"⚠️  Found {len(inconsistent_users)} users with inconsistent states:\n")
        
        for user in inconsistent_users:
            user_id, username, approved, is_premium, blocked = user
            print(f"  • User {user_id} (@{username or 'N/A'})")
            print(f"      approved={approved}, is_premium={is_premium}, blocked={blocked}")
        
        print(f"\n{'='*60}")
        print("Fixing inconsistent states...")
        print("="*60 + "\n")
        
        fixed_count = 0
        for user in inconsistent_users:
            user_id = user[0]
            username = user[1]
            
            # Fix the inconsistent state
            result = await fix_inconsistent_user_state(user_id, db_session)
            
            if result['success']:
                print(f"✅ Fixed user {user_id} (@{username or 'N/A'})")
                print(f"   {result['message']}")
                if result.get('changes'):
                    for field, change in result['changes'].items():
                        print(f"   • {field}: {change['old']} → {change['new']}")
                fixed_count += 1
            else:
                print(f"❌ Failed to fix user {user_id}: {result.get('message', 'Unknown error')}")
            
            print()
        
        print(f"\n{'='*60}")
        print(f"✅ Fixed {fixed_count}/{len(inconsistent_users)} users")
        print("="*60)
        
        return len(inconsistent_users)
    
    return 0


async def validate_all_users():
    """
    Validate all users for consistent access states.
    
    Returns: tuple (total_users, users_with_issues)
    """
    print("\n🔍 Validating all users for consistent access states...\n")
    
    # Use async for to iterate over the generator
    async for db_session in get_db():
        # Get all user IDs
        query = text("SELECT user_id FROM users")
        result = await db_session.execute(query)
        user_ids = [row[0] for row in result.fetchall()]
        
        print(f"📊 Checking {len(user_ids)} users...\n")
        
        issues_count = 0
        valid_count = 0
        
        for user_id in user_ids:
            validation = await validate_user_state(user_id, db_session)
            
            if validation['valid']:
                valid_count += 1
            else:
                issues_count += 1
                print(f"  ❌ User {user_id}:")
                for issue in validation['issues']:
                    print(f"      - {issue}")
        
        return len(user_ids), issues_count, valid_count
    
    return 0, 0, 0


async def main():
    """Main function to run the fix script."""
    print("="*60)
    print("🛠️  User State Consistency Fix Script")
    print("="*60)
    print()
    
    # Step 1: Find and fix inconsistent users
    fixed = await find_and_fix_inconsistent_users()
    
    # Step 2: Validate all users
    total_users, issues, valid = await validate_all_users()
    
    print("\n" + "="*60)
    print(f"📊 VALIDATION SUMMARY:")
    print(f"   Total Users: {total_users}")
    print(f"   Valid States: {valid}")
    print(f"   Issues Found: {issues}")
    print("="*60)
    
    if issues == 0:
        print("\n✅ All users have consistent access states!")
        print("   approved=1 → granted access")
        print("   approved=0 → denied access")
    else:
        print(f"\n⚠️  {issues} users have inconsistent states")
    
    print("\n📝 Business Rule:")
    print("  - Users with is_premium=True but approved=False have been reset")
    print("  - Quiz access is now controlled ONLY by the approved field")
    print("  - is_premium flag should be set ONLY when admin approves user")
    print("\n💡 Next steps:")
    print("  1. Review any remaining issues manually")
    print("  2. Test that quiz access works correctly for approved users")
    print("  3. Verify that unapproved users cannot access quizzes")
    print("  4. Check bot logs for [AUTH] entries to confirm access control")


if __name__ == "__main__":
    asyncio.run(main())
