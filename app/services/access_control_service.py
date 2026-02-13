"""
SECURITY FIX: Strict Access Control Service

🚨 CRITICAL: This module enforces the business rule:
"A user can access quizzes ONLY IF approved = 1"

NO fallback paths. NO bypasses. NO exceptions.

Business Rule:
- User submits screenshot → screenshot_submitted = 1
- Admin approves → approved = 1, is_premium = 1
- User gets lifetime access ONLY after approved = 1

Any state like (approved=0, is_premium=1) is INVALID and should NOT grant access.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, AccessAuditLog

logger = logging.getLogger(__name__)

# Enable debug logging for authorization
DEBUG_AUTH = True

# Access denial messages
ACCESS_DENIED = {
    'NOT_APPROVED': (
        "❌ Access Denied\n\n"
        "Your account is not approved yet.\n"
        "Please complete payment and wait for admin approval."
    ),
    'NO_USER': (
        "❌ Access Denied\n\n"
        "User account not found. Please /start first."
    ),
    'SYSTEM_ERROR': (
        "❌ Access Denied\n\n"
        "System error occurred. Please try again later."
    ),
    'BLOCKED': (
        "❌ Access Denied\n\n"
        "Your account has been blocked. Please contact admin."
    ),
}


async def can_access_quiz(
    user_id: int,
    session: AsyncSession,
    log_attempt: bool = True,
    handler_name: str = "unknown"
) -> Dict[str, Any]:
    """
    🔐 SINGLE SOURCE OF TRUTH for quiz access.
    
    🚨 STRICT ENFORCEMENT: Access is granted ONLY IF user.approved = 1
    
    This function checks NOTHING else:
    - is_premium flag is IGNORED
    - has_active_subscription is IGNORED  
    - payment status is IGNORED (unless it determines approval)
    - referral status is IGNORED
    
    Args:
        user_id: Telegram user ID
        session: Database session
        log_attempt: Whether to log this access attempt
        handler_name: Name of the handler for logging
    
    Returns:
        Dict with keys:
        - allowed: bool (True ONLY if approved = 1)
        - reason: str (user-friendly message if denied)
        - reason_code: str (internal code for logging)
        - user: User object or None
    """
    
    result = {
        'allowed': False,
        'reason': '',
        'reason_code': '',
        'user': None
    }
    
    # Use RAW SQL to bypass any ORM caching issues
    # This ensures we always get the freshest approved status
    try:
        query = text(
            "SELECT user_id, username, approved, is_premium, blocked "
            "FROM users WHERE user_id = :user_id"
        )
        db_result = await session.execute(query, {"user_id": user_id})
        row = db_result.fetchone()
        
        if not row:
            result['reason_code'] = 'NO_USER'
            result['reason'] = ACCESS_DENIED['NO_USER']
            
            await _log_denied_access(
                session, user_id, handler_name, 
                result['reason_code'], 
                "User not found in database"
            )
            return result
        
        user_id_db, username, approved, is_premium, blocked = row
        result['user'] = {
            'user_id': user_id_db,
            'username': username,
            'approved': approved,
            'is_premium': is_premium,
            'blocked': blocked
        }
        
        if DEBUG_AUTH:
            logger.debug(
                f"[AUTH] User {user_id}: approved={approved}, "
                f"is_premium={is_premium}, blocked={blocked}, "
                f"handler={handler_name}"
            )
        
        # Check if blocked
        if blocked:
            result['reason_code'] = 'BLOCKED'
            result['reason'] = ACCESS_DENIED['BLOCKED']
            
            await _log_denied_access(
                session, user_id, handler_name,
                result['reason_code'],
                f"User is blocked"
            )
            return result
        
        # 🚨 CRITICAL: Check ONLY the approved field
        # This is the SINGLE SOURCE OF TRUTH
        # No fallback paths, no bypasses, no exceptions
        
        if not approved:
            # User is NOT approved - DENY ACCESS
            result['reason_code'] = 'NOT_APPROVED'
            result['reason'] = ACCESS_DENIED['NOT_APPROVED']
            
            # Log the denied access attempt with full details
            await _log_denied_access(
                session, user_id, handler_name,
                result['reason_code'],
                f"approved={approved}, is_premium={is_premium}, "
                f"has_active_subscription=False"
            )
            
            # Security warning for inconsistent state
            if is_premium:
                logger.warning(
                    f"🚨 SECURITY ALERT: User {user_id} has is_premium=True "
                    f"but approved=False! This is an inconsistent state."
                )
            
            return result
        
        # User is approved - GRANT ACCESS
        result['allowed'] = True
        result['reason_code'] = 'ACCESS_GRANTED'
        
        await _log_access_granted(
            session, user_id, handler_name,
            f"User approved={approved}, is_premium={is_premium}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking quiz access for user {user_id}: {e}")
        result['reason_code'] = 'SYSTEM_ERROR'
        result['reason'] = ACCESS_DENIED['SYSTEM_ERROR']
        
        await _log_denied_access(
            session, user_id, handler_name,
            result['reason_code'],
            f"System error: {str(e)}"
        )
        return result


async def can_access_quiz_simple(
    user_id: int,
    session: AsyncSession
) -> Tuple[bool, str]:
    """
    Simple boolean check for quiz access.
    
    Returns:
        Tuple of (allowed: bool, reason_code: str)
        allowed is True ONLY if user.approved = 1
    
    Usage:
        allowed, reason = await can_access_quiz_simple(user_id, session)
        if not allowed:
            await message.answer(ACCESS_DENIED[reason])
            return
    """
    try:
        query = text(
            "SELECT approved, is_premium, blocked FROM users WHERE user_id = :user_id"
        )
        result = await session.execute(query, {"user_id": user_id})
        row = result.fetchone()
        
        if not row:
            return False, 'NO_USER'
        
        approved, is_premium, blocked = row
        
        if blocked:
            return False, 'BLOCKED'
        
        if not approved:
            # Log security alert for inconsistent state
            if is_premium:
                logger.warning(
                    f"🚨 SECURITY: User {user_id} has is_premium=True "
                    f"but approved=False"
                )
            return False, 'NOT_APPROVED'
        
        return True, 'ACCESS_GRANTED'
        
    except Exception as e:
        logger.error(f"Error in can_access_quiz_simple for user {user_id}: {e}")
        return False, 'SYSTEM_ERROR'


async def require_quiz_access(
    user_id: int,
    session: AsyncSession,
    handler_name: str = "unknown"
) -> Optional[Dict[str, Any]]:
    """
    Convenience wrapper for quiz access check.
    
    Returns None if access is granted.
    Returns the full result dict if access is denied (for sending message).
    
    Usage:
        result = await require_quiz_access(user_id, session, "start_quiz_handler")
        if result:
            await message.answer(result['reason'])
            return
    """
    result = await can_access_quiz(
        user_id=user_id,
        session=session,
        log_attempt=True,
        handler_name=handler_name
    )
    
    if not result['allowed']:
        return result
    
    return None


async def _log_denied_access(
    session: AsyncSession,
    user_id: int,
    handler_name: str,
    reason_code: str,
    details: str
):
    """Log every denied access attempt for security auditing."""
    try:
        # Try to use AccessAuditLog if it exists
        audit_log = AccessAuditLog(
            user_id=user_id,
            action="access_denied",
            resource="quiz",
            access_granted=False,
            reason=f"{handler_name}: {reason_code} - {details}",
            created_at=datetime.utcnow()
        )
        session.add(audit_log)
        await session.commit()
    except Exception:
        # If table doesn't exist, log to regular logger
        logger.warning(
            f"🚫 ACCESS DENIED | User: {user_id} | "
            f"Handler: {handler_name} | Reason: {reason_code} | Details: {details}"
        )


async def _log_access_granted(
    session: AsyncSession,
    user_id: int,
    handler_name: str,
    details: str
):
    """Log successful access for auditing."""
    try:
        audit_log = AccessAuditLog(
            user_id=user_id,
            action="access_granted",
            resource="quiz",
            access_granted=True,
            reason=f"{handler_name}: {details}",
            created_at=datetime.utcnow()
        )
        session.add(audit_log)
        await session.commit()
    except Exception:
        if DEBUG_AUTH:
            logger.debug(f"✅ ACCESS GRANTED | User: {user_id} | Handler: {handler_name}")


# =============================================================================
# UTILITY FUNCTIONS FOR ADMIN PANEL
# =============================================================================

async def get_user_access_status(
    user_id: int,
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Get detailed access status for a user.
    
    Returns:
        Dict with access status details for admin review.
    """
    # Use raw SQL to get freshest data
    query = text(
        "SELECT user_id, username, approved, is_premium, blocked, created_at "
        "FROM users WHERE user_id = :user_id"
    )
    result = await session.execute(query, {"user_id": user_id})
    row = result.fetchone()
    
    if not row:
        return {
            'exists': False,
            'can_access': False,
            'message': 'User not found'
        }
    
    approved = row[2]
    is_premium = row[3]
    blocked = row[4]
    
    return {
        'exists': True,
        'user_id': row[0],
        'username': row[1],
        'approved': approved,
        'is_premium': is_premium,
        'blocked': blocked,
        'can_access': approved == True and not blocked,
        'state_valid': (approved == True) or (approved == False and is_premium == False),
        'message': (
            '✅ User can access quizzes' if approved and not blocked
            else '❌ User cannot access quizzes'
        )
    }


async def validate_user_state(
    user_id: int,
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Validate that a user's access flags are in a consistent state.
    
    Returns:
        Dict with validation result.
    """
    query = text(
        "SELECT user_id, approved, is_premium, blocked FROM users WHERE user_id = :user_id"
    )
    result = await session.execute(query, {"user_id": user_id})
    row = result.fetchone()
    
    if not row:
        return {'valid': False, 'issue': 'User not found'}
    
    user_id, approved, is_premium, blocked = row
    
    # Check for invalid states
    issues = []
    
    # Check for blocked status
    if blocked:
        issues.append(
            "WARNING: User is blocked. Blocked users cannot access quizzes."
        )
    
    # Check for inconsistent premium/approved state
    if is_premium and not approved:
        issues.append(
            "INVALID: is_premium=True but approved=False. "
            "Premium flag should only be set when user is approved."
        )
    
    if is_premium and approved:
        issues.append(
            "VALID: is_premium=True and approved=True. "
            "This is the correct approved state."
        )
    
    if not is_premium and approved:
        issues.append(
            "VALID: is_premium=False and approved=True. "
            "User is approved but premium flag not set."
        )
    
    if not is_premium and not approved:
        issues.append(
            "VALID: is_premium=False and approved=False. "
            "User has not been approved yet."
        )
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'user_id': user_id,
        'approved': approved,
        'is_premium': is_premium,
        'blocked': blocked
    }


async def force_refresh_user(
    user_id: int,
    session: AsyncSession
) -> Optional[User]:
    """
    Force refresh a user from the database.
    
    Use this after admin approval to ensure the latest data is read.
    """
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Force refresh from database
        await session.refresh(user)
        # Expire all loaded attributes to force fresh read on next access
        session.expire_all()
    
    return user


async def fix_inconsistent_user_state(
    user_id: int,
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Fix inconsistent user state where is_premium=True but approved=False.
    
    This function should be used to clean up data issues.
    
    Returns:
        Dict with fix result.
    """
    query = text(
        "SELECT user_id, approved, is_premium FROM users WHERE user_id = :user_id"
    )
    result = await session.execute(query, {"user_id": user_id})
    row = result.fetchone()
    
    if not row:
        return {'success': False, 'message': 'User not found'}
    
    _, approved, is_premium = row
    
    # If user has is_premium=True but approved=False, reset is_premium
    if is_premium and not approved:
        update_query = text(
            "UPDATE users SET is_premium = :is_premium WHERE user_id = :user_id"
        )
        await session.execute(update_query, {
            "user_id": user_id,
            "is_premium": False
        })
        await session.commit()
        
        logger.info(
            f"🔧 FIXED: Reset is_premium to False for user {user_id} "
            f"(was True with approved=False)"
        )
        
        return {
            'success': True,
            'message': 'Fixed inconsistent state: is_premium reset to False',
            'changes': {
                'is_premium': {'old': True, 'new': False}
            }
        }
    
    return {
        'success': True,
        'message': 'No inconsistent state found',
        'changes': {}
    }

