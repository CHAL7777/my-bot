"""
Payment Service - Redesigned for Safe Payment Handling

This service handles payment operations with:
- Safe attribute access (handles missing columns gracefully)
- Proper error handling for all edge cases
- Idempotent operations (prevents duplicate processing)
- Clear user-friendly error messages

Payment Model:
- One-time lifetime payment: User pays once for lifetime access
- Screenshot-based: Users upload payment screenshot for admin review
- Admin approval required: Admin must approve before access is granted
"""

import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.repositories.referral_repo import ReferralRepository
from app.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Payment Service for handling one-time payment model.
    
    Features:
    - Safe handling of missing columns and records
    - Idempotent payment approval (prevents duplicate processing)
    - Clear error messages for users
    - Integration with User.is_premium flag for lifetime access
    """
    
    def __init__(self, payment_repo: PaymentRepository, user_repo: UserRepository):
        self.payment_repo = payment_repo
        self.user_repo = user_repo
    
    # ============== Payment Initiation ==============
    
    async def initiate_payment(self, user_id: int, subscription_days: int = None) -> Dict[str, Any]:
        """
        Initiate payment process with safety checks.
        
        This method checks:
        1. User exists in database
        2. User is not already approved (one-time payment rule)
        3. User doesn't have an active subscription
        4. No pending payments exist
        
        Args:
            user_id: Telegram user ID
            subscription_days: Number of days for subscription (None for lifetime)
            
        Returns:
            Dict with payment details and instructions
            
        Raises:
            Exception with user-friendly message if payment cannot be initiated
        """
        # Get user
        user = await self.user_repo.get_user(user_id)
        
        if not user:
            raise Exception(
                "❌ User account not found.\n\n"
                "Please start a conversation with the bot first using /start."
            )
        
        # Calculate amount based on subscription type
        amount = self._calculate_amount(subscription_days)
        
        # Check if user is already premium - ONE-TIME PAYMENT RULE
        is_premium = getattr(user, 'is_premium', False) or getattr(user, 'approved', False)
        if is_premium:
            raise Exception(
                "✅ You've already unlocked full access!\n\n"
                "Your account is approved and you have access to all quiz levels. "
                "No additional payment is needed.\n\n"
                "Use /quiz to start learning!"
            )
        
        # Check for active subscription (subscription-based model)
        try:
            active_sub = await self.payment_repo.get_active_subscription(user_id)
            if active_sub:
                end_date = getattr(active_sub, 'end_date', None)
                end_date_str = end_date.strftime('%d %b %Y') if end_date else 'unknown'
                raise Exception(
                    f"📅 You already have an active subscription!\n\n"
                    f"Your subscription is valid until {end_date_str}. "
                    "No additional payment is needed."
                )
        except NotImplementedError:
            # Subscription system not implemented, ignore
            pass
        
        # Check for existing pending payments
        try:
            user_payments = await self.payment_repo.get_user_payments(user_id)
            pending_payments = [p for p in user_payments if p.status == 'pending']
            
            if pending_payments:
                pending = pending_payments[0]
                raise Exception(
                    "⏳ Payment Already Pending\n\n"
                    f"You have a payment (ID: #{pending.payment_id}) waiting for review.\n"
                    "Please wait for admin approval before submitting a new payment.\n\n"
                    "Contact @admin if you need assistance."
                )
        except Exception as e:
            # If payment repo fails, log but continue (might be schema issue)
            logger.warning(f"Error checking pending payments for user {user_id}: {e}")
        
        return {
            'amount': amount,
            'currency': settings.CURRENCY,
            'subscription_days': subscription_days,
            'instructions': self._get_payment_instructions(amount, subscription_days)
        }
    
    def _calculate_amount(self, subscription_days: Optional[int]) -> float:
        """
        Calculate payment amount based on subscription type.
        
        Args:
            subscription_days: Number of days (None for lifetime one-time payment)
            
        Returns:
            Amount in local currency
        """
        # Lifetime one-time payment
        if subscription_days is None:
            return float(settings.ONE_TIME_PRICE)
        
        # Subscription-based pricing
        if subscription_days == 30:
            return float(settings.SUBSCRIPTION_PRICE_30_DAYS)
        elif subscription_days == 90:
            return float(settings.SUBSCRIPTION_PRICE_90_DAYS)
        else:
            # Default to one-time price for unknown subscription types
            return float(settings.ONE_TIME_PRICE)
    
    def _get_payment_instructions(self, amount: float, subscription_days: Optional[int]) -> str:
        """
        Generate payment instructions.
        
        Args:
            amount: Payment amount
            subscription_days: Subscription duration in days (None for lifetime)
            
        Returns:
            Formatted payment instructions string
        """
        if subscription_days is None:
            # Lifetime payment instructions
            instructions = f"""
💰 *One-time Payment • Lifetime Access* 💰

💵 Amount: {amount} {settings.CURRENCY}

Please follow these steps:
1. Send {amount} {settings.CURRENCY} via one of the accepted methods
2. Take a clear screenshot of the payment confirmation
3. Upload the screenshot here so admins can verify

Payment methods:
• Bank Transfer: Account details provided in the UI
• Mobile payments (Telebirr / UPI equivalent)

*Note:* Include your User ID in the payment description.
            """.strip()
        else:
            # Subscription payment instructions
            instructions = f"""
💰 *Subscription Payment* 💰

💵 Amount: {amount} {settings.CURRENCY}
📅 Duration: {subscription_days} days

Please follow these steps:
1. Send {amount} {settings.CURRENCY} via one of the accepted methods
2. Take a clear screenshot of the payment confirmation
3. Upload the screenshot here so admins can verify

Payment methods:
• Bank Transfer: Account details provided in the UI
• Mobile payments (Telebirr / UPI equivalent)

*Note:* Include your User ID in the payment description.
            """.strip()
        
        return instructions
    
    # ============== Payment Status ==============
    
    async def get_payment_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's payment status with safe attribute access.
        
        This method handles:
        - Missing user records
        - Missing columns (uses getattr with defaults)
        - No payment history
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict with payment status information
        """
        user = await self.user_repo.get_user(user_id)
        
        # Default response for non-existent user
        if not user:
            return {
                'is_premium': False,
                'has_active_subscription': False,
                'subscription': None,
                'pending_payments': 0,
                'payment_history': [],
                'error': 'user_not_found'
            }
        
        # Check premium status safely
        is_premium = getattr(user, 'is_premium', False) or getattr(user, 'approved', False)
        
        # Build subscription info for premium users
        subscription = None
        if is_premium:
            # Get the latest approved payment for reference
            try:
                user_payments = await self.payment_repo.get_user_payments(user_id)
                approved_payments = [p for p in user_payments if p.status == 'approved']
                latest_payment = approved_payments[0] if approved_payments else None
                
                subscription = {
                    'start_date': getattr(latest_payment, 'approved_at', None) or user.created_at,
                    'end_date': None,  # Lifetime - no end date
                    'days_left': None,  # Lifetime - unlimited
                    'is_trial': False,
                    'is_lifetime': True
                }
            except Exception as e:
                logger.warning(f"Error getting payment history for user {user_id}: {e}")
                subscription = {
                    'start_date': user.created_at,
                    'end_date': None,
                    'days_left': None,
                    'is_trial': False,
                    'is_lifetime': True
                }
        
        # Get pending payments count
        pending_count = 0
        payment_history = []
        try:
            user_payments = await self.payment_repo.get_user_payments(user_id)
            pending_payments = [p for p in user_payments if p.status == 'pending']
            pending_count = len(pending_payments)
            
            # Build payment history with safe attribute access
            payment_history = []
            for p in user_payments[:10]:  # Last 10 payments
                payment_history.append({
                    'payment_id': p.payment_id,
                    'amount': getattr(p, 'amount', 0),
                    'subscription_days': getattr(p, 'subscription_days', None),
                    'status': p.status,
                    'created_at': p.created_at,
                    'approved_at': getattr(p, 'approved_at', None),
                    'rejected_reason': getattr(p, 'rejected_reason', None)
                })
        except Exception as e:
            logger.warning(f"Error getting payments for user {user_id}: {e}")
            # Continue with empty payment history
        
        return {
            'is_premium': is_premium,
            'has_active_subscription': is_premium,  # For backward compatibility
            'subscription': subscription,
            'pending_payments': pending_count,
            'payment_history': payment_history
        }
    
    # ============== Save Payment Screenshot ==============
    
    async def save_payment_screenshot(
        self, 
        user_id: int, 
        file_id: str, 
        file_path: str,
        subscription_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save payment screenshot and create payment record.
        
        Safety checks:
        - User exists
        - User doesn't have active subscription
        - No existing pending payments
        
        Args:
            user_id: Telegram user ID
            file_id: Telegram file ID for the screenshot
            file_path: Local file path where screenshot is saved
            subscription_days: Subscription duration in days
            
        Returns:
            Dict with payment details
            
        Raises:
            Exception with user-friendly message on failure
        """
        # Calculate amount
        amount = self._calculate_amount(subscription_days)
        
        # Verify user exists
        user = await self.user_repo.get_user(user_id)
        if not user:
            raise Exception(
                "❌ User account not found.\n\n"
                "Please restart the bot with /start."
            )
        
        # Check for active subscription
        try:
            active_sub = await self.payment_repo.get_active_subscription(user_id)
            if active_sub:
                raise Exception(
                    "⚠️ You already have an active subscription!\n\n"
                    "Please wait for it to expire before making a new payment."
                )
        except NotImplementedError:
            pass
        
        # Check for existing pending payments
        try:
            user_payments = await self.payment_repo.get_user_payments(user_id)
            if any(p.status == 'pending' for p in user_payments):
                raise Exception(
                    "⏳ You already have a pending payment!\n\n"
                    "Please wait for admin approval before submitting a new one."
                )
        except Exception as e:
            logger.warning(f"Error checking pending payments: {e}")
        
        # Create payment record
        try:
            payment = await self.payment_repo.create_payment(
                user_id=user_id,
                amount=amount,
                screenshot_file_id=file_id,
                subscription_days=subscription_days
            )
        except Exception as e:
            raise Exception(
                f"❌ Failed to create payment record.\n\n"
                f"Error: {str(e)}\n\n"
                "Please try again or contact support."
            )
        
        # Save screenshot to local storage
        try:
            local_path = await self._save_screenshot_locally(file_path, payment.payment_id)
            # Update payment with local path
            await self.payment_repo.update_payment_path(payment.payment_id, local_path)
        except Exception as e:
            logger.warning(f"Error saving screenshot locally: {e}")
            # Continue without local save - not critical
        
        return {
            'payment_id': payment.payment_id,
            'amount': amount,
            'subscription_days': subscription_days,
            'status': payment.status,
            'created_at': payment.created_at
        }
    
    async def _save_screenshot_locally(self, file_path: str, payment_id: int) -> str:
        """
        Save screenshot to local storage with unique filename.
        
        Args:
            file_path: Source file path
            payment_id: Payment ID for unique naming
            
        Returns:
            Local path where file was saved
        """
        screenshots_dir = os.path.join(settings.DATA_DIR, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Get file extension
        _, ext = os.path.splitext(file_path)
        if not ext:
            ext = '.jpg'
        
        # Create unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        local_filename = f"payment_{payment_id}_{timestamp}{ext}"
        local_path = os.path.join(screenshots_dir, local_filename)
        
        # Copy file (preserve metadata, don't overwrite)
        shutil.copy2(file_path, local_path)
        
        return local_path
    
    # ============== Payment Approval ==============
    
    async def approve_payment(self, payment_id: int, admin_id: int) -> Dict[str, Any]:
        """
        Approve a payment with idempotency checks.

        This method:
        1. Verifies payment exists and is pending
        2. Updates payment status to 'approved'
        3. Grants lifetime premium to user
        4. Triggers referral completion (counts the referral for the referrer)
        5. Handles race conditions safely

        Args:
            payment_id: Payment ID to approve
            admin_id: Admin performing the approval

        Returns:
            Dict with approval details

        Raises:
            Exception with details if approval fails
        """
        try:
            # Approve payment and grant premium - all in one transaction
            from datetime import datetime
            from app.db.base import get_db
            from app.repositories.referral_repo import ReferralRepository

            result = {
                'success': False,
                'payment_id': payment_id,
                'user_id': None,
                'is_premium': False,
                'referral_completed': False
            }

            # Process everything in a single atomic transaction
            async for session in get_db():
                payment_repo = PaymentRepository(session)
                user_repo = UserRepository(session)
                referral_repo = ReferralRepository(session)

                # Get payment in the new session
                payment = await payment_repo.get_payment(payment_id)

                if not payment:
                    raise Exception(f"Payment #{payment_id} not found")

                if payment.status != 'pending':
                    raise Exception(f"Payment #{payment_id} is already {payment.status}")

                result['user_id'] = payment.user_id
                result['subscription_days'] = getattr(payment, 'subscription_days', None)
                result['amount'] = getattr(payment, 'amount', 0)

                # 1. Approve payment
                now = datetime.utcnow()
                payment.status = 'approved'
                payment.approved_by = admin_id
                payment.approved_at = now
                session.add(payment)
                
                # 2. Grant lifetime premium
                user = await user_repo.get_user(payment.user_id)
                if user:
                    user.is_premium = True
                    user.approved = True
                    user.updated_at = now
                    result['is_premium'] = True
                    
                    # Get username for result
                    result['username'] = getattr(user, 'username', None)
                    
                    logger.info(f"✅ APPROVED: user_id={user.user_id} is_premium=True, approved=True")
                
                # 3. Complete referral (counts the referral for the referrer)
                try:
                    from app.services.referral_service import ReferralService
                    referral_service = ReferralService(referral_repo, user_repo)
                    
                    referral_result = await referral_service.complete_referral_with_session(
                        payment.user_id
                    )
                    
                    if referral_result.get('success'):
                        if referral_result.get('count_incremented'):
                            logger.info(
                                f"✅ REFERRAL COUNTED: Referrer {referral_result.get('referrer_id')} "
                                f"earned credit for referred user {payment.user_id}"
                            )
                            result['referral_completed'] = True
                            result['referrer_id'] = referral_result.get('referrer_id')
                            
                            if referral_result.get('reward_granted'):
                                result['reward_granted_to_referrer'] = True
                                result['reward_message'] = referral_result.get('reward_message', '')
                                logger.info(
                                    f"🎉 REFERRAL REWARD: Referrer {referral_result.get('referrer_id')} "
                                    f"earned lifetime premium!"
                                )
                        
                        elif referral_result.get('already_completed'):
                            logger.info(
                                f"ℹ️ Referral already completed for referred user {payment.user_id}"
                            )
                            result['referral_already_counted'] = True
                        else:
                            logger.info(
                                f"ℹ️ {referral_result.get('message', 'No pending referral')}"
                            )
                    
                except Exception as referral_error:
                    logger.error(
                        f"❌ Error completing referral for payment #{payment_id}: {referral_error}"
                    )
                    # Don't fail payment approval for referral errors
                    result['referral_error'] = str(referral_error)
                
                # Commit all changes atomically
                await session.commit()
                
                # Refresh to verify
                await session.refresh(user)
                logger.info(
                    f"🔍 VERIFIED: user_id={user.user_id if user else 'N/A'} "
                    f"approved={user.approved if user else 'N/A'}, "
                    f"is_premium={user.is_premium if user else 'N/A'}"
                )
            
            result['success'] = True
            result['approved_by'] = admin_id
            result['approved_at'] = now
            
            logger.info(f"✅ APPROVAL COMPLETE: Payment #{payment_id} approved successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error approving payment #{payment_id}: {e}")
            raise
    
    async def reject_payment(
        self, 
        payment_id: int, 
        admin_id: int, 
        reason: str
    ) -> Dict[str, Any]:
        """
        Reject a payment with validation.
        
        Args:
            payment_id: Payment ID to reject
            admin_id: Admin performing the rejection
            reason: Reason for rejection (required)
            
        Returns:
            Dict with rejection details
            
        Raises:
            Exception if rejection fails
        """
        if not reason or len(reason.strip()) < 5:
            raise Exception("Rejection reason must be at least 5 characters")
        
        try:
            payment = await self.payment_repo.reject_payment(
                payment_id=payment_id,
                admin_id=admin_id,
                reason=reason.strip()
            )
            
            if not payment:
                raise Exception(f"Payment #{payment_id} not found or already processed")
            
            # Get user for notification
            user = await self.user_repo.get_user(payment.user_id)
            
            return {
                'success': True,
                'payment_id': payment.payment_id,
                'user_id': payment.user_id,
                'username': getattr(user, 'username', None) if user else None,
                'rejection_reason': reason,
                'rejected_by': admin_id,
                'rejected_at': payment.approved_at
            }
            
        except Exception as e:
            logger.error(f"Error rejecting payment #{payment_id}: {e}")
            raise
    
    # ============== Admin Utilities ==============
    
    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """
        Get all pending payments with user details.
        
        Returns:
            List of payment dicts with user info
        """
        try:
            payments = await self.payment_repo.get_pending_payments()
            result = []
            
            for payment in payments:
                user = await self.user_repo.get_user(payment.user_id)
                
                result.append({
                    'payment_id': payment.payment_id,
                    'user_id': payment.user_id,
                    'username': getattr(user, 'username', None) if user else None,
                    'first_name': getattr(user, 'first_name', 'Unknown') if user else 'Unknown',
                    'last_name': getattr(user, 'last_name', None) if user else None,
                    'amount': getattr(payment, 'amount', 0),
                    'subscription_days': getattr(payment, 'subscription_days', None),
                    'created_at': payment.created_at,
                    'screenshot_file_id': getattr(payment, 'screenshot_file_id', None),
                    'screenshot_file_path': getattr(payment, 'screenshot_file_path', None)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting pending payments: {e}")
            return []
    
    async def get_revenue_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get revenue analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with revenue statistics
        """
        try:
            return await self.payment_repo.get_revenue_stats(days)
        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return {
                'total_revenue': 0,
                'payment_count': 0,
                'avg_revenue_per_payment': 0,
                'daily_trend': []
            }

