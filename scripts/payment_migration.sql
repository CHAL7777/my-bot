-- Migration: Add payments and subscriptions tables, ensure users.approved default false
-- Run this against your MariaDB database to create payments workflow tables.

CREATE TABLE IF NOT EXISTS `payments` (
  `payment_id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `screenshot_file_id` VARCHAR(255),
  `screenshot_file_path` VARCHAR(500),
  `status` ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  `amount` DOUBLE NOT NULL,
  `subscription_days` INT NOT NULL,
  `transaction_id` VARCHAR(100),
  `notes` TEXT,
  `approved_by` BIGINT,
  `approved_at` DATETIME,
  `rejected_reason` TEXT,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_payment_status` (`status`,`created_at`),
  INDEX `idx_user_payments` (`user_id`,`created_at`),
  CONSTRAINT `fk_payments_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_payments_approver` FOREIGN KEY (`approved_by`) REFERENCES `users`(`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `subscriptions` (
  `subscription_id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `payment_id` INT NOT NULL,
  `status` ENUM('active','expired','cancelled') NOT NULL DEFAULT 'active',
  `start_date` DATETIME NOT NULL,
  `end_date` DATETIME NOT NULL,
  `is_trial` TINYINT(1) DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_subscription_dates` (`end_date`,`status`),
  INDEX `idx_user_subscription` (`user_id`,`end_date`),
  CONSTRAINT `fk_sub_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sub_payment` FOREIGN KEY (`payment_id`) REFERENCES `payments`(`payment_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Ensure user.approved default is false
ALTER TABLE `users`
  MODIFY COLUMN `approved` TINYINT(1) NOT NULL DEFAULT 0;

-- Note: If you use Alembic, prefer generating an Alembic migration instead of running this SQL directly.
