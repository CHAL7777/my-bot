from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.repositories.user_repo import UserRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.question_repo import QuestionRepository
from app.config import settings

class UserService:
    def __init__(self, user_repo: UserRepository, 
                 payment_repo: PaymentRepository,
                 attempt_repo: AttemptRepository,
                 question_repo: QuestionRepository = None):
        self.user_repo = user_repo
        self.payment_repo = payment_repo
        self.attempt_repo = attempt_repo
        self.question_repo = question_repo
    
    async def register_user(self, user_id: int, username: str = None,
                           first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """
        Register new user.
        
        ⚠️ CRITICAL: Users are NOT granted premium access automatically.
        Premium access is ONLY granted after admin approval (approved = 1).
        
        The `ENABLE_TRIAL` setting is now IGNORED for quiz access.
        Users must be explicitly approved by an admin to access quizzes.
        """
        # Check if user already exists
        user = await self.user_repo.get_user(user_id)
        
        if user:
            return {
                'is_new': False,
                'user': user,
                'has_premium': user.is_premium  # Will be True only after admin approval
            }
        
        # Create new user - approved = False by default
        user = await self.user_repo.create_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        # ⚠️ CRITICAL: DO NOT set is_premium = True here!
        # Users must be explicitly approved by an admin.
        # The ENABLE_TRIAL setting is deprecated for quiz access control.
        # Premium access is granted ONLY via admin approval (approve_user in admin_users handler).
        
        return {
            'is_new': True,
            'user': user,
            'has_premium': False,  # Users start as non-premium
            'is_lifetime': False   # Users must be approved to get lifetime access
        }
    
    async def _has_premium_access(self, user_id: int) -> bool:
        """Check if user has premium access (lifetime or subscription)"""
        user = await self.user_repo.get_user(user_id)
        if not user:
            return False
        # For lifetime premium model, check is_premium flag
        return user.is_premium
    
    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get complete user profile with statistics"""
        user = await self.user_repo.get_user(user_id)
        if not user:
            raise Exception("User not found")
        
        # Get user statistics
        user_stats = await self.user_repo.get_user_statistics(user_id)
        
        # Get recent activity
        recent_attempts = await self.attempt_repo.get_user_attempts(user_id, limit=10)
        
        # Get premium status (lifetime premium model)
        has_premium = user.is_premium
        
        # Get daily limits
        daily_limit = await self.user_repo.get_daily_limit(user_id)
        
        # Get weak areas
        weak_chapters = await self.user_repo.get_user_progress(user_id)
        weak_chapters = sorted(weak_chapters, key=lambda x: x.accuracy)[:5]
        
        # Format weak chapters
        formatted_weak_chapters = []
        for progress in weak_chapters:
            if progress.total_attempts >= 3:  # Only include if attempted at least 3 times
                formatted_weak_chapters.append({
                    'subject_id': progress.subject_id,
                    'chapter_id': progress.chapter_id,
                    'difficulty': progress.difficulty,
                    'accuracy': progress.accuracy,
                    'attempts': progress.total_attempts
                })
        
        return {
            'user_id': user.user_id,
            'username': user.username,
            'name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
            'role': user.role,
            'created_at': user.created_at,
            'blocked': user.blocked,
            'stats': user_stats,
            'subscription': {
                'active': has_premium,
                'is_lifetime': has_premium,
                'has_premium': has_premium
            },
            'daily_limits': {
                'quiz_count': daily_limit.quiz_count,
                'question_count': daily_limit.question_count,
                'max_quizzes': settings.DAILY_QUIZ_LIMIT,
                'remaining_quizzes': max(0, settings.DAILY_QUIZ_LIMIT - daily_limit.quiz_count)
            },
            'weak_chapters': formatted_weak_chapters,
            'recent_activity': len(recent_attempts)
        }
    
    async def can_access_difficulty(self, user_id: int, difficulty: str) -> bool:
        """
        Check if user can access quizzes of given difficulty.
        
        ⚠️ CRITICAL: Access is granted ONLY IF user.approved = 1
        
        This function checks NOTHING else:
        - is_premium flag is IGNORED
        - has_active_subscription is IGNORED
        - payment status is IGNORED
        
        Only admin approval (approved = 1) grants quiz access.
        
        Args:
            user_id: Telegram user ID
            difficulty: 'simple', 'medium', or 'hard'
            
        Returns:
            True ONLY if user.approved = 1, False otherwise
        """
        if difficulty == 'simple':
            # ⚠️ CRITICAL: Even simple quizzes require approval!
            # This is a security requirement - ALL quizzes require approval.
            pass
        
        # Get fresh user data from database
        user = await self.user_repo.get_user(user_id)
        if not user:
            return False
        
        # 🚨 STRICT CHECK: Access granted ONLY if approved = 1
        # No fallback paths, no bypasses, no exceptions
        return user.approved == True
    
    async def get_daily_progress(self, user_id: int) -> Dict[str, Any]:
        """Get user's daily progress"""
        today = datetime.now().date()
        
        # Get today's attempts
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        # This would require a new method in attempt_repo
        # For now, we'll use user stats for all time
        stats = await self.attempt_repo.get_user_stats(user_id, days=None)
        
        # Get daily limit
        daily_limit = await self.user_repo.get_daily_limit(user_id)
        
        return {
            'date': today,
            'attempts': stats.get('total_attempts', 0),
            'correct': stats.get('correct_attempts', 0),
            'accuracy': stats.get('accuracy', 0),
            'quiz_count': daily_limit.quiz_count,
            'question_count': daily_limit.question_count,
            'remaining_quizzes': max(0, settings.DAILY_QUIZ_LIMIT - daily_limit.quiz_count)
        }
    
    async def get_learning_path(self, user_id: int) -> List[Dict[str, Any]]:
        """Get personalized learning path for user"""
        # Get user's progress
        user_progress = await self.user_repo.get_user_progress(user_id)
        
        # Get all subjects using question_repo
        subjects = []
        if self.question_repo:
            subjects = await self.question_repo.get_subjects()
        else:
            return []  # Cannot generate learning path without subjects
        
        # This is a simplified version - in reality, you'd have more complex logic
        learning_path = []
        
        for subject in subjects:
            # Get chapters for this subject
            chapters = await self.question_repo.get_chapters(subject.subject_id)
            
            for chapter in chapters:
                # Check if user has attempted this chapter
                chapter_progress = [
                    p for p in user_progress 
                    if p.subject_id == subject.subject_id and p.chapter_id == chapter.chapter_id
                ]
                
                if not chapter_progress:
                    # Not attempted yet - recommend
                    learning_path.append({
                        'subject': subject.subject_name,
                        'chapter': chapter.chapter_name,
                        'status': 'not_started',
                        'recommended_difficulty': 'simple',
                        'priority': 'high'
                    })
                else:
                    # Calculate average accuracy
                    avg_accuracy = sum(p.accuracy for p in chapter_progress) / len(chapter_progress)
                    
                    if avg_accuracy < 60:
                        # Needs improvement
                        learning_path.append({
                            'subject': subject.subject_name,
                            'chapter': chapter.chapter_name,
                            'status': 'needs_improvement',
                            'accuracy': avg_accuracy,
                            'recommended_difficulty': 'simple',
                            'priority': 'high'
                        })
                    elif avg_accuracy < 80:
                        # Can improve
                        learning_path.append({
                            'subject': subject.subject_name,
                            'chapter': chapter.chapter_name,
                            'status': 'good',
                            'accuracy': avg_accuracy,
                            'recommended_difficulty': 'medium',
                            'priority': 'medium'
                        })
                    else:
                        # Mastered - can try hard difficulty
                        learning_path.append({
                            'subject': subject.subject_name,
                            'chapter': chapter.chapter_name,
                            'status': 'mastered',
                            'accuracy': avg_accuracy,
                            'recommended_difficulty': 'hard',
                            'priority': 'low'
                        })
        
        # Sort by priority (high to low)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        learning_path.sort(key=lambda x: priority_order[x['priority']])
        
        return learning_path[:10]  # Return top 10 recommendations