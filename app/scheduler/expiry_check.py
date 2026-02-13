from datetime import datetime, timedelta

from app.db.base import get_db
from app.repositories.payment_repo import PaymentRepository
from app.repositories.leaderboard_repo import LeaderboardRepository

class ExpiryChecker:
    def __init__(self, bot):
        self.bot = bot
    
    async def check_subscription_expiry(self):
        """Check and update expired subscriptions"""
        try:
            async for session in get_db():
                payment_repo = PaymentRepository(session)
                
                # Check for expired subscriptions
                expired_count = await payment_repo.check_subscription_expiry()
                
                if expired_count > 0:
                    print(f"Updated {expired_count} expired subscriptions")
                
        except Exception as e:
            print(f"Error checking subscription expiry: {e}")
    
    async def cleanup_old_data(self):
        """Cleanup old data to keep database size manageable"""
        try:
            async for session in get_db():
                leaderboard_repo = LeaderboardRepository(session)
                
                # Cleanup old leaderboard entries
                cleaned_count = await leaderboard_repo.cleanup_old_leaderboards()
                
                if cleaned_count > 0:
                    print(f"Cleaned up {cleaned_count} old leaderboard entries")
                
                # Additional cleanup tasks can be added here:
                # - Old quiz attempts
                # - Old payment records
                # - Old user activity logs
                
        except Exception as e:
            print(f"Error in data cleanup: {e}")
    
    async def update_leaderboards(self):
        """Update all leaderboards"""
        try:
            async for session in get_db():
                from app.services.leaderboard_service import LeaderboardService
                from app.repositories.attempt_repo import AttemptRepository
                
                attempt_repo = AttemptRepository(session)
                leaderboard_repo = LeaderboardRepository(session)
                
                leaderboard_service = LeaderboardService(leaderboard_repo, attempt_repo)
                
                # Update all leaderboards
                await leaderboard_service.update_all_leaderboards()
                
                print("Updated all leaderboards")
                
        except Exception as e:
            print(f"Error updating leaderboards: {e}")