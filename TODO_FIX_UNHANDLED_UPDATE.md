# TODO: Fix Unhandled Update - Datetime Comparison Issue

## Error
```
2026-02-05 04:06:20,476 - app.webhook_main - ERROR - Failed to process update 702096633: can't compare offset-naive and offset-aware datetimes
```

## Root Cause
The error occurs when comparing `datetime.now()` (naive datetime) with database timestamps that are timezone-aware (from PostgreSQL). The comparison fails with "can't compare offset-naive and offset-aware datetimes".

## Files Fixed

### 1. `app/scheduler/reminders.py`
- Added helper function `_make_naive_utc()` to convert timezone-aware datetimes to naive
- Changed `datetime.now()` to `datetime.utcnow()` for consistency
- Updated `send_daily_reminders()` to handle timezone-aware datetimes from database
- Updated `send_subscription_reminders()` to use `datetime.utcnow()`

### 2. `app/middlewares/rate_limit.py`
- Added `timezone` import for future datetime handling

## Implementation Details

### New Helper Function
```python
def _make_naive_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to naive (no timezone info).
    
    This handles both timezone-aware and naive datetimes from the database.
    PostgreSQL timestamps are often timezone-aware, while datetime.utcnow() is naive.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC then remove timezone info
        return dt.replace(tzinfo=None)
    return dt
```

### Fixed Comparison Pattern
Before:
```python
cutoff_date = datetime.now() - timedelta(days=3)
if not attempts or attempts[0].created_at < cutoff_date:
```

After:
```python
cutoff_date = datetime.utcnow() - timedelta(days=3)
last_attempt_time = None
if attempts and attempts[0].created_at:
    last_attempt_time = _make_naive_utc(attempts[0].created_at)

if not attempts or (last_attempt_time and last_attempt_time < cutoff_date):
```

## Remaining Work
The following files also use `datetime.now()` but are SQLAlchemy server-side comparisons that should work fine:
- `app/repositories/attempt_repo.py` - Uses in SQL WHERE clauses (handled by SQLAlchemy)
- `app/repositories/user_repo.py` - Uses in SQL WHERE clauses
- `app/repositories/leaderboard_repo.py` - Uses in SQL WHERE clauses
- `app/services/leaderboard_service.py` - Uses in SQL WHERE clauses
- `app/services/analytics_service.py` - Uses in SQL WHERE clauses

These are passed directly to SQLAlchemy which handles them on the server side.

## Testing
After applying the fix, verify:
1. Webhook updates process without datetime errors
2. Daily reminders send correctly
3. Subscription reminders work as expected

