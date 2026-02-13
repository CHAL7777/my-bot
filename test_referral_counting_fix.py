"""
Test Script for Referral Counting Fix

This script tests the complete referral flow:
1. Create referrer and referred users
2. Process a referral (pending status)
3. Approve a payment for the referred user
4. Verify referral is completed and referrer's count is incremented

Usage:
    python test_referral_counting_fix.py
"""

import asyncio
import sys
import os

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import random
import string

# Import database and models
from app.db.base import get_db, Base, engine
from app.db.models import User, Referral, Payment
from sqlalchemy import select, update, delete


def generate_test_user_id():
    """Generate a unique test user ID"""
    return int(f"999{random.randint(100000, 999999)}")


def generate_referral_code():
    """Generate a test referral code"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(chars) for _ in range(8))
    return f"REF{code}"


async def create_test_user(session, user_id, username=None, first_name="Test"):
    """Create a test user"""
    # Check if user exists
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update referral code for testing
        existing.referral_code = generate_referral_code()
        await session.commit()
        return existing
    
    user = User(
        user_id=user_id,
        username=username or f"test_{user_id}",
        first_name=first_name,
        referral_code=generate_referral_code(),
        referral_count=0,
        is_premium=False,
        approved=False
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_referral(session, referrer_id, referred_id):
    """Create a pending referral"""
    # Check if referral already exists
    result = await session.execute(
        select(Referral).where(
            (Referral.referrer_id == referrer_id) & 
            (Referral.referred_id == referred_id)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing
    
    referral = Referral(
        referrer_id=referrer_id,
        referred_id=referred_id,
        status='pending'
    )
    session.add(referral)
    await session.commit()
    await session.refresh(referral)
    return referral


async def create_payment(session, user_id, amount=100.0):
    """Create a pending payment for the user"""
    payment = Payment(
        user_id=user_id,
        amount=amount,
        status='pending',
        subscription_days=None  # Lifetime
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_user_referral_count(session, user_id):
    """Get user's referral count"""
    result = await session.execute(
        select(User.referral_count).where(User.user_id == user_id)
    )
    return result.scalar() or 0


async def get_referral_status(session, referrer_id, referred_id):
    """Get referral status"""
    result = await session.execute(
        select(Referral).where(
            (Referral.referrer_id == referrer_id) & 
            (Referral.referred_id == referred_id)
        )
    )
    referral = result.scalar_one_or_none()
    return referral.status if referral else None


async def cleanup_test_data(session, user_ids):
    """Clean up test data"""
    # Delete referrals
    for user_id in user_ids:
        await session.execute(
            delete(Referral).where(
                (Referral.referrer_id == user_id) | 
                (Referral.referred_id == user_id)
            )
        )
    
    # Delete payments
    for user_id in user_ids:
        await session.execute(
            delete(Payment).where(Payment.user_id == user_id)
        )
    
    # Delete users
    for user_id in user_ids:
        await session.execute(
            delete(User).where(User.user_id == user_id)
        )
    
    await session.commit()


async def test_referral_flow():
    """Test the complete referral flow"""
    print("=" * 60)
    print("Referral Counting Fix - Test Script")
    print("=" * 60)
    
    # Test user IDs
    referrer_id = generate_test_user_id()
    referred_id = referrer_id + 1
    
    test_users = [referrer_id, referred_id]
    
    try:
        # Create database tables
        print("\n[1] Setting up database...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("    ✓ Database tables ready")
        
        # Test the flow with a new session
        async for session in get_db():
            print("\n[2] Creating test users...")
            
            # Create referrer
            referrer = await create_test_user(session, referrer_id, "referrer_bot", "ReferrerBot")
            print(f"    ✓ Created referrer: user_id={referrer.user_id}, referral_code={referrer.referral_code}")
            print(f"      Initial referral_count: {referrer.referral_count}")
            
            # Create referred user
            referred = await create_test_user(session, referred_id, "referred_bot", "ReferredBot")
            print(f"    ✓ Created referred user: user_id={referred.user_id}")
            
            # Create pending referral
            print("\n[3] Creating pending referral...")
            referral = await create_referral(session, referrer.user_id, referred.user_id)
            print(f"    ✓ Created referral: id={referral.id}, status={referral.status}")
            
            # Verify initial state
            initial_count = await get_user_referral_count(session, referrer.user_id)
            print(f"\n[4] Initial state:")
            print(f"    Referrer referral_count: {initial_count}")
            print(f"    Referral status: {referral.status}")
            
            # Now test the referral service directly
            print("\n[5] Testing complete_referral_on_payment_approval...")
            
            from app.repositories.referral_repo import ReferralRepository
            from app.services.referral_service import ReferralService
            
            referral_repo = ReferralRepository(session)
            referral_service = ReferralService(referral_repo, None)  # user_repo can be None for this test
            
            result = await referral_service.complete_referral_on_payment_approval(referred.user_id)
            
            print(f"    Result: {result}")
            
            # Verify the referral was completed
            final_status = await get_referral_status(session, referrer.user_id, referred.user_id)
            final_count = await get_user_referral_count(session, referrer.user_id)
            
            print(f"\n[6] Final state:")
            print(f"    Referral status: {final_status}")
            print(f"    Referrer referral_count: {final_count}")
            
            # Check referrer's user record
            await session.refresh(referrer)
            print(f"    Referrer referral_count (from DB): {referrer.referral_count}")
            
            # Verify results
            success = True
            
            if final_status != 'completed':
                print(f"\n❌ FAILED: Referral status should be 'completed', got '{final_status}'")
                success = False
            else:
                print(f"\n✓ Referral status is 'completed'")
            
            if final_count != 1:
                print(f"❌ FAILED: Referrer referral_count should be 1, got {final_count}")
                success = False
            else:
                print(f"✓ Referrer referral_count is 1")
            
            if success:
                print("\n" + "=" * 60)
                print("✅ ALL TESTS PASSED!")
                print("=" * 60)
                print("\nThe referral counting fix is working correctly.")
                print("When a referred user's payment is approved:")
                print("  1. The referral status changes from 'pending' to 'completed'")
                print("  2. The referrer's referral_count is incremented by 1")
            else:
                print("\n" + "=" * 60)
                print("❌ SOME TESTS FAILED!")
                print("=" * 60)
            
            return success
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n[7] Cleaning up test data...")
        try:
            async for session in get_db():
                await cleanup_test_data(session, test_users)
                print("    ✓ Test data cleaned up")
        except Exception as e:
            print(f"    ⚠ Cleanup error (can be ignored): {e}")


async def test_payment_service_integration():
    """Test that PaymentService.approve_payment properly triggers referral completion"""
    print("\n" + "=" * 60)
    print("Payment Service Integration Test")
    print("=" * 60)
    
    referrer_id = generate_test_user_id()
    referred_id = referrer_id + 1
    payment_user_id = referred_id  # Same as referred user
    
    test_users = [referrer_id, referred_id]
    
    try:
        async for session in get_db():
            print("\n[1] Creating test users...")
            
            # Create referrer
            referrer = await create_test_user(session, referrer_id, "paytest_referrer", "PayTestReferrer")
            print(f"    ✓ Created referrer: user_id={referrer.user_id}")
            print(f"      Initial referral_count: {referrer.referral_count}")
            
            # Create referred user who will make payment
            referred = await create_test_user(session, referred_id, "paytest_referred", "PayTestReferred")
            print(f"    ✓ Created referred user: user_id={referred.user_id}")
            
            # Create pending referral
            referral = await create_referral(session, referrer.user_id, referred.user_id)
            print(f"    ✓ Created pending referral: id={referral.id}, status={referral.status}")
            
            # Create pending payment for referred user
            payment = await create_payment(session, referred.user_id, amount=100.0)
            print(f"    ✓ Created pending payment: id={payment.payment_id}")
            
            # Now test PaymentService.approve_payment
            print("\n[2] Testing PaymentService.approve_payment...")
            
            from app.services.payment_service import PaymentService
            from app.repositories.payment_repo import PaymentRepository
            from app.repositories.user_repo import UserRepository
            
            payment_repo = PaymentRepository(session)
            user_repo = UserRepository(session)
            payment_service = PaymentService(payment_repo, user_repo)
            
            # Approve the payment (this should also complete the referral)
            admin_id = 12345  # Test admin ID
            result = await payment_service.approve_payment(payment.payment_id, admin_id)
            
            print(f"\n    Payment approval result:")
            print(f"      success: {result.get('success')}")
            print(f"      referral_completed: {result.get('referral_completed')}")
            print(f"      referrer_id: {result.get('referrer_id')}")
            if result.get('referral_error'):
                print(f"      referral_error: {result.get('referral_error')}")
            
            # Verify results
            print("\n[3] Verifying results...")
            
            # Refresh referral
            await session.refresh(referral)
            print(f"    Referral status: {referral.status}")
            
            # Refresh referrer
            await session.refresh(referrer)
            print(f"    Referrer referral_count: {referrer.referral_count}")
            
            # Check payment status
            await session.refresh(payment)
            print(f"    Payment status: {payment.status}")
            
            success = True
            
            if referral.status != 'completed':
                print(f"\n❌ FAILED: Referral status should be 'completed', got '{referral.status}'")
                success = False
            
            if referrer.referral_count != 1:
                print(f"❌ FAILED: Referrer referral_count should be 1, got {referrer.referral_count}")
                success = False
            
            if payment.status != 'approved':
                print(f"❌ FAILED: Payment status should be 'approved', got '{payment.status}'")
                success = False
            
            if success:
                print("\n" + "=" * 60)
                print("✅ PAYMENT SERVICE INTEGRATION TEST PASSED!")
                print("=" * 60)
                print("\nWhen admin approves a payment:")
                print("  1. Payment status changes to 'approved'")
                print("  2. Referral status changes from 'pending' to 'completed'")
                print("  3. Referrer's referral_count is incremented by 1")
            
            return success
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n[4] Cleaning up test data...")
        try:
            async for session in get_db():
                await cleanup_test_data(session, test_users)
                print("    ✓ Test data cleaned up")
        except Exception as e:
            print(f"    ⚠ Cleanup error (can be ignored): {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print(" REFERRAL COUNTING FIX - VERIFICATION TESTS")
    print("=" * 60)
    
    # Run tests
    test1_passed = await test_referral_flow()
    test2_passed = await test_payment_service_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    print(f" Referral Flow Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f" Payment Integration Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The referral counting fix is working.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

