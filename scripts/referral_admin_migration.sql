-- Migration Script: Referral System & Multi-Admin Support
-- Run this after the main schema is created

-- =====================================================
-- PART 1: REFERRAL SYSTEM
-- =====================================================

-- Add referral fields to users table
ALTER TABLE users ADD COLUMN referral_code VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN referred_by BIGINT NULL;
ALTER TABLE users ADD COLUMN referral_count INT DEFAULT 0;

-- Create referrals table to track referral relationships
CREATE TABLE IF NOT EXISTS referrals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    referred_id BIGINT NOT NULL,
    status ENUM('pending', 'completed', 'cancelled') DEFAULT 'pending',
    reward_claimed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_referral (referrer_id, referred_id),
    INDEX idx_referrer (referrer_id),
    INDEX idx_referred (referred_id),
    INDEX idx_status (status)
);

-- Create index for faster referral code lookups
CREATE INDEX idx_users_referral_code ON users(referral_code);
CREATE INDEX idx_users_referred_by ON users(referred_by);

-- =====================================================
-- PART 2: MULTI-ADMIN SUPPORT
-- =====================================================

-- Create telegram_admins table for database-backed admin management
CREATE TABLE IF NOT EXISTS telegram_admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    role ENUM('superadmin', 'admin') DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    added_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_admin_user_id (user_id),
    INDEX idx_admin_role (role)
);

-- =====================================================
-- PART 3: INITIAL DATA SEEDING
-- =====================================================

-- Seed initial admins from environment ADMIN_IDS
-- This will be done via Python script (scripts/seed_initial_admins.py)
-- to respect the ADMIN_IDS configuration

-- Example seed query (run manually if needed):
-- INSERT INTO telegram_admins (user_id, username, role, added_by) VALUES
-- (123456789, 'admin_username', 'superadmin', NULL);

-- =====================================================
-- PART 4: UPGRADE FUNCTIONS (Optional)
-- =====================================================

-- Function to get user's referral link (for reference)
-- Usage: SELECT get_referral_link(user_id);
DELIMITER //
CREATE FUNCTION get_referral_link(user_id BIGINT) 
RETURNS VARCHAR(255)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE ref_code VARCHAR(20);
    DECLARE bot_url VARCHAR(100) DEFAULT 'https://t.me/YourBotName';
    
    SELECT referral_code INTO ref_code FROM users WHERE user_id = user_id;
    
    IF ref_code IS NOT NULL THEN
        RETURN CONCAT(bot_url, '?start=ref_', ref_code);
    END IF;
    
    RETURN NULL;
END //
DELIMITER ;

-- Function to complete referral (for stored procedure)
-- Usage: CALL complete_referral(referral_id);
DELIMITER //
CREATE PROCEDURE complete_referral(IN p_referral_id INT)
BEGIN
    UPDATE referrals 
    SET status = 'completed', 
        completed_at = NOW() 
    WHERE id = p_referral_id;
    
    UPDATE users 
    SET referral_count = referral_count + 1 
    WHERE user_id = (SELECT referrer_id FROM referrals WHERE id = p_referral_id);
END //
DELIMITER ;

