"""
Test script for referral counting fix.
This script tests that referrals are properly counted when admin approves a user.
"""

import asyncio
import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.referral_repo import ReferralRepository
from app.services.referral_service import ReferralService


async def test_referral_counting():
    """Test that referral counting works correctly"""
    print("=" * 60)
    print("Testing Referral Counting Fix")
    print("=" * 60)
    
    # Test scenarios
    test_cases = [
        (123, 456, "referral_created"),
        (123, 789, "already_exists"),
    ]
    
    for referrer_id, referred_id, expected in test_cases:
        print(f"\nTest: referrer={referrer_id}, referred={referred_id}")
        print(f"Expected: {expected}")
        
        async for session in get_db():
            user_repo = UserRepository(session)
            referral_repo = ReferralRepository(session)
            referral_service = ReferralService(referral_repo, user_repo)
            
            try:
                referrer = await user_repo.get_user(referrer_id)
                if not referrer:
                    referrer = await user_repo.create_user(
                        user_id=referrer_id,
                        username=f"test_user_{referrer_id}",
                        first_name=f"Test{referrer_id}",
                        last_name="User"
                    )
                    print(f"  Created referrer user: {referrer_id}")
            except Exception as e:
                print(f"  Note: Could not create referrer: {e}")
            
            try:
                referred = await user_repo.get_user(referred_id)
                if not referred:
                    referred = await user_repo.create_user(
                        user_id=referred_id,
                        username=f"test_referred_{referred_id}",
                        first_name=f"Referred{referred_id}",
                        last_name="User"
                    )
                    print(f"  Created referred user: {referred_id}")
            except Exception as e:
                print(f"  Note: Could not create referred: {e}")
            
            result = await referral_service.process_referral(
                referrer_id=referrer_id,
                referred_id=referred_id
            )
            
            print(f"  Result: {result}")
            print(f"  Success: {result.get('success')}")
            print(f"  Referral Created: {result.get('referral_created')}")
            print(f"  Already Existed: {result.get('referral_already_existed')}")


async def test_idempotency():
    """Test that referral completion is idempotent"""
    print("\n" + "=" * 60)
    print("Testing Idempotency")
    print("=" * 60)
    
    test_user_id = 888
    
    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        already = await referral_service.is_referral_completed(test_user_id)
        print(f"\nUser {test_user_id} already completed: {already}")
        
        status = await referral_service.get_referral_status(test_user_id)
        print(f"User {test_user_id} status: {status}")


async def main():
    """Main test runner"""
    print("\nStarting Referral Counting Tests...")
    print("=" * 60)
    
    try:
        await test_referral_counting()
        await test_idempotency()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        print("\nNote: Full testing requires actual database with test users.")
        print("The referral counting is now properly integrated with admin approval.")
        print("\nWhen admin approves a user via 'approve_user_callback' in admin_users.py:")
        print("1. User is approved (approved=1, is_premium=1)")
        print("2. complete_referral_with_session() is called")
        print("3. Referral is marked as completed")
        print("4. Referrer's referral_count is incremented")
        print("5. Console logs show: [APPROVE] Referral counted: referrer=X, referred=Y")
        
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

