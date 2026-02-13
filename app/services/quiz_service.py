import random
import uuid
import time
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.user_repo import UserRepository
from app.config import settings

class QuizService:
    def __init__(self, question_repo: QuestionRepository, 
                 attempt_repo: AttemptRepository,
                 user_repo: UserRepository):
        self.question_repo = question_repo
        self.attempt_repo = attempt_repo
        self.user_repo = user_repo
        
        # Points system based on difficulty
        self.difficulty_points = {
            'simple': 1,
            'medium': 2,
            'hard': 3
        }
    
    async def start_quiz(self, user_id: int, subject_id: int, 
                        chapter_id: int, difficulty: str) -> Dict[str, Any]:
        """Start a new quiz session"""
        # Get total questions available for this chapter + difficulty
        total_available = await self.question_repo.get_question_count(
            subject_id=subject_id,
            chapter_id=chapter_id,
            difficulty=difficulty
        )
        
        # Determine questions per round:
        # - If > 25 questions available → 25 per round
        # - If ≤ 25 questions available → 10 per round
        if total_available > 25:
            questions_per_round = 25
        else:
            questions_per_round = 10
        
        # Ensure we don't ask for more than available
        limit = min(questions_per_round, total_available)
        
        # Get random questions for this chapter + difficulty
        questions = await self.question_repo.get_random_questions(
            subject_id=subject_id,
            chapter_id=chapter_id,
            difficulty=difficulty,
            limit=limit
        )

        if not questions:
            raise Exception("No questions available for this selection yet.")

        # Ensure each question is a JSON-serializable dict (some callers
        # may accidentally return ORM objects)
        def _serialize_question(q):
            if isinstance(q, dict):
                return q
            # Fallback for SQLAlchemy model instances
            return {
                'question_id': getattr(q, 'question_id', None),
                'subject_id': getattr(q, 'subject_id', None),
                'chapter_id': getattr(q, 'chapter_id', None),
                'question_text': getattr(q, 'question_text', ''),
                'option_a': getattr(q, 'option_a', ''),
                'option_b': getattr(q, 'option_b', ''),
                'option_c': getattr(q, 'option_c', ''),
                'option_d': getattr(q, 'option_d', ''),
                'correct_option': getattr(q, 'correct_option', None),
                'difficulty': getattr(q, 'difficulty', None),
                'explanation': getattr(q, 'explanation', None),
            }

        questions_serializable = [_serialize_question(q) for q in questions]

        # Create quiz session
        quiz_session_id = str(uuid.uuid4())

        return {
            'quiz_session_id': quiz_session_id,
            'questions': questions_serializable,
            'current_question': 0,
            'score': 0,
            # Use epoch timestamp (float) to keep value JSON-serializable
            'start_time': time.time(),
            'subject_id': subject_id,
            'chapter_id': chapter_id,
            'difficulty': difficulty,
            'total_questions': len(questions_serializable),
        }
    
    async def process_answer(self, user_id: int, quiz_session_id: str,
                           question_id: int, selected_option: str,
                           time_taken: int) -> Tuple[bool, Dict[str, Any]]:
        """Process user's answer to a question"""
        # Get question
        question = await self.question_repo.get_question(question_id)
        if not question:
            raise Exception("Question not found")
        
        # Check if answer is correct
        is_correct = (selected_option == question.correct_option)
        
        # Calculate points
        points = self.difficulty_points[question.difficulty] if is_correct else 0
        
        # Record attempt
        attempt = await self.attempt_repo.create_attempt(
            user_id=user_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct,
            time_taken=time_taken,
            quiz_session_id=quiz_session_id
        )
        
        # Update user progress
        await self.user_repo.update_user_progress(
            user_id=user_id,
            subject_id=question.subject_id,
            chapter_id=question.chapter_id,
            difficulty=question.difficulty,
            is_correct=is_correct,
            time_taken=time_taken
        )
        
        # Prepare response
        response = {
            'is_correct': is_correct,
            'points': points,
            'correct_option': question.correct_option,
            'explanation': question.explanation,
            'attempt_id': attempt.attempt_id
        }
        
        return is_correct, response
    
    async def finish_quiz(self, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Finish quiz and calculate final results"""
        end_time = datetime.now()
        start_time = quiz_data['start_time']
        total_time = (end_time - start_time).total_seconds()
        
        # Calculate accuracy
        total_questions = quiz_data['total_questions']
        score = quiz_data.get('score', 0)
        
        # Maximum possible score
        max_score = total_questions * self.difficulty_points[quiz_data['difficulty']]
        
        # Calculate accuracy percentage
        accuracy = (score / max_score * 100) if max_score > 0 else 0
        
        # Determine performance level
        if accuracy >= 80:
            performance = "Excellent! 🎉"
            suggestion = "Try a higher difficulty level!"
        elif accuracy >= 60:
            performance = "Good! 👍"
            suggestion = "Keep practicing to improve!"
        else:
            performance = "Needs Improvement 📚"
            suggestion = "Review this chapter and try again."
        
        # Get weak areas
        weak_chapters = await self.question_repo.get_weak_chapters(
            user_id=quiz_data.get('user_id'),
            limit=3
        )
        
        return {
            'score': score,
            'total_questions': total_questions,
            'accuracy': round(accuracy, 2),
            'total_time': round(total_time, 2),
            'performance': performance,
            'suggestion': suggestion,
            'weak_chapters': weak_chapters,
            'average_time_per_question': round(total_time / total_questions, 2) if total_questions > 0 else 0
        }
    
    async def get_quiz_summary(self, quiz_session_id: str) -> List[Dict[str, Any]]:
        """Get detailed summary of a quiz session"""
        attempts = await self.attempt_repo.get_quiz_session_attempts(quiz_session_id)
        
        summary = []
        for attempt in attempts:
            question = await self.question_repo.get_question(attempt.question_id)
            if question:
                summary.append({
                    'question': question.question_text[:100] + "..." if len(question.question_text) > 100 else question.question_text,
                    'selected_option': attempt.selected_option,
                    'correct_option': question.correct_option,
                    'is_correct': attempt.is_correct,
                    'time_taken': attempt.time_taken,
                    'explanation': question.explanation
                })
        
        return summary
    
    async def get_quiz_session_details(self, quiz_session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details of a quiz session including subject and chapter names.
        
        Args:
            quiz_session_id: The unique session ID for the quiz
            
        Returns:
            Dict containing quiz session details or None if not found
        """
        attempts = await self.attempt_repo.get_quiz_session_attempts(quiz_session_id)
        
        if not attempts:
            return None
        
        # Get first attempt to find subject/chapter info
        first_attempt = attempts[0]
        first_question = await self.question_repo.get_question(first_attempt.question_id)
        
        if not first_question:
            return None
        
        # Get subject and chapter info
        subject = await self.question_repo.get_subject(first_question.subject_id)
        chapter = await self.question_repo.get_chapter(first_question.chapter_id)
        
        # Calculate statistics
        total_questions = len(attempts)
        correct_count = sum(1 for a in attempts if a.is_correct)
        total_time = sum(a.time_taken for a in attempts)
        
        # Build detailed question list
        questions = []
        for i, attempt in enumerate(attempts, 1):
            question = await self.question_repo.get_question(attempt.question_id)
            if question:
                # Determine which option was selected by user
                user_selected = attempt.selected_option
                
                # Get option text for user's selection and correct answer
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
    
    async def get_recommended_quiz(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get recommended quiz based on user's performance"""
        # Get user's weak chapters
        weak_chapters = await self.question_repo.get_weak_chapters(user_id, limit=1)
        
        if not weak_chapters:
            # If no weak chapters, suggest random quiz
            subjects = await self.question_repo.get_subjects()
            if not subjects:
                return None
            
            subject = random.choice(subjects)
            chapters = await self.question_repo.get_chapters(subject.subject_id)
            if not chapters:
                return None
            
            chapter = random.choice(chapters)
            difficulty = 'simple'  # Start with simple
            
            return {
                'subject_id': subject.subject_id,
                'subject_name': subject.subject_name,
                'chapter_id': chapter.chapter_id,
                'chapter_name': chapter.chapter_name,
                'difficulty': difficulty,
                'reason': "Try this quiz to get started!"
            }
        
        # Recommend quiz for weakest chapter
        weak_chapter = weak_chapters[0]
        
        # Determine appropriate difficulty based on accuracy
        if weak_chapter['accuracy'] < 40:
            difficulty = 'simple'
        elif weak_chapter['accuracy'] < 70:
            difficulty = 'medium'
        else:
            difficulty = 'hard'
        
        return {
            'subject_id': weak_chapter['subject_id'],
            'subject_name': weak_chapter['subject_name'],
            'chapter_id': weak_chapter['chapter_id'],
            'chapter_name': weak_chapter['chapter_name'],
            'difficulty': difficulty,
            'reason': f"Your accuracy in this chapter is {weak_chapter['accuracy']}%. Practice more to improve!"
        }