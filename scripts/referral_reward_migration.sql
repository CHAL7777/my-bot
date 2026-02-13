-- Migration Script: Referral System Enhancement
-- Run this to add referral_balance column and update status values
-- Compatible with PostgreSQL/Supabase

-- ============================================================================
-- STEP 1: Add referral_balance column to users table
-- ============================================================================

-- Add referral_balance column (if not exists)
-- This stores the user's referral earnings in Birr
ALTER TABLE IF EXISTS users 
ADD COLUMN IF NOT EXISTS referral_balance DECIMAL(10,2) DEFAULT 0.00;

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_referral_balance 
ON users(referral_balance);

-- ============================================================================
-- STEP 2: Update referral status enum (PostgreSQL only)
-- ============================================================================

-- For PostgreSQL, we need to create a new enum type and update the column
-- This changes 'completed' to 'approved' in the referral_status enum

-- Step 2a: Create new enum type if old one exists
DO $$
BEGIN
    -- Check if old enum type exists
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'referral_status_old') THEN
        DROP TYPE referral_status_old CASCADE;
    END IF;
    
    -- Rename old enum to backup
    ALTER TYPE referral_status RENAME TO referral_status_old;
    
    -- Create new enum with 'approved' instead of 'completed'
    CREATE TYPE referral_status AS ENUM ('pending', 'approved', 'cancelled');
    
    -- Update the column to use new enum
    ALTER TABLE referrals 
    ALTER COLUMN status TYPE referral_status USING status::text::referral_status;
    
    -- Drop old enum
    DROP TYPE referral_status_old CASCADE;
END $$;

-- ============================================================================
-- STEP 3: Add new columns to referrals table
-- ============================================================================

-- Add reward_claimed_at column (if not exists)
ALTER TABLE IF EXISTS referrals 
ADD COLUMN IF NOT EXISTS reward_claimed_at TIMESTAMP;

-- Rename completed_at to approved_at (if completed_at exists)
-- Note: This preserves existing data
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'referrals' AND column_name = 'completed_at') THEN
        ALTER TABLE referrals RENAME COLUMN completed_at TO approved_at;
    ELSE
        -- If completed_at doesn't exist, just add approved_at
        ALTER TABLE IF EXISTS referrals 
        ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Add indexes for performance
-- ============================================================================

-- Create index for created_at (useful for sorting by newest referrals)
CREATE INDEX IF NOT EXISTS idx_referrals_created 
ON referrals(created_at DESC);

-- Create index for approved_at (useful for filtering approved referrals)
CREATE INDEX IF NOT EXISTS idx_referrals_approved_at 
ON referrals(approved_at);

-- ============================================================================
-- STEP 5: Update existing data (optional)
-- ============================================================================

-- Any referrals that were marked as 'completed' are now 'approved'
-- (This was handled by the enum migration above)

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check if columns were added
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'users' AND column_name = 'referral_balance';

-- Check referral status values
-- SELECT DISTINCT status FROM referrals;

-- Check for any pending referrals that should be approved
-- SELECT COUNT(*) FROM referrals WHERE status = 'pending';

-- Check for any approved referrals
-- SELECT COUNT(*) FROM referrals WHERE status = 'approved';

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================

-- To rollback:
-- 1. ALTER TABLE users DROP COLUMN IF EXISTS referral_balance;
-- 2. DROP INDEX IF EXISTS idx_users_referral_balance;
-- 3. Recreate the old enum (pending, completed, cancelled)
-- 4. ALTER TABLE referrals ALTER COLUMN status TYPE referral_status_old;
-- 5. DROP TYPE referral_status;
-- 6. ALTER TYPE referral_status_old RENAME TO referral_status;

