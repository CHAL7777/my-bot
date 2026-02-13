-- Migration script to create subscriptions table
-- Run this to fix handler errors related to missing subscriptions table

-- For SQLite
-- Note: SQLite doesn't support all ALTER TABLE operations, so we create the table if it doesn't exist

-- Create subscriptions table (SQLite compatible)
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    payment_id INTEGER,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'expired', 'cancelled')),
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    is_trial BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments (payment_id) ON DELETE SET NULL
);

-- Create indexes for subscriptions table
CREATE INDEX IF NOT EXISTS idx_subscription_user ON subscriptions (user_id, status);
CREATE INDEX IF NOT EXISTS idx_subscription_end ON subscriptions (end_date);
CREATE INDEX IF NOT EXISTS idx_subscription_active ON subscriptions (user_id, status, end_date);

-- For MySQL/MariaDB, run this version:
-- 
-- CREATE TABLE subscriptions (
--     subscription_id INT AUTO_INCREMENT PRIMARY KEY,
--     user_id BIGINT NOT NULL,
--     payment_id INT,
--     status ENUM('active', 'expired', 'cancelled') DEFAULT 'active',
--     start_date DATETIME NOT NULL,
--     end_date DATETIME NOT NULL,
--     is_trial BOOLEAN DEFAULT FALSE,
--     created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
--     updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     INDEX idx_subscription_user (user_id, status),
--     INDEX idx_subscription_end (end_date),
--     INDEX idx_subscription_active (user_id, status, end_date),
--     FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
--     FOREIGN KEY (payment_id) REFERENCES payments (payment_id) ON DELETE SET NULL
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verify table was created (for both SQLite and MySQL)
-- SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions';
-- OR for MySQL: SHOW TABLES LIKE 'subscriptions';
