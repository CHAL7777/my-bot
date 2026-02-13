-- ============================================================================
-- FIX: Add missing columns to subscriptions table
-- ============================================================================
-- This script adds the missing columns that the code expects:
-- - is_trial: Boolean for trial subscriptions
-- - updated_at: Datetime for tracking updates
-- - created_at: Datetime for tracking creation
-- ============================================================================

-- Add is_trial column if it doesn't exist
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS is_trial BOOLEAN DEFAULT FALSE;

-- Add updated_at column if it doesn't exist
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Add created_at column if it doesn't exist
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Verify the columns were added
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'subscriptions'
ORDER BY ORDINAL_POSITION;

-- ============================================================================
-- Alternative: If the table has issues, you can recreate it with this script
-- ============================================================================
/*
DROP TABLE IF EXISTS subscriptions;

CREATE TABLE subscriptions (
    subscription_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    payment_id INT,
    status ENUM('active', 'expired', 'cancelled') DEFAULT 'active',
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    is_trial BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_subscription (user_id, status, end_date),
    INDEX idx_subscription_dates (start_date, end_date)
);
*/

SELECT '✓ Migration complete! subscriptions table updated.' AS status;

