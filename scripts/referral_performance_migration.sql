-- Referral Performance Optimization Migration
-- Adds indexes to improve query performance for referral operations
-- Run this to optimize referral system performance

-- Add indexes on referrals table for common query patterns
-- These indexes will significantly speed up:
-- - Referral stats queries (count by status)
-- - Top referrers leaderboard (ORDER BY referral_count)
-- - User referral lookups (referrer_id, referred_id)

-- Index on referrer_id for "get user's referrals" queries
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id 
ON referrals(referrer_id);

-- Index on referred_id for "who referred this user" queries  
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id 
ON referrals(referred_id);

-- Composite index on (referrer_id, status) for stats queries
-- This is used by get_referral_stats() optimized query
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_status 
ON referrals(referrer_id, status);

-- Index on status for "get pending referrals" queries
CREATE INDEX IF NOT EXISTS idx_referrals_status 
ON referrals(status);

-- Index on created_at for time-based queries (e.g., "this month's referrals")
CREATE INDEX IF NOT EXISTS idx_referrals_created_at 
ON referrals(created_at);

-- Composite index for leaderboard queries (users with referrals)
-- This speeds up get_top_referrers()
CREATE INDEX IF NOT EXISTS idx_users_referral_count 
ON users(referral_count DESC) 
WHERE referral_count > 0;

-- Analyze tables to update statistics for query planner
ANALYZE referrals;
ANALYZE users;

-- Verify indexes were created
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('referrals', 'users')
ORDER BY tablename, indexname;

-- Show query performance improvement
-- Before indexes: Sequential scan on referrals table
-- After indexes: Index scan using idx_referrals_referrer_status

