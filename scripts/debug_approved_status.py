#!/usr/bin/env python3
"""
Debug Script: Check what the access control service actually reads
Run this to verify the approved status being read from DB
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.base import db


async def check_actual_status():
    """Check what the access control service reads from DB"""
    print("🔍 Checking actual approved status from database...")
    
    async with db.async_session() as session:
        # This is what the access control service does
        query = text(
            "SELECT user_id, username, approved, is_premium "
            "FROM users WHERE user_id = :user_id"
        )
        
        # Get all users
        result = await session.execute(text("SELECT user_id, username, approved, is_premium FROM users"))
        users = result.fetchall()
        
        print("\n📋 Current database state:")
        print("-" * 60)
        print(f"{'user_id':<20} {'username':<15} {'approved':<10} {'is_premium':<12}")
        print("-" * 60)
        
        for user in users:
            user_id, username, approved, is_premium = user
            print(f"{user_id:<20} {username or 'N/A':<15} {approved:<10} {is_premium:<12}")
            
            # Check if user can access (this is what the middleware checks)
            if approved:
                print(f"   ✅ Can access quiz (approved={approved})")
            else:
                print(f"   ❌ CANNOT access quiz (approved={approved})")
        
        print("-" * 60)
        
        # Now check using the exact middleware logic
        print("\n🔐 Testing access control logic:")
        print("-" * 60)
        
        for user in users:
            user_id = user[0]
            # This is exactly what can_access_quiz_simple does
            query = text("SELECT approved FROM users WHERE user_id = :user_id")
            result = await session.execute(query, {"user_id": user_id})
            row = result.fetchone()
            
            if row:
                approved = row[0]
                can_access = approved == True or approved == 1
                print(f"User {user_id}: approved={approved} ({type(approved).__name__}), can_access={can_access}")
                
                if not can_access:
                    print(f"   🚨 PROBLEM: User has approved={approved} but middleware says can_access={can_access}")
        
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(check_actual_status())

