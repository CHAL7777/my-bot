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
    
    # ============== Logging Helper ==============
    
    def _log_error(self, method_name: str, error: Exception, context: Dict[str, Any] = None):
        """Log error with context for debugging."""
        log_data = {
            'method': method_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
        }
        if context:
            log_data['context'] = context
        logger.error(f"ReferralService.{method_name}: {log_data}")
    
    def _log_info(self, message: str, context: Dict[str, Any] = None):
        """Log info message with context."""
        log_data = {'message': message}
        if context:
            log_data.update(context)
        logger.info(f"ReferralService: {log_data}")
    
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
            self._log_error('capture_referral_on_start', e, {
                'referrer_id': referrer_id,
                'referred_id': referred_id
            })
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
            credited = await self.credit_referral_reward(referrer_id, reward_amount)
            result['reward_credited'] = credited
            result['reward_amount'] = reward_amount
            
            # 4. Mark reward as claimed
            await self.referral_repo.mark_reward_claimed(referral.id)
            
            result['success'] = True
            result['message'] = f'Referral approved. {reward_amount} Birr credited to referrer.'
            
            logger.info(
                f"[REFERRAL] Approved: referred={referred_id}, "
                f"reward={reward_amount} to referrer={referrer_id}"
            )
            
            # 5. Send notification to referrer
            if bot:
                await self.notify_referrer_about_reward(bot, referrer_id, reward_amount, referred_id)
            
        except Exception as e:
            self._log_error('approve_referral_and_credit_reward', e, {
                'referred_id': referred_id
            })
            result['message'] = f'Error: {str(e)}'
        
        return result
    
    async def credit_referral_reward(self, referrer_id: int, amount: float) -> bool:
        """
        Credit referral reward to user's balance.
        
        Updates the referral_balance column in users table.
        """
        try:
            user = await self.user_repo.get_user(referrer_id)
            if user:
                current_balance = getattr(user, 'referral_balance', 0) or 0
                new_balance = current_balance + amount
                await self.user_repo.update_user(referrer_id, referral_balance=new_balance)
                logger.info(f"[REFERRAL] Credited {amount} to user {referrer_id}, new balance: {new_balance}")
                return True
            return False
        except Exception as e:
            self._log_error('credit_referral_reward', e, {
                'referrer_id': referrer_id,
                'amount': amount
            })
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
            self._log_error('notify_referrer_about_reward', e, {
                'referrer_id': referrer_id,
                'amount': amount,
                'referred_user_id': referred_user_id
            })
    
    # ============== Existing Methods (kept for compatibility) ==============
    
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
    
    async def get_user_by_referral_code(self, referral_code: str) -> Optional[Dict[str, Any]]:
        """Get user by referral code"""
        try:
            user = await self.user_repo.get_user_by_referral_code(referral_code)
            return user
        except Exception as e:
            self._log_error('get_user_by_referral_code', e, {'referral_code': referral_code})
            return None
    
    async def get_referral_link(self, user_id: int) -> str:
        """Generate referral link for user"""
        referral_code = await self.get_referral_code(user_id)
        bot_username = getattr(settings, 'BOT_USERNAME', 'YourBotName')
        return f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    async def get_top_referrers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top referrers leaderboard"""
        try:
            return await self.referral_repo.get_top_referrers(limit)
        except Exception as e:
            self._log_error('get_top_referrers', e, {'limit': limit})
            raise
    
    async def get_user_referrals(self, user_id: int) -> List[Dict[str, Any]]:
        """Get detailed referral information for user"""
        try:
            referrals = await self.referral_repo.get_user_referrals(user_id)
            
            result = []
            for referral in referrals:
                referred_user = await self.user_repo.get_user(referral.referred_id)
                if referred_user:
                    result.append({
                        'referral_id': referral.id,
                        'referred_user': {
                            'user_id': referred_user.user_id,
                            'username': getattr(referred_user, 'username', None),
                            'first_name': getattr(referred_user, 'first_name', None),
                            'last_name': getattr(referred_user, 'last_name', None)
                        },
                        'status': referral.status,
                        'created_at': referral.created_at,
                        'approved_at': getattr(referral, 'approved_at', None),
                        'reward_claimed': getattr(referral, 'reward_claimed', False)
                    })
            
            return result
        except Exception as e:
            self._log_error('get_user_referrals', e, {'user_id': user_id})
            raise
    
    async def validate_referral_code(self, referral_code: str) -> bool:
        """Validate that referral code exists and is valid"""
        try:
            user = await self.get_user_by_referral_code(referral_code)
            return user is not None
        except Exception as e:
            self._log_error('validate_referral_code', e, {'referral_code': referral_code})
            return False
    
    async def cancel_referral(self, referral_id: int, reason: str = "") -> Dict[str, Any]:
        """Cancel a referral"""
        result = {
            'success': False,
            'message': '',
            'referral_id': referral_id
        }
        
        try:
            referral = await self.referral_repo.get_referral_by_id(referral_id)
            if not referral:
                result['message'] = 'Referral not found'
                return result
            
            if referral.status == 'approved':
                result['message'] = 'Cannot cancel an approved referral'
                return result
            
            cancelled = await self.referral_repo.cancel_referral(referral_id)
            
            if cancelled:
                result['success'] = True
                result['message'] = 'Referral cancelled'
                self._log_info('Referral cancelled', {
                    'referral_id': referral_id,
                    'reason': reason
                })
            else:
                result['message'] = 'Failed to cancel referral'
                
        except Exception as e:
            self._log_error('cancel_referral', e, {
                'referral_id': referral_id,
                'reason': reason
            })
            result['message'] = f'Error cancelling referral: {str(e)}'
        
        return result
    
    async def process_referral(self, referrer_id: int, referred_id: int) -> Dict[str, Any]:
        """
        Legacy method - kept for backward compatibility.
        
        Use capture_referral_on_start() instead for new code.
        """
        return await self.capture_referral_on_start(referrer_id, referred_id)
    
    async def is_referral_completed(self, referred_id: int) -> bool:
        """Check if referral for user is already completed (approved)"""
        try:
            referrals = await self.referral_repo.get_referrals_to_user(
                referred_id, 
                status='approved'
            )
            return len(referrals) > 0
        except Exception:
            return False
    
    async def complete_referral_on_payment_approval(self, referred_id: int) -> Dict[str, Any]:
        """
        Legacy method - kept for backward compatibility.
        
        Use approve_referral_and_credit_reward() instead.
        """
        return await self.approve_referral_and_credit_reward(referred_id)
    
    async def complete_referral_with_session(self, referred_id: int) -> Dict[str, Any]:
        """
        Complete referral with self-contained session management.
        
        This is called from payment_service.py when admin approves payment.
        Creates its own database session and handles the complete transaction.
        """
        from app.db.base import get_db
        from app.repositories.referral_repo import ReferralRepository
        from app.repositories.user_repo import UserRepository
        
        result = {
            'success': False,
            'message': '',
            'referrer_id': None,
            'count_incremented': False,
            'reward_credited': False,
            'already_completed': False
        }
        
        try:
            async for session in get_db():
                referral_repo = ReferralRepository(session)
                user_repo = UserRepository(session)
                
                # Get the referral
                referrals = await referral_repo.get_referrals_to_user(referred_id, status='pending')
                
                if not referrals:
                    # Check if already approved
                    approved_refs = await referral_repo.get_referrals_to_user(referred_id, status='approved')
                    if approved_refs:
                        result['already_completed'] = True
                        result['success'] = True
                        result['message'] = 'Referral already approved'
                        result['referrer_id'] = approved_refs[0].referrer_id
                    else:
                        result['message'] = 'No referral found'
                    return result
                
                referral = referrals[0]
                referrer_id = referral.referrer_id
                result['referrer_id'] = referrer_id
                
                # APPROVE REFERRAL
                await referral_repo.approve_referral(referral.id)
                logger.info(f"[REFERRAL] Approved: referral_id={referral.id}")
                
                # CREDIT REWARD to referrer
                reward_amount = self.REFERRAL_REWARD_AMOUNT
                credited = await self.credit_referral_reward(referrer_id, reward_amount)
                result['reward_credited'] = credited
                
                # Mark reward as claimed
                await referral_repo.mark_reward_claimed(referral.id)
                
                # Increment referral count on referrer
                try:
                    referrer_user = await user_repo.get_user(referrer_id)
                    if referrer_user:
                        new_count = (getattr(referrer_user, 'referral_count', 0) or 0) + 1
                        await user_repo.update_user(referrer_id, referral_count=new_count)
                        result['count_incremented'] = True
                        logger.info(f"[REFERRAL] Incremented referral_count for {referrer_id} to {new_count}")
                except Exception as count_error:
                    logger.warning(f"[REFERRAL] Could not increment referral count: {count_error}")
                
                result['success'] = True
                result['message'] = f'Referral completed. {reward_amount} Birr credited.'
                
                logger.info(
                    f"[REFERRAL] Complete: referrer={referrer_id}, "
                    f"referred={referred_id}, reward={reward_amount}"
                )
                
                return result
                
        except Exception as e:
            self._log_error('complete_referral_with_session', e, {
                'referred_id': referred_id
            })
            result['message'] = f'Error: {str(e)}'
        
        return result

