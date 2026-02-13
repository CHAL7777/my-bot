from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Leaderboard, User, QuizAttempt, Question

# Scoring system: Simple=1, Medium=2, Hard=3 points per correct answer
SCORE_VALUES = {
    'simple': 1,
    'medium': 2,
    'hard': 3
}

class LeaderboardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _get_period_start(self, period: str) -> Optional[datetime]:
        """Get the start datetime for the period"""
        now = datetime.now()
        
        if period == 'daily':
            # Today at midnight
            return datetime.combine(now.date(), datetime.min.time())
        elif period == 'weekly':
            # Start of current week (Monday)
            days_since_monday = now.weekday()
            return datetime.combine(now.date() - timedelta(days=days_since_monday), datetime.min.time())
        elif period == 'monthly':
            # First day of current month
            return datetime(now.year, now.month, 1)
        else:  # overall
            return None  # No date filter
    
    async def _get_score_subquery(self, period_start: Optional[datetime] = None):
        """Get subquery for calculating user scores"""
        from app.db.models import QuizAttempt, Question
        
        # Base conditions
        conditions = [
            QuizAttempt.is_correct == True,
            User.user_id == QuizAttempt.user_id,
            User.blocked == False
        ]
        
        if period_start:
            conditions.append(QuizAttempt.created_at >= period_start)
        
        # Build the score calculation query
        score_case = case(
            (Question.difficulty == 'simple', 1),
            (Question.difficulty == 'medium', 2),
            (Question.difficulty == 'hard', 3),
            else_=0
        )
        
        query = select(
            QuizAttempt.user_id,
            func.sum(score_case).label('total_score'),
            func.count(QuizAttempt.attempt_id).label('total_questions'),
            func.sum(score_case).label('correct_score'),
            (func.count(QuizAttempt.attempt_id) * 100.0 / 
             func.nullif(func.count(QuizAttempt.attempt_id), 0) * 100).label('accuracy')
        ).join(
            Question, QuizAttempt.question_id == Question.question_id
        ).where(
            and_(*conditions)
        ).group_by(
            QuizAttempt.user_id
        )
        
        return query
    
    async def get_leaderboard_realtime(self, period: str, limit: int = 50, 
                                        user_id: int = None) -> Dict[str, Any]:
        """
        Get leaderboard calculated in real-time from QuizAttempt data.
        
        Args:
            period: 'daily', 'weekly', 'monthly', or 'overall'
            limit: Maximum number of entries to return
            user_id: Optional user ID to include their rank in the response
            
        Returns:
            Dict with 'leaderboard' list and 'total_users' count
        """
        from app.db.models import QuizAttempt, Question
        
        period_start = self._get_period_start(period)
        
        # Base conditions for joining with User
        base_conditions = [
            User.user_id == QuizAttempt.user_id,
            User.blocked == False
        ]
        
        if period_start:
            base_conditions.append(QuizAttempt.created_at >= period_start)
        
        # Score calculation based on difficulty
        score_case = case(
            (Question.difficulty == 'simple', 1),
            (Question.difficulty == 'medium', 2),
            (Question.difficulty == 'hard', 3),
            else_=0
        )
        
        # Subquery to get user stats
        subquery = select(
            QuizAttempt.user_id,
            func.sum(score_case).label('total_score'),
            func.count(QuizAttempt.attempt_id).label('total_questions')
        ).join(
            Question, QuizAttempt.question_id == Question.question_id
        ).where(
            and_(*base_conditions)
        ).group_by(
            QuizAttempt.user_id
        ).having(
            func.count(QuizAttempt.attempt_id) >= 5  # Minimum 5 questions required
        ).subquery()
        
        # Main query to get ranked users
        query = select(
            subquery.c.user_id,
            subquery.c.total_score,
            subquery.c.total_questions,
            User.username,
            User.first_name,
            User.last_name
        ).join(
            User, subquery.c.user_id == User.user_id
        ).order_by(
            desc(subquery.c.total_score),
            desc(subquery.c.total_questions)
        ).limit(limit)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        # Build leaderboard list
        leaderboard = []
        for rank, row in enumerate(rows, start=1):
            username = row.username or f"User {row.user_id}"
            if row.first_name:
                display_name = f"{row.first_name} {row.last_name or ''}".strip()
                if display_name:
                    username = display_name
            
            leaderboard.append({
                'rank': rank,
                'user_id': row.user_id,
                'username': username,
                'score': row.total_score or 0,
                'questions': row.total_questions or 0,
                'accuracy': 0  # Simplified - can calculate if needed
            })
        
        # Get total qualified users count
        count_query = select(func.count()).select_from(subquery)
        count_result = await self.session.execute(count_query)
        total_users = count_result.scalar() or 0
        
        # Get user's rank if requested
        user_rank = None
        if user_id:
            # Create a ranking for the specific user
            user_query = select(
                subquery.c.total_score,
                subquery.c.total_questions
            ).where(
                subquery.c.user_id == user_id
            )
            user_result = await self.session.execute(user_query)
            user_row = user_result.first()
            
            if user_row:
                # Find user's rank by counting users with higher scores
                rank_query = select(func.count()).select_from(subquery).where(
                    or_(
                        subquery.c.total_score > user_row.total_score,
                        and_(
                            subquery.c.total_score == user_row.total_score,
                            subquery.c.total_questions > user_row.total_questions
                        )
                    )
                )
                rank_result = await self.session.execute(rank_query)
                user_rank_num = rank_result.scalar() or 0
                
                user_rank = {
                    'rank': user_rank_num + 1,
                    'score': user_row.total_score or 0,
                    'accuracy': 0,
                    'questions': user_row.total_questions or 0
                }
        
        return {
            'leaderboard': leaderboard,
            'total_users': total_users,
            'user_rank': user_rank
        }
    
    async def get_user_rank_realtime(self, user_id: int, period: str) -> Optional[Dict[str, Any]]:
        """
        Get user's rank calculated in real-time from QuizAttempt data.
        
        Args:
            user_id: The user to get rank for
            period: 'daily', 'weekly', 'monthly', or 'overall'
            
        Returns:
            Dict with rank info or None if user doesn't qualify
        """
        from app.db.models import QuizAttempt, Question
        
        period_start = self._get_period_start(period)
        
        base_conditions = [
            QuizAttempt.user_id == user_id,
            QuizAttempt.is_correct == True,
            User.user_id == QuizAttempt.user_id,
            User.blocked == False
        ]
        
        if period_start:
            base_conditions.append(QuizAttempt.created_at >= period_start)
        
        # Calculate user's score
        score_case = case(
            (Question.difficulty == 'simple', 1),
            (Question.difficulty == 'medium', 2),
            (Question.difficulty == 'hard', 3),
            else_=0
        )
        
        user_query = select(
            func.sum(score_case).label('total_score'),
            func.count(QuizAttempt.attempt_id).label('total_questions')
        ).join(
            Question, QuizAttempt.question_id == Question.question_id
        ).join(
            User, QuizAttempt.user_id == User.user_id
        ).where(
            and_(*base_conditions)
        )
        
        result = await self.session.execute(user_query)
        user_row = result.first()
        
        if not user_row or (user_row.total_questions or 0) < 5:
            return None  # User doesn't qualify (less than 5 questions)
        
        user_score = user_row.total_score or 0
        user_questions = user_row.total_questions or 0
        
        # Count how many users have higher scores
        conditions = [
            QuizAttempt.is_correct == True,
            User.user_id == QuizAttempt.user_id,
            User.blocked == False
        ]
        
        if period_start:
            conditions.append(QuizAttempt.created_at >= period_start)
        
        higher_query = select(
            QuizAttempt.user_id
        ).join(
            Question, QuizAttempt.question_id == Question.question_id
        ).join(
            User, QuizAttempt.user_id == User.user_id
        ).where(
            and_(*conditions)
        ).group_by(
            QuizAttempt.user_id
        ).having(
            and_(
                func.count(QuizAttempt.attempt_id) >= 5,
                or_(
                    func.sum(score_case) > user_score,
                    and_(
                        func.sum(score_case) == user_score,
                        func.count(QuizAttempt.attempt_id) > user_questions
                    )
                )
            )
        )
        
        count_result = await self.session.execute(select(func.count()).select_from(higher_query.subquery()))
        higher_count = count_result.scalar() or 0
        
        return {
            'rank': higher_count + 1,
            'score': user_score,
            'accuracy': 0,  # Simplified
            'questions': user_questions
        }
    
    async def get_total_participants(self, period: str) -> int:
        """
        Get total number of participants who qualify for the leaderboard.
        
        Args:
            period: 'daily', 'weekly', 'monthly', or 'overall'
            
        Returns:
            Count of users with at least 5 questions in the period
        """
        from app.db.models import QuizAttempt, Question
        
        period_start = self._get_period_start(period)
        
        conditions = [
            QuizAttempt.is_correct == True,
            User.user_id == QuizAttempt.user_id,
            User.blocked == False
        ]
        
        if period_start:
            conditions.append(QuizAttempt.created_at >= period_start)
        
        score_case = case(
            (Question.difficulty == 'simple', 1),
            (Question.difficulty == 'medium', 2),
            (Question.difficulty == 'hard', 3),
            else_=0
        )
        
        query = select(
            QuizAttempt.user_id
        ).join(
            Question, QuizAttempt.question_id == Question.question_id
        ).join(
            User, QuizAttempt.user_id == User.user_id
        ).where(
            and_(*conditions)
        ).group_by(
            QuizAttempt.user_id
        ).having(
            func.count(QuizAttempt.attempt_id) >= 5
        )
        
        result = await self.session.execute(select(func.count()).select_from(query.subquery()))
        return result.scalar() or 0
    
    async def update_leaderboard(self, period: str, rankings: List[Dict[str, Any]]):
        """Update leaderboard with new rankings"""
        # Clear existing rankings for this period
        stmt = delete(Leaderboard).where(Leaderboard.period == period)
        await self.session.execute(stmt)
        
        # Insert new rankings
        for rank, data in enumerate(rankings, start=1):
            leaderboard_entry = Leaderboard(
                user_id=data['user_id'],
                period=period,
                total_score=data['total_score'],
                total_accuracy=data['accuracy'],
                total_questions=data['total_questions'],
                rank_position=rank
            )
            self.session.add(leaderboard_entry)
        
        await self.session.commit()
    
    async def get_leaderboard(self, period: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get leaderboard for a period - falls back to realtime if Leaderboard table is empty"""
        from app.db.models import QuizAttempt, Question
        
        period_start = self._get_period_start(period)
        
        base_conditions = [
            User.user_id == QuizAttempt.user_id,
            User.blocked == False
        ]
        
        if period_start:
            base_conditions.append(QuizAttempt.created_at >= period_start)
        
        # Score calculation based on difficulty
        score_case = case(
            (Question.difficulty == 'simple', 1),
            (Question.difficulty == 'medium', 2),
            (Question.difficulty == 'hard', 3),
            else_=0
        )
        
        # Subquery to get user stats with minimum 5 questions
        subquery = select(
            QuizAttempt.user_id,
            func.sum(score_case).label('total_score'),
            func.count(QuizAttempt.attempt_id).label('total_questions')
        ).join(
            Question, QuizAttempt.question_id == Question.question_id
        ).where(
            and_(*base_conditions)
        ).group_by(
            QuizAttempt.user_id
        ).having(
            func.count(QuizAttempt.attempt_id) >= 5
        ).subquery()
        
        # Main query to get ranked users
        query = select(
            subquery.c.user_id,
            subquery.c.total_score,
            subquery.c.total_questions,
            User.username,
            User.first_name,
            User.last_name
        ).join(
            User, subquery.c.user_id == User.user_id
        ).order_by(
            desc(subquery.c.total_score),
            desc(subquery.c.total_questions)
        ).limit(limit)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        leaderboard = []
        for rank, row in enumerate(rows, start=1):
            username = row.username or f"User {row.user_id}"
            if row.first_name:
                display_name = f"{row.first_name} {row.last_name or ''}".strip()
                if display_name:
                    username = display_name
            
            leaderboard.append({
                'rank': rank,
                'user_id': row.user_id,
                'username': username,
                'score': row.total_score or 0,
                'accuracy': 0,
                'questions': row.total_questions or 0
            })
        
        return leaderboard
    
    async def get_user_rank(self, user_id: int, period: str) -> Optional[Dict[str, Any]]:
        """Get user's rank - uses realtime calculation"""
        return await self.get_user_rank_realtime(user_id, period)
    
    async def get_leaderboard_stats(self) -> Dict[str, Any]:
        """Get leaderboard statistics"""
        # Get total participants for each period
        daily_count = await self.get_total_participants('daily')
        weekly_count = await self.get_total_participants('weekly')
        monthly_count = await self.get_total_participants('monthly')
        overall_count = await self.get_total_participants('overall')
        
        period_stats = {
            'daily': daily_count,
            'weekly': weekly_count,
            'monthly': monthly_count,
            'overall': overall_count
        }
        
        # Get top performers overall
        overall_leaderboard = await self.get_leaderboard_realtime('overall', limit=10)
        top_performers = []
        for entry in overall_leaderboard['leaderboard']:
            top_performers.append({
                'user_id': entry['user_id'],
                'username': entry['username'],
                'total_score': entry['score'],
                'avg_accuracy': entry['accuracy']
            })
        
        return {
            'period_stats': period_stats,
            'top_performers': top_performers,
            'last_updated': datetime.now()
        }
    
    async def cleanup_old_leaderboards(self, keep_days: int = 30):
        """Remove old leaderboard entries"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        stmt = delete(Leaderboard).where(
            and_(
                Leaderboard.period.in_(['daily', 'weekly']),
                Leaderboard.last_updated < cutoff_date
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        return result.rowcount
