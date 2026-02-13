# Quiz Statistics Implementation Plan

## Overview
Implement comprehensive quiz statistics feature to replace "Coming soon" placeholders with real data.

## Tasks

### Phase 1: Repository Layer ✅ COMPLETED
- [x] 1.1 Add `get_total_attempts()` method to attempt_repo.py
- [x] 1.2 Add `get_average_accuracy()` method to attempt_repo.py
- [x] 1.3 Add `get_average_time()` method to attempt_repo.py
- [x] 1.4 Add `get_attempts_by_hour()` method to attempt_repo.py
- [x] 1.5 Add `get_quiz_sessions_count()` method to attempt_repo.py
- [x] 1.6 Add `get_attempts_by_period()` method for daily/weekly/monthly stats

### Phase 2: Analytics Service Layer ✅ COMPLETED
- [x] 2.1 Add `get_quiz_statistics()` method to analytics_service.py
- [x] 2.2 Add `get_popular_times()` method for morning/afternoon/evening breakdown
- [x] 2.3 Add `get_daily_quiz_stats()` for daily trend data
- [x] 2.4 Add `_calculate_quiz_trends()` for trend analysis

### Phase 3: Handler Layer ✅ COMPLETED
- [x] 3.1 Update `admin_stats_quizzes_callback()` to use real data
- [x] 3.2 Add enhanced quiz stats with trend information
- [x] 3.3 Add drill-down options (peak hour display)

### Phase 4: Testing
- [ ] 4.1 Test with existing database data
- [ ] 4.2 Verify edge cases (no data, single attempt, etc.)
- [ ] 4.3 Test performance with large datasets

## Files Modified
1. `app/repositories/attempt_repo.py` - Added aggregate statistics methods
2. `app/services/analytics_service.py` - Added quiz statistics methods
3. `app/handlers/admin_stats.py` - Updated handler to use real data

## Expected Output
After implementation, the admin quiz statistics shows:
- Total Quiz Attempts: X (real number)
- Correct Answers: X (with accuracy percentage)
- Avg Time: X.X seconds
- Quiz Sessions: X
- Active Users (30d): X
- Today's Attempts and Accuracy
- Popular Times (Morning/Afternoon/Evening with counts and percentages)
- Trend comparison (up/down/stable)
- Peak Hour

