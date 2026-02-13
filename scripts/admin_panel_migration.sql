-- Admin Panel Implementation - Database Migration
-- Run this script to add the admin_logs table and ensure all admin features work

-- ==================== Admin Logs Table ====================
-- This table tracks all admin actions for auditing purposes

CREATE TABLE IF NOT EXISTS admin_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_user_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_admin_logs_admin (admin_user_id),
    INDEX idx_admin_logs_action (action),
    INDEX idx_admin_logs_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== Add indexes to existing tables for better performance ====================

-- Users table indexes
ALTER TABLE users 
ADD INDEX idx_users_created_at (created_at),
ADD INDEX idx_users_blocked (blocked),
ADD INDEX idx_users_approved (approved);

-- Payments table indexes
ALTER TABLE payments 
ADD INDEX idx_payments_user_status (user_id, status),
ADD INDEX idx_payments_approved_by (approved_by);

-- Questions table indexes
ALTER TABLE questions 
ADD INDEX idx_questions_subject_chapter (subject_id, chapter_id),
ADD INDEX idx_questions_difficulty_active (difficulty, is_active);

-- ==================== Insert sample data for testing ====================

-- Sample subjects (optional - for testing)
-- INSERT INTO subjects (subject_name, description) VALUES 
-- ('Mathematics', 'Basic math operations and calculations'),
-- ('Science', 'Physics, Chemistry, and Biology'),
-- ('English', 'Grammar and vocabulary');

-- ==================== Verification ====ALTER TABLE users 
ADD INDEX idx_users_created_at (created_at),
ADD INDEX idx_users_blocked (blocked),
ADD INDEX idx_users_approved (approved);

-- Payments table indexes
ALTER TABLE payments 
ADD INDEX idx_payments_user_status (user_id, status),
ADD INDEX idx_payments_approved_by (approved_by);

-- Questions table indexes
ALTER TABLE questions 
ADD INDEX idx_questions_subject_chapter (subject_id, chapter_id),
ADD INDEX idx_questions_difficulty_active (difficulty, is_active);================

-- Check if tables exist
-- SHOW TABLES LIKE 'admin_logs';
-- SHOW TABLES LIKE 'users';
-- SHOW TABLES LIKE 'payments';
-- SHOW TABLES LIKE 'questions';

-- Check admin_logs structure
-- DESCRIBE admin_logs;

-- View recent admin logs (after some actions are performed)
-- SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT 10;

