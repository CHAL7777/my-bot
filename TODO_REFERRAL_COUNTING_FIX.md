# Referral Counting Fix - TODO

## Problem
The referral system is not counting referrals when:
1. A user pays and gets approved
2. The admin approves the payment

## Root Cause
In `payment_service.py`, the `approve_payment()` method tries to get a session from repositories:
```python
session = getattr(self.payment_repo, 'session', None)
if session is None:
    session = getattr(self.user_repo, 'session', None)
if session:
    # ... referral completion code
```

Since repositories don't expose their sessions as attributes (sessions are created by `get_db()` context manager), `session` is always `None` and the referral completion is **always skipped**.

## Fix Plan

### Step 1: Fix payment_service.py - approve_payment() method
- Create a proper async session using `get_db()` context manager
- Call `referral_service.complete_referral_on_payment_approval()` with the new session
- Log the referral completion result for debugging

### Step 2: Test the fix
- Verify referral is created when new user joins with referral code
- Verify referral is completed when payment is approved
- Verify referrer's referral_count is incremented

## Files to Modify
1. `app/services/payment_service.py` - Fix `approve_payment()` method

## Implementation Details

The fix will:
1. Inside `approve_payment()`, create a new async session using `async for session in get_db()`
2. Create `ReferralRepository` with the new session
3. Create `ReferralService` with the referral_repo and user_repo
4. Call `complete_referral_on_payment_approval(referred_user_id)` to count the referral
5. Log the result for debugging

This ensures referrals are properly counted when payments are approved.

## Progress
- [x] Step 1: Fix payment_service.py approve_payment() method
- [ ] Step 2: Test the referral counting fix

