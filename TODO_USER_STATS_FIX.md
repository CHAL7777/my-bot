# User Stats Fix

## Problem
User stats were not working because the `get_user_stats` method in `attempt_repo.py` was defaulting to only showing stats from the last 24 hours (`days=1`). Users who took quizzes more than a day ago would see 0 stats.

## Solution
Modified `get_user_stats` to accept `days=None` for all-time stats and updated all calls to use `days=None` instead of the default `days=1`.

## Changes Made
- [x] Modified `get_user_stats` method in `app/repositories/attempt_repo.py` to support `days=None` for all-time stats
- [x] Updated "My Profile" stats call in `main.py` to use `days=None`
- [x] Updated `/stats` command in `main.py` to use `days=None`
- [x] Updated user service call in `app/services/user_service.py` to use `days=None`

## Testing
- [ ] Test the `/stats` command to ensure it shows all-time stats
- [ ] Test the "My Profile" section to ensure it shows all-time stats
- [ ] Verify that users with old quiz attempts now see their stats correctly
