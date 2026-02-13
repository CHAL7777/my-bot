from typing import List, Optional, Tuple, Dict, Any
import random
from datetime import date
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Question, Subject, Chapter

class QuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_question(self, question_id: int) -> Optional[Question]:
        """Get question by ID"""
        query = select(Question).where(Question.question_id == question_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_random_questions(self, subject_id: int, chapter_id: int, 
                                  difficulty: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get random questions based on filters - returns JSON-serializable dicts"""
        # First, get all question IDs that match the criteria
        query = select(Question.question_id).where(
            and_(
                Question.subject_id == subject_id,
                Question.chapter_id == chapter_id,
                Question.difficulty == difficulty,
                Question.is_active == True
            )
        )
        result = await self.session.execute(query)
        question_ids = [row[0] for row in result.all()]
        
        if not question_ids:
            return []
        
        # Select random IDs
        if len(question_ids) <= limit:
            selected_ids = question_ids
        else:
            selected_ids = random.sample(question_ids, limit)
        
        # Get full question objects and convert to dicts
        query = select(Question).where(Question.question_id.in_(selected_ids))
        result = await self.session.execute(query)
        questions = result.scalars().all()
        
        # Convert SQLAlchemy objects to JSON-serializable dicts
        return [
            {
                'question_id': q.question_id,
                'subject_id': q.subject_id,
                'chapter_id': q.chapter_id,
                'question_text': q.question_text,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_option': q.correct_option,
                'difficulty': q.difficulty,
                'explanation': q.explanation
            }
            for q in questions
        ]
    
    async def create_question(self, **kwargs) -> Question:
        """Create new question"""
        question = Question(**kwargs)
        self.session.add(question)
        await self.session.commit()
        return question
    
    async def update_question(self, question_id: int, **kwargs) -> Optional[Question]:
        """Update question"""
        stmt = update(Question).where(Question.question_id == question_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        
        return await self.get_question(question_id)
    
    async def delete_question(self, question_id: int) -> bool:
        """Delete question (soft delete)"""
        stmt = update(Question).where(Question.question_id == question_id).values(is_active=False)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_subjects(self, eager_load: bool = False) -> List[Subject]:
        '''
        Get all active subjects.
        
        Args:
            eager_load: If True, loads questions and chapters eagerly
                       to prevent DetachedInstanceError. Use this when
                       you need to access subject.questions or subject.chapters
                       outside of the session context.
        
        Returns:
            List of Subject objects
        '''
        query = select(Subject).where(Subject.is_active == True)
        
        if eager_load:
            # Eager load relationships to prevent DetachedInstanceError
            query = query.options(
                selectinload(Subject.questions),
                selectinload(Subject.chapters)
            )
        
        query = query.order_by(Subject.subject_name)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_subjects_with_counts(self) -> Tuple[List[Subject], Dict[int, int]]:
        '''
        Get all subjects with their question counts pre-computed.
        
        This method prevents DetachedInstanceError by computing counts
        within the session and returning them separately.
        
        Returns:
            Tuple of (subjects, subject_counts_dict)
            - subjects: List of Subject objects (relationships not accessed)
            - subject_counts: Dict mapping subject_id -> question_count
        '''
        subjects = await self.get_subjects(eager_load=False)
        subject_counts: Dict[int, int] = {}
        
        for subject in subjects:
            count = await self.get_question_count(subject_id=subject.subject_id)
            subject_counts[subject.subject_id] = count
        
        return subjects, subject_counts
    
    async def get_subject(self, subject_id: int) -> Optional[Subject]:
        """Get subject by ID"""
        query = select(Subject).where(Subject.subject_id == subject_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_subject_by_name(self, subject_name: str) -> Optional[Subject]:
        """Get subject by name"""
        query = select(Subject).where(Subject.subject_name == subject_name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_subject(self, subject_name: str, description: str = None) -> Subject:
        """Create new subject"""
        subject = Subject(subject_name=subject_name, description=description)
        self.session.add(subject)
        await self.session.commit()
        return subject
    
    async def update_subject(self, subject_id: int, **kwargs) -> Optional[Subject]:
        """Update subject"""
        stmt = update(Subject).where(Subject.subject_id == subject_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        
        return await self.get_subject(subject_id)
    
    async def delete_subject(self, subject_id: int) -> bool:
        """Delete subject (soft delete)"""
        stmt = update(Subject).where(Subject.subject_id == subject_id).values(is_active=False)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_chapters(self, subject_id: int) -> List[Chapter]:
        """Get all chapters for a subject"""
        query = select(Chapter).where(
            and_(
                Chapter.subject_id == subject_id,
                Chapter.is_active == True
            )
        ).order_by(Chapter.chapter_order)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_chapter(self, chapter_id: int) -> Optional[Chapter]:
        """Get chapter by ID"""
        query = select(Chapter).where(Chapter.chapter_id == chapter_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_chapter(self, subject_id: int, chapter_name: str, 
                           chapter_order: int = 0, description: str = None) -> Chapter:
        """Create new chapter"""
        chapter = Chapter(
            subject_id=subject_id,
            chapter_name=chapter_name,
            chapter_order=chapter_order,
            description=description
        )
        self.session.add(chapter)
        await self.session.commit()
        return chapter
    
    async def get_question_count(self, subject_id: int = None, chapter_id: int = None, 
                               difficulty: str = None) -> int:
        """Get count of active questions with filters"""
        query = select(func.count(Question.question_id)).where(Question.is_active == True)
        
        if subject_id:
            query = query.where(Question.subject_id == subject_id)
        if chapter_id:
            query = query.where(Question.chapter_id == chapter_id)
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_chapter_counts_batch(
        self, 
        subject_id: int, 
        chapter_ids: list[int]
    ) -> dict[int, dict[str, int]]:
        """
        OPTIMIZED: Get question counts for multiple chapters in a single query.
        
        Returns dict mapping chapter_id -> {total, simple, medium, hard}
        
        Before: 4 queries per chapter (N * 4 queries)
        After:  1 query total (1 query for all chapters)
        
        Args:
            subject_id: Subject ID to filter by
            chapter_ids: List of chapter IDs to get counts for
            
        Returns:
            Dict: {chapter_id: {'total': int, 'simple': int, 'medium': int, 'hard': int}}
        """
        if not chapter_ids:
            return {}
        
        # Single query with conditional aggregation using case()
        # Use func.count() with case() for cross-database compatibility
        query = select(
            Question.chapter_id,
            func.count(case((Question.question_id != None, 1))).label('total'),
            func.count(case((Question.difficulty == 'simple', 1))).label('simple'),
            func.count(case((Question.difficulty == 'medium', 1))).label('medium'),
            func.count(case((Question.difficulty == 'hard', 1))).label('hard'),
        ).where(
            and_(
                Question.subject_id == subject_id,
                Question.chapter_id.in_(chapter_ids),
                Question.is_active == True
            )
        ).group_by(Question.chapter_id)
        
        result = await self.session.execute(query)
        
        # Build result dict
        counts = {}
        for row in result.all():
            counts[row.chapter_id] = {
                'total': row.total or 0,
                'simple': row.simple or 0,
                'medium': row.medium or 0,
                'hard': row.hard or 0
            }
        
        # Ensure all chapter_ids are in result (even with 0 counts)
        for chapter_id in chapter_ids:
            if chapter_id not in counts:
                counts[chapter_id] = {'total': 0, 'simple': 0, 'medium': 0, 'hard': 0}
        
        return counts
    
    async def search_questions(self, search_term: str, limit: int = 20) -> List[Question]:
        """Search questions by text"""
        query = select(Question).where(
            and_(
                Question.is_active == True,
                or_(
                    Question.question_text.ilike(f"%{search_term}%"),
                    Question.option_a.ilike(f"%{search_term}%"),
                    Question.option_b.ilike(f"%{search_term}%"),
                    Question.option_c.ilike(f"%{search_term}%"),
                    Question.option_d.ilike(f"%{search_term}%")
                )
            )
        ).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_weak_chapters(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get user's weakest chapters based on accuracy"""
        from app.db.models import UserProgress
        
        query = select(
            UserProgress.subject_id,
            UserProgress.chapter_id,
            UserProgress.difficulty,
            UserProgress.accuracy,
            Subject.subject_name,
            Chapter.chapter_name
        ).join(
            Subject, UserProgress.subject_id == Subject.subject_id
        ).join(
            Chapter, UserProgress.chapter_id == Chapter.chapter_id
        ).where(
            and_(
                UserProgress.user_id == user_id,
                UserProgress.total_attempts >= 5
            )
        ).order_by(UserProgress.accuracy.asc()).limit(limit)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        return [
            {
                'subject_id': row.subject_id,
                'chapter_id': row.chapter_id,
                'subject_name': row.subject_name,
                'chapter_name': row.chapter_name,
                'difficulty': row.difficulty,
                'accuracy': row.accuracy
            }
            for row in rows
        ]
    
    async def get_question_stats(self) -> Dict[str, Any]:
        """Get overall question statistics"""
        query = select(func.count(Question.question_id)).where(Question.is_active == True)
        result = await self.session.execute(query)
        total_questions = result.scalar() or 0
        
        query = select(
            Question.difficulty,
            func.count(Question.question_id)
        ).where(
            Question.is_active == True
        ).group_by(Question.difficulty)
        
        result = await self.session.execute(query)
        difficulty_stats = {row[0]: row[1] for row in result.all()}
        
        query = select(
            Subject.subject_name,
            func.count(Question.question_id)
        ).join(
            Question, Subject.subject_id == Question.subject_id
        ).where(
            Question.is_active == True
        ).group_by(Subject.subject_name)
        
        result = await self.session.execute(query)
        subject_stats = {row[0]: row[1] for row in result.all()}
        
        return {
            'total_questions': total_questions,
            'by_difficulty': difficulty_stats,
            'by_subject': subject_stats
        }
    
    async def get_attempted_question_ids(
        self, 
        user_id: int, 
        subject_id: int, 
        chapter_id: int, 
        difficulty: str,
        today: date = None
    ) -> List[int]:
        """
        Get list of question IDs that user has already attempted today 
        for this chapter + difficulty combination.
        
        This is used to ensure new random questions are shown each time
        the user starts/resumes a quiz.
        """
        from app.db.models import QuizAttempt, Question as QuestionModel
        from datetime import datetime
        
        if today is None:
            today = date.today()
        
        # Get today's start datetime
        today_start = datetime.combine(today, datetime.min.time())
        
        query = select(QuestionModel.question_id).join(
            QuizAttempt, QuestionModel.question_id == QuizAttempt.question_id
        ).where(
            and_(
                QuizAttempt.user_id == user_id,
                QuestionModel.subject_id == subject_id,
                QuestionModel.chapter_id == chapter_id,
                QuestionModel.difficulty == difficulty,
                QuizAttempt.created_at >= today_start
            )
        ).distinct()
        
        result = await self.session.execute(query)
        return [row[0] for row in result.all()]
    
    async def get_all_attempted_question_ids_today(self, user_id: int) -> List[int]:
        """
        Get all question IDs that user has attempted today (across all chapters and levels).
        
        This is used to ensure random questions are shown each time user starts/resumes quiz,
        regardless of which chapter/level they choose.
        """
        from app.db.models import QuizAttempt, Question as QuestionModel
        from datetime import datetime
        
        today = date.today()
        # Get today's start datetime
        today_start = datetime.combine(today, datetime.min.time())
        
        query = select(QuestionModel.question_id).join(
            QuizAttempt, QuestionModel.question_id == QuizAttempt.question_id
        ).where(
            and_(
                QuizAttempt.user_id == user_id,
                QuizAttempt.created_at >= today_start
            )
        ).distinct()
        
        result = await self.session.execute(query)
        return [row[0] for row in result.all()]
    
    async def get_random_questions_excluding(
        self, 
        subject_id: int, 
        chapter_id: int, 
        difficulty: str, 
        exclude_ids: List[int],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get random questions excluding already attempted ones.
        
        This ensures that when user cancels and restarts quiz,
        they get new questions they haven't seen today.
        """
        # First, get all question IDs that match the criteria
        base_query = select(Question.question_id).where(
            and_(
                Question.subject_id == subject_id,
                Question.chapter_id == chapter_id,
                Question.difficulty == difficulty,
                Question.is_active == True
            )
        )
        
        # Exclude already attempted questions
        if exclude_ids:
            base_query = base_query.where(~Question.question_id.in_(exclude_ids))
        
        result = await self.session.execute(base_query)
        question_ids = [row[0] for row in result.all()]
        
        if not question_ids:
            return []
        
        # Select random IDs
        if len(question_ids) <= limit:
            selected_ids = question_ids
        else:
            selected_ids = random.sample(question_ids, limit)
        
        # Get full question objects and convert to dicts
        query = select(Question).where(Question.question_id.in_(selected_ids))
        result = await self.session.execute(query)
        questions = result.scalars().all()
        
        # Convert SQLAlchemy objects to JSON-serializable dicts
        return [
            {
                'question_id': q.question_id,
                'subject_id': q.subject_id,
                'chapter_id': q.chapter_id,
                'question_text': q.question_text,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_option': q.correct_option,
                'difficulty': q.difficulty,
                'explanation': q.explanation
            }
            for q in questions
        ]

