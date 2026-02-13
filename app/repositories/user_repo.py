from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.models import User, UserProgress, UserDailyLimit, UserChapterDailyLimit

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (with or without @)"""
        username = username.lstrip('@')
        result = await self.session.execute(
            select(User).where(
                or_(
                    User.username == username,
                    User.username == f"@{username}"
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None) -> User:
        """Create new user"""
        # Check if user already exists first
        existing = await self.get_user(user_id)
        if existing:
            return existing
        
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        self.session.add(user)
        await self.session.commit()
        # Refresh to ensure we have the latest data including auto-generated fields
        await self.session.refresh(user)
        return user
    
    async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """
        Update user information with verification.
        
        🚨 CRITICAL: Always commit and verify the update was persisted.
        """
        logger.info(f"🔧 UPDATE_USER: Starting update for user_id={user_id}, fields={kwargs}")
        
        stmt = update(User).where(User.user_id == user_id).values(**kwargs)
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        logger.info(f"🔍 UPDATE_USER: Commit completed for user_id={user_id}, rows affected={result.rowcount}")
        
        # 🚨 CRITICAL: Re-fetch user to verify the update
        updated_user = await self.get_user(user_id)
        
        if updated_user:
            logger.info(
                f"🔍 UPDATE_USER: Retrieved user_id={user_id}, approved={updated_user.approved}, "
                f"is_premium={getattr(updated_user, 'is_premium', None)}"
            )
            
            # If approved was set but still shows 0, force update
            if 'approved' in kwargs and kwargs['approved'] == True and not updated_user.approved:
                logger.error(
                    f"🚨 UPDATE_USER: approved=True was set but DB shows approved=0! "
                    f"Force-updating user_id={user_id}"
                )
                await self.session.execute(
                    text("UPDATE users SET approved = 1 WHERE user_id = :user_id"),
                    {"user_id": user_id}
                )
                await self.session.commit()
                logger.info(f"✅ UPDATE_USER: Force update completed for user_id={user_id}")
                
                # Verify again
                final_check = await self.get_user(user_id)
                if final_check:
                    logger.info(
                        f"🔍 UPDATE_USER: Final check user_id={user_id}, approved={final_check.approved}"
                    )
        
        return updated_user
    
    async def block_user(self, user_id: int) -> bool:
        """Block a user"""
        stmt = update(User).where(User.user_id == user_id).values(blocked=True)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def unblock_user(self, user_id: int) -> bool:
        """Unblock a user"""
        stmt = update(User).where(User.user_id == user_id).values(blocked=False)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_user_progress(self, user_id: int, subject_id: int = None, 
                               chapter_id: int = None, difficulty: str = None) -> List[UserProgress]:
        """Get user progress with optional filters"""
        query = select(UserProgress).where(UserProgress.user_id == user_id)
        
        if subject_id:
            query = query.where(UserProgress.subject_id == subject_id)
        if chapter_id:
            query = query.where(UserProgress.chapter_id == chapter_id)
        if difficulty:
            query = query.where(UserProgress.difficulty == difficulty)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_user_progress(self, user_id: int, subject_id: int, 
                                  chapter_id: int, difficulty: str, 
                                  is_correct: bool, time_taken: int) -> UserProgress:
        """Update user progress after answering a question"""
        # Find existing progress
        query = select(UserProgress).where(
            and_(
                UserProgress.user_id == user_id,
                UserProgress.subject_id == subject_id,
                UserProgress.chapter_id == chapter_id,
                UserProgress.difficulty == difficulty
            )
        )
        result = await self.session.execute(query)
        progress = result.scalar_one_or_none()
        
        if progress:
            # Update existing progress
            progress.total_attempts += 1
            if is_correct:
                progress.correct_attempts += 1
            progress.total_time_spent += time_taken
            progress.last_attempt = datetime.now()
            progress.accuracy = (progress.correct_attempts / progress.total_attempts) * 100
        else:
            # Create new progress record
            progress = UserProgress(
                user_id=user_id,
                subject_id=subject_id,
                chapter_id=chapter_id,
                difficulty=difficulty,
                total_attempts=1,
                correct_attempts=1 if is_correct else 0,
                total_time_spent=time_taken,
                last_attempt=datetime.now(),
                accuracy=100.0 if is_correct else 0.0
            )
            self.session.add(progress)
        
        await self.session.commit()
        return progress
    
    async def get_daily_limit(self, user_id: int, today: date = None) -> UserDailyLimit:
        """Get or create daily limit record for user"""
        if today is None:
            today = date.today()
        # Ensure the user exists to satisfy foreign key constraint
        user = await self.get_user(user_id)
        if user is None:
            await self.create_user(user_id)

        query = select(UserDailyLimit).where(
            and_(
                UserDailyLimit.user_id == user_id,
                UserDailyLimit.date == today
            )
        )
        result = await self.session.execute(query)
        limit = result.scalar_one_or_none()

        if not limit:
            limit = UserDailyLimit(user_id=user_id, date=today)
            self.session.add(limit)
            await self.session.commit()

        return limit
    
    async def increment_daily_quiz_count(self, user_id: int) -> bool:
        """Increment daily quiz count for user"""
        today = date.today()
        limit = await self.get_daily_limit(user_id, today)
        
        limit.quiz_count += 1
        await self.session.commit()
        return True
    
    async def increment_daily_question_count(self, user_id: int, count: int = 1) -> bool:
        """Increment daily question count for user"""
        today = date.today()
        limit = await self.get_daily_limit(user_id, today)
        
        limit.question_count += count
        await self.session.commit()
        return True
    
    async def reset_daily_limits(self):
        """Reset daily limits for all users (call this daily)"""
        today = date.today()
        # This is typically done via a scheduled task
        pass
    
    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        query = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_users(self, search_term: str) -> List[User]:
        """Search users by username or name"""
        query = select(User).where(
            or_(
                User.username.ilike(f"%{search_term}%"),
                User.first_name.ilike(f"%{search_term}%"),
                User.last_name.ilike(f"%{search_term}%")
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_user_by_referral_code(self, referral_code: str) -> Optional[User]:
        """Get user by their referral code (efficient lookup)"""
        if not referral_code:
            return None
        query = select(User).where(User.referral_code == referral_code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_users_count(self, days: int = 7) -> int:
        """Get count of active users in last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(func.count(func.distinct(User.user_id))).where(
            User.created_at >= cutoff_date
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a user"""
        # Total attempts
        query = select(func.count(UserProgress.id)).where(UserProgress.user_id == user_id)
        result = await self.session.execute(query)
        total_attempts = result.scalar() or 0
        
        # Total correct attempts
        query = select(func.sum(UserProgress.correct_attempts)).where(UserProgress.user_id == user_id)
        result = await self.session.execute(query)
        total_correct = result.scalar() or 0
        
        # Average accuracy
        query = select(func.avg(UserProgress.accuracy)).where(UserProgress.user_id == user_id)
        result = await self.session.execute(query)
        avg_accuracy = result.scalar() or 0
        
        # Time spent
        query = select(func.sum(UserProgress.total_time_spent)).where(UserProgress.user_id == user_id)
        result = await self.session.execute(query)
        total_time_spent = result.scalar() or 0
        
        # Chapters attempted
        query = select(func.count(func.distinct(UserProgress.chapter_id))).where(UserProgress.user_id == user_id)
        result = await self.session.execute(query)
        chapters_attempted = result.scalar() or 0
        
        return {
            'total_attempts': total_attempts,
            'total_correct': total_correct,
            'avg_accuracy': round(avg_accuracy, 2),
            'total_time_spent': total_time_spent,
            'chapters_attempted': chapters_attempted,
            'success_rate': round((total_correct / total_attempts * 100) if total_attempts > 0 else 0, 2)
        }
    
    # =========================================================================
    # CHAPTER-LEVEL DAILY LIMIT METHODS
    # =========================================================================
    
    async def get_chapter_daily_limit(
        self, 
        user_id: int, 
        subject_id: int, 
        chapter_id: int, 
        difficulty: str,
        today: date = None
    ) -> UserChapterDailyLimit:
        """
        Get or create daily limit record for user per chapter + difficulty.
        
        This enables tracking of 25 questions per day per chapter per level.
        """
        if today is None:
            today = date.today()
        
        # Ensure the user exists to satisfy foreign key constraint
        user = await self.get_user(user_id)
        if user is None:
            await self.create_user(user_id)

        query = select(UserChapterDailyLimit).where(
            and_(
                UserChapterDailyLimit.user_id == user_id,
                UserChapterDailyLimit.subject_id == subject_id,
                UserChapterDailyLimit.chapter_id == chapter_id,
                UserChapterDailyLimit.difficulty == difficulty,
                UserChapterDailyLimit.date == today
            )
        )
        result = await self.session.execute(query)
        limit = result.scalar_one_or_none()

        if not limit:
            limit = UserChapterDailyLimit(
                user_id=user_id,
                subject_id=subject_id,
                chapter_id=chapter_id,
                difficulty=difficulty,
                date=today
            )
            self.session.add(limit)
            await self.session.commit()

        return limit
    
    async def increment_chapter_daily_question_count(
        self, 
        user_id: int, 
        subject_id: int, 
        chapter_id: int, 
        difficulty: str,
        count: int = 1
    ) -> bool:
        """
        Increment daily question count for user per chapter + difficulty.
        
        Returns True if incremented successfully.
        """
        today = date.today()
        limit = await self.get_chapter_daily_limit(
            user_id, subject_id, chapter_id, difficulty, today
        )
        
        limit.question_count += count
        await self.session.commit()
        return True
    
    async def get_chapter_question_count_today(
        self, 
        user_id: int, 
        subject_id: int, 
        chapter_id: int, 
        difficulty: str,
        today: date = None
    ) -> int:
        """
        Get the number of questions answered today for this chapter + difficulty.
        
        Returns the current question count (0 if no record exists).
        """
        if today is None:
            today = date.today()
        
        query = select(UserChapterDailyLimit.question_count).where(
            and_(
                UserChapterDailyLimit.user_id == user_id,
                UserChapterDailyLimit.subject_id == subject_id,
                UserChapterDailyLimit.chapter_id == chapter_id,
                UserChapterDailyLimit.difficulty == difficulty,
                UserChapterDailyLimit.date == today
            )
        )
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count if count is not None else 0
    
    # =========================================================================
    # REFERRAL METHODS
    # =========================================================================
    
    async def increment_referral_count(self, user_id: int) -> bool:
        """
        Safely increment user's referral count by 1.
        
        This is used when a referred user completes payment and gets approved.
        
        Args:
            user_id: The referrer's user ID
            
        Returns:
            True if incremented successfully, False otherwise
        """
        try:
            # Get current user to check referral_count
            user = await self.get_user(user_id)
            if not user:
                logger.warning(f"User {user_id} not found when incrementing referral count")
                return False
            
            current_count = user.referral_count or 0
            new_count = current_count + 1
            
            # Use SQL UPDATE to increment
            stmt = update(User).where(User.user_id == user_id).values(
                referral_count=new_count
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            logger.info(f"✅ Incremented referral_count for user {user_id}: {current_count} -> {new_count}")
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"❌ Error incrementing referral count for user {user_id}: {e}")
            await self.session.rollback()
            return False
