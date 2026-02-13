-- Migration: Add Leaderboard and Progress Models
-- Generated from SQLAlchemy models
-- Run this migration to create the new tables

-- ============================================================================
-- Leaderboard Entries Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    period VARCHAR(9) NOT NULL,
    score INTEGER DEFAULT 0,
    accuracy FLOAT DEFAULT 0.0,
    total_quizzes INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    avg_time_per_question FLOAT DEFAULT 0.0,
    rank INTEGER,
    created_at DATETIME,
    updated_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS unique_user_period_leaderboard ON leaderboard_entries (user_id, period);
CREATE INDEX IF NOT EXISTS idx_leaderboard_period_rank ON leaderboard_entries (period, rank);
CREATE INDEX IF NOT EXISTS idx_leaderboard_user_period ON leaderboard_entries (user_id, period);

-- ============================================================================
-- Achievements Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type VARCHAR(8) NOT NULL,
    icon VARCHAR(20),
    requirement JSON,
    points INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME,
    PRIMARY KEY (id)
);

-- ============================================================================
-- User Achievements Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    achievement_id INTEGER NOT NULL,
    unlocked_at DATETIME,
    progress JSON,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY(achievement_id) REFERENCES achievements (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS unique_user_achievement ON user_achievements (user_id, achievement_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements (user_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_achievement ON user_achievements (achievement_id);

-- ============================================================================
-- Daily Goals Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_goals (
    id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    date DATE NOT NULL,
    target_quizzes INTEGER DEFAULT 3,
    completed_quizzes INTEGER DEFAULT 0,
    target_accuracy FLOAT DEFAULT 70.0,
    achieved_accuracy FLOAT DEFAULT 0.0,
    is_completed BOOLEAN DEFAULT 0,
    reward_claimed BOOLEAN DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS unique_user_daily_goal ON daily_goals (user_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_goals_user_date ON daily_goals (user_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_goals_date ON daily_goals (date);

-- ============================================================================
-- System Config Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME,
    updated_at DATETIME,
    PRIMARY KEY (id),
    UNIQUE (key)
);

CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config (key);
CREATE INDEX IF NOT EXISTS idx_system_config_active ON system_config (is_active);

-- ============================================================================
-- AdminLogs Table Update (SKIPPED - already migrated)
-- The admin_logs table already has the new schema with admin_id column
-- This section is intentionally left empty to avoid parse errors
-- ============================================================================

-- Ensure indexes exist on admin_logs (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin ON admin_logs (admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action ON admin_logs (action);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target ON admin_logs (target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created ON admin_logs (created_at);

-- ============================================================================
-- Seed Initial Achievements (Optional)
-- Uses INSERT OR IGNORE to be idempotent
-- ============================================================================

INSERT OR IGNORE INTO achievements (id, name, description, type, icon, requirement, points) VALUES
    (1, 'First Steps', 'Complete your first quiz', 'completion', '🎯', '{"total_quizzes": 1}', 10),
    (2, 'Getting Started', 'Complete 10 quizzes', 'completion', '⭐', '{"total_quizzes": 10}', 20),
    (3, 'Quiz Master', 'Complete 50 quizzes', 'completion', '🏆', '{"total_quizzes": 50}', 50),
    (4, 'On Fire', 'Maintain a 3-day streak', 'streak', '🔥', '{"streak_days": 3}', 30),
    (5, 'Unstoppable', 'Maintain a 7-day streak', 'streak', '💥', '{"streak_days": 7}', 75),
    (6, 'Speed Demon', 'Answer 10 questions in under 5 seconds each', 'speed', '⚡', '{"avg_time": 5, "min_questions": 10}', 40),
    (7, 'Sharp Shooter', 'Achieve 80% accuracy in a session', 'accuracy', '🎯', '{"accuracy": 80}', 35),
    (8, 'Perfectionist', 'Achieve 100% accuracy on 10 questions', 'accuracy', '💯', '{"accuracy": 100, "min_questions": 10}', 100),
    (9, 'High Scorer', 'Score over 100 points in a single session', 'score', '💎', '{"max_score": 100}', 40),
    (10, 'Legend', 'Score over 500 points total', 'score', '👑', '{"total_score": 500}', 150);

-- ============================================================================
-- Seed Initial System Config (Optional)
-- Uses INSERT OR IGNORE to be idempotent
-- ============================================================================

INSERT OR IGNORE INTO system_config (id, key, value, description) VALUES
    (1, 'daily_goal_quizzes', '3', 'Default daily quiz target'),
    (2, 'daily_goal_accuracy', '70.0', 'Default daily accuracy target'),
    (3, 'streak_bonus_points', '5', 'Bonus points per streak day'),
    (4, 'leaderboard_refresh_interval', '3600', 'Leaderboard refresh interval in seconds'),
    (5, 'max_questions_per_session', '25', 'Maximum questions per quiz session'),
    (6, 'question_timeout', '30', 'Default question timeout in seconds');

