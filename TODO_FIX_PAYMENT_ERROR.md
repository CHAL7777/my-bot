# TODO: Fix KeyError 'has_active_subscription'

## Issue
Error: `KeyError: 'has_active_subscription'` when checking payment status

## Root Cause
- `payment_status_callback` expects `status['has_active_subscription']` and `status['subscription']`
- `PaymentService.get_payment_status()` returns `is_premium` but not these keys

## Plan
1. [ ] Update `get_payment_status()` in `payment_service.py` to add `has_active_subscription` and `subscription` keys
2. [ ] Update `payment_status_callback` in `payment.py` to handle None subscription

## Status
- [ ] Not Started
- [x] In Progress
- [ ] Completed

