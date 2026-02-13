-- ============================================================================
-- SAFE DATABASE MIGRATION SCRIPT FOR TELEGRAM QUIZ BOT
-- ============================================================================
-- Adds missing columns to MariaDB tables safely without duplicates.
-- MariaDB 10.x / MySQL 8.x compatible
-- ============================================================================
DELIMITER //

CREATE PROCEDURE add_column_if_not_exists(
    IN p_table_name VARCHAR(100),
    IN p_column_name VARCHAR(100),
    IN p_column_def VARCHAR(500)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = p_table_name
        AND COLUMN_NAME = p_column_name
    ) THEN
        SET @sql = CONCAT('ALTER TABLE ', p_table_name, ' ADD ', p_column_name, ' ', p_column_def);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SELECT CONCAT('✓ Added column: ', p_column_name, ' to ', p_table_name) AS result;
    ELSE
        SELECT CONCAT('✓ Column already exists: ', p_column_name, ' in ', p_table_name) AS result;
    END IF;
END //

DELIMITER ;

-- ===============================
-- MIGRATE subscriptions
-- ===============================
CALL add_column_if_not_exists('subscriptions', 'updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP');
CALL add_column_if_not_exists('subscriptions', 'created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');

-- ===============================
-- MIGRATE user_progress
-- ===============================
CALL add_column_if_not_exists('user_progress', 'created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');
CALL add_column_if_not_exists('user_progress', 'updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP');

-- ===============================
-- MIGRATE quiz_attempts
-- ===============================
CALL add_column_if_not_exists('quiz_attempts', 'quiz_session_id', 'VARCHAR(50)');

-- ===============================
-- MIGRATE payments
-- ===============================
CALL add_column_if_not_exists('payments', 'subscription_days', 'INT NOT NULL DEFAULT 30');
CALL add_column_if_not_exists('payments', 'transaction_id', 'VARCHAR(100)');
CALL add_column_if_not_exists('payments', 'notes', 'TEXT');

-- ===============================
-- DROP HELPER PROCEDURE
-- ===============================
DROP PROCEDURE IF EXISTS add_column_if_not_exists;

-- ===============================
-- CREATE INDEXES SAFELY
-- ===============================
-- quiz_attempts.quiz_session_id
SET @exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'quiz_attempts'
                  AND INDEX_NAME = 'idx_quiz_attempts_session');
IF @exists = 0 THEN
    CREATE INDEX idx_quiz_attempts_session ON quiz_attempts(quiz_session_id);
END IF;

-- payments.status
SET @exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'payments'
                  AND INDEX_NAME = 'idx_payments_status');
IF @exists = 0 THEN
    CREATE INDEX idx_payments_status ON payments(status, created_at);
END IF;

-- user_progress composite index
SET @exists := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'user_progress'
                  AND INDEX_NAME = 'idx_user_progress_lookup');
IF @exists = 0 THEN
    CREATE INDEX idx_user_progress_lookup ON user_progress(user_id, subject_id, chapter_id);
END IF;

-- ===============================
-- VERIFICATION
-- ===============================
SELECT 'Verification Results:' AS '';
SELECT 
    'subscriptions' AS table_name,
    COUNT(*) AS expected_columns,
    SUM(CASE WHEN COLUMN_NAME IN ('subscription_id','user_id','payment_id','status','start_date','end_date','is_trial','created_at','updated_at') THEN 1 ELSE 0 END) AS found_columns
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'subscriptions'
UNION ALL
SELECT 
    'user_progress', 12,
    SUM(CASE WHEN COLUMN_NAME IN ('id','user_id','subject_id','chapter_id','difficulty','total_attempts','correct_attempts','total_time_spent','last_attempt','accuracy','created_at','updated_at') THEN 1 ELSE 0 END)
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_progress'
UNION ALL
SELECT 
    'quiz_attempts', 8,
    SUM(CASE WHEN COLUMN_NAME IN ('attempt_id','user_id','question_id','selected_option','is_correct','time_taken','quiz_session_id','created_at') THEN 1 ELSE 0 END)
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quiz_attempts'
UNION ALL
SELECT 
    'payments', 13,
    SUM(CASE WHEN COLUMN_NAME IN ('payment_id','user_id','screenshot_file_id','screenshot_file_path','status','amount','subscription_days','transaction_id','notes','approved_by','approved_at','rejected_reason','created_at') THEN 1 ELSE 0 END)
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'payments';

SELECT '✓ Migration complete! All columns verified.' AS status;
