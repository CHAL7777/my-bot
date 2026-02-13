"""
Feedback Service for Interactive Quiz Bot

This service handles:
- Random message selection from templates
- Streak tracking and management
- Progress calculation
- Score formatting
- End-of-quiz performance evaluation
"""

import random
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.utils.feedback_messages import (
    get_random_celebration,
    get_random_encouragement,
    get_streak_message,
    get_end_of_quiz_message,
    format_progress_message,
    get_quiz_start_message,
)


@dataclass
class FeedbackResult:
    """Data class to hold feedback result information"""
    emoji: str
    title: str
    message: str
    show_streak: bool = False
    streak_count: int = 0


class FeedbackService:
    """
    Service for managing quiz feedback and user encouragement.
    
    This service provides:
    - Dynamic celebrations for correct answers
    - Encouragement for wrong answers (no shaming)
    - Streak tracking and celebration
    - Progress and score updates
    - End-of-quiz performance messages
    """
    
    def __init__(self):
        """Initialize the feedback service"""
        self._streak_cache: Dict[int, int] = {}  # user_id -> current streak
    
    def get_correct_answer_feedback(
        self, 
        user_id: int,
        points_earned: int = 0,
        current_score: int = 0,
        question_number: int = 1,
        total_questions: int = 10
    ) -> FeedbackResult:
        """
        Get celebratory feedback for a correct answer.
        
        Args:
            user_id: The user's ID for streak tracking
            points_earned: Points earned for this answer
            current_score: Current total score (points)
            question_number: Current question number
            total_questions: Total questions in quiz
        
        Returns:
            FeedbackResult with celebration message
        """
        # Get random celebration message
        celebration = get_random_celebration()
        
        # Check and update streak
        self._streak_cache[user_id] = self._streak_cache.get(user_id, 0) + 1
        current_streak = self._streak_cache[user_id]
        
        # Build the message (title already in celebration message)
        emoji = celebration["emoji"]
        message = celebration["message"]  # Use full message as-is
        
        # Add streak info if applicable
        if current_streak >= 2:
            streak_info = get_streak_message(current_streak)
            message += f"\n\n{streak_info['emoji']} *{streak_info['title']}*"
            message += f"\n{streak_info['message']}"
        
        # Add progress hint
        if question_number < total_questions:
            message += f"\n\n💪 Question {question_number}/{total_questions}"
        
        return FeedbackResult(
            emoji=emoji,
            title="",  # Empty title to avoid duplication
            message=message,
            show_streak=(current_streak >= 2),
            streak_count=current_streak
        )
    
    def get_wrong_answer_feedback(
        self,
        user_id: int,
        correct_option: str,
        explanation: Optional[str] = None,
        current_score: int = 0,
        question_number: int = 1,
        total_questions: int = 10
    ) -> FeedbackResult:
        """
        Get encouraging feedback for a wrong answer.
        
        Args:
            user_id: The user's ID for streak tracking
            correct_option: The correct answer option (A, B, C, D)
            explanation: Optional explanation for the answer
            current_score: Current total score (points) - not displayed
            question_number: Current question number
            total_questions: Total questions in quiz
        
        Returns:
            FeedbackResult with encouraging message
        """
        # Reset streak on wrong answer
        self._streak_cache[user_id] = 0
        
        # Get random encouragement message
        encouragement = get_random_encouragement(correct_option)
        
        # Build the message
        emoji = encouragement["emoji"]
        message = encouragement["message"]
        
        # Add correct answer prominently highlighted
        message += f"\n\n✨ *The correct answer is: {correct_option}* ✨"
        
        # Add explanation if available with nice formatting
        if explanation:
            # Truncate long explanations
            if len(explanation) > 500:
                explanation = explanation[:500] + "..."
            message += f"\n\n📚 *Explanation:*\n{explanation}"
        
        # Add encouragement for next question
        remaining = total_questions - question_number
        if remaining > 0:
            message += f"\n\n🚀 Keep going! {remaining} more to go!"
        
        return FeedbackResult(
            emoji=emoji,
            title="",  # Empty title to avoid duplication
            message=message,
            show_streak=False,
            streak_count=0
        )
    
    def get_end_of_quiz_feedback(
        self,
        user_id: int,
        score: int,
        total_questions: int,
        correct_answers: int,
        total_time: float,
        difficulty: str = "simple"
    ) -> FeedbackResult:
        """
        Get end-of-quiz celebration message based on performance.
        
        Args:
            user_id: The user's ID for streak tracking
            score: Total points earned
            total_questions: Total number of questions
            correct_answers: Number of correct answers
            total_time: Total time spent in seconds
            difficulty: Quiz difficulty level
        
        Returns:
            FeedbackResult with performance celebration
        """
        # Calculate accuracy
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Get longest streak (clear cache after quiz)
        longest_streak = self._streak_cache.get(user_id, 0)
        self._streak_cache[user_id] = 0  # Reset for next quiz
        
        # Get end-of-quiz message based on performance
        quiz_feedback = get_end_of_quiz_message(
            accuracy=accuracy,
            score=score,
            total_questions=total_questions,
            streak=longest_streak
        )
        
        # Build comprehensive results message
        message_parts = []
        
        # Add celebration header
        message_parts.append(f"{quiz_feedback['emoji']} *{quiz_feedback['title']}*")
        message_parts.append(f"\n{quiz_feedback['message']}")
        
        # Add separator
        message_parts.append("\n" + "─" * 25)
        
        # Add detailed stats - HIGHLIGHTED
        message_parts.append("\n🏆 *YOUR RESULTS:*")
        message_parts.append(f"\n✅ *{correct_answers}/{total_questions}* questions correct")
        message_parts.append(f"📈 *Accuracy:* *{accuracy:.0f}%*")
        message_parts.append(f"⏱️ *Time:* *{total_time:.0f}s*")
        
        # Add performance tier with emoji
        if accuracy >= 90:
            message_parts.append("\n\n🥇 *AMAZING!*")
            message_parts.append("\nYou're a quiz master! 🌟")
        elif accuracy >= 70:
            message_parts.append("\n\n🏆 *EXCELLENT!*")
            message_parts.append("\nGreat job! Keep it up! 💪")
        elif accuracy >= 50:
            message_parts.append("\n\n👍 *GOOD JOB!*")
            message_parts.append("\nYou're improving! 🎯")
        else:
            message_parts.append("\n\n💪 *KEEP PRACTICING!*")
            message_parts.append("\nEvery expert was once a beginner! 🌱")
        
        # Add longest streak if notable
        if longest_streak >= 3:
            message_parts.append(f"\n\n🔥 *Best streak: {longest_streak}*")
        
        return FeedbackResult(
            emoji=quiz_feedback["emoji"],
            title="",  # Empty title since we include it in message
            message="\n".join(message_parts),
            show_streak=(longest_streak >= 3),
            streak_count=longest_streak
        )
    
    def get_progress_display(
        self,
        question_number: int,
        total_questions: int,
        score: int,
        streak: int = 0
    ) -> str:
        """
        Format a progress display string.
        
        Args:
            question_number: Current question number
            total_questions: Total questions in quiz
            score: Current score
            streak: Current streak count
        
        Returns:
            Formatted progress string
        """
        return format_progress_message(
            current=question_number,
            total=total_questions,
            score=score,
            streak=streak
        )
    
    def get_quiz_start_message(self) -> Dict[str, str]:
        """
        Get a motivational quiz start message.
        
        Returns:
            Dictionary with emoji and message
        """
        return get_quiz_start_message()
    
    def reset_streak(self, user_id: int) -> None:
        """
        Reset the streak for a user.
        
        Args:
            user_id: The user's ID
        """
        self._streak_cache[user_id] = 0
    
    def get_current_streak(self, user_id: int) -> int:
        """
        Get the current streak for a user.
        
        Args:
            user_id: The user's ID
        
        Returns:
            Current streak count
        """
        return self._streak_cache.get(user_id, 0)
    
    def calculate_performance_grade(self, accuracy: float) -> Tuple[str, str, str]:
        """
        Calculate a performance grade based on accuracy.
        
        Args:
            accuracy: Percentage of correct answers (0-100)
        
        Returns:
            Tuple of (grade_emoji, grade_text, encouragement)
        """
        if accuracy >= 95:
            return ("🥇", "Perfect!", "You're a natural!")
        elif accuracy >= 85:
            return ("🏆", "Excellent!", "Almost perfect!")
        elif accuracy >= 75:
            return ("🌟", "Great Job!", "Keep it up!")
        elif accuracy >= 65:
            return ("👍", "Good Work!", "You're improving!")
        elif accuracy >= 50:
            return ("😊", "Nice Effort!", "Keep practicing!")
        elif accuracy >= 35:
            return ("💪", "Keep Trying!", "Don't give up!")
        else:
            return ("🌱", "Learning!", "Every expert was once a beginner!")
    
    def format_score_display(
        self, 
        score: int, 
        max_score: int,
        show_percentage: bool = True
    ) -> str:
        """
        Format a score display string.
        
        Args:
            score: Current score
            max_score: Maximum possible score
            show_percentage: Whether to show percentage
        
        Returns:
            Formatted score string
        """
        result = f"🏆 Score: {score}"
        
        if show_percentage:
            percentage = (score / max_score * 100) if max_score > 0 else 0
            result += f" ({percentage:.0f}%)"
        
        return result
    
    def get_encouragement_for_retry(self, accuracy: float) -> str:
        """
        Get encouragement message for retrying a quiz.
        
        Args:
            accuracy: Previous quiz accuracy
        
        Returns:
            Encouragement message
        """
        if accuracy >= 80:
            return random.choice([
                "Try a higher difficulty for more challenge!",
                "You're ready for the next level!",
                "Challenge yourself with harder questions!",
            ])
        elif accuracy >= 50:
            return random.choice([
                "Review the missed questions and try again!",
                "You're close to mastery! Give it another shot!",
                "A bit more practice and you'll ace it!",
            ])
        else:
            return random.choice([
                "Practice makes perfect! Try again!",
                "Every attempt makes you stronger!",
                "Don't give up — you're on a learning journey!",
            ])
