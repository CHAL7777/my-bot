# TODO: Fix Subscription Middleware and Inline Quiz Start

## Problem
- Inline callback (`start_quiz`) shows "Access Denied" even for users with approved payments
- `SubscriptionMiddleware` uses async context manager that closes before handler runs
- `inline_start_quiz_callback` doesn't check `has_active_subscription` consistently

## Fix Plan

### 1. Fix SubscriptionMiddleware
**File:** `app/middlewares/subscription.py`
- Remove `async for` pattern that closes session before handler
- Use context manager properly to keep session open until handler completes
- Properly inject `has_active_subscription` into `data` dict

### 2. Add subscription check to inline_start_quiz_callback
**File:** `app/handlers/start.py`
- Add check for `has_active_subscription` before allowing quiz access
- Show appropriate message if user needs to subscribe

### 3. Keep start_quiz_flow check for defense in depth
**File:** `app/handlers/quiz.py`
- Keep existing Payment check as additional safety layer

## Implementation Steps

- [x] Analyze the problem and identify root causes
- [x] Fix SubscriptionMiddleware to properly check subscription
- [x] Add has_active_subscription check to inline_start_quiz_callback
- [x] Add error handling for "message not modified" Telegram errors
- [ ] Test the fix

## Changes Made

### 1. Fixed `app/middlewares/subscription.py`
- Changed from `async for session in get_db()` to `async with session() as db_session`
- The subscription check result is now stored in `data` dict BEFORE the context manager closes
- Added proper logging for debugging

### 2. Fixed `app/handlers/start.py`
- Simplified `inline_start_quiz_callback` to use `has_active_subscription` from middleware
- Removed redundant database query that checked `user.approved` flag
- Now uses the single source of truth for premium access

## Root Cause Analysis

The issue was in `SubscriptionMiddleware`:
```python
async def __call__(self, handler, event, data):
    data['has_active_subscription'] = False  # Default
    
    try:
        async for session in get_db():  # Session closes here!
            # Check subscription...
            data['has_active_subscription'] = access_result['allowed']
    except Exception:
        # Error handling...
    
    # Handler called AFTER session is closed!
    return await handler(event, data)
```

The `async for` context manager closes the session AFTER setting `has_active_subscription`, but the real issue was the inline callback was doing its own DB check on `user.approved` which was out of sync with the payment-based check.

Now both the middleware and the callback use the same `has_active_subscription` value from the middleware.

