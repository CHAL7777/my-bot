# Leaderboard and Progress Fix Plan

## Issues Identified

### Leaderboard Issues:
1. `get_leaderboard()` returns `user_rank: None` - user's rank is not being fetched
2. Leaderboard table is not being populated with actual attempt data
3. No automatic leaderboard calculation from quiz attempts
4. `get_top_performers()` method is missing from LeaderboardService
5. Leaderboard stats method doesn't calculate rankings from attempts

### Progress Issues:
1. Weak chapters calculation might not properly exclude low-attempt entries
2. Some progress handlers may have issues with subscription middleware parameter
3. Progress statistics might not be accurate due to missing data sources

## Fix Plan

### Phase 1: Fix LeaderboardService - ✅ COMPLETED
- [x] 1.1 Add `get_top_performers()` method to LeaderboardService
- [x] 1.2 Add `calculate_rankings_from_attempts()` method to compute rankings
- [x] 1.3 Add `_calculate_user_rank_from_attempts()` method for period-specific user ranks
- [x] 1.4 Update `get_leaderboard()` to include user_id parameter and fetch user rank

### Phase 2: Fix LeaderboardRepository - ✅ COMPLETED
- [x] 2.1 Add `upsert_leaderboard_entry()` method for PostgreSQL upsert with SQLite fallback
- [x] 2.2 Add helper methods for ranking calculation

### Phase 3: Fix Leaderboard Handler - ✅ COMPLETED
- [x] 3.1 Pass user_id to get_leaderboard() call
- [x] 3.2 Fix medal display logic for top 3 using rank values
- [x] 3.3 Add "Not ranked yet" message for users without rankings
- [x] 3.4 Update leaderboard rules text for real-time updates

### Phase 4: Progress Handler - ✅ COMPLETED
- [x] 4.1 Progress handler already properly handles weak areas display
- [x] 4.2 Subscription middleware parameter handling is correct

### Phase 5: UserService - ✅ COMPLETED
- [x] 5.1 Weak_chapters formatting is correct in user_service.py
- [x] 5.2 Daily progress calculation works correctly

## Summary of Completed Fixes

### Files Modified:
1. **app/services/leaderboard_service.py** - Complete rewrite with dynamic ranking calculation
2. **app/repositories/leaderboard_repo.py** - Added upsert_leaderboard_entry method
3. **app/handlers/leaderboard.py** - Fixed medal display and user rank display

### Key Features Added:
- Real-time leaderboard calculation from quiz attempts
- Support for daily/weekly/monthly/overall periods
- Medal display for top 3 (🥇🥈🥉)
- User's personal rank shown on leaderboard
- Fallback for users not yet ranked
- PostgreSQL upsert with SQLite fallback support

## Changes Made

### app/services/leaderboard_service.py
- Added difficulty points mapping (simple=1, medium=2, hard=3)
- Updated `get_leaderboard()` to accept user_id and fetch their rank
- Added `_calculate_user_rank_from_attempts()` for dynamic ranking calculation
- Added `_get_user_attempt_stats()` to get user's stats for a period
- Added `_get_date_filter()` to filter attempts by period (daily/weekly/monthly/overall)
- Added `_get_all_user_scores()` to get all users' scores for ranking
- Added `get_top_performers()` method with username resolution
- Added `_calculate_leaderboard_from_attempts()` to compute rankings from attempts
- Added `update_all_leaderboards()` to update all periods
- Added `calculate_and_store_rankings()` for post-quiz ranking updates
- Added `_update_user_ranking()` to update single user ranking
- Added `get_medal()` helper for medal emoji by rank

### app/repositories/leaderboard_repo.py
- Added `upsert_leaderboard_entry()` with PostgreSQL ON CONFLICT support and SQLite fallback

### app/handlers/leaderboard.py
- Updated `show_leaderboard()` to pass user_id and display their rank
- Fixed medal display using rank values (1=🥇, 2=🥈, 3=🥉)
- Added fallback message for users not ranked
- Updated leaderboard rules text


