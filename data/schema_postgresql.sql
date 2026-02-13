-- PostgreSQL Schema for Telegram Quiz Bot
-- Compatible with Supabase, Neon, Railway, Koyeb, and all PostgreSQL 14+ providers
-- 
-- IMPORTANT: This schema uses IF NOT EXISTS checks which are compatible with all providers.
-- No DO $$ blocks that might fail on some platforms.
--
-- Run this on your PostgreSQL database:
--   psql -h host -p 5432 -U user -d dbname -f schema_postgresql.sql

-- ============================================================================
-- ENUM TYPES - Created with conditional checks (Supabase compatible)
-- ============================================================================

-- User roles
CREATE TYPE user_role AS ENUM ('student', 'admin');
COMMENT ON TYPE user_role IS 'User permission levels in the system';

-- Question difficulty levels
CREATE TYPE question_difficulty AS ENUM ('simple', 'medium', 'hard');
COMMENT ON TYPE question_difficulty IS 'Difficulty levels for quiz questions';

-- Multiple choice options for correct answers
CREATE TYPE correct_option AS ENUM ('A', 'B', 'C', 'D');
COMMENT ON TYPE correct_option IS 'Valid options for correct answers';

-- Multiple choice options for user selections
CREATE TYPE selected_option AS ENUM ('A', 'B', 'C', 'D');
COMMENT ON TYPE selected_option IS 'Options that users can select';

-- Payment processing statuses
CREATE TYPE payment_status AS ENUM ('pending', 'approved', 'rejected');
COMMENT ON TYPE payment_status IS 'Status of payment transactions';

-- Leaderboard time periods
CREATE TYPE leaderboard_period AS ENUM ('daily', 'weekly', 'monthly', 'overall');
COMMENT ON TYPE leaderboard_period IS 'Time periods for leaderboard rankings';

-- Progress tracking difficulty levels
CREATE TYPE progress_difficulty AS ENUM ('simple', 'medium', 'hard');
COMMENT ON TYPE progress_difficulty IS 'Difficulty levels for user progress tracking';

-- Admin panel user roles
CREATE TYPE admin_role AS ENUM ('superadmin', 'moderator');
COMMENT ON TYPE admin_role IS 'Admin panel user permission levels';

-- Contact/support ticket categories
CREATE TYPE contact_category AS ENUM ('payment', 'quiz_error', 'access', 'general', 'feedback');
COMMENT ON TYPE contact_category IS 'Categories for user support tickets';

-- Contact ticket statuses
CREATE TYPE contact_status AS ENUM ('open', 'replied', 'closed');
COMMENT ON TYPE contact_status IS 'Status of support tickets';

-- Referral status tracking
CREATE TYPE referral_status AS ENUM ('pending', 'completed', 'cancelled');
COMMENT ON TYPE referral_status IS 'Status of referral relationships';

-- Telegram bot admin roles
CREATE TYPE telegram_admin_role AS ENUM ('superadmin', 'admin');
COMMENT ON TYPE telegram_admin_role IS 'Telegram bot administrator roles';

-- Chapter limit difficulty types
CREATE TYPE chapter_limit_difficulty AS ENUM ('simple', 'medium', 'hard');
COMMENT ON TYPE chapter_limit_difficulty IS 'Difficulty types for chapter daily limits';

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Users: Main table for storing Telegram user information
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    role user_role DEFAULT 'student',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    blocked BOOLEAN DEFAULT FALSE,
    approved BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    referral_code VARCHAR(20) UNIQUE,
    referred_by BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    referral_count INTEGER DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE users IS 'Main user table storing all Telegram bot users with their profiles and status';
COMMENT ON COLUMN users.user_id IS 'Telegram user ID (primary key)';
COMMENT ON COLUMN users.referral_code IS 'Unique code for referral program';
COMMENT ON COLUMN users.referred_by IS 'User who referred this user (self-referencing foreign key)';

-- Subjects: Categories for quiz questions
CREATE TABLE IF NOT EXISTS subjects (
    subject_id SERIAL PRIMARY KEY,
    subject_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE subjects IS 'Quiz subjects/topics available for users to study';
COMMENT ON COLUMN subjects.subject_name IS 'Unique name of the subject (e.g., Mathematics, Physics)';

-- Chapters: Subdivisions within subjects
CREATE TABLE IF NOT EXISTS chapters (
    chapter_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_name VARCHAR(100) NOT NULL,
    chapter_order INTEGER DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subject_id, chapter_name)
);
COMMENT ON TABLE chapters IS 'Chapters within subjects for organizing questions hierarchically';
COMMENT ON COLUMN chapters.chapter_order IS 'Order of display for chapters within a subject';

-- Questions: Core quiz content
CREATE TABLE IF NOT EXISTS questions (
    question_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    difficulty question_difficulty NOT NULL,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option correct_option NOT NULL,
    explanation TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE questions IS 'Quiz questions with multiple choice options and explanations';
COMMENT ON COLUMN questions.explanation IS 'Detailed explanation shown after answering';

-- User Progress: Tracks user performance and learning
CREATE TABLE IF NOT EXISTS user_progress (
    progress_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    difficulty progress_difficulty NOT NULL,
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    total_time_spent INTEGER DEFAULT 0,
    last_attempt TIMESTAMP WITH TIME ZONE,
    accuracy FLOAT DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subject_id, chapter_id, difficulty)
);
COMMENT ON TABLE user_progress IS 'Tracks user performance per subject, chapter, and difficulty level';
COMMENT ON COLUMN user_progress.accuracy IS 'Percentage of correct answers (0-100)';

-- Quiz Attempts: Records of individual question attempts
CREATE TABLE IF NOT EXISTS quiz_attempts (
    attempt_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    selected_option selected_option,
    is_correct BOOLEAN,
    time_taken INTEGER DEFAULT 0,
    quiz_session_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE quiz_attempts IS 'Individual quiz attempt records for analytics and review';
COMMENT ON COLUMN quiz_attempts.time_taken IS 'Time taken to answer in seconds';

-- Payments: Subscription and payment tracking
CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    screenshot_file_id VARCHAR(255),
    screenshot_file_path VARCHAR(500),
    status payment_status DEFAULT 'pending',
    amount FLOAT NOT NULL,
    subscription_days INTEGER,
    transaction_id VARCHAR(100),
    notes TEXT,
    approved_by BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE payments IS 'Payment records for premium subscriptions and payment verification';
COMMENT ON COLUMN payments.screenshot_file_id IS 'Telegram file ID for payment screenshot';

-- Leaderboard: Rankings and scores
CREATE TABLE IF NOT EXISTS leaderboard (
    leaderboard_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    period leaderboard_period NOT NULL,
    total_score INTEGER DEFAULT 0,
    total_accuracy FLOAT DEFAULT 0.00,
    total_questions INTEGER DEFAULT 0,
    rank_position INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, period)
);
COMMENT ON TABLE leaderboard IS 'Leaderboard entries for different time periods (daily, weekly, monthly, overall)';
COMMENT ON COLUMN leaderboard.period IS 'Time period for this leaderboard entry';

-- ============================================================================
-- LIMIT TRACKING TABLES
-- ============================================================================

-- User Daily Limits: Overall daily usage limits
CREATE TABLE IF NOT EXISTS user_daily_limits (
    limit_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    quiz_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);
COMMENT ON TABLE user_daily_limits IS 'Tracks daily usage limits for quizzes and questions per user';

-- User Chapter Daily Limits: Per-chapter difficulty limits
CREATE TABLE IF NOT EXISTS user_chapter_daily_limits (
    chapter_limit_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    difficulty chapter_limit_difficulty NOT NULL,
    date DATE NOT NULL,
    question_count INTEGER DEFAULT 0,
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subject_id, chapter_id, difficulty, date)
);
COMMENT ON TABLE user_chapter_daily_limits IS 'Tracks daily question limits per chapter and difficulty level';

-- ============================================================================
-- ADMINISTRATION TABLES
-- ============================================================================

-- Admin Users: Web panel administrators
CREATE TABLE IF NOT EXISTS admin_users (
    admin_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role admin_role DEFAULT 'moderator',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE admin_users IS 'Admin users for the web-based administration panel';
COMMENT ON COLUMN admin_users.password_hash IS 'BCrypt hashed password for web panel access';

-- Admin Logs: Audit trail for admin actions
CREATE TABLE IF NOT EXISTS admin_logs (
    log_id SERIAL PRIMARY KEY,
    admin_user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE admin_logs IS 'Audit log of all administrative actions performed in the system';

-- Telegram Admins: Bot administrators
CREATE TABLE IF NOT EXISTS telegram_admins (
    telegram_admin_id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    role telegram_admin_role DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    added_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE telegram_admins IS 'Telegram bot administrators with special privileges';

-- ============================================================================
-- SUPPORT AND COMMUNICATION TABLES
-- ============================================================================

-- Contact Messages: User support tickets
CREATE TABLE IF NOT EXISTS contact_messages (
    message_id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(20) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category contact_category NOT NULL,
    subject VARCHAR(200),
    message_text TEXT NOT NULL,
    status contact_status DEFAULT 'open',
    admin_reply TEXT,
    replied_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    replied_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE contact_messages IS 'User support tickets and contact messages';
COMMENT ON COLUMN contact_messages.ticket_id IS 'Unique ticket identifier for user reference';

-- Access Audit Log: Security and access tracking
CREATE TABLE IF NOT EXISTS access_audit_log (
    audit_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    access_granted BOOLEAN NOT NULL,
    reason VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE access_audit_log IS 'Security audit log tracking all access attempts to system resources';

-- ============================================================================
-- REFERRAL SYSTEM TABLES
-- ============================================================================

-- Referrals: Tracks referral relationships
CREATE TABLE IF NOT EXISTS referrals (
    referral_id SERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    referred_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    status referral_status DEFAULT 'pending',
    reward_claimed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(referrer_id, referred_id)
);
COMMENT ON TABLE referrals IS 'Tracks referral relationships between users for rewards program';

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_premium ON users(is_premium);
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active);

-- Subjects indexes
CREATE INDEX IF NOT EXISTS idx_subjects_is_active ON subjects(is_active);

-- Chapters indexes
CREATE INDEX IF NOT EXISTS idx_chapters_subject_id ON chapters(subject_id);
CREATE INDEX IF NOT EXISTS idx_chapters_is_active ON chapters(is_active);
CREATE INDEX IF NOT EXISTS idx_chapters_subject_order ON chapters(subject_id, chapter_order);

-- Questions indexes
CREATE INDEX IF NOT EXISTS idx_questions_subject_chapter ON questions(subject_id, chapter_id);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_is_active ON questions(is_active);
CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at);

-- User Progress indexes
CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_subject_chapter ON user_progress(subject_id, chapter_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_difficulty ON user_progress(difficulty);
CREATE INDEX IF NOT EXISTS idx_user_progress_accuracy ON user_progress(accuracy);

-- Quiz Attempts indexes
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_date ON quiz_attempts(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_question ON quiz_attempts(question_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_session ON quiz_attempts(quiz_session_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_is_correct ON quiz_attempts(is_correct);

-- Payments indexes
CREATE INDEX IF NOT EXISTS idx_payments_user_date ON payments(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_approved_at ON payments(approved_at);

-- Leaderboard indexes
CREATE INDEX IF NOT EXISTS idx_leaderboard_period_rank ON leaderboard(period, rank_position);
CREATE INDEX IF NOT EXISTS idx_leaderboard_user_period ON leaderboard(user_id, period);

-- User Daily Limits indexes
CREATE INDEX IF NOT EXISTS idx_daily_limits_user_date ON user_daily_limits(user_id, date);

-- User Chapter Daily Limits indexes
CREATE INDEX IF NOT EXISTS idx_chapter_limits_user_chapter ON user_chapter_daily_limits(user_id, chapter_id, difficulty, date);

-- Contact Messages indexes
CREATE INDEX IF NOT EXISTS idx_contact_ticket_id ON contact_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_contact_user_status ON contact_messages(user_id, status);
CREATE INDEX IF NOT EXISTS idx_contact_category_status ON contact_messages(category, status);
CREATE INDEX IF NOT EXISTS idx_contact_created_at ON contact_messages(created_at);

-- Access Audit Log indexes
CREATE INDEX IF NOT EXISTS idx_access_audit_user_date ON access_audit_log(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_access_audit_resource_action ON access_audit_log(resource, action);
CREATE INDEX IF NOT EXISTS idx_access_audit_granted ON access_audit_log(access_granted);

-- Referrals indexes
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_status ON referrals(referrer_id, status);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_status ON referrals(referred_id, status);
CREATE INDEX IF NOT EXISTS idx_referrals_created_at ON referrals(created_at);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for active premium users
CREATE OR REPLACE VIEW active_premium_users AS
SELECT 
    user_id,
    username,
    first_name,
    last_name,
    created_at,
    last_active
FROM users 
WHERE is_premium = TRUE 
    AND blocked = FALSE 
    AND approved = TRUE
ORDER BY last_active DESC;

-- View for daily leaderboard
CREATE OR REPLACE VIEW daily_leaderboard_view AS
SELECT 
    l.leaderboard_id,
    l.user_id,
    u.username,
    u.first_name,
    u.last_name,
    l.total_score,
    l.total_accuracy,
    l.total_questions,
    l.rank_position,
    l.last_updated
FROM leaderboard l
JOIN users u ON l.user_id = u.user_id
WHERE l.period = 'daily'
    AND u.blocked = FALSE
ORDER BY l.rank_position ASC
LIMIT 100;

-- View for pending payments requiring approval
CREATE OR REPLACE VIEW pending_payments_view AS
SELECT 
    p.payment_id,
    p.user_id,
    u.username,
    u.first_name,
    u.last_name,
    p.amount,
    p.subscription_days,
    p.created_at,
    p.screenshot_file_id
FROM payments p
JOIN users u ON p.user_id = u.user_id
WHERE p.status = 'pending'
ORDER BY p.created_at DESC;

-- View for open support tickets
CREATE OR REPLACE VIEW open_support_tickets AS
SELECT 
    cm.message_id,
    cm.ticket_id,
    cm.user_id,
    u.username,
    u.first_name,
    u.last_name,
    cm.category,
    cm.subject,
    cm.message_text,
    cm.created_at
FROM contact_messages cm
JOIN users u ON cm.user_id = u.user_id
WHERE cm.status = 'open'
ORDER BY cm.created_at DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to generate unique ticket IDs
CREATE OR REPLACE FUNCTION generate_ticket_id()
RETURNS VARCHAR(20) AS $$
DECLARE
    ticket_id VARCHAR(20);
BEGIN
    ticket_id := 'TICKET-' || to_char(CURRENT_DATE, 'YYYYMMDD') || '-' || 
                 LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');
    RETURN ticket_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate user accuracy
CREATE OR REPLACE FUNCTION calculate_accuracy(
    p_user_id BIGINT,
    p_subject_id INTEGER,
    p_chapter_id INTEGER,
    p_difficulty progress_difficulty
)
RETURNS FLOAT AS $$
DECLARE
    total_attempts INTEGER;
    correct_attempts INTEGER;
    accuracy FLOAT;
BEGIN
    SELECT 
        COUNT(*),
        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
    INTO total_attempts, correct_attempts
    FROM quiz_attempts qa
    JOIN questions q ON qa.question_id = q.question_id
    WHERE qa.user_id = p_user_id
        AND q.subject_id = p_subject_id
        AND q.chapter_id = p_chapter_id
        AND q.difficulty = p_difficulty::text::question_difficulty;
    
    IF total_attempts > 0 THEN
        accuracy := (correct_attempts::FLOAT / total_attempts) * 100;
    ELSE
        accuracy := 0;
    END IF;
    
    RETURN accuracy;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger for updating user progress accuracy
CREATE OR REPLACE TRIGGER update_user_progress_accuracy
AFTER INSERT OR UPDATE ON quiz_attempts
FOR EACH ROW
EXECUTE FUNCTION update_user_progress_accuracy();

-- Create function for the trigger first
CREATE OR REPLACE FUNCTION update_user_progress_accuracy()
RETURNS TRIGGER AS $$
BEGIN
    -- Update accuracy in user_progress table
    UPDATE user_progress up
    SET 
        accuracy = calculate_accuracy(
            NEW.user_id,
            (SELECT subject_id FROM questions WHERE question_id = NEW.question_id),
            (SELECT chapter_id FROM questions WHERE question_id = NEW.question_id),
            (SELECT difficulty::text::progress_difficulty FROM questions WHERE question_id = NEW.question_id)
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE up.user_id = NEW.user_id
        AND up.subject_id = (SELECT subject_id FROM questions WHERE question_id = NEW.question_id)
        AND up.chapter_id = (SELECT chapter_id FROM questions WHERE question_id = NEW.question_id)
        AND up.difficulty = (SELECT difficulty::text::progress_difficulty FROM questions WHERE question_id = NEW.question_id);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all tables that have updated_at column
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subjects_updated_at
BEFORE UPDATE ON subjects
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chapters_updated_at
BEFORE UPDATE ON chapters
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_questions_updated_at
BEFORE UPDATE ON questions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_progress_updated_at
BEFORE UPDATE ON user_progress
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at
BEFORE UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_admin_users_updated_at
BEFORE UPDATE ON admin_users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_telegram_admins_updated_at
BEFORE UPDATE ON telegram_admins
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA (Optional - remove if not needed)
-- ============================================================================

-- Insert default admin user (password: admin123)
-- You should change this password immediately after installation
INSERT INTO admin_users (username, password_hash, email, role) 
VALUES (
    'admin', 
    '$2b$12$YOUR_HASH_HERE', -- Replace with actual bcrypt hash for 'admin123'
    'admin@quizbot.com', 
    'superadmin'
) ON CONFLICT (username) DO NOTHING;

-- Insert sample subject
INSERT INTO subjects (subject_name, description) 
VALUES ('Mathematics', 'Basic mathematics and problem solving') 
ON CONFLICT (subject_name) DO NOTHING;

-- Insert sample chapter
INSERT INTO chapters (subject_id, chapter_name, chapter_order, description) 
VALUES (
    (SELECT subject_id FROM subjects WHERE subject_name = 'Mathematics'),
    'Algebra',
    1,
    'Introduction to algebraic expressions and equations'
) ON CONFLICT (subject_id, chapter_name) DO NOTHING;

-- ============================================================================
-- DATABASE MAINTENANCE
-- ============================================================================

-- Create a function to clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Delete quiz attempts older than 90 days
    DELETE FROM quiz_attempts WHERE created_at < CURRENT_DATE - INTERVAL '90 days';
    
    -- Delete audit logs older than 180 days
    DELETE FROM access_audit_log WHERE created_at < CURRENT_DATE - INTERVAL '180 days';
    
    -- Delete closed tickets older than 30 days
    DELETE FROM contact_messages 
    WHERE status = 'closed' 
        AND closed_at < CURRENT_DATE - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANT PERMISSIONS (Adjust based on your deployment)
-- ============================================================================

-- Note: These are examples. Adjust according to your security requirements.
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO quizbot_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO quizbot_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Query to verify all tables were created
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size('public.' || table_name)) as size,
    (SELECT count(*) FROM public." || table_name || ") as row_count
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Query to verify enum types
SELECT typname as enum_type, enumlabel as value
FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
ORDER BY typname, enumsortorder;