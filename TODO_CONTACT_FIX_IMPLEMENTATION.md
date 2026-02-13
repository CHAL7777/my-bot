# Contact Fix Implementation Plan

## Problem
Users are always being told to wait 10 minutes even when they haven't sent a contact message before.

## Root Cause
The `RateLimitMiddleware` in `app/middlewares/rate_limit.py` has TWO issues:
1. It blocks `/contact` commands BEFORE the handler is called
2. The in-memory rate limit NEVER resets because `reset_limits()` is never called

This conflicts with the proper database-based rate limiting in `contact_repo.py` which was already working.

## Solution: Option A
Remove contact from middleware rate limiting - the database check in `contact_repo.py` is sufficient and more reliable.

## Files to Modify

### 1. `app/middlewares/rate_limit.py`
- [x] Remove `contact` from the `rate_limits` dictionary
- [x] Remove special handling for `contact` event type in `__call__` method
- [x] Remove custom alert message for contact rate limit

### 2. `app/handlers/start.py`
- [x] Update `contact_new_callback` to show better error message when rate limited
- [x] Ensure database rate limit check works correctly

## Changes Made

### Change 1: app/middlewares/rate_limit.py
```python
# BEFORE:
self.rate_limits = {
    'message': (20, 60),
    'callback': (30, 60),
    'quiz_start': (5, 120),
    'payment': (5, 3600),
    'contact': (1, CONTACT_RATE_LIMIT_MINUTES * 60),  # Remove this
}

# AFTER:
self.rate_limits = {
    'message': (20, 60),
    'callback': (30, 60),
    'quiz_start': (5, 120),
    'payment': (5, 3600),
    # Contact removed - uses database rate limiting instead
}
```

### Change 2: Remove contact special handling
```python
# Remove from __call__:
elif text.startswith('/contact'):
    event_type = 'contact'  # Remove this

# And remove the custom alert:
if event_type == 'contact':
    await event.answer(
        "⏳ You've already submitted a support request recently. "
        f"Please wait {CONTACT_RATE_LIMIT_MINUTES} minutes before sending another.",
        show_alert=True
    )
else:
    await event.answer(
        "⏳ Too many requests. Please wait a moment.",
        show_alert=True
    )

# Replace with just:
await event.answer(
    "⏳ Too many requests. Please wait a moment.",
    show_alert=True
)
```

## Result
After this fix:
- Users can access the contact flow immediately
- Rate limiting is handled by the database check in `contact_repo.py`
- The 10-minute limit will work correctly after sending ONE message
- Users who have never sent a message before won't be blocked

## Testing
- [ ] User who never sent contact message can access `/contact`
- [ ] User can send first message without rate limit error
- [ ] After sending one message, user gets proper 10-minute rate limit
- [ ] After 10 minutes, user can send another message

