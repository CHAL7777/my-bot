# 🔐 Telegram Quiz Bot - Security Audit Report

**Date:** 2024
**Severity:** CRITICAL (Business Impact)
**Status:** ACCESS BYPASS VULNERABILITY

---

## Executive Summary

The Telegram Quiz Bot has a **critical security vulnerability** that allows users to access premium features without admin approval of their payment screenshots. This document provides a complete root cause analysis, fix plan, and implementation guide.

---

## 🚨 Root Cause Analysis

### Vulnerability Summary

Users can access premium quizzes **without payment approval** due to multiple security gaps in the access control system.

---

### **Cause 1: Incomplete Subscription Middleware**

**File:** `app/middlewares/subscription.py`

**Problem:** The middleware only checks `User.is_premium` flag but doesn't verify:
1. Whether a payment screenshot was uploaded
2. Whether payment status is `APPROVED`
3. Whether the approval has a valid admin signature

**Vulnerable Code:**
```python
async def __call__(self, handler, event, data):
    if await self._should_skip_check(event):
        return await handler(event, data)  # ⚠️ SKIPS CHECKS!
    
    user_id = event.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        user = await user_repo.get_user(user_id)
        
        if user:
            data['has_active_subscription'] = user.is_premium
            data['is_premium'] = user.is_premium  # ⚠️ Only checks this flag!
```

**Issue:** The `_should_skip_check()` method allows bypass for:
- `payment_*` callbacks
- `back_to_*` callbacks
- `cancel_*` callbacks

---

### **Cause 2: Payment Status Not Verified in Quiz Handlers**

**File:** `app/handlers/quiz.py`

**Problem:** Difficulty selection only checks `has_active_subscription` from middleware, which can be stale or bypassed.

**Vulnerable Code:**
```python
@router.callback_query(F.data.startswith("difficulty_"))
async def select_difficulty(callback, state, has_active_subscription: bool = False):
    difficulty = callback.data.split("_")[1]
    
    if difficulty in ['medium', 'hard'] and not has_active_subscription:
        await callback.answer("Premium Feature!", show_alert=True)
        return
    # ⚠️ No direct database verification!
```

---

### **Cause 3: User Model Has Duplicate Flags**

**File:** `app/db/models.py`

**Problem:** User model has both `approved` and `is_premium` flags:
```python
class User(Base):
    approved = Column(Boolean, default=False)   # ⚠️ Confusing!
    is_premium = Column(Boolean, default=False)  # ⚠️ Redundant!
```

This creates confusion about which flag to check and allows edge cases where:
- User is `approved=True` but `is_premium=False`
- User is `is_premium=True` but no approved payment exists

---

### **Cause 4: No Screenshot Validation Before Approval**

**File:** `app/handlers/admin_payments.py`

**Problem:** Admin can approve payment without screenshot verification:
```python
async def confirm_approve_payment_callback(callback, is_admin: bool = False):
    # No check if screenshot_file_id exists!
    result = await payment_service.approve_payment(payment_id, callback.from_user.id)
```

---

### **Cause 5: Race Condition in Payment Approval**

**File:** `app/repositories/payment_repo.py`

**Problem:** Payment approval doesn't use database locking, allowing:
- Double approval of same payment
- Concurrent approval attempts

**Vulnerable Code:**
```python
async def approve_payment(self, payment_id: int, admin_id: int):
    payment = await self.get_payment(payment_id)  # ⚠️ No lock!
    if payment.status != 'pending':
        raise Exception(...)
```

---

### **Cause 6: Answer Handler Doesn't Verify Subscription**

**File:** `app/handlers/answers.py`

**Problem:** Once quiz starts, there's no verification on each answer:
```python
@router.callback_query(F.data.startswith("answer_"), QuizStates.quiz_in_progress)
async def handle_answer(callback, state, has_active_subscription: bool = False):
    # ⚠️ No subscription check inside quiz!
```

---

## ✅ Fixed Logic Flow

### New Access Control Flow

```
User Attempts Premium Quiz
        ↓
Check: can_access_premium(user_id)
        ↓
    ┌───► TRUE ───► ALLOW ACCESS ───► Log success
    │
    ▼
FALSE ──► Send blocking message
        ↓
    ┌───► Payment Pending ───► "Pending approval"
    ├───► No Payment ───► "Upload screenshot first"
    ├───► Payment Rejected ───► "Contact admin"
    └───► No Screenshot ───► "Upload payment proof"
```

### Database Query for Access Check

```sql
-- STRICT ACCESS CHECK QUERY
SELECT 
    u.user_id,
    u.is_premium,
    p.status as payment_status,
    p.screenshot_file_id IS NOT NULL as has_screenshot,
    p.approved_at IS NOT NULL as is_approved
FROM users u
LEFT JOIN payments p ON u.user_id = p.user_id 
    AND p.status = 'approved'
    AND p.approved_at IS NOT NULL
WHERE u.user_id = :user_id;
```

---

## 🔧 SQL Schema Fixes

### Migration Script

```sql
-- File: scripts/security_fix_migration.sql

-- 1. Add constraints to ensure data integrity

-- Make sure payments have unique approved status per user
ALTER TABLE payments ADD CONSTRAINT chk_one_approved_payment 
    CHECK (status IN ('pending', 'approved', 'rejected'));

-- Ensure approved payments have admin signature
ALTER TABLE payments ADD CONSTRAINT chk_approved_has_admin 
    CHECK (status != 'approved' OR approved_by IS NOT NULL);

-- Ensure approved payments have timestamp
ALTER TABLE payments ADD CONSTRAINT chk_approved_has_timestamp 
    CHECK (status != 'approved' OR approved_at IS NOT NULL);

-- 2. Create index for fast access checks
CREATE INDEX idx_payments_approved_user ON payments(user_id, status) 
WHERE status = 'approved';

-- 3. Add audit table for access attempts
CREATE TABLE access_audit_log (
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

CREATE INDEX idx_access_audit_user ON access_audit_log(user_id, created_at);
```

---

## 🐍 Python Implementation

### 1. Create Single Source of Truth - Access Control Service

```python
# app/services/access_control_service.py

"""
Access Control Service - SINGLE SOURCE OF TRUTH for premium access.

This service provides a unified function can_access_premium(user_id) that:
1. Verifies payment screenshot exists
2. Verifies payment status is APPROVED
3. Verifies admin approval with signature and timestamp
4. Logs all access attempts for auditing

Usage:
    from app.services.access_control_service import can_access_premium
    
    access = await can_access_premium(user_id)
    if not access['allowed']:
        await message.answer(access['reason'])
        return
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Payment

logger = logging.getLogger(__name__)

# Access denial reasons
ACCESS_DENIED = {
    'NO_USER': '❌ User account not found. Please /start first.',
    'NO_PAYMENT': '💳 No payment on record. Please upload payment screenshot first.',
    'PAYMENT_PENDING': '⏳ Payment is pending admin review. Please wait.',
    'PAYMENT_REJECTED': '❌ Payment was rejected. Contact admin for details.',
    'NO_SCREENSHOT': '📸 Payment screenshot required. Please upload proof of payment.',
    'NOT_APPROVED': '🔒 Payment not yet approved. Wait for admin verification.',
    'ACCESS_GRANTED': '✅ Premium access confirmed.',
}


async def can_access_premium(
    user_id: int, 
    session: AsyncSession,
    log_attempt: bool = True,
    resource: str = "quiz",
    action: str = "start"
) -> Dict[str, Any]:
    """
    🔐 SINGLE SOURCE OF TRUTH for premium access check.
    
    This function MUST be called for EVERY premium access attempt.
    
    Args:
        user_id: Telegram user ID
        session: Database session
        log_attempt: Whether to log this access attempt
        resource: Resource being accessed (quiz, leaderboard, etc.)
        action: Action being performed (start, answer, view)
    
    Returns:
        Dict with keys:
        - allowed: bool
        - reason: str (user-friendly message)
        - reason_code: str (internal code)
        - user: User object or None
        - payment: Payment object or None
    """
    
    result = {
        'allowed': False,
        'reason': '',
        'reason_code': 'UNKNOWN',
        'user': None,
        'payment': None
    }
    
    # Step 1: Check if user exists
    user = await session.get(User, user_id)
    if not user:
        result['reason_code'] = 'NO_USER'
        result['reason'] = ACCESS_DENIED['NO_USER']
        
        if log_attempt:
            await _log_access_attempt(
                session, user_id, resource, action, False, 
                result['reason_code']
            )
        return result
    
    result['user'] = user
    
    # Step 2: Get the LATEST approved payment for this user
    # We specifically look for APPROVED payments with proper admin signature
    query = select(Payment).where(
        and_(
            Payment.user_id == user_id,
            Payment.status == 'approved',
            Payment.approved_by.isnot(None),  # Admin must be set
            Payment.approved_at.isnot(None)   # Approval timestamp must be set
        )
    ).order_by(Payment.approved_at.desc()).limit(1)
    
    result_query = await session.execute(query)
    approved_payment = result_query.scalar_one_or_none()
    
    # Step 3: Verify payment exists
    if not approved_payment:
        # Check if there's a pending payment
        pending_query = select(Payment).where(
            and_(
                Payment.user_id == user_id,
                Payment.status == 'pending'
            )
        ).order_by(Payment.created_at.desc()).limit(1)
        
        pending_result = await session.execute(pending_query)
        pending_payment = pending_result.scalar_one_or_none()
        
        if pending_payment:
            result['reason_code'] = 'PAYMENT_PENDING'
            result['reason'] = ACCESS_DENIED['PAYMENT_PENDING']
            result['payment'] = pending_payment
            
            if log_attempt:
                await _log_access_attempt(
                    session, user_id, resource, action, False,
                    result['reason_code']
                )
            return result
        
        # Check if there's a rejected payment
        rejected_query = select(Payment).where(
            and_(
                Payment.user_id == user_id,
                Payment.status == 'rejected'
            )
        ).order_by(Payment.created_at.desc()).limit(1)
        
        rejected_result = await session.execute(rejected_query)
        rejected_payment = rejected_result.scalar_one_or_none()
        
        if rejected_payment:
            result['reason_code'] = 'PAYMENT_REJECTED'
            result['reason'] = ACCESS_DENIED['PAYMENT_REJECTED']
            result['reason'] += f"\n📝 Reason: {rejected_payment.rejected_reason or 'Not specified'}"
            result['payment'] = rejected_payment
            
            if log_attempt:
                await _log_access_attempt(
                    session, user_id, resource, action, False,
                    result['reason_code']
                )
            return result
        
        # No payment found at all
        result['reason_code'] = 'NO_PAYMENT'
        result['reason'] = ACCESS_DENIED['NO_PAYMENT']
        
        if log_attempt:
            await _log_access_attempt(
                session, user_id, resource, action, False,
                result['reason_code']
            )
        return result
    
    result['payment'] = approved_payment
    
    # Step 4: Verify screenshot exists (required for approval to be valid)
    if not approved_payment.screenshot_file_id and not approved_payment.screenshot_file_path:
        # This should never happen if approval is done correctly
        # But we check anyway for data integrity
        logger.warning(
            f"SECURITY ALERT: User {user_id} has approved payment "
            f"#{approved_payment.payment_id} without screenshot!"
        )
        
        result['reason_code'] = 'NO_SCREENSHOT'
        result['reason'] = ACCESS_DENIED['NO_SCREENSHOT']
        
        if log_attempt:
            await _log_access_attempt(
                session, user_id, resource, action, False,
                result['reason_code']
            )
        return result
    
    # Step 5: All checks passed - access granted
    result['allowed'] = True
    result['reason_code'] = 'ACCESS_GRANTED'
    result['reason'] = ACCESS_DENIED['ACCESS_GRANTED']
    
    if log_attempt:
        await _log_access_attempt(
            session, user_id, resource, action, True,
            result['reason_code']
        )
    
    return result


async def _log_access_attempt(
    session: AsyncSession,
    user_id: int,
    resource: str,
    action: str,
    access_granted: bool,
    reason_code: str
):
    """Log access attempt for auditing and security monitoring."""
    from app.db.models import AccessAuditLog
    
    try:
        audit_log = AccessAuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            access_granted=access_granted,
            reason=reason_code,
            created_at=datetime.utcnow()
        )
        session.add(audit_log)
        await session.commit()
    except Exception as e:
        # Don't fail the main operation if logging fails
        logger.error(f"Failed to log access attempt: {e}")


# Convenience function for handlers
async def require_premium_access(
    user_id: int,
    session: AsyncSession,
    resource: str = "premium_quiz",
    action: str = "access"
) -> Optional[Dict[str, Any]]:
    """
    Convenience wrapper for premium access check.
    
    Returns the full result dict if access denied (for sending message),
    or None if access is granted.
    
    Usage:
        result = await require_premium_access(user_id, session)
        if result:
            await message.answer(result['reason'])
            return
    """
    result = await can_access_premium(
        user_id=user_id,
        session=session,
        log_attempt=True,
        resource=resource,
        action=action
    )
    
    if not result['allowed']:
        return result
    
    return None
```

---

### 2. Updated Subscription Middleware (Hardened)

```python
# app/middlewares/subscription.py (UPDATED)

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.services.access_control_service import can_access_premium

class SubscriptionMiddleware(BaseMiddleware):
    """
    Hardened middleware for subscription/premium access control.
    
    This middleware now performs a STRICT check using the centralized
    access_control_service.can_access_premium() function.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ):
        user_id = event.from_user.id
        
        # Get database session
        async for session in get_db():
            # Perform STRICT access check
            access_result = await can_access_premium(
                user_id=user_id,
                session=session,
                log_attempt=True,
                resource="middleware_check",
                action="verify"
            )
            
            # Inject access status into data for handlers
            data['has_active_subscription'] = access_result['allowed']
            data['is_premium'] = access_result['allowed']
            data['access_result'] = access_result
            data['user'] = access_result.get('user')
            
            # For commands that can skip middleware, we don't call handler here
            # Instead, we let the handler decide based on data['has_active_subscription']
        
        # Call handler
        return await handler(event, data)
    
    async def _should_skip_check(self, event: Message | CallbackQuery) -> bool:
        """
        CRITICAL: This method is now DISABLED for security.
        
        Previously, this allowed bypassing subscription checks for certain callbacks.
        This is a SECURITY RISK and has been removed.
        
        DO NOT add any conditions here that return True!
        """
        return False
```

---

### 3. Updated Quiz Handler (With Direct Database Check)

```python
# app/handlers/quiz.py (UPDATED)

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.menu import MainMenuKeyboard
from app.services.access_control_service import require_premium_access
from app.db.base import get_db

router = Router()

class QuizStates(StatesGroup):
    selecting_subject = State()
    selecting_chapter = State()
    selecting_difficulty = State()
    quiz_in_progress = State()
    waiting_for_answer = State()


@router.callback_query(F.data.startswith("difficulty_"), QuizStates.selecting_difficulty)
async def select_difficulty(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle difficulty selection with STRICT access control.
    
    This handler now performs a DIRECT database check using the
    access_control_service, bypassing any middleware caching.
    """
    difficulty = callback.data.split("_")[1]
    
    # For premium difficulties, perform DIRECT database check
    if difficulty in ['medium', 'hard']:
        async for session in get_db():
            access_denied = await require_premium_access(
                user_id=callback.from_user.id,
                session=session,
                resource="quiz_difficulty",
                action=f"select_{difficulty}"
            )
            
            if access_denied:
                await callback.answer(
                    access_denied['reason'],
                    show_alert=True
                )
                return
        
        # Access granted - continue with quiz
    # Simple difficulty is free - no check needed
    
    # ... rest of handler logic ...
```

---

### 4. Updated Payment Approval Handler (With Screenshot Verification)

```python
# app/handlers/admin_payments.py (UPDATED)

@router.callback_query(F.data.startswith("confirm_approve_payment_"))
async def confirm_approve_payment_callback(callback: types.CallbackQuery, 
                                           is_admin: bool = False):
    """
    Confirm and process payment approval with STRICT validation.
    
    Security checks:
    1. Payment must exist
    2. Payment must be pending
    3. Screenshot MUST exist
    4. Admin ID must be set
    """
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment = await payment_repo.get_payment(payment_id)
        
        # VALIDATION 1: Payment exists
        if not payment:
            await safe_update_admin_message(
                callback,
                f"❌ Payment #{payment_id} not found!",
                parse_mode='Markdown',
                reply_markup=None
            )
            await callback.answer()
            return
        
        # VALIDATION 2: Payment is pending
        if payment.status != 'pending':
            await safe_update_admin_message(
                callback,
                f"⚠️ Payment #{payment_id} is already {payment.status}.\n"
                f"Cannot re-approve.",
                parse_mode='Markdown',
                reply_markup=None
            )
            await callback.answer()
            return
        
        # VALIDATION 3: Screenshot must exist
        if not payment.screenshot_file_id:
            await safe_update_admin_message(
                callback,
                f"❌ *Security Alert: No Screenshot*\n\n"
                f"Payment #{payment_id} has no screenshot attached.\n"
                f"Cannot approve payment without proof of payment.\n\n"
                f"Please ask user to upload screenshot first.",
                parse_mode='Markdown',
                reply_markup=None
            )
            await callback.answer()
            return
        
        # All validations passed - proceed with approval
        payment_service = PaymentService(payment_repo, user_repo)
        
        try:
            result = await payment_service.approve_payment(
                payment_id, 
                callback.from_user.id
            )
            
            # Notify user
            try:
                await callback.bot.send_message(
                    chat_id=result['user_id'],
                    text=(
                        f"✅ *Payment Approved!*\n\n"
                        f"Your payment has been approved.\n"
                        f"You now have lifetime premium access!\n\n"
                        f"Use /quiz to start learning."
                    ),
                    parse_mode='Markdown'
                )
            except Exception:
                pass
            
            # Update admin message
            await safe_update_admin_message(
                callback,
                (
                    f"✅ *Payment Approved*\n\n"
                    f"Payment #{payment_id} approved successfully.\n"
                    f"User notified of premium access."
                ),
                parse_mode='Markdown',
                reply_markup=None
            )
            
        except Exception as e:
            await safe_update_admin_message(
                callback,
                f"❌ Approval failed: {str(e)}",
                parse_mode='Markdown',
                reply_markup=None
            )
    
    await callback.answer()
```

---

### 5. Updated Answer Handler (With Access Verification)

```python
# app/handlers/answers.py (UPDATED)

@router.callback_query(F.data.startswith("answer_"), QuizStates.quiz_in_progress)
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle answer with access verification.
    
    This prevents users from answering premium questions
    if their access was revoked or expired.
    """
    # Parse answer data
    parts = callback.data.split("_")
    question_id = int(parts[1])
    selected_option = parts[2]
    
    user_id = callback.from_user.id
    
    # For hard difficulty, verify access on EACH answer
    data = await state.get_data()
    difficulty = data.get('difficulty', 'simple')
    
    if difficulty == 'hard':
        async for session in get_db():
            access_denied = await require_premium_access(
                user_id=user_id,
                session=session,
                resource="quiz_answer",
                action="submit"
            )
            
            if access_denied:
                await callback.message.edit_text(
                    "⚠️ *Access Revoked*\n\n"
                    "Your premium access has been revoked.\n"
                    "Please contact admin if this is an error.",
                    parse_mode='Markdown',
                    reply_markup=MainMenuKeyboard.get_main_menu_inline()
                )
                await state.clear()
                await callback.answer()
                return
    
    # Process answer (rest of logic unchanged)
    # ...
```

---

## 📋 Final Checklist

### Database Changes
- [ ] Run migration script to add constraints
- [ ] Create access_audit_log table
- [ ] Add indexes for fast lookups

### Code Changes
- [ ] Create `access_control_service.py` with `can_access_premium()` function
- [ ] Update `subscription.py` middleware
- [ ] Update `quiz.py` difficulty selection handler
- [ ] Update `admin_payments.py` approval handler
- [ ] Update `answers.py` answer handler

### Testing
- [ ] Test: User with no payment → Blocked
- [ ] Test: User with pending payment → Blocked with "pending" message
- [ ] Test: User with rejected payment → Blocked with "rejected" message
- [ ] Test: User with approved payment + screenshot → Allowed
- [ ] Test: Admin approves without screenshot → Rejected with error
- [ ] Test: Double approval → Rejected
- [ ] Test: Access logging → Verified in database

### Monitoring
- [ ] Set up alerts for:
  - Multiple access denial attempts
  - Approved payments without screenshots
  - Failed approval attempts

---

## 🔄 Rollback Plan

If issues arise, rollback can be done by:
1. Reverting to previous middleware code
2. Removing the new access control checks
3. Using database backup if needed

---

## 📞 Security Contact

For security concerns, contact: @admin

---

**This document is a living document and should be updated as the system evolves.**

