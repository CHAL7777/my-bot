from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import logging

from app.db.models import Payment, User

logger = logging.getLogger(__name__)

class PaymentRepository:
    """
    Repository for payment operations with one-time payment model support.
    
    Features:
    - Atomic transactions for payment approval
    - Idempotency checks to prevent duplicate processing
    - Integration with User.approved and User.is_premium flags
    - Safe attribute access (handles missing columns gracefully)
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_payment(
        self, 
        user_id: int, 
        amount: float, 
        screenshot_file_id: str = None,
        transaction_id: str = None, 
        notes: str = None,
        subscription_days: int = None
    ) -> Payment:
        """
        Create new payment record with safety checks.
        
        Prevents duplicate payments by checking for existing pending payments.
        
        Args:
            user_id: Telegram user ID
            amount: Payment amount
            screenshot_file_id: Telegram file ID for screenshot
            transaction_id: Payment transaction ID from user
            notes: Additional notes
            subscription_days: Subscription duration in days
            
        Returns:
            Created Payment object
            
        Raises:
            Exception if user already has pending payment
        """
        # Check for existing pending payment first
        existing_pending = await self.get_pending_payment_for_user(user_id)
        if existing_pending:
            raise Exception(
                f"User {user_id} already has a pending payment (ID: #{existing_pending.payment_id})"
            )
        
        payment = Payment(
            user_id=user_id,
            amount=amount,
            screenshot_file_id=screenshot_file_id,
            transaction_id=transaction_id,
            notes=notes,
            subscription_days=subscription_days,
            status='pending'
        )
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment
    
    async def update_payment_path(self, payment_id: int, file_path: str) -> bool:
        """
        Update payment with local screenshot path.
        
        Args:
            payment_id: Payment ID
            file_path: Local file path
            
        Returns:
            True if updated successfully
        """
        try:
            await self.session.execute(
                update(Payment)
                .where(Payment.payment_id == payment_id)
                .values(screenshot_file_path=file_path)
            )
            await self.session.commit()
            return True
        except Exception as e:
            logger.warning(f"Error updating payment path: {e}")
            await self.session.rollback()
            return False
    
    async def get_pending_payment_for_user(self, user_id: int) -> Optional[Payment]:
        """Get pending payment for a specific user (for idempotency check)"""
        query = select(Payment).where(
            and_(
                Payment.user_id == user_id,
                Payment.status == 'pending'
            )
        ).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID"""
        query = select(Payment).where(Payment.payment_id == payment_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_payment_with_user(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get payment with user details for admin review.
        
        Returns dict with payment and user info for display.
        """
        payment = await self.get_payment(payment_id)
        if not payment:
            return None
        
        user = await self.session.get(User, payment.user_id)
        
        return {
            'payment': payment,
            'user': user,
            'user_id': payment.user_id,
            'username': user.username if user else None,
            'first_name': user.first_name if user else "Unknown",
            'last_name': user.last_name if user else None,
            'created_at': payment.created_at,
            'amount': payment.amount,
            'status': payment.status,
            'screenshot_file_id': payment.screenshot_file_id,
            'screenshot_file_path': payment.screenshot_file_path,
            'rejected_reason': payment.rejected_reason,
            'approved_by': payment.approved_by,
            'approved_at': payment.approved_at
        }
    
    async def get_user_payments(self, user_id: int) -> List[Payment]:
        """Get all payments for a user"""
        query = select(Payment).where(
            Payment.user_id == user_id
        ).order_by(desc(Payment.created_at))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_pending_payments(self, limit: int = 50) -> List[Payment]:
        """Get pending payments for admin approval"""
        query = select(Payment).where(
            Payment.status == 'pending'
        ).order_by(asc(Payment.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def _create_subscription(self, user_id: int, payment_id: int, 
                                   start_date: datetime, end_date: datetime,
                                   is_trial: bool = False):
        # Subscriptions removed in lifetime model. Use User.is_premium instead.
        raise NotImplementedError("Subscriptions are deprecated for lifetime premium model")
    
    async def approve_payment(self, payment_id: int, admin_id: int) -> Optional[Payment]:
        """
        Approve a payment with atomic transaction.
        
        Idempotency: Only processes if status is 'pending'.
        Prevents duplicate approvals.
        
        Actions:
        1. Verify payment exists and is pending
        2. Update payment status to 'approved'
        3. Set approved_by and approved_at
        4. Grant lifetime premium to user (User.is_premium = True, User.approved = True)
        
        🚨 CRITICAL: Always commit and verify the user.approved = 1 update.
        """
        # Get payment
        payment = await self.get_payment(payment_id)
        
        # IDEMPOTENCY CHECK: Only process if pending
        if not payment:
            raise Exception(f"Payment #{payment_id} not found")
        
        if payment.status != 'pending':
            raise Exception(
                f"Payment #{payment_id} has already been "
                f"{payment.status}. Cannot re-approve."
            )
        
        try:
            now = datetime.utcnow()

            # Update payment as approved
            payment.status = 'approved'
            payment.approved_by = admin_id
            payment.approved_at = now

            # Grant lifetime premium to user - ALWAYS set approved = 1
            # 🚨 CRITICAL: This is the main fix - always set approved regardless of is_premium
            user = await self.session.get(User, payment.user_id)
            if user:
                user.is_premium = True
                user.approved = True  # 🚨 CRITICAL: Always set approved = 1
                user.updated_at = now
                self.session.add(user)
                
                logger.info(
                    f"✅ APPROVAL: Setting user_id={user.user_id} "
                    f"is_premium=True, approved=True for payment #{payment_id}"
                )

            await self.session.commit()
            await self.session.refresh(payment)
            
            # 🚨 CRITICAL VERIFICATION: Re-fetch user to verify approved = 1
            if user:
                await self.session.refresh(user)
                logger.info(
                    f"🔍 VERIFIED: user_id={user.user_id} approved={user.approved}, "
                    f"is_premium={user.is_premium} after commit"
                )
                
                # Double-check with raw SQL to bypass any ORM caching
                from sqlalchemy import text
                result = await self.session.execute(
                    text("SELECT approved, is_premium FROM users WHERE user_id = :user_id"),
                    {"user_id": user.user_id}
                )
                row = result.fetchone()
                if row:
                    db_approved, db_premium = row
                    logger.info(
                        f"🔍 RAW_SQL_VERIFY: user_id={user.user_id} "
                        f"approved={db_approved}, is_premium={db_premium}"
                    )
                    
                    # If raw SQL shows approved=0 but ORM shows 1, force update
                    if db_approved == 0:
                        logger.error(
                            f"🚨 CRITICAL: Commit succeeded but DB still shows approved=0! "
                            f"Force-updating user_id={user.user_id}"
                        )
                        await self.session.execute(
                            text("UPDATE users SET approved = 1 WHERE user_id = :user_id"),
                            {"user_id": user.user_id}
                        )
                        await self.session.commit()
                        logger.info(f"✅ FORCE UPDATE: user_id={user.user_id} approved=1")

            return payment
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ APPROVAL FAILED: Payment #{payment_id}, error: {str(e)}")
            raise Exception(f"Failed to approve payment: {str(e)}")
    
    async def reject_payment(self, payment_id: int, admin_id: int, reason: str) -> Optional[Payment]:
        """
        Reject a payment with validation.
        
        Idempotency: Only processes if status is 'pending'.
        
        Args:
            payment_id: Payment ID to reject
            admin_id: Admin who rejected
            reason: Reason for rejection (required)
        """
        if not reason or len(reason.strip()) < 5:
            raise Exception("Rejection reason must be at least 5 characters")
        
        payment = await self.get_payment(payment_id)
        
        # IDEMPOTENCY CHECK: Only process if pending
        if not payment:
            raise Exception(f"Payment #{payment_id} not found")
        
        if payment.status != 'pending':
            raise Exception(
                f"Payment #{payment_id} has already been "
                f"{payment.status}. Cannot re-reject."
            )
        
        try:
            payment.status = 'rejected'
            payment.approved_by = admin_id
            payment.approved_at = datetime.utcnow()
            payment.rejected_reason = reason.strip()
            
            await self.session.commit()
            await self.session.refresh(payment)
            
            return payment
            
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to reject payment: {str(e)}")
    
    async def get_active_subscription(self, user_id: int):
        """
        Get user's active subscription.
        
        Note: Subscriptions are deprecated. For lifetime premium model, 
        use User.is_premium instead.
        """
        # Return None as subscriptions are deprecated
        return None
    
    async def create_trial_subscription(self, user_id: int, trial_days: int):
        """
        Create trial subscription for new user.
        
        Note: Trial subscriptions are deprecated. Use User.is_premium directly.
        """
        raise NotImplementedError("Trial subscriptions are deprecated for lifetime premium model")
    
    async def check_subscription_expiry(self):
        """
        Check and update expired subscriptions.
        
        Note: Subscription expiry checking is deprecated. 
        For lifetime premium model, premium status never expires.
        """
        return 0
    
    async def get_revenue_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get revenue statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Total revenue
        query = select(
            func.sum(Payment.amount),
            func.count(Payment.payment_id)
        ).where(
            and_(
                Payment.status == 'approved',
                Payment.created_at >= cutoff_date
            )
        )
        result = await self.session.execute(query)
        row = result.first()
        total_revenue = row[0] or 0
        payment_count = row[1] or 0
        
        # Daily revenue trend
        query = select(
            func.date(Payment.created_at).label('date'),
            func.sum(Payment.amount).label('daily_revenue'),
            func.count(Payment.payment_id).label('daily_count')
        ).where(
            and_(
                Payment.status == 'approved',
                Payment.created_at >= cutoff_date
            )
        ).group_by(func.date(Payment.created_at)).order_by(asc('date'))
        
        result = await self.session.execute(query)
        daily_trend = []
        for row in result.all():
            daily_trend.append({
                'date': row.date,
                'revenue': row.daily_revenue or 0,
                'count': row.daily_count or 0
            })
        
        return {
            'total_revenue': total_revenue,
            'payment_count': payment_count,
            'avg_revenue_per_payment': round(total_revenue / payment_count, 2) if payment_count > 0 else 0,
            'daily_trend': daily_trend
        }
