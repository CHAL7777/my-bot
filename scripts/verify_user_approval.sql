-- ============================================================================
-- VERIFICATION SCRIPT: Check User Approval Status
-- 
-- Run this after approving a payment to verify the user's approved status.
-- ============================================================================

-- ============================================================================
-- 1. CHECK SPECIFIC USER
-- Replace 7342121804 with the actual user_id
-- ============================================================================
SELECT 
    user_id, 
    username, 
    first_name,
    approved, 
    is_premium,
    has_active_subscription,
    blocked,
    created_at,
    updated_at
FROM users 
WHERE user_id = 7342121804;

-- Expected output: approved should be 1, is_premium should be 1

-- ============================================================================
-- 2. FIND INCONSISTENT USERS (is_premium=1 but approved=0)
-- This is the CRITICAL check - these users have access but shouldn't!
-- ============================================================================
SELECT 
    user_id, 
    username, 
    first_name,
    approved, 
    is_premium,
    has_active_subscription
FROM users 
WHERE is_premium = 1 AND approved = 0;

-- If rows are returned, this is a problem! Fix with:
-- UPDATE users SET approved = 1 WHERE is_premium = 1 AND approved = 0;

-- ============================================================================
-- 3. FIND USERS WITH PENDING APPROVAL
-- Users who have made payments but haven't been approved
-- ============================================================================
SELECT 
    u.user_id,
    u.username,
    u.first_name,
    u.approved,
    u.is_premium,
    p.payment_id,
    p.amount,
    p.status,
    p.created_at
FROM users u
LEFT JOIN payments p ON u.user_id = p.user_id
WHERE p.status = 'approved'
  AND u.approved = 0
GROUP BY u.user_id, u.username, u.first_name, u.approved, u.is_premium, p.payment_id, p.amount, p.status, p.created_at;

-- ============================================================================
-- 4. FIX ALL INCONSISTENT USERS (GOLD STANDARD)
-- Run this to fix all users who have is_premium=1 but approved=0
-- ============================================================================
-- UPDATE users SET approved = 1 WHERE is_premium = 1 AND approved = 0;

-- ============================================================================
-- 5. CHECK RECENT APPROVALS
-- See the most recently approved users
-- ============================================================================
SELECT 
    u.user_id,
    u.username,
    u.approved,
    u.is_premium,
    p.payment_id,
    p.approved_at,
    p.approved_by
FROM users u
JOIN payments p ON u.user_id = p.user_id
WHERE p.status = 'approved'
ORDER BY p.approved_at DESC
LIMIT 20;

-- ============================================================================
-- 6. COUNT STATISTICS
-- ============================================================================
SELECT 
    COUNT(*) as total_users,
    SUM(approved) as approved_count,
    SUM(is_premium) as premium_count,
    SUM(CASE WHEN approved = 0 AND is_premium = 1 THEN 1 ELSE 0 END) as inconsistent_count
FROM users;

