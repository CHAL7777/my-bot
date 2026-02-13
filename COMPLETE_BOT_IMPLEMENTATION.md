# Complete Telegram Quiz Bot Implementation Plan

## Overview
This document outlines the comprehensive implementation plan for a feature-rich Telegram Quiz Bot.

## Priority Order (Based on User Feedback)

### Phase 1: Core Infrastructure (Foundation)
1. Database schema additions
2. New repositories
3. New services

### Phase 2: Progress & Analytics
1. Progress tracking handler
2. Weak areas analysis
3. Statistics dashboard

### Phase 3: Leaderboard System
1. Leaderboard handler
2. Rankings by different criteria
3. Achievement system

### Phase 4: Admin Panel
1. Admin handler with sub-menus
2. User management
3. Question management
4. Analytics dashboard

### Phase 5: Gamification
1. Daily goals
2. Challenges
3. Achievements & badges
4. Comparative analytics

---

## Phase 1: Database Schema Additions

### New Tables Required:

```sql
-- leaderboard_entries
CREATE TABLE leaderboard_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    quiz_session_id TEXT,
    score INTEGER DEFAULT 0,
    accuracy REAL DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    time_spent INTEGER DEFAULT 0,
    period_type TEXT DEFAULT 'all_time',  -- daily, weekly, monthly, all_time
    period_value TEXT,  -- date for daily, week_id for weekly, etc.
    subject_id INTEGER,
    chapter_id INTEGER,
    difficulty TEXT DEFAULT 'simple',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- achievements
CREATE TABLE achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    category TEXT,  -- streak, score, accuracy, speed, completion
    requirement TEXT,  -- JSON condition
    points INTEGER DEFAULT 0,
    rarity TEXT DEFAULT 'common',  -- common, rare, epic, legendary
    is_active INTEGER DEFAULT 1
);

-- user_achievements
CREATE TABLE user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress INTEGER DEFAULT 100,  -- % completion if not earned
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id)
);

-- daily_goals
CREATE TABLE daily_goals (
    goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    target_quizzes INTEGER DEFAULT 5,
    target_score INTEGER DEFAULT 100,
    target_accuracy REAL DEFAULT 70,
    quizzes_completed INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    average_accuracy REAL DEFAULT 0,
    is_completed INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, date)
);

-- challenges
CREATE TABLE challenges (
    challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT,  -- speed, accuracy, streak, score, subject_mastery
    target_value INTEGER NOT NULL,
    target_metric TEXT,  -- questions, accuracy, days, points
    subject_id INTEGER,
    difficulty TEXT,
    start_date DATE,
    end_date DATE,
    reward_points INTEGER DEFAULT 0,
    reward_badge_code TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

-- user_challenges
CREATE TABLE user_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    progress INTEGER DEFAULT 0,
    is_completed INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(challenge_id)
);

-- analytics
CREATE TABLE analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    metric_type TEXT NOT NULL,  -- daily_active_users, quizzes_completed, etc.
    value REAL NOT NULL,
    subject_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- admin_actions
CREATE TABLE admin_actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    target_user_id INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(user_id)
);

-- system_config
CREATE TABLE system_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 2: New Repositories

### 2.1 leaderboard_repo.py
```python
class LeaderboardRepository:
    async def update_entry(user_id, quiz_session_id, score, accuracy, ...)
    async def get_global_rankings(limit=100, offset=0)
    async def get_weekly_rankings(limit=100, offset=0)
    async def get_subject_rankings(subject_id, limit=100)
    async def get_chapter_rankings(chapter_id, limit=100)
    async def get_user_rank(user_id, period='all_time')
    async def get_top_performers(limit=10)
    async def get_improvement_rankings()  # Most improved this week
```

### 2.2 achievement_repo.py
```python
class AchievementRepository:
    async def get_all_achievements()
    async def get_user_achievements(user_id)
    async def check_and_award_achievements(user_id, quiz_result)
    async def get_achievement_progress(user_id, achievement_code)
    async def get_recent_achievements(limit=10)
```

### 2.3 analytics_repo.py
```python
class AnalyticsRepository:
    async def record_metric(date, metric_type, value, subject_id=None)
    async def get_daily_stats(date)
    async def get_weekly_stats(week_start)
    async def get_subject_popularity()
    async def get_difficulty_distribution()
    async def get_average_completion_rate()
```

---

## Phase 3: New Services

### 3.1 progress_service.py
```python
class ProgressService:
    async def analyze_user_progress(user_id, period='30d')
    async def identify_weak_areas(user_id)
    async def generate_recommendations(user_id)
    async def get_accuracy_trend(user_id, subject_id=None)
    async def get_speed_analysis(user_id)
    async def get_improvement_metrics(user_id)
    async def calculate_strength_score(user_id)
```

### 3.2 leaderboard_service.py
```python
class LeaderboardService:
    async def refresh_daily_leaderboard()
    async def refresh_weekly_leaderboard()
    async def calculate_ranks(period='all_time')
    async def get_leaderboard(page=1, per_page=20, filters={})
    async def award_badges_to_top_performers()
```

### 3.3 achievement_service.py
```python
class AchievementService:
    async def initialize_achievements()
    async def check_achievements(user_id, event_type, data)
    async def award_achievement(user_id, achievement_code)
    async def get_achievement_stats(user_id)
    async def get_next_achievements(user_id)
```

---

## Phase 4: Handlers

### 4.1 progress.py (NEW)
```python
@router.message(Command("progress"))
async def command_progress(message: Message, state: FSMContext)

@router.callback_query(F.data == "progress_overview")
async def show_overview(callback: CallbackQuery)

@router.callback_query(F.data == "progress_weak")
async def show_weak_areas(callback: CallbackQuery)

@router.callback_query(F.data == "progress_trends")
async def show_trends(callback: CallbackQuery)

@router.callback_query(F.data == "progress_recommendations")
async def show_recommendations(callback: CallbackQuery)
```

### 4.2 leaderboard.py (NEW - Comprehensive)
```python
@router.message(Command("leaderboard"))
async def command_leaderboard(message: Message)

@router.callback_query(F.data == "leaderboard_daily")
async def show_daily_leaderboard(callback: CallbackQuery)

@router.callback_query(F.data == "leaderboard_weekly")
async def show_weekly_leaderboard(callback: CallbackQuery)

@router.callback_query(F.data == "leaderboard_monthly")
async def show_monthly_leaderboard(callback: CallbackQuery)

@router.callback_query(F.data == "leaderboard_all")
async def show_all_time_leaderboard(callback: CallbackQuery)

@router.callback_query(F.data.startswith("leaderboard_subject_"))
async def show_subject_leaderboard(callback: CallbackQuery)

@router.callback_query(F.data == "leaderboard_my_rank")
async def show_my_rank(callback: CallbackQuery)
```

### 4.3 achievements.py (NEW)
```python
@router.message(Command("achievements"))
async def command_achievements(message: Message)

@router.callback_query(F.data == "achievements_overview")
async def show_achievements_overview(callback: CallbackQuery)

@router.callback_query(F.data == "achievements_earned")
async def show_earned_achievements(callback: CallbackQuery)

@router.callback_query(F.data == "achievements_available")
async def show_available_achievements(callback: CallbackQuery)
```

### 4.4 admin_comprehensive.py (NEW - Full Admin Panel)
```python
@router.message(Command("admin"))
async def command_admin(message: Message, is_admin: bool)

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery)

@router.callback_query(F.data == "admin_questions")
async def admin_questions(callback: CallbackQuery)

@router.callback_query(F.data == "admin_analytics")
async def admin_analytics(callback: CallbackQuery)

@router.callback_query(F.data == "admin_config")
async def admin_config(callback: CallbackQuery)

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery)

# User Management Sub-handlers
@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_detail(callback: CallbackQuery)

@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_user(callback: CallbackQuery)

@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban_user(callback: CallbackQuery)

# Question Management Sub-handlers
@router.callback_query(F.data == "admin_add_question")
async def admin_add_question(callback: CallbackQuery)

@router.callback_query(F.data.startswith("admin_edit_question_"))
async def admin_edit_question(callback: CallbackQuery)

@router.callback_query(F.data.startswith("admin_delete_question_"))
async def admin_delete_question(callback: CallbackQuery)

@router.callback_query(F.data == "admin_import_questions")
async def admin_import_questions(callback: CallbackQuery)

# Analytics Sub-handlers
@router.callback_query(F.data == "admin_stats_overview")
async def admin_stats_overview(callback: CallbackQuery)

@router.callback_query(F.data == "admin_user_analytics")
async def admin_user_analytics(callback: CallbackQuery)

@router.callback_query(F.data == "admin_quiz_analytics")
async def admin_quiz_analytics(callback: CallbackQuery)
```

---

## Phase 5: Keyboards

### 5.1 progress_keyboard.py (NEW)
```python
class ProgressKeyboard:
    @staticmethod
    def get_progress_menu() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_weak_areas_keyboard(weak_areas: List[dict]) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_recommendations_keyboard(recommendations: List[dict]) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_trends_keyboard() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_subject_breakdown_keyboard(subjects: List[dict]) -> InlineKeyboardMarkup
```

### 5.2 leaderboard_keyboard.py (NEW)
```python
class LeaderboardKeyboard:
    @staticmethod
    def get_leaderboard_menu() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_leaderboard_filters() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_leaderboard_table(
        rankings: List[dict], 
        page: int, 
        total_pages: int,
        user_id: int
    ) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_my_rank_keyboard(rank_info: dict) -> InlineKeyboardMarkup
```

### 5.3 achievement_keyboard.py (NEW)
```python
class AchievementKeyboard:
    @staticmethod
    def get_achievement_menu() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_achievement_grid(
        achievements: List[dict], 
        user_id: int
    ) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_achievement_detail(achievement: dict) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_badges_display(user_badges: List[dict]) -> InlineKeyboardMarkup
```

### 5.4 admin_keyboard.py (NEW - Comprehensive)
```python
class AdminKeyboard:
    @staticmethod
    def get_admin_menu() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_user_management_keyboard() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_user_list_keyboard(
        users: List[dict], 
        page: int, 
        total_pages: int
    ) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_user_detail_keyboard(user: dict) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_question_management_keyboard() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_question_list_keyboard(
        questions: List[dict], 
        page: int
    ) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_analytics_dashboard_keyboard() -> InlineKeyboardMarkup
    
    @staticmethod
    def get_config_keyboard(config: dict) -> InlineKeyboardMarkup
    
    @staticmethod
    def get_broadcast_keyboard() -> InlineKeyboardMarkup
```

---

## Phase 6: FSM States for Admin

```python
class AdminStates(StatesGroup):
    """Admin panel FSM states"""
    main_menu = State()
    
    # User management
    user_list = State()
    user_detail = State()
    user_search = State()
    confirm_ban = State()
    confirm_unban = State()
    
    # Question management
    question_list = State()
    add_question = State()
    edit_question = State()
    import_questions = State()
    confirm_delete_question = State()
    
    # Analytics
    analytics_overview = State()
    analytics_users = State()
    analytics_quizzes = State()
    analytics_export = State()
    
    # Configuration
    config_edit = State()
    backup_confirm = State()
    
    # Broadcast
    broadcast_message = State()
    broadcast_confirm = State()
```

---

## Implementation Steps

### Step 1: Create Database Migrations
- Write SQL migration script for new tables
- Test migration on development database
- Create rollback script

### Step 2: Implement Repositories
- leaderboard_repo.py
- achievement_repo.py
- analytics_repo.py

### Step 3: Implement Services
- progress_service.py
- leaderboard_service.py
- achievement_service.py

### Step 4: Implement Keyboards
- progress_keyboard.py
- leaderboard_keyboard.py
- achievement_keyboard.py
- admin_keyboard.py (comprehensive)

### Step 5: Implement Handlers
- progress.py
- leaderboard.py
- achievements.py
- admin_comprehensive.py

### Step 6: Register in Bot
- Update __init__.py
- Update bot.py

### Step 7: Testing
- Test each feature
- Test edge cases
- Test admin flows

---

## Estimated Files to Create/Modify

### New Files (12):
1. `app/repositories/leaderboard_repo.py`
2. `app/repositories/achievement_repo.py`
3. `app/repositories/analytics_repo.py`
4. `app/services/progress_service.py`
5. `app/services/leaderboard_service.py`
6. `app/services/achievement_service.py`
7. `app/keyboards/progress_keyboard.py`
8. `app/keyboards/leaderboard_keyboard.py`
9. `app/keyboards/achievement_keyboard.py`
10. `app/keyboards/admin_keyboard.py`
11. `app/handlers/progress.py`
12. `app/handlers/leaderboard.py`
13. `app/handlers/achievements.py`
14. `app/handlers/admin_comprehensive.py`

### Modified Files (3):
1. `app/handlers/__init__.py`
2. `app/bot.py`
3. `data/schema.sql`

### New Database Migration (1):
1. `scripts/comprehensive_features_migration.sql`

---

## Next Steps

Do you want me to proceed with implementing this plan? I recommend starting with:

1. **Database migrations** - Foundation
2. **Progress service & handler** - Core learning value
3. **Leaderboard service & handler** - Motivational feature
4. **Admin panel** - Critical for management

Let me know which phase you'd like to start with, or if you want me to implement the entire plan!
