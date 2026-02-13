# Quiz & User Statistics Fix Plan

## Issues Identified

### 1. Quiz Statistics Not Working
- `admin_stats_quizzes_callback` in admin_stats.py
- The handler may fail silently or return empty data

### 2. User Statistics Not Working  
- `admin_stats_users_callback` in admin_stats.py
- Uses `get_all_users(limit=500)` which may not return all users

### 3. `/stats` Command Missing days=None
- `show_stats` in main.py doesn't pass `days=None` to `get_user_stats()`
- This causes it to only show stats from the last 24 hours

## Fixes to Implement

### Fix 1: admin_stats.py - Quiz Statistics
- Add error logging
- Handle empty data gracefully
- Pass proper parameters to analytics service

### Fix 2: admin_stats.py - User Statistics  
- Improve user counting logic
- Handle empty data better
- Add better error handling

### Fix 3: main.py - show_stats
- Add `days=None` parameter to `get_user_stats()` call
- This will show all-time stats instead of just today's

## Status
- [ ] Create TODO.md (done)
- [ ] Fix admin_stats.py - quiz statistics handler
- [ ] Fix admin_stats.py - user statistics handler  
- [ ] Fix main.py - show_stats command
- [ ] Test the fixes

