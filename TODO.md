# Payment Notification Fix

## Issue
- Log message: "Failed to notify user: 'subscription_days'"
- Error occurs when trying to access 'subscription_days' from result dictionary in notification code
- KeyError because 'subscription_days' key was missing from the result dictionary returned by `approve_payment`

## Root Cause
- In `payment_service.py`, the `approve_payment` method initializes result dictionary but doesn't set 'subscription_days' and 'amount' keys until after the transaction
- Notification code in `admin_payments.py` tries to access these keys immediately after calling `approve_payment`

## Fix Applied
- Added `result['subscription_days'] = getattr(payment, 'subscription_days', None)` and `result['amount'] = getattr(payment, 'amount', 0)` right after setting `result['user_id']`
- Used `getattr` for safe attribute access in case the payment object doesn't have these attributes

## Testing
- [x] Test payment approval flow to ensure notification works correctly
- [x] Verify that 'subscription_days' and 'amount' are properly included in notifications
- [x] Check that both lifetime (None) and subscription-based payments work

## Status
✅ **FIXED** - Payment notification issue resolved by adding missing keys to result dictionary

## Files Modified
- `app/services/payment_service.py` - Added missing keys to result dictionary
