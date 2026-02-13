from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QuizAttempt

class AttemptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_attempt(self, user_id: int, question_id: int, 
                            selected_option: str, is_correct: bool,
                            time_taken: int = 0, quiz_session_id: str = None) -> QuizAttempt:
        """Create new quiz attempt record"""
        attempt = QuizAttempt(
            user_id=user_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct,
            time_taken=time_taken,
            quiz_session_id=quiz_session_id
        )
        self.session.add(attempt)
        await self.session.commit()
        return attempt
    
    async def get_attempt(self, attempt_id: int) -> Optional[QuizAttempt]:
        """Get attempt by ID"""
        query = select(QuizAttempt).where(QuizAttempt.attempt_id == attempt_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_attempts(self, user_id: int, limit: int = 10) -> List[QuizAttempt]:
        """Get recent attempts for a user"""
        query = select(QuizAttempt).where(
            QuizAttempt.user_id == user_id
        ).order_by(desc(QuizAttempt.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_user_quiz_sessions(self, user_id: int) -> List[str]:
        """Get unique quiz session IDs for a user"""
        query = select(QuizAttempt.quiz_session_id).where(
            QuizAttempt.user_id == user_id
        ).distinct()
        
        result = await self.session.execute(query)
        return [row[0] for row in result.all() if row[0]]
    
    async def get_attempts_by_session(self, quiz_session_id: str) -> List[QuizAttempt]:
        """Get all attempts for a quiz session"""
        query = select(QuizAttempt).where(
            QuizAttempt.quiz_session_id == quiz_session_id
        ).order_by(QuizAttempt.created_at)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_quiz_session_attempts(self, quiz_session_id: str) -> List[QuizAttempt]:
        """Get all attempts for a quiz session (alias for get_attempts_by_session)"""
        return await self.get_attempts_by_session(quiz_session_id)
    async def get_quiz_session_details(self, quiz_session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details of a quiz session including subject and chapter names.
        
        Args:
            quiz_session_id: The unique session ID for the quiz
            
        Returns:
            Dict containing quiz session details or None if not found
        """
        from app.repositories.question_repo import QuestionRepository
        
        attempts = await self.get_attempts_by_session(quiz_session_id)
        
        if not attempts:
            return None
        
        first_attempt = attempts[0]
        
        question_repo = QuestionRepository(self.session)
        first_question = await question_repo.get_question(first_attempt.question_id)
        
        if not first_question:
            return None
        
        subject = await question_repo.get_subject(first_question.subject_id)
        chapter = await question_repo.get_chapter(first_question.chapter_id)
        
        total_questions = len(attempts)
        correct_count = sum(1 for a in attempts if a.is_correct)
        total_time = sum(a.time_taken for a in attempts)
        
        questions = []
        for i, attempt in enumerate(attempts, 1):
            question = await question_repo.get_question(attempt.question_id)
            if question:
                user_selected = attempt.selected_option
                
                options = {
                    'A': question.option_a,
                    'B': question.option_b,
                    'C': question.option_c,
                    'D': question.option_d
                }
                
                questions.append({
                    'question_number': i,
                    'question_id': question.question_id,
                    'question_text': question.question_text,
                    'options': options,
                    'user_selected': user_selected,
                    'correct_option': question.correct_option,
                    'is_correct': attempt.is_correct,
                    'time_taken': attempt.time_taken,
                    'explanation': question.explanation,
                    'difficulty': question.difficulty
                })
        
        return {
            'quiz_session_id': quiz_session_id,
            'subject_name': subject.subject_name if subject else 'Unknown',
            'chapter_name': chapter.chapter_name if chapter else 'Unknown',
            'difficulty': first_question.difficulty,
            'total_questions': total_questions,
            'correct_answers': correct_count,
            'incorrect_answers': total_questions - correct_count,
            'accuracy': round((correct_count / total_questions * 100), 2) if total_questions > 0 else 0,
            'total_time': total_time,
            'average_time': round(total_time / total_questions, 2) if total_questions > 0 else 0,
            'questions': questions
        }

    
    async def get_user_stats(self, user_id: int, days: int = None) -> Dict[str, Any]:
        """Get user statistics for attempts"""
        # If days is None, get all-time stats (no date filter)
        # If days is specified, filter by cutoff date
        if days is not None:
            cutoff_date = datetime.now() - timedelta(days=days)
            date_filter = QuizAttempt.created_at >= cutoff_date
        else:
            # No date filter for all-time stats
            date_filter = None

        # Build the base conditions
        base_conditions = [QuizAttempt.user_id == user_id]
        if date_filter is not None:
            base_conditions.append(date_filter)

        # Total attempts
        query = select(func.count(QuizAttempt.attempt_id)).where(
            and_(*base_conditions)
        )
        result = await self.session.execute(query)
        total_attempts = result.scalar() or 0

        # Correct attempts
        correct_conditions = base_conditions + [QuizAttempt.is_correct == True]
        query = select(func.count(QuizAttempt.attempt_id)).where(
            and_(*correct_conditions)
        )
        result = await self.session.execute(query)
        correct_attempts = result.scalar() or 0

        # Average time per question
        time_conditions = base_conditions
        query = select(func.avg(QuizAttempt.time_taken)).where(
            and_(*time_conditions)
        )
        result = await self.session.execute(query)
        avg_time = result.scalar() or 0

        # Accuracy
        accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

        return {
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'accuracy': round(accuracy, 2),
            'avg_time': round(avg_time, 2) if avg_time else 0
        }
    
    async def get_daily_attempts(self, user_id: int, date: datetime = None) -> int:
        """Get number of attempts for a specific date"""
        if date is None:
            date = datetime.now()
        
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = datetime.combine(date.date(), datetime.max.time())
        
        query = select(func.count(QuizAttempt.attempt_id)).where(
            and_(
                QuizAttempt.user_id == user_id,
                QuizAttempt.created_at >= start_of_day,
                QuizAttempt.created_at <= end_of_day
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_question_attempts_count(self, question_id: int) -> Dict[str, int]:
        """Get total and correct attempts for a question"""
        query = select(
            func.count(QuizAttempt.attempt_id),
            func.sum(QuizAttempt.is_correct.cast(Integer))
        ).where(QuizAttempt.question_id == question_id)
        
        result = await self.session.execute(query)
        row = result.first()
        
        return {
            'total_attempts': row[0] or 0,
            'correct_attempts': row[1] or 0
        }
    
    async def get_success_rate_by_question(self, question_id: int) -> float:
        """Get success rate for a specific question"""
        stats = await self.get_question_attempts_count(question_id)
        
        if stats['total_attempts'] == 0:
            return 0
        
        return (stats['correct_attempts'] / stats['total_attempts']) * 100
    
    async def get_popular_questions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most attempted questions"""
        query = select(
            QuizAttempt.question_id,
            func.count(QuizAttempt.attempt_id).label('attempt_count')
        ).group_by(QuizAttempt.question_id).order_by(
            desc('attempt_count')
        ).limit(limit)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        return [
            {
                'question_id': row[0],
                'attempt_count': row[1]
            }
            for row in rows
        ]
    
    async def cleanup_old_attempts(self, days: int = 90) -> int:
        """Delete attempts older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # This would need to be implemented with actual deletion
        # For now, return 0 as this is a placeholder
        return 0
    
    # ============== Quiz Statistics Methods ==============
    
    async def get_total_attempts(self) -> int:
        """Get total number of quiz attempts"""
        query = select(func.count(QuizAttempt.attempt_id))
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_total_correct_attempts(self) -> int:
        """Get total number of correct attempts"""
        query = select(func.count(QuizAttempt.attempt_id)).where(
            QuizAttempt.is_correct == True
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_average_accuracy(self) -> float:
        """Calculate overall average accuracy across all attempts"""
        total = await self.get_total_attempts()
        if total == 0:
            return 0.0
        
        correct = await self.get_total_correct_attempts()
        return round((correct / total) * 100, 2)
    
    async def get_average_time_per_question(self) -> float:
        """Calculate average time spent per question in seconds"""
        query = select(func.avg(QuizAttempt.time_taken))
        result = await self.session.execute(query)
        avg_time = result.scalar()
        return round(avg_time, 2) if avg_time else 0.0
    
    async def get_attempts_by_hour(self) -> Dict[int, int]:
        """
        Get distribution of attempts by hour of day (0-23)
        
        Returns:
            Dict mapping hour number to attempt count
        """
        query = select(
            func.extract('hour', QuizAttempt.created_at).label('hour'),
            func.count(QuizAttempt.attempt_id).label('count')
        ).group_by('hour')
        
        result = await self.session.execute(query)
        rows = result.all()
        
        # Convert to dict with hour as int key
        return {int(row.hour): row.count for row in rows}
    
    async def get_attempts_by_period(self, days: int = 30) -> Dict[str, int]:
        """
        Get attempts distribution by time period (morning, afternoon, evening)
        
        Morning: 6-12 (6 AM to 12 PM)
        Afternoon: 12-18 (12 PM to 6 PM)
        Evening: 18-24 (6 PM to 12 AM)
        Night: 0-6 (12 AM to 6 AM)
        
        Args:
            days: Number of days to consider
            
        Returns:
            Dict with period names and attempt counts
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(
            func.extract('hour', QuizAttempt.created_at).label('hour'),
            func.count(QuizAttempt.attempt_id).label('count')
        ).where(
            QuizAttempt.created_at >= cutoff_date
        ).group_by('hour')
        
        result = await self.session.execute(query)
        rows = result.all()
        
        # Initialize counts
        counts = {
            'morning': 0,   # 6-12
            'afternoon': 0, # 12-18
            'evening': 0,   # 18-24
            'night': 0      # 0-6
        }
        
        # Categorize each hour
        for row in rows:
            hour = int(row.hour)
            count = row.count
            if 6 <= hour < 12:
                counts['morning'] += count
            elif 12 <= hour < 18:
                counts['afternoon'] += count
            elif 18 <= hour < 24:
                counts['evening'] += count
            else:  # 0-6
                counts['night'] += count
        
        return counts
    
    async def get_quiz_sessions_count(self) -> int:
        """Get count of unique quiz sessions"""
        query = select(func.count(func.distinct(QuizAttempt.quiz_session_id)))
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_daily_attempt_counts(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily attempt counts for trend analysis
        
        Args:
            days: Number of days to include
            
        Returns:
            List of dicts with date, attempts, and accuracy
        """
        daily_stats = []
        
        for i in range(days, -1, -1):
            date = datetime.now().date() - timedelta(days=i)
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = datetime.combine(date, datetime.max.time())
            
            # Get attempts for this day
            query = select(QuizAttempt).where(
                and_(
                    QuizAttempt.created_at >= start_of_day,
                    QuizAttempt.created_at <= end_of_day
                )
            )
            result = await self.session.execute(query)
            attempts = result.scalars().all()
            
            if attempts:
                total = len(attempts)
                correct = sum(1 for a in attempts if a.is_correct)
                accuracy = round((correct / total) * 100, 2)
                avg_time = round(sum(a.time_taken for a in attempts) / total, 2)
            else:
                total = 0
                accuracy = 0.0
                avg_time = 0.0
            
            daily_stats.append({
                'date': date,
                'attempts': total,
                'correct': sum(1 for a in attempts if a.is_correct) if attempts else 0,
                'accuracy': accuracy,
                'avg_time': avg_time
            })
        
        return daily_stats
    
    async def get_quiz_stats_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive quiz statistics summary
        
        Returns:
            Dict with all quiz statistics
        """
        total_attempts = await self.get_total_attempts()
        correct_attempts = await self.get_total_correct_attempts()
        avg_accuracy = await self.get_average_accuracy()
        avg_time = await self.get_average_time_per_question()
        session_count = await self.get_quiz_sessions_count()
        period_counts = await self.get_attempts_by_period()
        hourly_counts = await self.get_attempts_by_hour()
        daily_trend = await self.get_daily_attempt_counts(30)
        
        # Calculate period percentages
        total_period = sum(period_counts.values())
        period_percentages = {}
        for period, count in period_counts.items():
            period_percentages[period] = round((count / total_period * 100), 2) if total_period > 0 else 0
        
        return {
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'accuracy': avg_accuracy,
            'avg_time_seconds': avg_time,
            'total_sessions': session_count,
            'period_counts': period_counts,
            'period_percentages': period_percentages,
            'hourly_distribution': hourly_counts,
            'daily_trend': daily_trend
        }
    
    async def get_active_users_count(self, days: int = 30) -> int:
        """Get count of users with at least one attempt in the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(func.count(func.distinct(QuizAttempt.user_id))).where(
            QuizAttempt.created_at >= cutoff_date
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
