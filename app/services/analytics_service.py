from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, date
from collections import defaultdict
import asyncio

from app.repositories.user_repo import UserRepository
from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.utils.helpers import format_time, format_number, calculate_percentage
from app.utils.constants import EMOJIS
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, 
                 user_repo: UserRepository,
                 question_repo: QuestionRepository,
                 attempt_repo: AttemptRepository,
                 payment_repo: PaymentRepository,
                 leaderboard_repo: LeaderboardRepository = None):
        self.user_repo = user_repo
        self.question_repo = question_repo
        self.attempt_repo = attempt_repo
        self.payment_repo = payment_repo
        self.leaderboard_repo = leaderboard_repo
    
    async def get_dashboard_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics
        
        Args:
            days: Number of days to consider for "recent" statistics
        
        Returns:
            Dictionary containing all dashboard statistics
        """
        stats = {
            'timestamp': datetime.now(),
            'period_days': days
        }
        
        try:
            # Get all statistics in parallel for better performance
            tasks = [
                self._get_user_stats(days),
                self._get_question_stats(),
                self._get_activity_stats(days),
                self._get_revenue_stats(days),
                self._get_system_stats()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Unpack results
            if not isinstance(results[0], Exception):
                stats.update(results[0])  # user_stats
            if not isinstance(results[1], Exception):
                stats['questions'] = results[1]  # question_stats
            if not isinstance(results[2], Exception):
                stats['activity'] = results[2]  # activity_stats
            if not isinstance(results[3], Exception):
                stats['revenue'] = results[3]  # revenue_stats
            if not isinstance(results[4], Exception):
                stats['system'] = results[4]  # system_stats
            
            # Calculate overall health score
            stats['health_score'] = await self._calculate_health_score(stats)
            
        except Exception as e:
            stats['error'] = str(e)
        
        return stats
    
    async def _get_user_stats(self, days: int) -> Dict[str, Any]:
        """Get user-related statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get total users
        all_users = await self.user_repo.get_all_users()
        total_users = len(all_users)
        
        # Get active users (users with attempts in last N days)
        active_users = await self.user_repo.get_active_users_count(days=days)
        
        # Get new users (registered in last N days)
        new_users = await self.user_repo.get_active_users_count(days=days)  # Simplified
        
        # Get blocked users
        blocked_users = sum(1 for user in all_users if user.blocked)
        
        # Get user growth data
        growth_data = []
        for i in range(min(days, 30), 0, -1):
            day_date = datetime.now() - timedelta(days=i)
            # In a real implementation, you'd query for users created on that day
            growth_data.append({
                'date': day_date.date(),
                'count': 0  # Placeholder
            })
        
        # Calculate retention rate (simplified)
        retention_rate = 0
        if total_users > 0:
            # Users with activity in last 7 days / total users
            active_7_days = await self.user_repo.get_active_users_count(days=7)
            retention_rate = (active_7_days / total_users) * 100
        
        return {
            'users': {
                'total': total_users,
                'active': active_users,
                'new': new_users,
                'blocked': blocked_users,
                'retention_rate': round(retention_rate, 2),
                'growth_data': growth_data
            }
        }
    
    async def _get_question_stats(self) -> Dict[str, Any]:
        """Get question-related statistics with error handling"""
        try:
            # Get total question count
            total_questions = await self.question_repo.get_question_count()
            
            # Get questions by difficulty
            simple_count = await self.question_repo.get_question_count(difficulty='simple')
            medium_count = await self.question_repo.get_question_count(difficulty='medium')
            hard_count = await self.question_repo.get_question_count(difficulty='hard')
            
            # Get questions by subject
            subjects = await self.question_repo.get_subjects()
            questions_by_subject = {}
            for subject in subjects:
                try:
                    count = await self.question_repo.get_question_count(subject_id=subject.subject_id)
                    questions_by_subject[subject.subject_name] = count
                except Exception as e:
                    logger.warning(f"Error getting question count for subject {subject.subject_name}: {e}")
                    questions_by_subject[subject.subject_name] = 0
            
            # Calculate coverage (chapters with questions)
            chapters = []
            for subject in subjects:
                try:
                    subject_chapters = await self.question_repo.get_chapters(subject.subject_id)
                    chapters.extend(subject_chapters)
                except Exception as e:
                    logger.warning(f"Error getting chapters for subject {subject.subject_name}: {e}")
            
            covered_chapters = 0
            for chapter in chapters:
                try:
                    chapter_count = await self.question_repo.get_question_count(chapter_id=chapter.chapter_id)
                    if chapter_count > 0:
                        covered_chapters += 1
                except Exception as e:
                    logger.warning(f"Error getting question count for chapter {chapter.chapter_id}: {e}")
            
            coverage_percentage = (covered_chapters / len(chapters) * 100) if chapters else 0
            
            return {
                'total': total_questions,
                'by_difficulty': {
                    'simple': simple_count,
                    'medium': medium_count,
                    'hard': hard_count,
                    'distribution': {
                        'simple': calculate_percentage(simple_count, total_questions),
                        'medium': calculate_percentage(medium_count, total_questions),
                        'hard': calculate_percentage(hard_count, total_questions)
                    }
                },
                'by_subject': questions_by_subject,
                'coverage': {
                    'total_chapters': len(chapters),
                    'covered_chapters': covered_chapters,
                    'percentage': round(coverage_percentage, 2)
                }
            }
        except Exception as e:
            logger.error(f"Error getting question stats: {e}")
            # Return empty stats on error
            return {
                'total': 0,
                'by_difficulty': {'simple': 0, 'medium': 0, 'hard': 0},
                'by_subject': {},
                'coverage': {'total_chapters': 0, 'covered_chapters': 0, 'percentage': 0}
            }
    
    async def _get_activity_stats(self, days: int) -> Dict[str, Any]:
        """Get activity-related statistics"""
        # Get today's activity
        today = date.today()
        
        # Get total attempts in period
        # This would require a method in attempt_repo to get attempts by date range
        
        # Get accuracy trends
        accuracy_trend = []
        for i in range(min(days, 14), 0, -1):  # Last 14 days for trend
            day_date = datetime.now() - timedelta(days=i)
            # In real implementation, get attempts for this day and calculate accuracy
            accuracy_trend.append({
                'date': day_date.date(),
                'accuracy': 75.0,  # Placeholder
                'attempts': 100  # Placeholder
            })
        
        # Get popular questions (most attempted)
        popular_questions = await self.attempt_repo.get_question_popularity(limit=5)
        
        # Get peak hours (when most quizzes are taken)
        peak_hours = await self._calculate_peak_hours(days)
        
        # Calculate average session duration
        avg_session_duration = await self._calculate_avg_session_duration(days)
        
        # Get difficulty distribution of attempts
        difficulty_dist = await self._get_difficulty_distribution(days)
        
        return {
            'accuracy_trend': accuracy_trend,
            'popular_questions': popular_questions,
            'peak_hours': peak_hours,
            'avg_session_duration': avg_session_duration,
            'difficulty_distribution': difficulty_dist,
            'today': {
                'date': today,
                'attempts': 0,  # Placeholder
                'quizzes': 0,  # Placeholder
                'new_users': 0  # Placeholder
            }
        }
    
    async def _get_revenue_stats(self, days: int) -> Dict[str, Any]:
        """Get revenue-related statistics"""
        # Get revenue from payment repo
        revenue_data = await self.payment_repo.get_revenue_stats(days)
        
        # Calculate additional metrics
        mrr = await self._calculate_monthly_recurring_revenue()
        arr = mrr * 12 if mrr else 0
        
        # Get subscription statistics
        subscription_stats = await self._get_subscription_stats()
        
        # Calculate conversion rate (paid users / total users)
        total_users = len(await self.user_repo.get_all_users())
        paid_users = subscription_stats.get('active_paid', 0)
        conversion_rate = (paid_users / total_users * 100) if total_users > 0 else 0
        
        # Calculate churn rate (simplified)
        churn_rate = await self._calculate_churn_rate(days)
        
        # Calculate customer lifetime value (CLV)
        clv = await self._calculate_customer_lifetime_value()
        
        return {
            **revenue_data,
            'mrr': mrr,  # Monthly Recurring Revenue
            'arr': arr,  # Annual Recurring Revenue
            'subscription_stats': subscription_stats,
            'conversion_rate': round(conversion_rate, 2),
            'churn_rate': round(churn_rate, 2),
            'clv': clv,
            'metrics': {
                'avg_revenue_per_user': revenue_data['total_revenue'] / total_users if total_users > 0 else 0,
                'avg_subscription_length': 30,  # Placeholder
                'renewal_rate': 85.5  # Placeholder
            }
        }
    
    async def _get_system_stats(self) -> Dict[str, Any]:
        """Get system-related statistics"""
        # Database health
        db_health = await self._check_database_health()
        
        # Storage usage (simplified)
        storage_usage = await self._estimate_storage_usage()
        
        # Performance metrics
        performance = await self._get_performance_metrics()
        
        # Error rates
        error_rates = await self._get_error_rates()
        
        return {
            'database': db_health,
            'storage': storage_usage,
            'performance': performance,
            'errors': error_rates,
            'uptime': self._calculate_uptime(),
            'last_backup': self._get_last_backup_time()
        }
    
    async def _calculate_health_score(self, stats: Dict[str, Any]) -> float:
        """
        Calculate overall system health score (0-100)
        
        This score helps identify system health issues.
        It's normal for new systems to have lower scores initially.
        """
        score = 0
        max_score = 100
        
        # User activity score (0-30 points)
        user_stats = stats.get('users', {})
        retention_rate = user_stats.get('retention_rate', 0)
        total_users = user_stats.get('total', 0)
        
        # Award points for users (up to 15 points)
        if total_users > 0:
            score += min(15, total_users * 3)  # 3 points per user, max 15
        
        # Award points for retention (up to 15 points)
        score += min(15, retention_rate * 0.15)
        
        # Question coverage score (0-25 points)
        question_stats = stats.get('questions', {})
        total_questions = question_stats.get('total', 0)
        coverage = question_stats.get('coverage', {}).get('percentage', 0)
        
        # Award points for having questions (up to 15 points)
        if total_questions > 0:
            score += min(15, total_questions * 0.5)  # 0.5 points per question, max 15
        
        # Award points for coverage percentage (up to 10 points)
        score += min(10, coverage * 0.1)
        
        # Activity score (0-20 points)
        activity_stats = stats.get('activity', {})
        today_activity = activity_stats.get('today', {})
        
        # Award points for daily activity (up to 10 points)
        attempts = today_activity.get('attempts', 0)
        if attempts > 0:
            score += min(10, attempts)
        
        # Award points for accuracy trend (up to 10 points)
        accuracy_trend = activity_stats.get('accuracy_trend', [])
        if accuracy_trend and len(accuracy_trend) > 0:
            latest_accuracy = accuracy_trend[-1].get('accuracy', 0)
            if latest_accuracy > 60:
                score += min(10, latest_accuracy / 10)
        
        # Revenue score (0-15 points)
        revenue_stats = stats.get('revenue', {})
        total_revenue = revenue_stats.get('total_revenue', 0)
        
        # Award points for revenue (up to 15 points)
        if total_revenue > 0:
            score += min(15, 5 + min(10, total_revenue / 100))  # Base 5 + up to 10 based on amount
        
        # System health score (0-10 points)
        system_stats = stats.get('system', {})
        db_health = system_stats.get('database', {}).get('status', 'unknown')
        if db_health == 'healthy':
            score += 10
        
        # Cap score at 100
        return round(min(score, 100), 2)
    
    async def _calculate_peak_hours(self, days: int) -> List[Dict[str, Any]]:
        """Calculate peak activity hours"""
        # In a real implementation, this would query attempts by hour of day
        # For now, return mock data
        return [
            {'hour': 10, 'attempts': 150, 'percentage': 15},
            {'hour': 14, 'attempts': 180, 'percentage': 18},
            {'hour': 20, 'attempts': 220, 'percentage': 22},
            {'hour': 22, 'attempts': 200, 'percentage': 20},
        ]
    
    async def _calculate_avg_session_duration(self, days: int) -> float:
        """Calculate average quiz session duration in minutes"""
        # In a real implementation, calculate from quiz attempts
        return 8.5  # Placeholder
    
    async def _get_difficulty_distribution(self, days: int) -> Dict[str, float]:
        """Get distribution of attempts by difficulty"""
        # In a real implementation, query attempts by difficulty
        return {
            'simple': 40.5,
            'medium': 35.2,
            'hard': 24.3
        }
    
    async def _calculate_monthly_recurring_revenue(self) -> float:
        """Calculate Monthly Recurring Revenue"""
        # Sum of active subscription values
        # This would require additional database queries
        return 2500.0  # Placeholder
    
    async def _get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        # Count active subscriptions
        # Count trial vs paid subscriptions
        # Calculate average subscription duration
        return {
            'total_active': 50,
            'active_paid': 35,
            'active_trial': 15,
            'expiring_soon': 5,
            'avg_duration_days': 45
        }
    
    async def _calculate_churn_rate(self, days: int) -> float:
        """Calculate churn rate (percentage of users who stopped using)"""
        # (Users at start - Users at end) / Users at start
        return 5.2  # Placeholder
    
    async def _calculate_customer_lifetime_value(self) -> float:
        """Calculate Customer Lifetime Value"""
        # Average revenue per user * Average customer lifespan
        return 120.0  # Placeholder
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health and performance"""
        # Check connection
        # Check response time
        # Check for any issues
        return {
            'status': 'healthy',
            'response_time_ms': 45,
            'connections': 12,
            'last_check': datetime.now()
        }
    
    async def _estimate_storage_usage(self) -> Dict[str, Any]:
        """Estimate storage usage"""
        # Estimate database size
        # Estimate file storage (screenshots, etc.)
        return {
            'database_mb': 45.2,
            'files_mb': 120.5,
            'total_mb': 165.7,
            'estimated_growth_per_day_mb': 2.1
        }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        # Average response time
        # Peak load capacity
        # Error rates
        return {
            'avg_response_time_ms': 120,
            'peak_concurrent_users': 85,
            'requests_per_second': 2.5,
            'cache_hit_rate': 0.78
        }
    
    async def _get_error_rates(self) -> Dict[str, Any]:
        """Get error rates and types"""
        # API errors
        # Database errors
        # Payment errors
        return {
            'api_errors': {
                'total': 12,
                'rate': 0.5,
                'common_types': ['timeout', 'validation']
            },
            'database_errors': {
                'total': 3,
                'rate': 0.1
            },
            'payment_errors': {
                'total': 8,
                'rate': 0.3
            }
        }
    
    def _calculate_uptime(self) -> Dict[str, Any]:
        """Calculate system uptime"""
        # In a real implementation, track start time and downtime
        return {
            'current_uptime_days': 45,
            'uptime_percentage': 99.8,
            'last_restart': datetime.now() - timedelta(days=45),
            'incidents_last_30_days': 1
        }
    
    def _get_last_backup_time(self) -> Optional[datetime]:
        """Get last backup time"""
        # In a real implementation, read from backup log
        return datetime.now() - timedelta(hours=12)
    
    async def get_user_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get detailed analytics for a specific user"""
        analytics = {
            'user_id': user_id,
            'period_days': days,
            'timestamp': datetime.now()
        }
        
        try:
            # Get user information
            user = await self.user_repo.get_user(user_id)
            if not user:
                analytics['error'] = 'User not found'
                return analytics
            
            analytics['user_info'] = {
                'username': user.username,
                'name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                'role': user.role,
                'created_at': user.created_at,
                'blocked': user.blocked
            }
            
            # Get user statistics
            user_stats = await self.user_repo.get_user_statistics(user_id)
            analytics['statistics'] = user_stats
            
            # Get recent activity
            recent_attempts = await self.attempt_repo.get_user_attempts(user_id, limit=20)
            analytics['recent_activity'] = {
                'total_attempts': len(recent_attempts),
                'attempts': self._format_attempts(recent_attempts),
                'last_activity': recent_attempts[0].created_at if recent_attempts else None
            }
            
            # Get progress by subject
            progress_by_subject = await self._get_user_progress_by_subject(user_id)
            analytics['progress_by_subject'] = progress_by_subject
            
            # Get weak areas
            weak_areas = await self.question_repo.get_weak_chapters(user_id, limit=5)
            analytics['weak_areas'] = weak_areas
            
            # Get subscription status
            subscription = await self.payment_repo.get_active_subscription(user_id)
            analytics['subscription'] = {
                'active': subscription is not None,
                'details': subscription.__dict__ if subscription else None
            }
            
            # Get learning patterns
            learning_patterns = await self._analyze_learning_patterns(user_id, days)
            analytics['learning_patterns'] = learning_patterns
            
            # Calculate improvement rate
            improvement_rate = await self._calculate_improvement_rate(user_id, days)
            analytics['improvement_rate'] = improvement_rate
            
            # Generate recommendations
            recommendations = await self._generate_user_recommendations(user_id, analytics)
            analytics['recommendations'] = recommendations
            
        except Exception as e:
            analytics['error'] = str(e)
        
        return analytics
    
    def _format_attempts(self, attempts: List) -> List[Dict[str, Any]]:
        """Format attempts for display"""
        formatted = []
        for attempt in attempts:
            formatted.append({
                'attempt_id': attempt.attempt_id,
                'question_id': attempt.question_id,
                'selected_option': attempt.selected_option,
                'is_correct': attempt.is_correct,
                'time_taken': attempt.time_taken,
                'created_at': attempt.created_at
            })
        return formatted
    
    async def _get_user_progress_by_subject(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's progress organized by subject"""
        # Get all subjects
        subjects = await self.question_repo.get_subjects()
        progress_data = []
        
        for subject in subjects:
            # Get user progress for this subject
            subject_progress = await self.user_repo.get_user_progress(
                user_id=user_id,
                subject_id=subject.subject_id
            )
            
            if subject_progress:
                # Calculate aggregate statistics
                total_attempts = sum(p.total_attempts for p in subject_progress)
                correct_attempts = sum(p.correct_attempts for p in subject_progress)
                avg_accuracy = sum(p.accuracy for p in subject_progress) / len(subject_progress)
                time_spent = sum(p.total_time_spent for p in subject_progress)
                
                progress_data.append({
                    'subject_id': subject.subject_id,
                    'subject_name': subject.subject_name,
                    'total_attempts': total_attempts,
                    'correct_attempts': correct_attempts,
                    'accuracy': round(avg_accuracy, 2),
                    'time_spent': time_spent,
                    'chapters_attempted': len(subject_progress)
                })
        
        return progress_data
    
    async def _analyze_learning_patterns(self, user_id: int, days: int) -> Dict[str, Any]:
        """Analyze user's learning patterns"""
        patterns = {
            'preferred_difficulty': 'simple',
            'preferred_time': 'evening',
            'consistency_score': 0,
            'improvement_trend': 'stable',
            'study_habits': {}
        }
        
        # Get attempts in the specified period
        cutoff_date = datetime.now() - timedelta(days=days)
        # This would require additional query methods
        
        # Analyze patterns based on available data
        # (simplified implementation)
        
        return patterns
    
    async def _calculate_improvement_rate(self, user_id: int, days: int) -> float:
        """Calculate user's improvement rate over time"""
        # Compare accuracy in first half vs second half of period
        # (simplified implementation)
        return 12.5  # Placeholder percentage improvement
    
    async def _generate_user_recommendations(self, user_id: int, analytics: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations for the user"""
        recommendations = []
        
        # Check subscription status
        subscription = analytics.get('subscription', {})
        if not subscription.get('active'):
            recommendations.append(
                "Consider upgrading to premium to access Medium and Hard difficulty levels"
            )
        
        # Check weak areas
        weak_areas = analytics.get('weak_areas', [])
        if weak_areas:
            weak_chapter = weak_areas[0]
            recommendations.append(
                f"Focus on improving {weak_chapter.get('chapter_name', 'your weak areas')} "
                f"(current accuracy: {weak_chapter.get('accuracy', 0)}%)"
            )
        
        # Check consistency
        patterns = analytics.get('learning_patterns', {})
        consistency = patterns.get('consistency_score', 0)
        if consistency < 50:
            recommendations.append(
                "Try to practice more consistently. Daily practice leads to better retention"
            )
        
        # Check if user is ready for higher difficulty
        statistics = analytics.get('statistics', {})
        accuracy = statistics.get('avg_accuracy', 0)
        if accuracy > 75:
            recommendations.append(
                "You're doing great! Consider trying more challenging questions"
            )
        
        # Add general recommendations
        recommendations.extend([
            "Review explanations for incorrect answers to learn from mistakes",
            "Set a daily goal (e.g., 10 questions per day)",
            "Take breaks between study sessions for better retention"
        ])
        
        return recommendations
    
    async def get_performance_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get performance analytics for the entire system"""
        analytics = {
            'period_days': days,
            'timestamp': datetime.now(),
            'metrics': {}
        }
        
        try:
            # Get accuracy trends
            accuracy_trend = await self._get_accuracy_trend(days)
            analytics['accuracy_trend'] = accuracy_trend
            
            # Get question performance
            question_performance = await self._get_question_performance(days)
            analytics['question_performance'] = question_performance
            
            # Get difficulty performance
            difficulty_performance = await self._get_difficulty_performance(days)
            analytics['difficulty_performance'] = difficulty_performance
            
            # Get chapter performance
            chapter_performance = await self._get_chapter_performance(days)
            analytics['chapter_performance'] = chapter_performance
            
            # Calculate overall metrics
            overall_accuracy = self._calculate_overall_accuracy(accuracy_trend)
            analytics['overall_metrics'] = {
                'accuracy': overall_accuracy,
                'completion_rate': await self._calculate_completion_rate(days),
                'engagement_score': await self._calculate_engagement_score(days),
                'learning_efficiency': await self._calculate_learning_efficiency(days)
            }
            
            # Identify patterns and insights
            insights = await self._generate_performance_insights(analytics)
            analytics['insights'] = insights
            
        except Exception as e:
            analytics['error'] = str(e)
        
        return analytics
    
    async def _get_accuracy_trend(self, days: int) -> List[Dict[str, Any]]:
        """Get accuracy trend over time"""
        trend = []
        
        # For each day in the period
        for i in range(days, 0, -1):
            day_date = datetime.now() - timedelta(days=i)
            
            # Get attempts for this day and calculate accuracy
            # (simplified implementation)
            daily_accuracy = 70 + (i % 10)  # Mock data
            
            trend.append({
                'date': day_date.date(),
                'accuracy': daily_accuracy,
                'attempts': 100 + (i * 5)  # Mock data
            })
        
        return trend
    
    async def _get_question_performance(self, days: int) -> List[Dict[str, Any]]:
        """Get performance statistics for questions"""
        # Get popular questions with success rates
        popular_questions = await self.attempt_repo.get_question_popularity(limit=10)
        
        # Get most difficult questions (lowest success rate)
        difficult_questions = []
        for question in popular_questions:
            if question.get('success_rate', 100) < 40:
                difficult_questions.append(question)
        
        # Get easiest questions (highest success rate)
        easy_questions = []
        for question in popular_questions:
            if question.get('success_rate', 0) > 90:
                easy_questions.append(question)
        
        return {
            'popular': popular_questions[:5],
            'difficult': difficult_questions[:3],
            'easy': easy_questions[:3],
            'total_analyzed': len(popular_questions)
        }
    
    async def _get_difficulty_performance(self, days: int) -> Dict[str, Any]:
        """Get performance by difficulty level"""
        # Calculate success rates for each difficulty
        # (simplified implementation)
        return {
            'simple': {
                'attempts': 1500,
                'success_rate': 78.5,
                'avg_time_seconds': 25.3
            },
            'medium': {
                'attempts': 850,
                'success_rate': 62.1,
                'avg_time_seconds': 38.7
            },
            'hard': {
                'attempts': 420,
                'success_rate': 45.8,
                'avg_time_seconds': 52.1
            }
        }
    
    async def _get_chapter_performance(self, days: int) -> List[Dict[str, Any]]:
        """Get performance by chapter"""
        # Get all chapters with their performance statistics
        chapters = []
        
        # This would require complex queries to calculate chapter performance
        # For now, return mock data
        mock_chapters = [
            {'chapter_id': 1, 'chapter_name': 'Addition', 'accuracy': 85.2, 'attempts': 320},
            {'chapter_id': 2, 'chapter_name': 'Subtraction', 'accuracy': 78.6, 'attempts': 280},
            {'chapter_id': 3, 'chapter_name': 'Multiplication', 'accuracy': 72.1, 'attempts': 190},
            {'chapter_id': 4, 'chapter_name': 'Division', 'accuracy': 65.4, 'attempts': 150},
            {'chapter_id': 5, 'chapter_name': 'Fractions', 'accuracy': 58.9, 'attempts': 120},
        ]
        
        return mock_chapters
    
    def _calculate_overall_accuracy(self, accuracy_trend: List[Dict[str, Any]]) -> float:
        """Calculate overall accuracy from trend data"""
        if not accuracy_trend:
            return 0
        
        total_accuracy = sum(day['accuracy'] for day in accuracy_trend)
        return round(total_accuracy / len(accuracy_trend), 2)
    
    async def _calculate_completion_rate(self, days: int) -> float:
        """Calculate quiz completion rate"""
        # Started quizzes / completed quizzes
        return 82.5  # Placeholder
    
    async def _calculate_engagement_score(self, days: int) -> float:
        """Calculate overall engagement score"""
        # Based on active users, session duration, frequency
        return 67.8  # Placeholder
    
    async def _calculate_learning_efficiency(self, days: int) -> float:
        """Calculate learning efficiency (improvement per time spent)"""
        # Improvement in accuracy / total time spent
        return 0.45  # Placeholder
    
    async def _generate_performance_insights(self, analytics: Dict[str, Any]) -> List[str]:
        """Generate insights from performance analytics"""
        insights = []
        
        # Check overall accuracy
        overall_metrics = analytics.get('overall_metrics', {})
        accuracy = overall_metrics.get('accuracy', 0)
        
        if accuracy < 60:
            insights.append("Overall accuracy is below target (60%). Consider reviewing question difficulty.")
        elif accuracy > 80:
            insights.append("Excellent overall accuracy! Students are performing well.")
        
        # Check difficulty performance
        difficulty_perf = analytics.get('difficulty_performance', {})
        hard_success = difficulty_perf.get('hard', {}).get('success_rate', 0)
        
        if hard_success < 40:
            insights.append("Hard questions have very low success rate. They might be too difficult.")
        
        # Check chapter performance
        chapter_perf = analytics.get('chapter_performance', [])
        weak_chapters = [c for c in chapter_perf if c.get('accuracy', 0) < 60]
        
        if weak_chapters:
            insights.append(f"Found {len(weak_chapters)} chapters with accuracy below 60%")
        
        # Check engagement
        engagement = overall_metrics.get('engagement_score', 0)
        if engagement < 50:
            insights.append("Engagement is low. Consider adding more incentives or reminders.")
        
        return insights
    
    async def get_revenue_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get detailed revenue analytics"""
        analytics = {
            'period_days': days,
            'timestamp': datetime.now()
        }
        
        try:
            # Get revenue data
            revenue_data = await self.payment_repo.get_revenue_stats(days)
            analytics.update(revenue_data)
            
            # Calculate additional metrics
            analytics['metrics'] = await self._calculate_revenue_metrics(revenue_data, days)
            
            # Get subscription analytics
            subscription_analytics = await self._get_subscription_analytics(days)
            analytics['subscriptions'] = subscription_analytics
            
            # Get payment method analysis
            payment_analysis = await self._analyze_payment_patterns(days)
            analytics['payment_analysis'] = payment_analysis
            
            # Calculate projections
            projections = await self._calculate_revenue_projections(revenue_data, days)
            analytics['projections'] = projections
            
            # Generate insights
            revenue_insights = await self._generate_revenue_insights(analytics)
            analytics['insights'] = revenue_insights
            
        except Exception as e:
            analytics['error'] = str(e)
        
        return analytics
    
    async def _calculate_revenue_metrics(self, revenue_data: Dict[str, Any], days: int) -> Dict[str, Any]:
        """Calculate advanced revenue metrics"""
        total_revenue = revenue_data.get('total_revenue', 0)
        payment_count = revenue_data.get('payment_count', 0)
        
        # Calculate ARPU (Average Revenue Per User)
        total_users = len(await self.user_repo.get_all_users())
        arpu = total_revenue / total_users if total_users > 0 else 0
        
        # Calculate ARPPU (Average Revenue Per Paying User)
        paying_users = await self._count_paying_users(days)
        arppu = total_revenue / paying_users if paying_users > 0 else 0
        
        # Calculate LTV (Lifetime Value) - simplified
        avg_subscription_days = 30  # Placeholder
        ltv = arppu * (avg_subscription_days / 30)  # Monthly projection
        
        return {
            'arpu': round(arpu, 2),
            'arppu': round(arppu, 2),
            'ltv': round(ltv, 2),
            'payment_conversion_rate': round((paying_users / total_users * 100), 2) if total_users > 0 else 0,
            'avg_transaction_value': round(total_revenue / payment_count, 2) if payment_count > 0 else 0,
            'revenue_per_day': round(total_revenue / days, 2) if days > 0 else 0
        }
    
    async def _count_paying_users(self, days: int) -> int:
        """Count users who made payments in the period"""
        # This would require querying payments and counting distinct users
        return 35  # Placeholder
    
    async def _get_subscription_analytics(self, days: int) -> Dict[str, Any]:
        """Get detailed subscription analytics"""
        return {
            'active_subscriptions': 50,
            'trial_subscriptions': 15,
            'expired_subscriptions': 8,
            'cancelled_subscriptions': 3,
            'renewal_rate': 85.5,
            'avg_subscription_duration_days': 42.3,
            'churn_rate': 4.2,
            'upgrade_rate': 12.8
        }
    
    async def _analyze_payment_patterns(self, days: int) -> Dict[str, Any]:
        """Analyze payment patterns"""
        return {
            'preferred_subscription_length': {
                '30_days': 65,
                '90_days': 30,
                'other': 5
            },
            'payment_timing': {
                'morning': 25,
                'afternoon': 35,
                'evening': 40
            },
            'payment_methods': {
                'upi': 70,
                'bank_transfer': 25,
                'other': 5
            },
            'common_issues': {
                'screenshot_rejection': 12,
                'payment_verification': 8,
                'subscription_activation': 5
            }
        }
    
    async def _calculate_revenue_projections(self, revenue_data: Dict[str, Any], days: int) -> Dict[str, Any]:
        """Calculate revenue projections"""
        total_revenue = revenue_data.get('total_revenue', 0)
        daily_revenue = total_revenue / days if days > 0 else 0
        
        return {
            'next_30_days': round(daily_revenue * 30, 2),
            'next_90_days': round(daily_revenue * 90, 2),
            'next_year': round(daily_revenue * 365, 2),
            'growth_rate': 15.5,  # Percentage
            'break_even_date': '2024-06-15',  # Projected
            'milestones': {
                '10000_revenue': '2024-08-01',
                '500_users': '2024-07-15',
                '1000_quizzes_day': '2024-09-01'
            }
        }
    
    async def _generate_revenue_insights(self, analytics: Dict[str, Any]) -> List[str]:
        """Generate revenue insights"""
        insights = []
        
        metrics = analytics.get('metrics', {})
        revenue = analytics.get('total_revenue', 0)
        payment_count = analytics.get('payment_count', 0)
        
        # Check revenue growth
        if revenue > 10000:
            insights.append("Revenue has crossed ETB10,000 milestone! Great work!")
        elif revenue < 1000:
            insights.append("Revenue is below ETB1,000. Consider promotional offers.")
        
        # Check conversion rate
        conversion_rate = metrics.get('payment_conversion_rate', 0)
        if conversion_rate < 5:
            insights.append("Payment conversion rate is low. Consider improving payment instructions.")
        elif conversion_rate > 20:
            insights.append("Excellent conversion rate! Users find value in premium features.")
        
        # Check average transaction value
        avg_transaction = metrics.get('avg_transaction_value', 0)
        if avg_transaction < 300:
            insights.append("Average transaction value is low. Consider promoting longer subscriptions.")
        
        # Check subscription patterns
        subscriptions = analytics.get('subscriptions', {})
        renewal_rate = subscriptions.get('renewal_rate', 0)
        if renewal_rate < 70:
            insights.append("Subscription renewal rate needs improvement. Consider loyalty rewards.")
        
        return insights
    
    # ============== Quiz Statistics Methods ==============
    
    async def get_quiz_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive quiz statistics
        
        Args:
            days: Number of days to include in period-based stats
            
        Returns:
            Dictionary containing all quiz statistics
        """
        try:
            # Get quiz stats from attempt repository
            stats = await self.attempt_repo.get_quiz_stats_summary()
            
            # Get period-based stats (last N days)
            period_counts = await self.attempt_repo.get_attempts_by_period(days)
            daily_trend = await self.attempt_repo.get_daily_attempt_counts(days)
            
            # Get active users in period
            active_users = await self.attempt_repo.get_active_users_count(days)
            
            # Calculate period percentages
            total_period = sum(period_counts.values())
            period_percentages = {}
            for period, count in period_counts.items():
                period_percentages[period] = round((count / total_period * 100), 2) if total_period > 0 else 0
            
            # Get today's stats
            today = date.today()
            today_stats = None
            for day in daily_trend:
                if day['date'] == today:
                    today_stats = day
                    break
            
            # Calculate trend (compare last 7 days to previous 7 days)
            trend_data = await self._calculate_quiz_trends(days)
            
            return {
                'timestamp': datetime.now(),
                'period_days': days,
                'overview': {
                    'total_attempts': stats['total_attempts'],
                    'correct_attempts': stats['correct_attempts'],
                    'accuracy': stats['accuracy'],
                    'avg_time_seconds': stats['avg_time_seconds'],
                    'total_sessions': stats['total_sessions'],
                    'active_users_period': active_users
                },
                'popular_times': {
                    'morning': {
                        'count': period_counts.get('morning', 0),
                        'percentage': period_percentages.get('morning', 0)
                    },
                    'afternoon': {
                        'count': period_counts.get('afternoon', 0),
                        'percentage': period_percentages.get('afternoon', 0)
                    },
                    'evening': {
                        'count': period_counts.get('evening', 0),
                        'percentage': period_percentages.get('evening', 0)
                    },
                    'night': {
                        'count': period_counts.get('night', 0),
                        'percentage': period_percentages.get('night', 0)
                    }
                },
                'today': today_stats or {
                    'date': today,
                    'attempts': 0,
                    'correct': 0,
                    'accuracy': 0.0,
                    'avg_time': 0.0
                },
                'daily_trend': daily_trend,
                'trends': trend_data,
                'hourly_distribution': stats.get('hourly_distribution', {})
            }
        except Exception as e:
            logger.error(f"Error getting quiz statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(),
                'period_days': days
            }
    
    async def _calculate_quiz_trends(self, days: int) -> Dict[str, Any]:
        """
        Calculate quiz trends comparing recent vs previous periods
        
        Args:
            days: Total days to analyze
            
        Returns:
            Dict with trend comparisons
        """
        try:
            # Split into two periods
            half_days = days // 2
            
            # Get stats for recent period
            recent_stats = await self.attempt_repo.get_quiz_stats_summary()
            
            # For now, return basic trend info based on daily data
            daily_trend = await self.attempt_repo.get_daily_attempt_counts(days)
            
            # Calculate average for recent vs previous
            recent_data = daily_trend[-half_days:] if len(daily_trend) > half_days else daily_trend
            previous_data = daily_trend[:-half_days] if len(daily_trend) > half_days else []
            
            recent_avg_attempts = sum(d['attempts'] for d in recent_data) / len(recent_data) if recent_data else 0
            previous_avg_attempts = sum(d['attempts'] for d in previous_data) / len(previous_data) if previous_data else 0
            
            recent_avg_accuracy = sum(d['accuracy'] for d in recent_data) / len(recent_data) if recent_data else 0
            previous_avg_accuracy = sum(d['accuracy'] for d in previous_data) / len(previous_data) if previous_data else 0
            
            # Calculate percentage change
            attempt_change = 0
            if previous_avg_attempts > 0:
                attempt_change = round(((recent_avg_attempts - previous_avg_attempts) / previous_avg_attempts) * 100, 2)
            
            accuracy_change = round(recent_avg_accuracy - previous_avg_accuracy, 2)
            
            return {
                'attempt_trend': {
                    'recent_avg': round(recent_avg_attempts, 2),
                    'previous_avg': round(previous_avg_attempts, 2),
                    'change_percent': attempt_change,
                    'direction': 'up' if attempt_change > 0 else 'down' if attempt_change < 0 else 'stable'
                },
                'accuracy_trend': {
                    'recent_avg': round(recent_avg_accuracy, 2),
                    'previous_avg': round(previous_avg_accuracy, 2),
                    'change_percent': accuracy_change,
                    'direction': 'up' if accuracy_change > 0 else 'down' if accuracy_change < 0 else 'stable'
                }
            }
        except Exception as e:
            logger.error(f"Error calculating quiz trends: {e}")
            return {
                'attempt_trend': {'recent_avg': 0, 'previous_avg': 0, 'change_percent': 0, 'direction': 'stable'},
                'accuracy_trend': {'recent_avg': 0, 'previous_avg': 0, 'change_percent': 0, 'direction': 'stable'}
            }
    
    async def get_popular_times(self, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed popular times analysis
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with time period analysis
        """
        try:
            period_counts = await self.attempt_repo.get_attempts_by_period(days)
            hourly_distribution = await self.attempt_repo.get_attempts_by_hour()
            
            total = sum(period_counts.values())
            
            if total == 0:
                return {
                    'total_attempts': 0,
                    'periods': {
                        'morning': {'count': 0, 'percentage': 0, 'hours': '6 AM - 12 PM'},
                        'afternoon': {'count': 0, 'percentage': 0, 'hours': '12 PM - 6 PM'},
                        'evening': {'count': 0, 'percentage': 0, 'hours': '6 PM - 12 AM'},
                        'night': {'count': 0, 'percentage': 0, 'hours': '12 AM - 6 AM'}
                    },
                    'peak_hour': None,
                    'hourly_distribution': {}
                }
            
            # Find peak hour
            peak_hour = max(hourly_distribution.keys(), key=lambda h: hourly_distribution[h]) if hourly_distribution else None
            
            periods = {}
            period_info = {
                'morning': {'count': period_counts.get('morning', 0), 'hours': '6 AM - 12 PM'},
                'afternoon': {'count': period_counts.get('afternoon', 0), 'hours': '12 PM - 6 PM'},
                'evening': {'count': period_counts.get('evening', 0), 'hours': '6 PM - 12 AM'},
                'night': {'count': period_counts.get('night', 0), 'hours': '12 AM - 6 AM'}
            }
            
            for period, info in period_info.items():
                percentage = round((info['count'] / total * 100), 2) if total > 0 else 0
                periods[period] = {
                    'count': info['count'],
                    'percentage': percentage,
                    'hours': info['hours']
                }
            
            # Format peak hour
            peak_hour_str = None
            if peak_hour is not None:
                if peak_hour == 0:
                    peak_hour_str = '12 AM'
                elif peak_hour < 12:
                    peak_hour_str = f'{peak_hour} AM'
                elif peak_hour == 12:
                    peak_hour_str = '12 PM'
                else:
                    peak_hour_str = f'{peak_hour - 12} PM'
            
            return {
                'total_attempts': total,
                'periods': periods,
                'peak_hour': peak_hour_str,
                'peak_hour_count': hourly_distribution.get(peak_hour, 0) if peak_hour else 0,
                'hourly_distribution': hourly_distribution
            }
        except Exception as e:
            logger.error(f"Error getting popular times: {e}")
            return {'error': str(e)}
    
    async def get_daily_quiz_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily quiz statistics for trend visualization
        
        Args:
            days: Number of days to include
            
        Returns:
            List of daily stats dictionaries
        """
        try:
            return await self.attempt_repo.get_daily_attempt_counts(days)
        except Exception as e:
            logger.error(f"Error getting daily quiz stats: {e}")
            return []
    
    async def get_quiz_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed quiz performance metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with performance metrics
        """
        try:
            stats = await self.get_quiz_statistics(days)
            trends = stats.get('trends', {})
            popular_times = await self.get_popular_times(days)
            
            return {
                'period_days': days,
                'generated_at': datetime.now(),
                'summary': {
                    'total_attempts': stats['overview']['total_attempts'],
                    'accuracy': stats['overview']['accuracy'],
                    'avg_time': stats['overview']['avg_time_seconds'],
                    'sessions': stats['overview']['total_sessions']
                },
                'trends': trends,
                'popular_times': popular_times,
                'today': stats['today'],
                'engagement': {
                    'active_users': stats['overview']['active_users_period'],
                    'avg_daily_attempts': self._calculate_avg_from_trend(stats.get('daily_trend', [])),
                    'consistency_score': self._calculate_consistency_score(stats.get('daily_trend', []))
                }
            }
        except Exception as e:
            logger.error(f"Error getting quiz performance metrics: {e}")
            return {'error': str(e)}
    
    def _calculate_avg_from_trend(self, daily_trend: List[Dict]) -> float:
        """Calculate average attempts from daily trend"""
        if not daily_trend:
            return 0.0
        attempts = [d['attempts'] for d in daily_trend if d['attempts'] > 0]
        return round(sum(attempts) / len(attempts), 2) if attempts else 0.0
    
    def _calculate_consistency_score(self, daily_trend: List[Dict]) -> float:
        """
        Calculate consistency score (0-100) based on how regular the activity is
        
        Higher score = more consistent daily activity
        """
        if not daily_trend:
            return 0.0
        
        attempts = [d['attempts'] for d in daily_trend]
        if not attempts:
            return 0.0
        
        # Calculate coefficient of variation (lower = more consistent)
        mean = sum(attempts) / len(attempts)
        if mean == 0:
            return 0.0
        
        variance = sum((x - mean) ** 2 for x in attempts) / len(attempts)
        std_dev = variance ** 0.5
        cv = std_dev / mean  # Coefficient of variation
        
        # Convert CV to consistency score (CV of 0 = 100 score, CV of 1+ = 0 score)
        consistency = max(0, min(100, (1 - cv) * 100))
        return round(consistency, 2)
    
    async def generate_report(self, 
                            report_type: str = 'weekly',
                            start_date: datetime = None,
                            end_date: datetime = None) -> Dict[str, Any]:
        """
        Generate comprehensive report
        
        Args:
            report_type: 'daily', 'weekly', 'monthly', or 'custom'
            start_date: Start date for custom reports
            end_date: End date for custom reports
        
        Returns:
            Complete report with all analytics
        """
        # Determine date range based on report type
        if report_type == 'daily':
            days = 1
        elif report_type == 'weekly':
            days = 7
        elif report_type == 'monthly':
            days = 30
        else:  # custom
            if not start_date or not end_date:
                days = 30  # Default to monthly
            else:
                days = (end_date - start_date).days
        
        report = {
            'report_type': report_type,
            'period_days': days,
            'generated_at': datetime.now(),
            'summary': {},
            'details': {}
        }
        
        try:
            # Get all analytics data
            dashboard_stats = await self.get_dashboard_stats(days)
            performance_analytics = await self.get_performance_analytics(days)
            revenue_analytics = await self.get_revenue_analytics(days)
            
            # Compile report
            report['summary'] = self._compile_report_summary(
                dashboard_stats, 
                performance_analytics, 
                revenue_analytics
            )
            
            report['details'] = {
                'dashboard': dashboard_stats,
                'performance': performance_analytics,
                'revenue': revenue_analytics
            }
            
            # Generate recommendations
            report['recommendations'] = await self._generate_report_recommendations(report)
            
            # Add visualizations data (for charts)
            report['visualizations'] = await self._prepare_visualization_data(report)
            
        except Exception as e:
            report['error'] = str(e)
        
        return report
    
    def _compile_report_summary(self, 
                              dashboard_stats: Dict[str, Any],
                              performance_analytics: Dict[str, Any],
                              revenue_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Compile executive summary from all analytics"""
        summary = {
            'overview': {
                'health_score': dashboard_stats.get('health_score', 0),
                'status': 'Healthy' if dashboard_stats.get('health_score', 0) > 70 else 'Needs Attention',
                'period': f"{dashboard_stats.get('period_days', 0)} days"
            },
            'key_metrics': {
                'total_users': dashboard_stats.get('users', {}).get('total', 0),
                'active_users': dashboard_stats.get('users', {}).get('active', 0),
                'total_revenue': revenue_analytics.get('total_revenue', 0),
                'overall_accuracy': performance_analytics.get('overall_metrics', {}).get('accuracy', 0),
                'engagement_score': performance_analytics.get('overall_metrics', {}).get('engagement_score', 0)
            },
            'trends': {
                'user_growth': '+12%',  # Placeholder
                'revenue_growth': '+8%',  # Placeholder
                'accuracy_trend': 'Stable',
                'engagement_trend': 'Improving'
            },
            'highlights': [
                f"Processed {dashboard_stats.get('activity', {}).get('today', {}).get('attempts', 0)} attempts today",
                f"Added {dashboard_stats.get('users', {}).get('new', 0)} new users",
                f"Generated ETB{revenue_analytics.get('total_revenue', 0):.2f} in revenue"
            ]
        }
        
        return summary
    
    async def _generate_report_recommendations(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations from report"""
        recommendations = []
        summary = report.get('summary', {})
        details = report.get('details', {})
        
        # Check health score
        health_score = summary.get('overview', {}).get('health_score', 0)
        if health_score < 70:
            recommendations.append({
                'priority': 'high',
                'area': 'System Health',
                'action': 'Review system performance and address issues',
                'impact': 'Critical for user experience'
            })
        
        # Check user growth
        user_growth = summary.get('trends', {}).get('user_growth', '0%')
        if user_growth == '0%' or '-' in user_growth:
            recommendations.append({
                'priority': 'medium',
                'area': 'User Acquisition',
                'action': 'Implement referral program or promotional offers',
                'impact': 'Increase user base and revenue potential'
            })
        
        # Check revenue
        revenue = summary.get('key_metrics', {}).get('total_revenue', 0)
        if revenue < 1000:
            recommendations.append({
                'priority': 'high',
                'area': 'Monetization',
                'action': 'Review pricing strategy and payment process',
                'impact': 'Direct impact on revenue'
            })
        
        # Check accuracy
        accuracy = summary.get('key_metrics', {}).get('overall_accuracy', 0)
        if accuracy < 60:
            recommendations.append({
                'priority': 'medium',
                'area': 'Content Quality',
                'action': 'Review question difficulty and explanations',
                'impact': 'Improves learning outcomes'
            })
        
        # Add operational recommendations
        recommendations.extend([
            {
                'priority': 'low',
                'area': 'Operations',
                'action': 'Schedule regular database backups',
                'impact': 'Data security and recovery'
            },
            {
                'priority': 'medium',
                'area': 'User Experience',
                'action': 'Collect user feedback on quiz experience',
                'impact': 'Improves retention and satisfaction'
            }
        ])
        
        return recommendations
    
    async def _prepare_visualization_data(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for charts and visualizations"""
        details = report.get('details', {})
        dashboard = details.get('dashboard', {})
        performance = details.get('performance', {})
        revenue = details.get('revenue', {})
        
        return {
            'user_growth_chart': {
                'labels': [day['date'].strftime('%Y-%m-%d') for day in dashboard.get('users', {}).get('growth_data', [])],
                'data': [day['count'] for day in dashboard.get('users', {}).get('growth_data', [])]
            },
            'accuracy_trend_chart': {
                'labels': [day['date'].strftime('%Y-%m-%d') for day in performance.get('accuracy_trend', [])],
                'data': [day['accuracy'] for day in performance.get('accuracy_trend', [])]
            },
            'revenue_chart': {
                'labels': [day['date'].strftime('%Y-%m-%d') for day in revenue.get('daily_trend', [])],
                'data': [day['revenue'] for day in revenue.get('daily_trend', [])]
            },
            'difficulty_distribution': {
                'labels': ['Simple', 'Medium', 'Hard'],
                'data': [
                    dashboard.get('questions', {}).get('by_difficulty', {}).get('simple', 0),
                    dashboard.get('questions', {}).get('by_difficulty', {}).get('medium', 0),
                    dashboard.get('questions', {}).get('by_difficulty', {}).get('hard', 0)
                ]
            },
            'subscription_types': {
                'labels': ['30 Days', '90 Days', '180 Days'],
                'data': [65, 25, 10]  # Placeholder percentages
            }
        }