-- Security Fix Migration Script
-- Run this to add audit logging and access control constraints

-- 1. Create access audit log table for security monitoring
CREATE TABLE IF NOT EXISTS access_audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    access_granted BOOLEAN NOT NULL,
    reason VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_access_audit_user ON access_audit_log(user_id, created_at);

-- Index for security monitoring
CREATE INDEX IF NOT EXISTS idx_access_audit_denied ON access_audit_log(access_granted, created_at) 
WHERE access_granted = FALSE;

-- 2. Add constraints to payments table to ensure data integrity

-- Ensure approved payments have admin signature (non-null)
ALTER TABLE payments ADD CONSTRAINT IF NOT EXISTS chk_approved_has_admin 
    CHECK (status != 'approved' OR approved_by IS NOT NULL);

-- Ensure approved payments have timestamp (non-null)
ALTER TABLE payments ADD CONSTRAINT IF NOT EXISTS chk_approved_has_timestamp 
    CHECK (status != 'approved' OR approved_at IS NOT NULL);

-- Ensure rejected payments have reason
ALTER TABLE payments ADD CONSTRAINT IF NOT EXISTS chk_rejected_has_reason 
    CHECK (status != 'rejected' OR rejected_reason IS NOT NULL);

-- 3. Create index for fast access checks on approved payments
CREATE INDEX IF NOT EXISTS idx_payments_approved_user ON payments(user_id, status) 
WHERE status = 'approved';

-- 4. Function to log access attempts (helper)
CREATE OR REPLACE FUNCTION log_access_attempt(
    p_user_id BIGINT,
    p_action VARCHAR(50),
    p_resource VARCHAR(100),
    p_access_granted BOOLEAN,
    p_reason VARCHAR(255)
) RETURNS VOID AS $$
BEGIN
    INSERT INTO access_audit_log (user_id, action, resource, access_granted, reason)
    VALUES (p_user_id, p_action, p_resource, p_access_granted, p_reason);
END;
$$ LANGUAGE plpgsql;

-- 5. Function to validate payment approval (helper)
CREATE OR REPLACE FUNCTION validate_payment_approval(p_payment_id INT)
RETURNS TABLE (
    is_valid BOOLEAN,
    message VARCHAR(255),
    admin_id BIGINT
) AS $$
DECLARE
    v_payment RECORD;
    v_is_valid BOOLEAN := FALSE;
    v_message VARCHAR(255) := 'Unknown error';
    v_admin_id BIGINT;
BEGIN
    -- Get payment
    SELECT * INTO v_payment FROM payments WHERE payment_id = p_payment_id;
    
    IF v_payment IS NULL THEN
        v_message := 'Payment not found';
    ELSIF v_payment.status != 'approved' THEN
        v_message := 'Payment status is ' || v_payment.status || ', not approved';
    ELSIF v_payment.approved_by IS NULL THEN
        v_message := 'No admin approval signature';
    ELSIF v_payment.approved_at IS NULL THEN
        v_message := 'No approval timestamp';
    ELSIF v_payment.screenshot_file_id IS NULL AND v_payment.screenshot_file_path IS NULL THEN
        v_message := 'No screenshot attached';
    ELSE
        v_is_valid := TRUE;
        v_message := 'Payment properly approved';
        v_admin_id := v_payment.approved_by;
    END IF;
    
    RETURN QUERY SELECT v_is_valid, v_message, v_admin_id;
END;
$$ LANGUAGE plpgsql;

-- 6. Trigger to automatically validate payments before approval
CREATE OR REPLACE FUNCTION check_before_update()
RETURNS TRIGGER AS $$
BEGIN
    -- When status changes to 'approved'
    IF NEW.status = 'approved' AND (OLD.status IS NULL OR OLD.status != 'approved') THEN
        -- Ensure screenshot exists
        IF NEW.screenshot_file_id IS NULL AND NEW.screenshot_file_path IS NULL THEN
            RAISE EXCEPTION 'Cannot approve payment without screenshot';
        END IF;
        
        -- Ensure admin signature exists
        IF NEW.approved_by IS NULL THEN
            RAISE EXCEPTION 'Admin ID must be set for approval';
        END IF;
        
        -- Ensure timestamp exists (will be set by DEFAULT, but ensure it's set)
        IF NEW.approved_at IS NULL THEN
            NEW.approved_at := NOW();
        END IF;
    END IF;
    
    -- When status changes to 'rejected'
    IF NEW.status = 'rejected' AND (OLD.status IS NULL OR OLD.status != 'rejected') THEN
        -- Ensure reason exists
        IF NEW.rejected_reason IS NULL OR TRIM(NEW.rejected_reason) = '' THEN
            RAISE EXCEPTION 'Rejection reason is required';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS payment_validation_trigger ON payments;
CREATE TRIGGER payment_validation_trigger
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION check_before_update();

-- 7. View for monitoring access attempts
CREATE OR REPLACE VIEW access_attempts_summary AS
SELECT 
    DATE(created_at) as access_date,
    resource,
    action,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN access_granted THEN 1 ELSE 0 END) as granted,
    SUM(CASE WHEN NOT access_granted THEN 1 ELSE 0 END) as denied,
    reason
FROM access_audit_log
GROUP BY DATE(created_at), resource, action, reason
ORDER BY access_date DESC, denied DESC;

-- 8. View for monitoring suspicious activity
CREATE OR REPLACE VIEW suspicious_activity AS
SELECT 
    user_id,
    COUNT(*) as denied_count,
    ARRAY_AGG(DISTINCT reason) as denial_reasons,
    MIN(created_at) as first_attempt,
    MAX(created_at) as last_attempt
FROM access_audit_log
WHERE access_granted = FALSE
GROUP BY user_id
HAVING COUNT(*) >= 5
ORDER BY denied_count DESC;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT ON access_audit_log TO your_app_user;
-- GRANT SELECT ON access_attempts_summary TO your_app_user;
-- GRANT SELECT ON suspicious_activity TO your_app_user;

-- Run with: psql -d your_database -f scripts/security_fix_migration.sql

