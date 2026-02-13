#!/usr/bin/env python3
"""
Test script to debug user saving issues in SQLite database.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.config import settings
from app.db.base import db
from app.db.models import User
from app.repositories.user_repo import UserRepository


async def test_user_creation():
    print("="*50)
    print("TESTING USER CREATION")
    print("="*50)
    
    test_user_id = 999999999
    username = "test_user"
    first_name = "Test"
    last_name = "User"
    
    print(f"\n1. Testing with user_id={test_user_id}")
    
    try:
        async with db.async_session() as session:
            print("  ✓ Got async session")
            user_repo = UserRepository(session)
            print("  ✓ Created UserRepository")
            
            print(f"\n2. Creating user...")
            user = await user_repo.create_user(
                user_id=test_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            print(f"  ✓ User created: {user}")
            
            print(f"\n3. Verifying user exists...")
            retrieved_user = await user_repo.get_user(test_user_id)
            if retrieved_user:
                print(f"  ✓ User retrieved: {retrieved_user}")
                print(f"    - user_id: {retrieved_user.user_id}")
                print(f"    - username: {retrieved_user.username}")
                print(f"    - first_name: {retrieved_user.first_name}")
                print(f"    - approved: {retrieved_user.approved}")
                print(f"    - is_premium: {retrieved_user.is_premium}")
            else:
                print("  ✗ User NOT found after creation!")
                return False
                
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n4. Checking with raw SQL...")
    try:
        async with db.async_session() as session:
            result = await session.execute(
                text("SELECT user_id, username, first_name, approved, is_premium FROM users WHERE user_id = :user_id"),
                {"user_id": test_user_id}
            )
            row = result.fetchone()
            if row:
                print(f"  ✓ Raw SQL result: {row}")
            else:
                print("  ✗ User NOT found in raw SQL query!")
                return False
    except Exception as e:
        print(f"  ✗ Raw SQL error: {e}")
    
    print(f"\n5. Cleaning up test user...")
    try:
        async with db.async_session() as session:
            await session.execute(
                text("DELETE FROM users WHERE user_id = :user_id"),
                {"user_id": test_user_id}
            )
            await session.commit()
            print(f"  ✓ Test user deleted")
    except Exception as e:
        print(f"  ✗ Cleanup error: {e}")
    
    return True


async def test_existing_users():
    print("\n" + "="*50)
    print("CHECKING EXISTING USERS")
    print("="*50)
    
    try:
        async with db.async_session() as session:
            result = await session.execute(text("SELECT user_id, username, first_name, approved, is_premium FROM users"))
            users = result.fetchall()
            
            print(f"\n  Found {len(users)} users:")
            for user in users:
                print(f"    - ID: {user[0]}, Username: {user[1]}, Name: {user[2]}, Approved: {user[3]}, Premium: {user[4]}")
                
            return len(users) > 0
    except Exception as e:
        print(f"  ✗ Error fetching users: {e}")
        return False


async def check_database_path():
    print("\n" + "="*50)
    print("CHECKING DATABASE PATH")
    print("="*50)
    
    db_path = settings.SQLITE_DB_PATH
    print(f"  Database URL: {settings.DATABASE_URL}")
    print(f"  Database path: {db_path}")
    print(f"  File exists: {Path(db_path).exists()}")
    
    if Path(db_path).exists():
        print(f"  File size: {Path(db_path).stat().st_size:,} bytes")
    
    return Path(db_path).exists()


async def main():
    print("Starting database test...\n")
    
    if not await check_database_path():
        print("✗ Database file not found!")
        return
    
    await test_existing_users()
    success = await test_user_creation()
    
    print("\n" + "="*50)
    if success:
        print("TEST PASSED")
    else:
        print("TEST FAILED")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())

