# Leaderboard Fix Plan

## Problem
The daily leaderboard shows "Total participants: 0" because the `Leaderboard` table is empty. The system needs to calculate rankings directly from `QuizAttempt` data in real-time.

## Root Cause
- `LeaderboardRepository.get_leaderboard()` queries the empty `Leaderboard` table
- There's no mechanism to populate the Leaderboard table with real data
- The scoring system (Simple=1, Medium=2, Hard=3 points) is not being applied

## Solution
Calculate leaderboard rankings in real-time from `QuizAttempt` data.

## Tasks Completed

### 1. Updated LeaderboardRepository (`app/repositories/leaderboard_repo.py`)
- [x] Added `get_leaderboard_realtime()` method with period-based filtering
- [x] Added `get_user_rank_realtime()` method
- [x] Added `get_total_participants()` method
- [x] Added `_get_period_start()` helper for date filtering by period
- [x] Updated `get_leaderboard()` to use real-time calculation
- [x] Updated `get_user_rank()` to use real-time calculation
- [x] Updated `get_leaderboard_stats()` to use real-time data

### 2. Updated LeaderboardService (`app/services/leaderboard_service.py`)
- [x] Modified `get_leaderboard()` to use real-time calculation with user_id support
- [x] Updated `get_user_leaderboard_summary()` with best_rank tracking
- [x] Simplified `update_all_leaderboards()` (caching now optional)

### 3. Updated Leaderboard Handler (`app/handlers/leaderboard.py`)
- [x] Pass user_id to `get_leaderboard()` for personal rank display
- [x] Fixed medals display (🥇🥈🥉)
- [x] Updated `top_performers_callback()` to use real-time leaderboard
- [x] Updated rules text to reflect real-time updates

### 4. Updated Referral System
- [x] Added `REFERRAL_REWARD_PER_STUDENT` config option (default: 20 Birr)
- [x] Updated referral message to show "Earn 20 Birr per Student"
- [x] Added total earnings calculation in referral stats
- [x] Updated share message to include earnings info

## How It Works Now

### Leaderboard
1. **Daily Leaderboard**: Shows users who attempted ≥5 questions TODAY
2. **Weekly Leaderboard**: Shows users who attempted ≥5 questions THIS WEEK
3. **Monthly Leaderboard**: Shows users who attempted ≥5 questions THIS MONTH
4. **All-Time Leaderboard**: Shows ALL qualifying users (no date filter)

**Scoring System Applied:**
- Simple difficulty: 1 point per correct answer
- Medium difficulty: 2 points per correct answer
- Hard difficulty: 3 points per correct answer

**Qualification:**
- Minimum 5 questions required to appear on leaderboard

### Referral System
- Users earn 20 Birr 神の愛 per approved student referral
- Earnings are added after referred user gets approved
- Total earnings displayed in referral stats
- Share messages include earning information

## Configuration
To change the referral reward per student, set in environment:
```
REFERRAL_REWARD_PER_STUDENT=20
```

