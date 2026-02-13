# User Stats and Admin List Fix Plan

## Issues Identified

### 1. User Statistics Not Working
- **Problem in `app/repositories/attempt_repo.py`**: The `get_user_stats` method has a logic bug where `date_filter = True` (a boolean) is used in SQL queries instead of a proper filter expression when `days=None`.
- **Problem in `app/handlers/admin_stats.py`**: The `admin_stats_users_callback` loads ALL users into memory and calculates stats in Python, which is inefficient.

### 2. List Admin Not Working
- **Problem**: The `TelegramAdminRepository.list_admins()` queries `TelegramAdmin.is_active == True` but if the TelegramAdmin table is empty or corrupted, it returns no results.
- **Potential issue**: The `get_all_admins_with_details()` method uses `session.get()` which may fail if the referenced User objects don't exist.

## Fixes Applied

### Phase 1: Fix User Statistics (`attempt_repo.py`) ✅
- Fixed `get_user_stats` method to properly handle `days=None`
- Changed `date_filter = True` to use conditional SQL conditions
- Now properly builds conditions list without date filter for all-time stats

### Phase 2: Fix Admin Repository (`admin_repo.py`) ✅
- Added try-except error handling in `get_admin_with_adder_info()`
- Added try-except error handling in `get_all_admins_with_details()`
- Prevents crashes when adder users are deleted

### Phase 3: Fix Admin Stats Handler (`admin_stats.py`) ✅
- Fixed trailing newline issue at end of file

## Files Modified
1. `app/repositories/attempt_repo.py` - Fixed `get_user_stats` method
2. `app/repositories/admin_repo.py` - Added error handling in 2 methods
3. `app/handlers/admin_stats.py` - Fixed file formatting

## Testing
After these fixes, test the following:
- User stats should show all-time stats (not just last 24 hours)
- Admin list should work even if adder users are deleted
- No crashes when accessing admin details

