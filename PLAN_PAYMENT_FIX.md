# Payment System Redesign Plan

## Information Gathered

After analyzing the codebase, the following issues were identified:

### 1. Database Schema Issues
- `Payment` model missing `subscription_days` column (exists in migration SQL but not in model)
- The model needs this column for subscription-based payments

### 2. Code Issues
- `PaymentService._calculate_amount()` defined twice with different signatures
- `PaymentService._get_payment_instructions()` has wrong indentation (inside the method)
- `get_active_subscription()` always returns `None`, breaking subscription checks
- Handler code doesn't safely handle missing columns or attributes
- Payment approval logic may fail if user has no payment record

### 3. Edge Cases Not Handled
- Users with no payment info
- Users with active/inactive subscriptions
- Manual verification (screenshot approval)
- Missing database columns
- Race conditions in payment approval

---

## Plan: Payment System Redesign

### Phase 1: Database Schema Update
1. **Update Payment Model** (`app/db/models.py`):
   - Add `subscription_days` column (Integer, nullable=True for lifetime payments)
   - Add `payment_type` column to distinguish lifetime vs subscription

### Phase 2: Fix PaymentService (`app/services/payment_service.py`)
1. Remove duplicate `_calculate_amount()` methods
2. Fix indentation issue in `_get_payment_instructions()`
3. Add proper error handling for missing attributes
4. Implement safe payment status checks

### Phase 3: Fix PaymentRepository (`app/repositories/payment_repo.py`)
1. Add proper subscription handling (for backward compatibility)
2. Improve idempotency checks
3. Add safe attribute access methods

### Phase 4: Update Handlers (`app/handlers/payment.py` & `admin_payments.py`)
1. Add safe attribute access using `.get()` method
2. Add proper exception handling for missing columns
3. Add user-friendly error messages

### Phase 5: Create Safe Payment Utility (`app/utils/payment_utils.py`)
1. Create a utility module with safe payment check functions
2. Implement helper functions for common payment operations
3. Add inline documentation

### Phase 6: Database Migration
1. Create migration script for missing columns
2. Update existing records

---

## Files to Edit

1. `app/db/models.py` - Add `subscription_days` and `payment_type` columns
2. `app/services/payment_service.py` - Fix method definitions and add safe checks
3. `app/repositories/payment_repo.py` - Add safe subscription handling
4. `app/handlers/payment.py` - Add safe attribute access
5. `app/handlers/admin_payments.py` - Add safe attribute access and error handling
6. `app/utils/__init__.py` - Export new payment utilities

## New Files to Create

1. `app/utils/payment_utils.py` - Safe payment checking utilities

## Followup Steps

1. Run database migration to add missing columns
2. Test payment flow: initiation → screenshot upload → admin approval
3. Verify edge cases: no payment info, already premium, pending payments
4. Run existing tests to ensure no regressions
5. Document the new payment flow

---

## Payment Flow (After Fixes)

```
User initiates payment
    ↓
Check eligibility (can_pay, already premium, has subscription)
    ↓
If eligible: Show payment instructions
    ↓
User uploads screenshot
    ↓
Save payment record with pending status
    ↓
Admin reviews payment (views screenshot inline)
    ↓
Admin approves/rejects with reason
    ↓
If approved: Grant lifetime premium (is_premium = True)
    ↓
Notify user of result
```

---

## Safe Payment Check API

```python
from app.utils.payment_utils import (
    is_user_premium,           # Check if user has lifetime access
    has_active_subscription,   # Check subscription status
    get_safe_payment_status,   # Get payment status with safe access
    can_user_make_payment      # Check if user can initiate payment
)
```

These functions handle:
- Missing columns (returns default values)
- None values (safe attribute access)
- Missing payment records (returns appropriate defaults)
- Race conditions (idempotent operations)

