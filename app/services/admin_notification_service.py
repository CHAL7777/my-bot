"""
Admin Notification Service - Telegram Quiz Bot

Automatically notifies Telegram admins when important events occur:
- New contact/support messages
- Pending payments submitted
- New user registrations
- System alerts
"""

from typing import List, Optional
from datetime import datetime

from app.db.base import get_db
from app.repositories.admin_repo import TelegramAdminRepository
from app.config import settings

# Category emojis for notifications
CATEGORY_EMOJIS = {
    'payment': '💳',
    'quiz_error': '🐛',
    'access': '🔒',
    'general': '💡',
    'feedback': '💬'
}

# Priority levels
PRIORITY = {
    'low': '🟢',
    'medium': '🟡',
    'high': '🔴',
    'urgent': '🚨'
}


class AdminNotificationService:
    """Service for sending notifications to Telegram admins"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def get_admin_chat_ids(self) -> List[int]:
        """Get all active admin chat IDs"""
        admin_ids = []
        
        async for session in get_db():
            admin_repo = TelegramAdminRepository(session)
            admins = await admin_repo.get_active_admins()
            
            for admin in admins:
                if admin.user_id:
                    admin_ids.append(admin.user_id)
        
        return admin_ids
    
    async def notify_new_contact_message(
        self,
        user_id: int,
        username: Optional[str],
        first_name: str,
        category: str,
        message_text: str,
        ticket_id: str
    ) -> int:
        """
        Notify all admins about a new contact/support message.
        
        Args:
            user_id: The user's Telegram ID
            username: The user's username (optional)
            first_name: The user's first name
            category: Message category (payment, quiz_error, access, general, feedback)
            message_text: The message content
            ticket_id: Generated ticket ID (e.g., SUP-1001)
            
        Returns:
            Number of admins notified
        """
        admin_ids = await self.get_admin_chat_ids()
        
        if not admin_ids:
            print(f"⚠️ No active admins to notify about ticket {ticket_id}")
            return 0
        
        category_emoji = CATEGORY_EMOJIS.get(category, '📬')
        priority = self._get_message_priority(category)
        
        # Build notification message
        username_display = f"@{username}" if username else "No username"
        
        # Truncate long messages for notification
        display_text = message_text[:200] + "..." if len(message_text) > 200 else message_text
        
        notification_text = (
            f"{priority} *New Support Ticket* {priority}\n\n"
            f"{category_emoji} *Category:* {category.upper()}\n"
            f"🎫 *Ticket:* `{ticket_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *User Info:*\n"
            f"• Name: {first_name}\n"
            f"• Username: {username_display}\n"
            f"• User ID: `{user_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 *Message:*\n"
            f"{display_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏰ *Time:* {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
            f"💡 *Quick Reply:*\n"
            f"`/reply {ticket_id} Your response here`"
        )
        
        # Send to all admins
        notified_count = 0
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                    parse_mode='Markdown'
                )
                notified_count += 1
            except Exception as e:
                print(f"❌ Failed to notify admin {admin_id}: {e}")
        
        print(f"✅ Notified {notified_count}/{len(admin_ids)} admins about ticket {ticket_id}")
        return notified_count
    
    async def notify_new_payment(
        self,
        user_id: int,
        username: Optional[str],
        first_name: str,
        amount: float,
        payment_id: int
    ) -> int:
        """
        Notify all admins about a new payment submission.
        
        Args:
            user_id: The user's Telegram ID
            username: The user's username (optional)
            first_name: The user's first name
            amount: Payment amount
            payment_id: Payment ID
            
        Returns:
            Number of admins notified
        """
        admin_ids = await self.get_admin_chat_ids()
        
        if not admin_ids:
            print(f"⚠️ No active admins to notify about payment {payment_id}")
            return 0
        
        username_display = f"@{username}" if username else "No username"
        currency = getattr(settings, 'CURRENCY_SYMBOL', 'ETB')
        
        notification_text = (
            f"💰 *New Payment Submitted*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *User:* {first_name}\n"
            f"• Username: {username_display}\n"
            f"• User ID: `{user_id}`\n\n"
            f"💵 *Amount:* {amount} {currency}\n"
            f"🆔 *Payment ID:* `{payment_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏰ *Time:* {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
            f"🔍 *Action Required:*\n"
            f"Review and approve/reject the payment.\n\n"
            f"💡 *Commands:*\n"
            f"`/admin_payments` - View all payments"
        )
        
        notified_count = 0
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                    parse_mode='Markdown'
                )
                notified_count += 1
            except Exception as e:
                print(f"❌ Failed to notify admin {admin_id}: {e}")
        
        print(f"✅ Notified {notified_count}/{len(admin_ids)} admins about payment {payment_id}")
        return notified_count
    
    async def notify_payment_approved(
        self,
        user_id: int,
        first_name: str,
        amount: float,
        admin_name: str
    ) -> int:
        """
        Notify user that their payment was approved.
        
        Args:
            user_id: The user's Telegram ID
            first_name: The user's first name
            amount: Payment amount
            admin_name: Name of approving admin
            
        Returns:
            Whether notification was sent successfully
        """
        currency = getattr(settings, 'CURRENCY_SYMBOL', 'ETB')
        
        notification_text = (
            f"✅ *Payment Approved!*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Hi {first_name}! Great news! 🎉\n\n"
            f"Your payment of *{amount} {currency}* has been approved by {admin_name}.\n\n"
            f"✅ *Premium access unlocked!*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 You can now access all premium features.\n"
            f"Start a quiz with /start to begin!\n\n"
            f"Thank you for your purchase! 🙏"
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            print(f"❌ Failed to notify user {user_id}: {e}")
            return False
    
    async def notify_payment_rejected(
        self,
        user_id: int,
        first_name: str,
        amount: float,
        reason: str,
        admin_name: str
    ) -> int:
        """
        Notify user that their payment was rejected.
        
        Args:
            user_id: The user's Telegram ID
            first_name: The user's first name
            amount: Payment amount
            reason: Rejection reason
            admin_name: Name of rejecting admin
            
        Returns:
            Whether notification was sent successfully
        """
        currency = getattr(settings, 'CURRENCY_SYMBOL', 'ETB')
        
        notification_text = (
            f"❌ *Payment Update*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Hi {first_name},\n\n"
            f"We regret to inform you that your payment of *{amount} {currency}* was not approved.\n\n"
            f"📝 *Reason:* {reason}\n"
            f"👤 *Reviewed by:* {admin_name}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 *What to do:*\n"
            f"• Please check your payment details\n"
            f"• Submit a new payment with correct information\n"
            f"• Contact us if you need assistance\n\n"
            f"Use /contact to reach support."
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            print(f"❌ Failed to notify user {user_id}: {e}")
            return False
    
    async def notify_referral_completed(
        self,
        referrer_id: int,
        referrer_name: str,
        referred_name: str,
        reward_amount: float
    ) -> int:
        """
        Notify referrer that they earned a referral reward.
        
        Args:
            referrer_id: The referrer's Telegram ID
            referrer_name: The referrer's name
            referred_name: The referred user's name
            reward_amount: Reward amount earned
            
        Returns:
            Whether notification was sent successfully
        """
        currency = getattr(settings, 'CURRENCY_SYMBOL', 'ETB')
        
        notification_text = (
            f"🎉 *Referral Bonus!*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Hi {referrer_name}! Great news! 🎁\n\n"
            f"You just earned a referral reward!\n\n"
            f"👤 *New referral:* {referred_name}\n"
            f"💰 *Reward:* {reward_amount} {currency}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 Keep sharing your referral code to earn more!\n"
            f"Use /referral to view your stats."
        )
        
        try:
            await self.bot.send_message(
                chat_id=referrer_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            print(f"❌ Failed to notify referrer {referrer_id}: {e}")
            return False
    
    async def broadcast_to_admins(
        self,
        message: str,
        priority: str = 'medium'
    ) -> int:
        """
        Send a broadcast message to all admins.
        
        Args:
            message: The message to send
            priority: Priority level (low, medium, high, urgent)
            
        Returns:
            Number of admins notified
        """
        admin_ids = await self.get_admin_chat_ids()
        
        if not admin_ids:
            return 0
        
        priority_emoji = PRIORITY.get(priority, '🟡')
        
        full_message = (
            f"{priority_emoji} *Admin Broadcast*\n\n"
            f"{message}\n\n"
            f"⏰ {datetime.now().strftime('%d %b %Y %H:%M')}"
        )
        
        notified_count = 0
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=full_message,
                    parse_mode='Markdown'
                )
                notified_count += 1
            except Exception as e:
                print(f"❌ Failed to notify admin {admin_id}: {e}")
        
        return notified_count
    
    def _get_message_priority(self, category: str) -> str:
        """Determine message priority based on category"""
        priority_map = {
            'payment': 'high',
            'quiz_error': 'medium',
            'access': 'high',
            'general': 'low',
            'feedback': 'low'
        }
        return priority_map.get(category, 'medium')


# Singleton instance (will be initialized in bot.py)
_admin_notification_service: Optional[AdminNotificationService] = None


def get_admin_notification_service(bot=None) -> AdminNotificationService:
    """Get or create the admin notification service singleton"""
    global _admin_notification_service
    
    if _admin_notification_service is None and bot is not None:
        _admin_notification_service = AdminNotificationService(bot)
    
    return _admin_notification_service


async def notify_admins_new_contact(
    bot,
    user_id: int,
    username: Optional[str],
    first_name: str,
    category: str,
    message_text: str,
    ticket_id: str
) -> int:
    """Convenience function to notify admins of new contact message"""
    service = get_admin_notification_service(bot)
    if service is None:
        service = AdminNotificationService(bot)
    return await service.notify_new_contact_message(
        user_id=user_id,
        username=username,
        first_name=first_name,
        category=category,
        message_text=message_text,
        ticket_id=ticket_id
    )


async def notify_admins_new_payment(
    bot,
    user_id: int,
    username: Optional[str],
    first_name: str,
    amount: float,
    payment_id: int
) -> int:
    """Convenience function to notify admins of new payment"""
    service = get_admin_notification_service(bot)
    if service is None:
        service = AdminNotificationService(bot)
    return await service.notify_new_payment(
        user_id=user_id,
        username=username,
        first_name=first_name,
        amount=amount,
        payment_id=payment_id
    )
