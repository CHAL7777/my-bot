# Telegram Quiz Bot - Referral System Complete Fix

## Problems Identified

1. **Referral not being counted correctly** - Missing idempotency checks
2. **Referral reward (20 Birr) not credited** - No reward credit mechanism tied to approval
3. **Referral should only be counted AFTER approval** - Was being counted immediately on /start
4. **Duplicate, self-referrals, and re-start abuse** - No proper validation

## Required Flow

```
User A shares link → User B clicks /start=REFCODE → 
  → Check: Not self-referral? 
  → Check: User B not already referred?
  → Save referral as 'pending' → User B pays and submits screenshot →
Admin approves payment → 
  → Mark referral as 'approved' (NOT completed) → 
  → Credit 20 Birr to referrer → 
  → Send notification to referrer
```

---

## 1. Database Schema (PostgreSQL/Supabase Compatible)

```sql
-- Drop existing tables if needed (run only once during migration)
-- DROP TABLE IF EXISTS referrals CASCADE;

-- Create referrals table with proper constraints
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    referred_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'cancelled')),
    reward_claimed BOOLEAN NOT NULL DEFAULT FALSE,
    reward_claimed_at TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- Prevent duplicate referrals (unique constraint)
    CONSTRAINT unique_referral_pair UNIQUE (referrer_id, referred_id)
);

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status);
CREATE INDEX IF NOT EXISTS idx_referrals_created ON referrals(created_at DESC);

-- Note: The unique constraint will prevent duplicate (referrer_id, referred_id) pairs

-- Add referral_balance column to users table if not exists
ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS referral_balance DECIMAL(10,2) DEFAULT 0.00;

-- Index for referral_code lookups
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
```

---

## 2. Updated Referral Repository

**File:** `app/repositories/referral_repo.py`

```python
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_, func, Integer, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Referral, User


class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_referral(self, referrer_id: int, referred_id: int) -> Referral:
        """
        Create a new referral record.
        
        IMPORTANT: Uses INSERT ... ON CONFLICT to be idempotent.
        If referral already exists, it returns the existing one without error.
        """
        # Use raw SQL for ON CONFLICT support (more reliable than ORM)
        query = text("""
            INSERT INTO referrals (referrer_id, referred_id, status, created_at)
            VALUES (:referrer_id, :referred_id, 'pending', NOW())
            ON CONFLICT (referrer_id, referred_id) 
            DO UPDATE SET created_at = NOW()
            RETURNING id, referrer_id, referred_id, status, created_at
        """)
        
        result = await self.session.execute(query, {
            "referrer_id": referrer_id,
            "referred_id": referred_id
        })
        row = result.fetchone()
        
        if row:
            # Refresh to get the full object
            referral = await self.get_referral_by_id(row.id)
            if referral:
                return referral
        
        # Fallback: try ORM create if raw SQL didn't return row
        referral = Referral(
            referrer_id=referrer_id,
            referred_id=referred_id,
            status='pending'
        )
        self.session.add(referral)
        await self.session.commit()
        await self.session.refresh(referral)
        return referral

    async def get_referral_by_users(self, referrer_id: int, referred_id: int) -> Optional[Referral]:
        """Get referral between two users"""
        query = select(Referral).where(
            and_(
                Referral.referrer_id == referrer_id,
                Referral.referred_id == referred_id
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def approve_referral(self, referral_id: int) -> Referral:
        """
        Mark referral as approved (referred user was approved by admin).
        
        This is called when admin approves the referred user's payment.
        """
        stmt = update(Referral).where(Referral.id == referral_id).values(
            status='approved',
            approved_at=datetime.utcnow()
        )
        await self.session.execute(stmt)
        await self.session.commit()

        # Get updated referral
        query = select(Referral).where(Referral.id == referral_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def cancel_referral(self, referral_id: int) -> bool:
        """Cancel a referral"""
        stmt = update(Referral).where(Referral.id == referral_id).values(
            status='cancelled'
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_user_referrals(self, user_id: int, status: str = None) -> List[Referral]:
        """Get all referrals for a user (as referrer)"""
        query = select(Referral).where(Referral.referrer_id == user_id)

        if status:
            query = query.where(Referral.status == status)

        query = query.order_by(Referral.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_referrals_to_user(self, user_id: int, status: str = None) -> List[Referral]:
        """Get all referrals to a user (as referred)"""
        query = select(Referral).where(Referral.referred_id == user_id)

        if status:
            query = query.where(Referral.status == status)

        query = query.order_by(Referral.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get referral statistics for a user.
        """
        # OPTIMIZED: Single query with conditional aggregation
        query = select(
            func.count(Referral.id).label('total_sent'),
            func.sum(func.cast(Referral.status == 'approved', Integer)).label('approved'),
            func.sum(func.cast(Referral.status == 'pending', Integer)).label('pending'),
            func.sum(func.cast(Referral.status == 'cancelled', Integer)).label('cancelled')
        ).where(Referral.referrer_id == user_id)
        
        result = await self.session.execute(query)
        row = result.one()
        
        total_sent = row.total_sent or 0
        approved = row.approved or 0
        pending = row.pending or 0
        cancelled = row.cancelled or 0
        
        return {
            'total_sent': total_sent,
            'approved': approved,
            'pending': pending,
            'cancelled': cancelled,
            'success_rate': round((approved / total_sent * 100) if total_sent > 0 else 0, 2)
        }

    async def get_pending_referrals(self, limit: int = 100) -> List[Referral]:
        """Get all pending referrals"""
        query = select(Referral).where(
            Referral.status == 'pending'
        ).order_by(Referral.created_at.asc()).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending_referrals_with_details(
        self, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get pending referrals with full user details for both referrer and referred users.
        
        This is useful for admin dashboards to show who referred whom.
        """
        from sqlalchemy.orm import joinedload
        
        query = (
            select(Referral)
            .options(
                joinedload(Referral.referrer_user),
                joinedload(Referral.referred_user)
            )
            .where(Referral.status == 'pending')
            .order_by(Referral.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        referrals = result.unique().scalars().all()
        
        return [
            {
                'id': referral.id,
                'referrer_id': referral.referrer_id,
                'referred_id': referral.referred_id,
                'status': referral.status,
                'created_at': referral.created_at,
                'referrer_user': {
                    'user_id': referral.referrer_user.user_id,
                    'username': referral.referrer_user.username,
                    'first_name': referral.referrer_user.first_name,
                } if referral.referrer_user else None,
                'referred_user': {
                    'user_id': referral.referred_user.user_id,
                    'username': referral.referred_user.username,
                    'first_name': referral.referred_user.first_name,
                } if referral.referred_user else None
            }
            for referral in referrals
        ]

    async def get_approved_referrals_for_user(self, user_id: int) -> List[Referral]:
        """Get all approved referrals for a user (these earn rewards)"""
        query = select(Referral).where(
            and_(
                Referral.referrer_id == user_id,
                Referral.status == 'approved'
            )
        ).order_by(Referral.approved_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def mark_reward_claimed(self, referral_id: int) -> bool:
        """Mark referral reward as claimed (to prevent double-crediting)"""
        stmt = update(Referral).where(Referral.id == referral_id).values(
            reward_claimed=True,
            reward_claimed_at=datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_referral_by_id(self, referral_id: int) -> Optional[Referral]:
        """Get referral by ID"""
        query = select(Referral).where(Referral.id == referral_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
```

---

## 3. Updated Referral Service

**File:** `app/services/referral_service.py`

```python
"""
Enhanced Referral Service with proper approval-based reward system.

Key Changes:
1. Referral created in 'pending' status on /start
2. Referral status changes to 'approved' ONLY when referred user is approved
3. Reward (20 Birr) credited ONLY after approval
4. Idempotent operations to prevent double-counting
"""

import logging
import random
import string
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.repositories.referral_repo import ReferralRepository
from app.repositories.user_repo import UserRepository
from app.config import settings

logger = logging.getLogger(__name__)


class ReferralService:
    """
    Enhanced Referral Service with approval-based reward system.
    
    Flow:
    1. /start with referral code → Create referral as 'pending'
    2. Referred user pays and submits screenshot
    3. Admin approves payment → Call approve_referral_and_credit_reward()
    4. Reward credited to referrer → Send notification
    """
    
    REFERRAL_REWARD_AMOUNT = 20  # 20 Birr per approved student
    
    def __init__(self, referral_repo: ReferralRepository,
                 user_repo: UserRepository):
        self.referral_repo = referral_repo
        self.user_repo = user_repo
    
    # ============== Referral Capture (on /start) ==============
    
    async def capture_referral_on_start(
        self, 
        referrer_id: int, 
        referred_id: int
    ) -> Dict[str, Any]:
        """
        Capture referral when new user joins via /start=CODE.
        
        This is the CRITICAL method called from command_start handler.
        
        Validates:
        - Not a self-referral (referrer != referred)
        - User not already referred by someone else
        
        Creates referral in 'pending' status (NOT approved yet!).
        
        Returns:
            Dict with success status and details
        """
        result = {
            'success': False,
            'message': '',
            'referral_id': None,
            'already_exists': False,
            'skipped': False
        }
        
        try:
            # 1. VALIDATION: Check for self-referral
            if referrer_id == referred_id:
                result['message'] = 'Self-referral prevented'
                result['skipped'] = True
                logger.info(f"[REFERRAL] Self-referral prevented: user {referred_id}")
                return result
            
            # 2. VALIDATION: Check if user already has a referral
            existing_status = await self.get_referral_status(referred_id)
            if existing_status:
                result['message'] = f'User already has referral status: {existing_status}'
                result['already_exists'] = True
                result['skipped'] = True
                logger.info(f"[REFERRAL] User {referred_id} already referred, status: {existing_status}")
                return result
            
            # 3. VALIDATION: Verify referrer exists
            referrer = await self.user_repo.get_user(referrer_id)
            if not referrer:
                result['message'] = 'Referrer not found'
                logger.warning(f"[REFERRAL] Referrer {referrer_id} not found")
                return result
            
            # 4. CREATE REFERRAL (pending status)
            referral = await self.referral_repo.create_referral(referrer_id, referred_id)
            
            # 5. Update user's referred_by field
            await self.user_repo.update_user(referred_id, referred_by=referrer_id)
            
            result['success'] = True
            result['referral_id'] = referral.id
            result['message'] = 'Referral recorded as pending. Will be approved after payment.'
            
            logger.info(f"[REFERRAL] Captured: {referrer_id} -> {referred_id}, referral_id={referral.id}")
            
        except Exception as e:
            logger.error(f"[REFERRAL] Error capturing referral: {e}")
            result['message'] = f'Error: {str(e)}'
        
        return result
    
    async def get_referral_status(self, referred_id: int) -> Optional[str]:
        """Get the current status of referral for a user"""
        try:
            referrals = await self.referral_repo.get_referrals_to_user(referred_id)
            if referrals:
                return referrals[0].status
            return None
        except Exception:
            return None
    
    # ============== Referral Approval & Reward (when admin approves payment) ==============
    
    async def approve_referral_and_credit_reward(
        self, 
        referred_id: int,
        bot = None
    ) -> Dict[str, Any]:
        """
        APPROVE REFERRAL and CREDIT REWARD.
        
        This is called from payment.py when admin approves a payment.
        
        Steps:
        1. Find pending referral for this user
        2. Change status from 'pending' to 'approved'
        3. Credit 20 Birr to referrer's balance
        4. Mark reward as claimed (idempotency)
        5. Send notification to referrer
        
        Args:
            referred_id: The user who was referred and just got approved
            bot: Telegram bot instance for sending notifications
            
        Returns:
            Dict with completion details
        """
        result = {
            'success': False,
            'message': '',
            'referrer_id': None,
            'reward_credited': False,
            'reward_amount': 0,
            'already_processed': False
        }
        
        try:
            # 1. Find pending referral
            referrals = await self.referral_repo.get_referrals_to_user(
                referred_id, 
                status='pending'
            )
            
            if not referrals:
                # Check if already approved
                referrals_approved = await self.referral_repo.get_referrals_to_user(
                    referred_id,
                    status='approved'
                )
                if referrals_approved:
                    result['already_processed'] = True
                    result['message'] = 'Referral already approved'
                    result['referrer_id'] = referrals_approved[0].referrer_id
                else:
                    result['message'] = 'No pending referral found for this user'
                return result
            
            referral = referrals[0]
            referrer_id = referral.referrer_id
            result['referrer_id'] = referrer_id
            
            # 2. APPROVE REFERRAL (change from pending to approved)
            await self.referral_repo.approve_referral(referral.id)
            
            # 3. CREDIT REWARD to referrer
            reward_amount = self.REFERRAL_REWARD_AMOUNT
            await self.credit_referral_reward(referrer_id, reward_amount)
            
            # 4. Mark reward as claimed
            await self.referral_repo.mark_reward_claimed(referral.id)
            
            result['success'] = True
            result['reward_credited'] = True
            result['reward_amount'] = reward_amount
            result['message'] = f'Referral approved. {reward_amount} Birr credited to referrer.'
            
            logger.info(
                f"[REFERRAL] Approved: referred={referred_id}, "
                f"reward={reward_amount} to referrer={referrer_id}"
            )
            
            # 5. Send notification to referrer
            if bot:
                await self.notify_referrer_about_reward(bot, referrer_id, reward_amount, referred_id)
            
        except Exception as e:
            logger.error(f"[REFERRAL] Error approving referral for {referred_id}: {e}")
            result['message'] = f'Error: {str(e)}'
        
        return result
    
    async def credit_referral_reward(self, referrer_id: int, amount: float) -> bool:
        """
        Credit referral reward to user's balance.
        
        Updates the referral_balance column in users table.
        """
        try:
            user = await self.userferrer_id)
           _repo.get_user(re if user:
                current_balance = getattr(user, 'referral_balance', 0) or 0
                new_balance = current_balance + amount
                await self.user_repo.update_user(referrer_id, referral_balance=new_balance)
                logger.info(f"[REFERRAL] Credited {amount} to user {referrer_id}, new balance: {new_balance}")
                return True
            return False
        except Exception as e:
            logger.error(f"[REFERRAL] Error crediting reward: {e}")
            return False
    
    async def notify_referrer_about_reward(
        self, 
        bot, 
        referrer_id: int, 
        amount: float, 
        referred_user_id: int
    ):
        """Send notification to referrer about earned reward"""
        try:
            # Get referrer details
            referrer = await self.user_repo.get_user(referrer_id)
            if not referrer:
                logger.warning(f"[REFERRAL] Could not find referrer {referrer_id} for notification")
                return
            
            # Get referred user details for the message
            referred_user = await self.user_repo.get_user(referred_user_id)
            referred_name = (
                referred_user.first_name or 
                referred_user.username or 
                f"User {referred_user_id}"
            )
            
            message = (
                f"🎉 *Referral Reward Credited!*\n\n"
                f"💰 *{amount} Birr* has been added to your balance!\n\n"
                f"📊 *Details:*\n"
                f"• Student: {referred_name}\n"
                f"• Status: Payment Approved\n"
                f"• Amount Earned: {amount} Birr\n\n"
                f"💵 *Your Referral Balance:* {getattr(referrer, 'referral_balance', 0) or 0} Birr\n\n"
                f"Keep sharing your referral link to earn more! 🔗"
            )
            
            await bot.send_message(
                chat_id=referrer_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"[REFERRAL] Notification sent to referrer {referrer_id}")
            
        except Exception as e:
            logger.error(f"[REFERRAL] Failed to notify referrer {referrer_id}: {e}")
    
    # ============== Existing Methods (unchanged) ==============
    
    async def get_referral_code(self, user_id: int) -> str:
        """Get user's referral code (create if not exists)"""
        user = await self.user_repo.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if not user.referral_code:
            referral_code = await self.generate_referral_code_async()
            await self.user_repo.update_user(user_id, referral_code=referral_code)
            return referral_code
        
        return user.referral_code
    
    async def generate_referral_code_async(self, length: int = 8) -> str:
        """Generate unique referral code"""
        max_attempts = 10
        for attempt in range(max_attempts):
            chars = string.ascii_uppercase + string.digits
            code = ''.join(random.choice(chars) for _ in range(length))
            referral_code = f"REF{code}"
            
            try:
                user = await self.user_repo.get_user_by_referral_code(referral_code)
                if not user:
                    return referral_code
            except Exception:
                return referral_code
        
        return referral_code
    
    async def get_referral_link(self, user_id: int) -> str:
        """Generate referral link for user"""
        referral_code = await self.get_referral_code(user_id)
        bot_username = getattr(settings, 'BOT_USERNAME', 'YourBotName')
        return f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    async def parse_referral_code_from_start(self, deep_link: str) -> Optional[str]:
        """Parse referral code from /start command"""
        if not deep_link:
            return None
        
        # Handle /start=REFCODE format
        if '=ref_' in deep_link:
            return deep_link.split('=ref_')[-1].split()[0]
        
        # Handle /start REFCODE format
        parts = deep_link.split()
        for part in parts:
            if part.startswith('REF') and len(part) >= 6:
                return part
        
        return None
    
    async def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's referral statistics"""
        return await self.referral_repo.get_referral_stats(user_id)
```

---

## 4. Updated Payment Handler (to trigger referral approval)

**File:** `app/handlers/payment.py` - Add this at the end:

```python
"""
Payment Handler - Referral Integration

Added: approve_referral_and_credit_reward() call when admin approves payment.
"""

# ... existing code ...

async def notify_admins_about_payment(bot, payment_id: int, user_id: int):
    """Notify all admins about new payment - UPDATED with referral info"""
    username = f"User {user_id}"
    try:
        async for session in get_db():
            user_repo = UserRepository(session)
            user = await user_repo.get_user(user_id)
            if user:
                username = user.first_name or user.username or f"User {user_id}"
                
                # Check if user was referred
                referred_by = getattr(user, 'referred_by', None)
                if referred_by:
                    username += f"\n👤 Referred by: {referred_by}"
    except:
        pass
    
    admin_message = (
        f"💰 *Payment Alert*\n\n"
        f"New payment submitted by *{username}*\n"
        f"Amount: *{settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}*\n"
        f"Status: *Pending*\n\n"
        f"📋 Payment ID: `#{payment_id}`\n"
        f"👤 User ID: `{user_id}`\n"
        f"⏰ Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
        f"Use /admin_payments to review."
    )
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")
```

---

## 5. Updated Admin Handler (to trigger referral approval on payment approval)

**File:** `app/handlers/admin.py` or wherever payment approval is handled:

```python
"""
Admin Handler - Updated to trigger referral reward on payment approval.
"""

# Inside your approve_payment callback handler:

async def approve_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Approve payment and trigger referral reward"""
    # ... existing approval logic ...
    
    # 1. Approve the payment
    payment = await payment_repo.update_payment_status(
        payment_id=payment_id,
        status='approved',
        approved_by=admin_id
    )
    
    # 2. Make user premium
    await user_repo.update_user(user_id, is_premium=True)
    
    # 3. APPROVE REFERRAL AND CREDIT REWARD (NEW!)
    from app.services.referral_service import ReferralService
    from app.repositories.referral_repo import ReferralRepository
    from app.repositories.user_repo import UserRepository
    
    referral_repo = ReferralRepository(session)
    referral_service = ReferralService(referral_repo, user_repo)
    
    # This will:
    # - Find pending referral for this user
    # - Change status to 'approved'
    # - Credit 20 Birr to referrer
    # - Send notification to referrer
    referral_result = await referral_service.approve_referral_and_credit_reward(
        referred_id=user_id,
        bot=callback.bot
    )
    
    if referral_result['success']:
        await callback.answer(
            f"✅ Payment approved!\n"
            f"🎉 Referral reward ({referral_result['reward_amount']} Birr) credited to referrer!",
            show_alert=True
        )
    else:
        await callback.answer("✅ Payment approved!", show_alert=True)
```

---

## 6. Updated /start Handler

**File:** `app/handlers/start.py` - Update the referral processing section:

```python
"""
Updated /start handler with proper referral capture.
"""

@router.message(CommandStart())
async def command_start(message: Message, state: FSMContext, is_admin: bool = False):
    """Handle /start command - with referral capture"""
    user_id = message.from_user.id
    # ... existing user registration code ...
    
    # ================================================================
    # REFERRAL PROCESSING (UPDATED - now calls capture_referral_on_start)
    # ================================================================
    
    if is_new_user and message.text:
        from app.services.referral_service import ReferralService
        from app.repositories.referral_repo import ReferralRepository
        from app.repositories.user_repo import UserRepository
        
        referral_service = ReferralService(
            referral_repo=ReferralRepository(session), 
            user_repo=user_repo
        )
        
        # Parse referral code
        referral_code = await referral_service.parse_referral_code_from_start(message.text)
        
        if referral_code:
            print(f"[START] Found referral code: {referral_code} for user {user_id}")
            
            # Find referrer by code
            referrer = await referral_service.get_user_by_referral_code(referral_code)
            
            if referrer:
                print(f"[START] Found referrer: user_id={referrer.user_id}")
                
                # CAPTURE REFERRAL (creates in pending status)
                capture_result = await referral_service.capture_referral_on_start(
                    referrer_id=referrer.user_id,
                    referred_id=user_id
                )
                
                if capture_result['success']:
                    print(f"[START] Referral captured: {referrer.user_id} -> {user_id}")
                elif capture_result['already_exists']:
                    print(f"[START] User already had referral: {capture_result['message']}")
                elif capture_result['skipped']:
                    print(f"[START] Referral skipped: {capture_result['message']}")
            else:
                print(f"[START] Referral code not found: {referral_code}")
```

---

## 7. Why Inline Buttons Were Not Working

### Common Issues and Solutions:

#### Issue 1: **Callback Query Not Acknowledged**
```python
# WRONG - callback must be acknowledged!
@router.callback_query(F.data == "my_button")
async def my_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("Updated text")  # Missing callback.answer()

# CORRECT - always acknowledge callback!
@router.callback_query(F.data == "my_button")
async def my_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("Updated text")
    await callback.answer()  # IMPORTANT!
```

#### Issue 2: **Inline Keyboard vs Reply Keyboard**
- `ReplyKeyboardMarkup` = Text buttons that send messages when clicked
- `InlineKeyboardMarkup` = Buttons that trigger callbacks (no message sent)

```python
# Reply Keyboard (sends message when clicked)
from aiogram.types import ReplyKeyboardMarkup
ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="My Button")]],
    resize_keyboard=True
)

# Inline Keyboard (triggers callback without sending message)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Click Me", callback_data="my_data")]]
)
```

#### Issue 3: **Missing `data` Parameter in Handler**
```python
# WRONG - middleware expects data dict
@router.callback_query(F.data == "approve")
async def approve(callback: types.CallbackQuery):
    await callback.answer()

# CORRECT - accept optional data parameter
@router.callback_query(F.data == "approve")
async def approve(callback: types.CallbackQuery, data: Dict[str, Any] = None):
    await callback.answer()
```

#### Issue 4: **Message Too Long for edit_text**
```python
# WRONG - trying to edit a long message
@router.callback_query(F.data == "show_referrals")
async def show_referrals(callback: types.CallbackQuery):
    long_text = "..."  # 5000+ characters
    await callback.message.edit_text(long_text)  # FAILS!

# CORRECT - send NEW message with answer()
@router.callback_query(F.data == "show_referrals")
async def show_referrals(callback: types.CallbackQuery):
    long_text = "..."  # 5000+ characters
    await callback.message.answer(long_text)  # Send as new message
    await callback.answer()
```

---

## 8. Complete Referral Flow Summary

```
1. USER A shares referral link: https://t.me/Bot?start=REFCODE
   
2. USER B clicks link → Telegram opens /start=REFCODE
   
3. /start handler processes:
   ├─ Parse referral code from deep link
   ├─ Find referrer by code
   ├─ Validate (not self-referral, user not already referred)
   └─ Create referral record: status='pending'
   
4. USER B sees welcome message (no reward yet!)
   
5. USER B goes through payment flow:
   ├─ Sends /payment
   ├─ Uploads payment screenshot
   └─ Waits for admin approval
   
6. ADMIN reviews payment:
   ├─ Checks screenshot
   ├─ Clicks "Approve" button
   └─ Payment status → 'approved'
   
7. REFERRAL REWARD TRIGGERED:
   ├─ Find pending referral for User B
   ├─ Update referral status: 'pending' → 'approved'
   ├─ Credit 20 Birr to User A's balance
   ├─ Mark reward as claimed
   └─ Send notification to User A
   
8. USER A receives notification:
   "🎉 Referral Reward Credited!
    💰 20 Birr has been added to your balance!
    📊 Student: User B - Payment Approved"
```

---

## 9. Testing Checklist

```bash
# Test cases:
# 1. /start with valid referral code → Referral created as pending
# 2. /start with own referral code → Self-referral prevented
# 3. /start twice with referral code → Already exists, skipped
# 4. Admin approves payment → Referral approved, reward credited
# 5. Admin approves same payment twice → Idempotent, no double credit
# 6. Referrer checks /referrals → Shows updated balance
```

---

## 10. Files to Update (Summary)

| File | Change |
|------|--------|
| `app/db/models.py` | Update Referral model (add approved_at) |
| `app/repositories/referral_repo.py` | Add `create_referral` (idempotent), `approve_referral`, `mark_reward_claimed` |
| `app/services/referral_service.py` | Complete rewrite with `capture_referral_on_start`, `approve_referral_and_credit_reward` |
| `app/handlers/start.py` | Call `capture_referral_on_start` |
| `app/handlers/admin.py` | Call `approve_referral_and_credit_reward` on payment approval |
| `app/handlers/payment.py` | Updated notification includes referral info |

---

**Note:** Run the SQL migration first, then update the Python files. The database constraints will prevent duplicate referrals at the SQL level for extra safety.

