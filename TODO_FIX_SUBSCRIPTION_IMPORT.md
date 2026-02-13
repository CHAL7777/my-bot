# Fix Subscription Import Error

## Issue
`ImportError: cannot import name 'Subscription' from 'app.db.models'`

The `Subscription` model was removed from `models.py` and replaced with `is_premium` flag on `User` model.

## Files to Fix

### 1. app/db/__init__.py
- [ ] Remove `Subscription` from imports
- [ ] Remove `Subscription` from `__all__` list

### 2. app/repositories/payment_repo.py
- [ ] Remove `Subscription` from imports
- [ ] Remove or update `_create_subscription` method
- [ ] Update `approve_payment` method (remove subscription creation)
- [ ] Update `get_active_subscription` method to check `User.is_premium`
- [ ] Remove `create_trial_subscription` method
- [ ] Remove `check_subscription_expiry` method
- [ ] Update `get_revenue_stats` method (remove subscription_days query)

### 3. app/repositories/user_repo.py
- [ ] Remove `Subscription` from imports

### 4. app/middlewares/subscription.py
- [ ] Update middleware to check `user.is_premium` instead of looking up subscriptions
- [ ] Update `__call__` method to get user and check `is_premium`
- [ ] Remove unused imports and code related to `Subscription`

## Changes Made

### Change 1: app/db/__init__.py
- Removed `Subscription` from imports and `__all__`

### Change 2: app/repositories/payment_repo.py
- Removed `Subscription` import
- Updated methods to work with lifetime premium model

### Change 3: app/repositories/user_repo.py
- Removed `Subscription` import

### Change 4: app/middlewares/subscription.py
- Updated to check `User.is_premium` instead of subscription lookups

## Testing
After making these changes, run:
```bash
python -m app.main
```

The import error should be resolved.

