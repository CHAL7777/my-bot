import asyncio
from datetime import datetime, timedelta
from typing import List

from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.leaderboard_repo import LeaderboardRepository


def _make_naive_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to naive (no timezone info).
    
    This handles both timezone-aware and naive datetimes from the database.
    PostgreSQL timestamps are often timezone-aware, while datetime.utcnow() is naive.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC then remove timezone info
        return dt.replace(tzinfo=None)
    return dt


class ReminderScheduler:
    def __init__(self, bot):
        self.bot = bot
    
    async def send_daily_reminders(self):
        """Send daily reminders to inactive users"""
        try:
            async for session in get_db():
                user_repo = UserRepository(session)
                attempt_repo = AttemptRepository(session)
                
                # Get users who haven't been active for 3 days
                # Use datetime.utcnow() for consistency with database timestamps
                cutoff_date = datetime.utcnow() - timedelta(days=3)
                
                # This would require additional query methods
                # For now, we'll send reminders to all active users
                users = await user_repo.get_all_users()
                
                for user in users:
                    if not user.blocked:
                        # Check last activity
                        attempts = await attempt_repo.get_user_attempts(user.user_id, limit=1)
                        
                        # Handle timezone-aware vs naive datetime comparison
                        last_attempt_time = None
                        if attempts and attempts[0].created_at:
                            last_attempt_time = _make_naive_utc(attempts[0].created_at)
                        
                        if not attempts or (last_attempt_time and last_attempt_time < cutoff_date):
                            # Send reminder
                            try:
                                await self.bot.send_message(
                                    chat_id=user.user_id,
                                    text=(
                                        "📚 *Quiz Time!*\n\n"
                                        "Haven't seen you in a while! Ready to test your knowledge today? "
                                        "Start a quiz and keep your learning streak alive! 🚀\n\n"
                                        "Use /quiz to get started!"
                                    ),
                                    parse_mode='Markdown'
                                )
                                
                                # Add delay to avoid hitting rate limits
                                await asyncio.sleep(0.1)
                                
                            except Exception as e:
                                # User might have blocked the bot
                                print(f"Failed to send reminder to {user.user_id}: {e}")
                
        except Exception as e:
            print(f"Error in daily reminders: {e}")
    
    async def send_weekly_leaderboard(self):
        """Send weekly leaderboard summary"""
        try:
            async for session in get_db():
                leaderboard_repo = LeaderboardRepository(session)
                
                # Get weekly leaderboard
                leaderboard = await leaderboard_repo.get_leaderboard('weekly', limit=10)
                
                if not leaderboard:
                    return
                
                # Format message
                message = "🏆 *Weekly Leaderboard Update* 🏆\n\n"
                
                for entry in leaderboard[:5]:
                    medal = self._get_medal(entry['rank'])
                    message += (
                        f"{medal} *{entry['username']}*\n"
                        f"   Score: {entry['score']} | "
                        f"Accuracy: {entry['accuracy']}%\n\n"
                    )
                
                message += (
                    "Keep up the great work! 🚀\n"
                    "Use /leaderboard to see full rankings."
                )
                
                # Send to all users
                users = await UserRepository(session).get_all_users()
                
                for user in users:
                    if not user.blocked:
                        try:
                            await self.bot.send_message(
                                chat_id=user.user_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                            
                            await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            print(f"Failed to send leaderboard to {user.user_id}: {e}")
                
        except Exception as e:
            print(f"Error in weekly leaderboard: {e}")
    
    async def send_subscription_reminders(self):
        """Send reminders for expiring subscriptions"""
        try:
            async for session in get_db():
                from app.repositories.payment_repo import PaymentRepository
                payment_repo = PaymentRepository(session)
                
                # Get subscriptions expiring in 3 days
                # Use datetime.utcnow() for consistency
                cutoff_date = datetime.utcnow() + timedelta(days=3)
                
                # This would require additional query methods
                # For now, we'll implement a placeholder
                
                # Implementation would:
                # 1. Get subscriptions expiring soon
                # 2. Send reminder messages
                # 3. Update reminder status
                
                pass
                
        except Exception as e:
            print(f"Error in subscription reminders: {e}")
    
    def _get_medal(self, rank: int) -> str:
        """Get medal emoji for rank"""
        if rank == 1:
            return "🥇"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        else:
            return f"{rank}."

