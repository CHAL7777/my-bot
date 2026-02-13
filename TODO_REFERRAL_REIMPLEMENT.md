# Referral System Fix - Implementation Plan

## Goal
Re-implement referral system to fix the issues where referrals are not being counted properly.

## Issues Identified
1. **Session Mismatch**: In `payment_service.py`, the `approve_payment()` method creates a new session but passes `self.user_repo` (with a different session) to `ReferralService`, causing database transaction issues.
2. **Duplicate Handler**: There are two `admin_payment_view_callback` functions in `admin_payments.py` which can cause conflicts.
3. **Referral completion** needs better logging and error handling.

## Implementation Steps

### Step 1: Fix `app/services/payment_service.py`
- [x] Fix session mismatch by creating user_repo with the same session
- [x] Add better logging for referral completion
- [x] Make referral completion optional to not block payment approval

### Step 2: Fix `app/handlers/admin_payments.py`
- [ ] Remove duplicate `admin_payment_view_callback` handler
- [ ] Consolidate to single handler with proper screenshot review

### Step 3: Enhance `app/services/referral_service.py`
- [ ] Add better error handling and logging
- [ ] Add idempotency checks for referral completion
- [ ] Add helper method to complete referral with session management

### Step 4: Create test script to verify fixes
- [ ] Create comprehensive test to verify referral flow works

## Files to Modify
1. `app/services/payment_service.py` - Fix session handling
2. `app/handlers/admin_payments.py` - Remove duplicate handlers
3. `app/services/referral_service.py` - Add robust error handling

## Testing
- Run test_referral.py to verify basic functionality
- Run test_referral_fix.py to verify fixes
- Test complete flow: new user joins with referral code → admin approves payment → referral counted

