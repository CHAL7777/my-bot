from typing import Dict, Any, List

from app.repositories.leaderboard_repo import LeaderboardRepository

class LeaderboardService:
    def __init__(self, leaderboard_repo: LeaderboardRepository, attempt_repo):
        self.leaderboard_repo = leaderboard_repo
        self.attempt_repo = attempt_repo

    async def get_leaderboard(self, period: str, limit: int = 50, 
                               user_id: int = None) -> Dict[str, Any]:
        """
        Get leaderboard for a period with real-time calculation from quiz attempts.
        
        Args:
            period: 'daily', 'weekly', 'monthly', or 'overall'
            limit: Maximum number of entries to return
            user_id: Optional user ID to include their personal rank
            
        Returns:
            Dict with 'leaderboard', 'total_users', and 'user_rank'
        """
        return await self.leaderboard_repo.get_leaderboard_realtime(
            period=period,
            limit=limit,
            user_id=user_id
        )

    async def get_user_leaderboard_summary(self, user_id: int) -> Dict[str, Any]:
        """Get user's ranking across all leaderboard periods"""
        periods = ['daily', 'weekly', 'monthly', 'overall']
        summary = {}
        best_rank = None
        best_period = None
        
        for p in periods:
            rank = await self.leaderboard_repo.get_user_rank_realtime(user_id, p)
            summary[p] = rank
            
            # Track best rank
            if rank and rank.get('rank'):
                if best_rank is None or rank['rank'] < best_rank:
                    best_rank = rank['rank']
                    best_period = p
        
        return {
            'summary': summary,
            'best_rank': best_rank,
            'best_period': best_period
        }

    async def update_all_leaderboards(self) -> bool:
        """Update cached leaderboards (optional - leaderboards now use real-time)"""
        # Leaderboards are now calculated in real-time, so this is no longer required
        # However, you can keep this for backwards compatibility or scheduled caching
        return True

    async def get_leaderboard_stats(self) -> Dict[str, Any]:
        """Get leaderboard statistics"""
        return await self.leaderboard_repo.get_leaderboard_stats()
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.repositories.user_repo import UserRepository
from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.payment_repo import PaymentRepository

class AnalyticsService:
    def __init__(self, user_repo: UserRepository,
                 question_repo: QuestionRepository,
                 attempt_repo: AttemptRepository,
                 payment_repo: PaymentRepository):
        self.user_repo = user_repo
        self.question_repo = question_repo
        self.attempt_repo = attempt_repo
        self.payment_repo = payment_repo
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get overall dashboard statistics"""
        # User statistics
        total_users = await self.user_repo.get_active_users_count(days=365)  # All users
        active_users = await self.user_repo.get_active_users_count(days=7)   # Active in last 7 days
        new_users_today = await self.user_repo.get_active_users_count(days=1)  # New/active today
        
        # Question statistics
        question_stats = await self.question_repo.get_question_stats()
        
        # Attempt statistics
        # Get attempts in last 24 hours
        attempts_today = await self.attempt_repo.get_attempts_since(datetime.now() - timedelta(days=1))
        
        # Payment statistics
        revenue_stats = await self.payment_repo.get_revenue_stats(days=30)
        
        return {
            'users': {
                'total': total_users,
                'active_7_days': active_users,
                'new_today': new_users_today,
                'growth_rate': round((new_users_today / total_users * 100), 2) if total_users > 0 else 0
            },
            'questions': question_stats,
            'activity': {
                'attempts_today': len(attempts_today),
                'avg_accuracy_today': self._calculate_avg_accuracy(attempts_today) if attempts_today else 0,
                'popular_questions': await self.attempt_repo.get_question_popularity(limit=5)
            },
            'revenue': revenue_stats,
            'timestamp': datetime.now()
        }
    
    def _calculate_avg_accuracy(self, attempts: List) -> float:
        """Calculate average accuracy from attempts"""
        if not attempts:
            return 0
        
        correct = sum(1 for attempt in attempts if attempt.is_correct)
        return round((correct / len(attempts)) * 100, 2)
    
    async def get_user_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get user analytics for the given period"""
        # Get user growth data
        user_growth = []
        for i in range(days, 0, -1):
            date = datetime.now() - timedelta(days=i)
            count = await self.user_repo.get_users_registered_on(date.date())
            user_growth.append({
                'date': date.date(),
                'count': count
            })
        
        # Get active users per day
        active_users = []
        for i in range(7, 0, -1):
            date = datetime.now() - timedelta(days=i)
            count = await self.user_repo.get_active_users_count(since=date)
            active_users.append({
                'date': date.date(),
                'count': count
            })
        
        # Get user demographics (simplified)
        # In a real implementation, you might have more user data
        
        return {
            'user_growth': user_growth,
            'active_users': active_users,
            'total_users': sum(day['count'] for day in user_growth),
            'avg_daily_active': sum(day['count'] for day in active_users) / len(active_users) if active_users else 0
        }
    
    async def get_performance_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get performance analytics"""
        # Get accuracy trends
        accuracy_trend = []
        for i in range(days, 0, -1):
            start_date = datetime.now() - timedelta(days=i)
            end_date = start_date + timedelta(days=1)
            
            # Get attempts for this day
            attempts = await self.attempt_repo.get_attempts_between(start_date, end_date)
            
            if attempts:
                correct = sum(1 for attempt in attempts if attempt.is_correct)
                accuracy = round((correct / len(attempts)) * 100, 2)
            else:
                accuracy = 0
            
            accuracy_trend.append({
                'date': start_date.date(),
                'accuracy': accuracy,
                'attempts': len(attempts)
            })
        
        # Get difficulty distribution
        difficulty_dist = await self.attempt_repo.get_difficulty_distribution(days)
        
        # Get top performing chapters
        top_chapters = await self.attempt_repo.get_top_chapters(days, limit=5)
        
        # Get weak chapters (lowest accuracy)
        weak_chapters = await self.attempt_repo.get_weak_chapters(days, limit=5)
        
        return {
            'accuracy_trend': accuracy_trend,
            'difficulty_distribution': difficulty_dist,
            'top_chapters': top_chapters,
            'weak_chapters': weak_chapters,
            'avg_accuracy': sum(day['accuracy'] for day in accuracy_trend) / len(accuracy_trend) if accuracy_trend else 0,
            'total_attempts': sum(day['attempts'] for day in accuracy_trend)
        }
    
    async def get_revenue_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get revenue analytics"""
        return await self.payment_repo.get_revenue_stats(days)
    
    async def get_weak_students(self, min_attempts: int = 10, 
                               accuracy_threshold: float = 50.0) -> List[Dict[str, Any]]:
        """Identify weak students who need attention"""
        # Get all users with sufficient attempts
        # This is a simplified version
        # In reality, you'd have a more complex query
        
        weak_students = []
        
        # For demonstration, we'll return an empty list
        # Actual implementation would query the database
        
        return weak_students
    
    async def generate_report(self, report_type: str, 
                            start_date: datetime = None,
                            end_date: datetime = None) -> Dict[str, Any]:
        """Generate detailed report"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        days = (end_date - start_date).days
        
        if report_type == 'daily':
            return await self._generate_daily_report(start_date)
        elif report_type == 'weekly':
            return await self._generate_weekly_report(start_date)
        elif report_type == 'monthly':
            return await self._generate_monthly_report(start_date)
        else:
            return await self._generate_custom_report(start_date, end_date)
    
    async def _generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generate daily report"""
        # Implementation would generate detailed daily report
        return {"message": "Daily report generation not implemented"}
    
    async def _generate_weekly_report(self, date: datetime) -> Dict[str, Any]:
        """Generate weekly report"""
        # Implementation would generate detailed weekly report
        return {"message": "Weekly report generation not implemented"}
    
    async def _generate_monthly_report(self, date: datetime) -> Dict[str, Any]:
        """Generate monthly report"""
        # Implementation would generate detailed monthly report
        return {"message": "Monthly report generation not implemented"}
    
    async def _generate_custom_report(self, start_date: datetime, 
                                    end_date: datetime) -> Dict[str, Any]:
        """Generate custom report for date range"""
        # Implementation would generate detailed custom report
        return {"message": "Custom report generation not implemented"}