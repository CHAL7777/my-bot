"""
Feedback Messages Templates for Interactive Quiz Bot

This module contains all the message templates for:
- Correct answer celebrations
- Wrong answer encouragement
- End-of-quiz celebrations
- Streak achievements
- Progress updates

All messages are designed to be friendly, motivating, and human-like.
"""

from typing import List, Dict, Any
import random


# ============================================================================
# CORRECT ANSWER CELEBRATIONS
# ============================================================================

CORRECT_ANSWER_CELEBRATIONS: List[Dict[str, str]] = [
    {
        "emoji": "🎉",
        "message": "Correct!",
        "description": "Basic celebration"
    },
    {
        "emoji": "👏",
        "message": "Well done!",
        "description": "Praise for good answer"
    },
    {
        "emoji": "🔥",
        "message": "Excellent work!",
        "description": "High praise for great answer"
    },
    {
        "emoji": "⭐",
        "message": "You're on fire!",
        "description": "Energetic celebration"
    },
    {
        "emoji": "🌟",
        "message": "Brilliant!",
        "description": "Impressive answer"
    },
    {
        "emoji": "🚀",
        "message": "Keep going!",
        "description": "Momentum encouragement"
    },
    {
        "emoji": "💯",
        "message": "Perfect!",
        "description": "Maximum score celebration"
    },
    {
        "emoji": "🏆",
        "message": "Champion move!",
        "description": "Victory celebration"
    },
    {
        "emoji": "🎯",
        "message": "Bullseye!",
        "description": "Precision celebration"
    },
    {
        "emoji": "💪",
        "message": "Strong answer!",
        "description": "Strength recognition"
    },
    {
        "emoji": "😊",
        "message": "Smart choice!",
        "description": "Intelligence praise"
    },
    {
        "emoji": "🙌",
        "message": "Fantastic!",
        "description": "Joyful celebration"
    },
    {
        "emoji": "✨",
        "message": "Outstanding!",
        "description": "Excellence recognition"
    },
    {
        "emoji": "🎊",
        "message": "Amazing!",
        "description": "Enthusiasm celebration"
    },
    {
        "emoji": "🥳",
        "message": "You're crushing it!",
        "description": "Energetic encouragement"
    },
]


# ============================================================================
# WRONG ANSWER ENCOURAGEMENTS (NO SHAMING!)
# ============================================================================

WRONG_ANSWER_ENCOURAGEMENTS: List[Dict[str, str]] = [
    {
        "emoji": "❌",
        "message": "Not quite, but nice try!",
        "description": "Gentle correction"
    },
    {
        "emoji": "💡",
        "message": "Don't worry — learning is progress!",
        "description": "Growth mindset encouragement"
    },
    {
        "emoji": "🤔",
        "message": "Almost there! Keep practicing!",
        "description": "Close attempt recognition"
    },
    {
        "emoji": "🌱",
        "message": "Every mistake is a learning opportunity!",
        "description": "Positive reframing"
    },
    {
        "emoji": "💪",
        "message": "You'll get it next time!",
        "description": "Future success encouragement"
    },
    {
        "emoji": "🔍",
        "message": "Nice attempt! The correct answer was {correct_option}.",
        "description": "Answer reveal"
    },
    {
        "emoji": "📚",
        "message": "That's okay! Practice makes perfect.",
        "description": "Encouragement to continue"
    },
    {
        "emoji": "😊",
        "message": "No problem! You're still learning.",
        "description": "Friendly reassurance"
    },
    {
        "emoji": "⏭️",
        "message": "On to the next one! You've got this!",
        "description": "Moving forward encouragement"
    },
    {
        "emoji": "🎯",
        "message": "Learning happens one question at a time!",
        "description": "Patience encouragement"
    },
    {
        "emoji": "👍",
        "message": "Good effort! Review the explanation and try again.",
        "description": "Effort recognition with guidance"
    },
    {
        "emoji": "🌟",
        "message": "You're building knowledge with every question!",
        "description": "Progress acknowledgment"
    },
    {
        "emoji": "🧠",
        "message": "Your brain is growing! Keep challenging yourself!",
        "description": "Neuroplasticity encouragement"
    },
    {
        "emoji": "🏃",
        "message": "Don't give up! The next one is waiting!",
        "description": "Persistence encouragement"
    },
    {
        "emoji": "📖",
        "message": "Review and recharge — you're doing great!",
        "description": "Study encouragement"
    },
]


# ============================================================================
# STREAK CELEBRATIONS
# ============================================================================

STREAK_MESSAGES: Dict[int, Dict[str, str]] = {
    2: {
        "emoji": "🔥",
        "title": "2 in a row!",
        "message": "You're heating up! Keep the momentum going!"
    },
    3: {
        "emoji": "🔥",
        "title": "3 streak!",
        "message": "On fire! 3 correct answers in a row!"
    },
    4: {
        "emoji": "🌟",
        "title": "4 streak!",
        "message": "Unstoppable! 4 questions right!"
    },
    5: {
        "emoji": "⭐",
        "title": "5 streak!",
        "message": "Legendary! 5 in a row — you're on another level!"
    },
    6: {
        "emoji": "🚀",
        "title": "6 streak!",
        "message": "Flying high! 6 correct answers!"
    },
    7: {
        "emoji": "🎉",
        "title": "7 streak!",
        "message": "Spectacular! 7 in a row!"
    },
    8: {
        "emoji": "🏆",
        "title": "8 streak!",
        "message": "Champion material! 8 straight!"
    },
    9: {
        "emoji": "👑",
        "title": "9 streak!",
        "message": "Royal performance! Almost perfect!"
    },
    10: {
        "emoji": "🥇",
        "title": "PERFECT 10!",
        "message": "GOLDEN STREAK! You're a quiz master! 🏅"
    },
}


# ============================================================================
# PROGRESS MESSAGES
# ============================================================================

PROGRESS_MESSAGES: List[Dict[str, str]] = [
    {
        "template": "📊 Question {current}/{total} | Score: {score}",
        "description": "Basic progress display"
    },
    {
        "template": "🎯 Progress: {current}/{total} | 🏆 Score: {score}",
        "description": "Progress with score"
    },
    {
        "template": "📈 {current} of {total} | Points: {score}",
        "description": "Simple progress"
    },
]


# ============================================================================
# END OF QUIZ CELEBRATIONS
# ============================================================================

# High performance (80% or above)
HIGH_SCORE_CELEBRATIONS: List[Dict[str, str]] = [
    {
        "emoji": "🎉👏🔥",
        "title": "Outstanding Performance!",
        "message": "You're absolutely crushing it! Your dedication is paying off!"
    },
    {
        "emoji": "🏆⭐🌟",
        "title": "Quiz Master!",
        "message": "Incredible work! You're proving to be a true knowledge champion!"
    },
    {
        "emoji": "🥳🎊✨",
        "title": "Spectacular!",
        "message": "Mind-blowing performance! Keep up the excellent work!"
    },
    {
        "emoji": "🚀💯👑",
        "title": "Champion!",
        "message": "Remarkable! You're leading the pack with this amazing score!"
    },
    {
        "emoji": "🎉🏅🥇",
        "title": "Gold Medal Performance!",
        "message": "First place worthy! Your hard work truly shows!"
    },
]

# Medium performance (50% - 79%)
MEDIUM_SCORE_MESSAGES: List[Dict[str, str]] = [
    {
        "emoji": "👍🙂",
        "title": "Good Job!",
        "message": "Solid effort! You're making great progress. Keep practicing!"
    },
    {
        "emoji": "💪📈",
        "title": "Nice Work!",
        "message": "You're improving! A bit more practice and you'll be unstoppable!"
    },
    {
        "emoji": "🌱🎯",
        "title": "Well Done!",
        "message": "Good understanding shown! Review the missed questions and try again!"
    },
    {
        "emoji": "👏📚",
        "title": "Keep It Up!",
        "message": "Nice performance! You're on the right track to mastery!"
    },
    {
        "emoji": "😊🚀",
        "title": "Great Effort!",
        "message": "You're doing wonderfully! Each quiz makes you stronger!"
    },
]

# Low performance (below 50%)
LOW_SCORE_ENCOURAGEMENTS: List[Dict[str, str]] = [
    {
        "emoji": "💪📚",
        "title": "Keep Learning!",
        "message": "Don't give up! Every expert was once a beginner. Review and try again!"
    },
    {
        "emoji": "🌱🔍",
        "title": "Learning Journey!",
        "message": "This is just the beginning! Learning takes time and you're on your way!"
    },
    {
        "emoji": "💡📖",
        "title": "Practice Makes Perfect!",
        "message": "Keep going! Every question you attempt makes you smarter!"
    },
    {
        "emoji": "🤗🎯",
        "title": "You're Trying!",
        "message": "Effort matters! Review the explanations and you'll improve!"
    },
    {
        "emoji": "🌟⏭️",
        "title": "Onward and Upward!",
        "message": "This quiz helped you learn! The next one will be even better!"
    },
]

# Perfect score (100%)
PERFECT_SCORE_CELEBRATION: Dict[str, str] = {
    "emoji": "🏆🎉🔥✨👑",
    "title": "PERFECT SCORE!",
    "message": "ABSOLUTELY INCREDIBLE! You've mastered this quiz perfectly! 🎊"
}


# ============================================================================
# QUIZ START MESSAGES
# ============================================================================

QUIZ_START_MESSAGES: List[Dict[str, str]] = [
    {
        "emoji": "🎯",
        "message": "Let's do this! Your quiz is ready!",
        "description": "Energetic start"
    },
    {
        "emoji": "🚀",
        "message": "Time to shine! Good luck!",
        "description": "Motivational start"
    },
    {
        "emoji": "⭐",
        "message": "Your challenge awaits! Give it your best!",
        "description": "Challenge welcome"
    },
    {
        "emoji": "💪",
        "message": "Ready, set, quiz! Let's go!",
        "description": "Action-oriented start"
    },
    {
        "emoji": "🌟",
        "message": "New quiz, new opportunity to learn!",
        "description": "Learning-focused start"
    },
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_random_celebration() -> Dict[str, str]:
    """Get a random correct answer celebration message"""
    return random.choice(CORRECT_ANSWER_CELEBRATIONS)


def get_random_encouragement(correct_option: str = None) -> Dict[str, str]:
    """Get a random wrong answer encouragement message"""
    message_data = random.choice(WRONG_ANSWER_ENCOURAGEMENTS)
    
    # If correct_option is provided and message has placeholder, replace it
    if correct_option and "{correct_option}" in message_data["message"]:
        message_data["message"] = message_data["message"].format(correct_option=correct_option)
    
    return message_data


def get_streak_message(streak_count: int) -> Dict[str, str]:
    """Get streak celebration message based on streak count"""
    # Check if we have a specific message for this streak count
    if streak_count in STREAK_MESSAGES:
        return STREAK_MESSAGES[streak_count]
    
    # For streaks beyond 10, scale up the celebration
    if streak_count > 10:
        return {
            "emoji": "🏆🔥",
            "title": f"{streak_count} Streak!",
            "message": "You're on a legendary run! Incredible consistency!"
        }
    
    # For streaks not in our dictionary, create dynamic message
    if streak_count >= 2:
        return {
            "emoji": "🔥",
            "title": f"{streak_count} Streak!",
            "message": f"Amazing! {streak_count} correct answers in a row!"
        }
    
    return {"emoji": "", "title": "", "message": ""}


def get_end_of_quiz_message(
    accuracy: float, 
    score: int, 
    total_questions: int,
    streak: int = 0
) -> Dict[str, str]:
    """
    Get end-of-quiz celebration message based on performance.
    
    Args:
        accuracy: Percentage of correct answers (0-100)
        score: Total points earned
        total_questions: Total number of questions in quiz
        streak: Longest streak achieved
    
    Returns:
        Dictionary with emoji, title, and message
    """
    # Perfect score!
    if accuracy == 100:
        result = PERFECT_SCORE_CELEBRATION.copy()
        if streak >= 5:
            result["message"] += f"\n\n🔥 Amazing {streak}-question streak!"
        return result
    
    # High performance
    if accuracy >= 80:
        result = random.choice(HIGH_SCORE_CELEBRATIONS)
        if streak >= 5:
            result["message"] += f"\n\n🔥 Incredible {streak}-question streak!"
        return result
    
    # Medium performance
    if accuracy >= 50:
        result = random.choice(MEDIUM_SCORE_MESSAGES)
        return result
    
    # Low performance - encouraging!
    result = random.choice(LOW_SCORE_ENCOURAGEMENTS)
    if streak >= 3:
        result["message"] += f"\n\n🔥 You had a {streak}-question streak! You're improving!"
    return result


def format_progress_message(
    current: int, 
    total: int, 
    score: int,
    streak: int = 0
) -> str:
    """Format a progress message showing current position and score"""
    template = random.choice(PROGRESS_MESSAGES)["template"]
    message = template.format(current=current, total=total, score=score)
    
    if streak >= 3:
        message += f" | 🔥 {streak} streak!"
    
    return message


def get_quiz_start_message() -> Dict[str, str]:
    """Get a random quiz start message"""
    return random.choice(QUIZ_START_MESSAGES)


# ============================================================================
# BEAUTIFUL RESULT TEMPLATES (For Enhanced Interactive Quiz)
# ============================================================================

# Beautiful result headers with celebration emojis
BEAUTIFUL_RESULT_HEADERS: List[Dict[str, str]] = [
    {
        "emoji": "🎉🏅🥇",
        "title": "GOLD MEDAL PERFORMANCE!",
        "style": "gold"
    },
    {
        "emoji": "🏆🔥✨",
        "title": "CHAMPION MOVE!",
        "style": "champion"
    },
    {
        "emoji": "⭐🌟💫",
        "title": "ABSOLUTELY BRILLIANT!",
        "style": "brilliant"
    },
    {
        "emoji": "🚀💯👑",
        "title": "OUTSTANDING!",
        "style": "outstanding"
    },
    {
        "emoji": "🎊🥳🌈",
        "title": "FANTASTIC!",
        "style": "fantastic"
    },
]

# Correct answer celebration (immediate feedback)
CORRECT_ANSWER_CELEBRATIONS_BEAUTIFUL: List[Dict[str, str]] = [
    {
        "emoji": "🎉",
        "message": "BRILLIANT! That's correct! ✨",
        "style": "celebration"
    },
    {
        "emoji": "🏆",
        "message": "CHAMPION! You got it! 🏅",
        "style": "champion"
    },
    {
        "emoji": "🔥",
        "message": "ON FIRE! Correct answer! 🔥",
        "style": "fire"
    },
    {
        "emoji": "⭐",
        "message": "STAR POWER! Exactly right! 🌟",
        "style": "star"
    },
    {
        "emoji": "🎯",
        "message": "BULLSEYE! Perfect hit! 🎯",
        "style": "bullseye"
    },
    {
        "emoji": "💯",
        "message": "PERFECT! Keep it up! 💯",
        "style": "perfect"
    },
    {
        "emoji": "🙌",
        "message": "AMAZING! You nailed it! 🙌",
        "style": "amazing"
    },
    {
        "emoji": "👏",
        "message": "EXCELLENT! Well done! 👏",
        "style": "excellent"
    },
    {
        "emoji": "🌈",
        "message": "SPECTACULAR! Correct! 🌈",
        "style": "spectacular"
    },
    {
        "emoji": "🚀",
        "message": "ROCKET POWER! Right answer! 🚀",
        "style": "rocket"
    },
]

# Wrong answer encouragement (no shaming!)
WRONG_ANSWER_BEAUTIFUL: List[Dict[str, str]] = [
    {
        "emoji": "💪",
        "message": "KEEP GOING! You can do this! 💪",
        "style": "encouragement"
    },
    {
        "emoji": "🌱",
        "message": "LEARNING JOURNEY! Every try counts! 🌱",
        "style": "growth"
    },
    {
        "emoji": "🔍",
        "message": "ALMOST! The answer was {correct_option} 🔍",
        "style": "hint"
    },
    {
        "emoji": "💡",
        "message": "NICE TRY! Learning is progress! 💡",
        "style": "learning"
    },
    {
        "emoji": "🌟",
        "message": "GOOD EFFORT! Next one is yours! 🌟",
        "style": "effort"
    },
    {
        "emoji": "🤗",
        "message": "DON'T GIVE UP! You're doing great! 🤗",
        "style": "support"
    },
    {
        "emoji": "🎯",
        "message": "ALMOST THERE! Keep practicing! 🎯",
        "style": "close"
    },
    {
        "emoji": "📚",
        "message": "REVIEW TIME! Knowledge is growing! 📚",
        "style": "review"
    },
]

# Progress bar styles with emojis
PROGRESS_BAR_STYLES: Dict[str, str] = {
    "stars": "⭐⭐⭐⭐⭐",
    "fire": "🔥🔥🔥🔥🔥",
    "medals": "🥇🥇🥇🥇🥇",
    "checkmarks": "✅✅✅✅✅",
    "rocket": "🚀🚀🚀🚀🚀",
}

# Beautiful result section templates
RESULT_SECTIONS: Dict[str, str] = {
    "score": "🏆 YOUR SCORE:",
    "correct": "✅ CORRECT ANSWERS:",
    "accuracy": "📈 ACCURACY:",
    "time": "⏱️ TIME TAKEN:",
    "streak": "🔥 STREAK:",
    "next": "⏭️ NEXT QUESTION:",
    "complete": "🎊 QUIZ COMPLETE!",
}

# Performance grade emojis and messages
PERFORMANCE_GRADES: Dict[str, Dict[str, str]] = {
    "gold": {
        "emoji": "🥇",
        "title": "GOLD MEDAL",
        "message": "First place worthy performance!"
    },
    "silver": {
        "emoji": "🥈",
        "title": "SILVER STAR",
        "message": "Excellent work, so close to perfect!"
    },
    "bronze": {
        "emoji": "🥉",
        "title": "BRONZE CHAMPION",
        "message": "Great effort, keep improving!"
    },
    "master": {
        "emoji": "👑",
        "title": "QUIZ MASTER",
        "message": "You're a true knowledge champion!"
    },
    "rising": {
        "emoji": "🌱",
        "title": "RISING STAR",
        "message": "Every expert was once a beginner!"
    },
}


# ============================================================================
# HELPER FUNCTIONS FOR BEAUTIFUL RESULTS
# ============================================================================

def get_beautiful_result_header(accuracy: float) -> Dict[str, str]:
    """
    Get a beautiful result header based on accuracy.
    
    Args:
        accuracy: Percentage of correct answers (0-100)
    
    Returns:
        Dictionary with emoji, title, and style
    """
    if accuracy >= 90:
        return {
            "emoji": "🎉🏅🥇",
            "title": "GOLD MEDAL PERFORMANCE!",
            "style": "gold"
        }
    elif accuracy >= 80:
        return {
            "emoji": "🏆🔥✨",
            "title": "CHAMPION MOVE!",
            "style": "champion"
        }
    elif accuracy >= 70:
        return {
            "emoji": "⭐🌟💫",
            "title": "ABSOLUTELY BRILLIANT!",
            "style": "brilliant"
        }
    elif accuracy >= 60:
        return {
            "emoji": "🚀💯👑",
            "title": "OUTSTANDING!",
            "style": "outstanding"
        }
    elif accuracy >= 50:
        return {
            "emoji": "👍😊",
            "title": "GOOD JOB!",
            "style": "good"
        }
    else:
        return {
            "emoji": "💪🌱",
            "title": "KEEP LEARNING!",
            "style": "improvement"
        }


def get_correct_answer_celebration() -> Dict[str, str]:
    """Get a random beautiful correct answer celebration"""
    return random.choice(CORRECT_ANSWER_CELEBRATIONS_BEAUTIFUL)


def get_wrong_answer_encouragement(correct_option: str = None) -> Dict[str, str]:
    """Get a random beautiful wrong answer encouragement"""
    message_data = random.choice(WRONG_ANSWER_BEAUTIFUL)
    
    # If correct_option is provided and message has placeholder, replace it
    if correct_option and "{correct_option}" in message_data["message"]:
        message_data["message"] = message_data["message"].format(correct_option=correct_option)
    
    return message_data


def build_beautiful_result_message(
    accuracy: float,
    correct_count: int,
    total_questions: int,
    score: int,
    time_taken: float,
    streak: int = 0,
    difficulty: str = "simple"
) -> str:
    """
    Build a beautiful complete result message.
    
    Args:
        accuracy: Percentage of correct answers
        correct_count: Number of correct answers
        total_questions: Total questions in quiz
        score: Total points earned
        time_taken: Total time in seconds
        streak: Longest streak achieved
        difficulty: Quiz difficulty level
    
    Returns:
        Formatted beautiful result message
    """
    # Get header based on accuracy
    header = get_beautiful_result_header(accuracy)
    
    # Build the message
    lines = []
    
    # Header with celebration
    lines.append(f"{header['emoji']} {header['title']}")
    lines.append("")
    lines.append(f"✨ {header['message']}")
    lines.append("")
    lines.append("─" * 25)
    lines.append("")
    
    # Score section
    lines.append(f"📊 Quiz Results:")
    lines.append("")
    lines.append(f"  🏆 Score: {score} points")
    lines.append(f"  ✅ Correct: {correct_count}/{total_questions}")
    lines.append(f"  📈 Accuracy: {accuracy:.1f}%")
    lines.append(f"  ⏱️ Time: {time_taken:.0f}s")
    lines.append("")
    lines.append("─" * 25)
    lines.append("")
    
    # Streak if notable
    if streak >= 2:
        lines.append(f"🔥 Streak: {streak} in a row!")
        lines.append("")
    
    # Encouragement based on performance
    if accuracy >= 80:
        lines.append("💪 KEEP IT UP! You're doing amazing!")
    elif accuracy >= 50:
        lines.append("🌱 GREAT EFFORT! Review and try again!")
    else:
        lines.append("📚 KEEP PRACTICING! Every question helps you learn!")
    
    return "\n".join(lines)


def build_single_answer_result(
    is_correct: bool,
    selected_option: str,
    correct_option: str,
    points_earned: int,
    time_taken: float,
    streak: int = 0,
    explanation: str = None
) -> str:
    """
    Build a beautiful single answer result message.
    
    Args:
        is_correct: Whether the answer was correct
        selected_option: The option user selected (A, B, C, D)
        correct_option: The correct answer option
        points_earned: Points earned for this answer
        time_taken: Time taken in seconds
        streak: Current streak count
        explanation: Optional explanation for the answer
    
    Returns:
        Formatted beautiful result message
    """
    lines = []
    
    if is_correct:
        # Correct answer celebration
        celebration = get_correct_answer_celebration()
        lines.append(f"{celebration['emoji']} *{celebration['message']}*")
        lines.append("")
        lines.append(f"✨ +{points_earned} point{'s' if points_earned > 1 else ''}")
    else:
        # Wrong answer encouragement
        encouragement = get_wrong_answer_encouragement(correct_option)
        lines.append(f"{encouragement['emoji']} *{encouragement['message']}*")
        lines.append("")
    
    # Time taken
    lines.append(f"⏱️ {time_taken:.1f}s")
    lines.append("")
    
    # Streak
    if streak >= 2:
        lines.append(f"🔥 {streak} streak!")
        lines.append("")
    
    # Correct answer
    lines.append("─" * 20)
    lines.append("")
    lines.append(f"📚 Correct Answer: {correct_option}")
    lines.append("")
    
    # Explanation if available
    if explanation:
        lines.append("─" * 20)
        lines.append("")
        lines.append("💡 *EXPLANATION:*")
        lines.append("")
        # Truncate long explanations
        if len(explanation) > 300:
            explanation = explanation[:300] + "..."
        lines.append(explanation)
    
    return "\n".join(lines)


def get_check_answer_button_text() -> str:
    """Get the beautiful 'Check Answer' button text with arrow"""
    return "✅ Check Answer → Learn Why"


def get_progress_indicator(current: int, total: int) -> str:
    """Get a beautiful progress indicator with emojis"""
    filled = "●" * current
    empty = "○" * (total - current)
    percentage = (current / total * 100) if total > 0 else 0
    bar = f"[{filled}{empty}] {percentage:.0f}%"
    return f"📊 {bar}"


def get_difficulty_emoji(difficulty: str) -> str:
    """Get emoji for difficulty level"""
    emojis = {
        "simple": "🟢",
        "medium": "🟡",
        "hard": "🔴"
    }
    return emojis.get(difficulty, "⚡")


# ============================================================================
# ENHANCED QUIZ RESULT BUILDERS (Learning Journey Style)
# ============================================================================

def get_performance_grade(accuracy: float) -> str:
    """
    Get performance grade based on accuracy percentage.

    Args:
        accuracy: Accuracy percentage (0-100)

    Returns:
        Grade key: "excellent", "great", "good", "average", or "needs_work"
    """
    if accuracy >= 90:
        return "excellent"
    elif accuracy >= 75:
        return "great"
    elif accuracy >= 60:
        return "good"
    elif accuracy >= 40:
        return "average"
    else:
        return "needs_work"


def get_progress_bar(accuracy: int, total: int = 10) -> str:
    """
    Generate a visual progress bar using emojis.

    Args:
        accuracy: Percentage value (0-100)
        total: Number of blocks for the bar (default 10)

    Returns:
        Progress bar string like "🟩🟩🟩🟨⬜⬜⬜⬜⬜⬜ 35%"
    """
    filled = max(0, min(accuracy // 10, total))
    empty = max(0, total - filled)

    bar = "🟩" * filled + "⬜" * empty
    return f"{bar} {accuracy}%"


def get_emoji_bar(correct: int, total: int) -> str:
    """
    Generate an emoji bar showing correct vs incorrect.

    Args:
        correct: Number of correct answers
        total: Total questions

    Returns:
        Emoji bar like "✅✅✅❌❌❌❌❌❌❌ 3/10"
    """
    correct_bar = "✅" * correct
    incorrect_bar = "❌" * (total - correct)
    return f"{correct_bar}{incorrect_bar} {correct}/{total}"


def get_grade_badge(accuracy: float) -> str:
    """Get grade badge based on accuracy"""
    if accuracy >= 90:
        return "👑 Quiz Master"
    elif accuracy >= 75:
        return "⭐ Star Performer"
    elif accuracy >= 60:
        return "🌟 Great Job"
    elif accuracy >= 40:
        return "🌱 Rising Star"
    else:
        return "🌱 Learning Journey"


def build_learning_journey_result(
    correct: int,
    total: int,
    accuracy: float,
    time_spent: float,
    subject_name: str,
    chapter_name: str,
    difficulty: str
) -> str:
    """
    Build the specific "Learning Journey!" result message format.

    This creates the exact format requested with beautiful styling:
    🌱🔍 *Learning Journey!*
    This is just the beginning! Learning takes time and you're on your way!

    Args:
        correct: Number of correct answers
        total: Total questions
        accuracy: Accuracy percentage
        time_spent: Time spent in seconds
        subject_name: Name of the subject
        chapter_name: Name of the chapter
        difficulty: Difficulty level

    Returns:
        Formatted beautiful result message
    """
    lines = []

    # Header
    lines.append("🌱🔍 *LEARNING JOURNEY!*")
    lines.append("")
    lines.append("This is just the beginning! Learning takes time and you're on your way!")
    lines.append("")
    lines.append("─────────────────────────")
    lines.append("")
    lines.append("🏆 *YOUR RESULTS:*")
    lines.append("")
    lines.append(f"✅ *{correct}/{total}* questions correct")
    lines.append(f"📈 *Accuracy:* *{accuracy:.0f}%*")
    lines.append(f"⏱️ *Time:* *{time_spent:.0f}s*")
    lines.append("")
    lines.append("💪 *KEEP PRACTICING!*")
    lines.append("")
    lines.append("Every expert was once a beginner! 🌱")
    lines.append("")
    lines.append("─────────────────────────")
    lines.append("")
    lines.append(f"📚 Subject: {subject_name}")
    lines.append(f"📖 Chapter: {chapter_name}")
    lines.append(f"⚡ Difficulty: {difficulty.capitalize()}")
    lines.append("")
    lines.append("─────────────────────────")
    lines.append("")
    lines.append(f"📊 Progress: {get_progress_bar(int(accuracy))}")
    lines.append(f"🏅 Grade: {get_grade_badge(accuracy)}")
    lines.append("")
    lines.append("─────────────────────────")
    lines.append("")
    lines.append("💡 *Every attempt makes you stronger!*")

    return "\n".join(lines)


def build_enhanced_result_message(
    correct: int,
    total: int,
    accuracy: float,
    time_spent: float,
    subject_name: str,
    chapter_name: str,
    difficulty: str
) -> str:
    """
    Build a beautiful enhanced result message with progress bar.

    Args:
        correct: Number of correct answers
        total: Total questions
        accuracy: Accuracy percentage
        time_spent: Time spent in seconds
        subject_name: Name of the subject
        chapter_name: Name of the chapter
        difficulty: Difficulty level

    Returns:
        Formatted beautiful result message
    """
    lines = []

    # Header with celebration based on performance
    grade = get_performance_grade(accuracy)
    if grade == "excellent":
        header_emoji = "🎉🏅🥇"
        header_title = "ABSOLUTELY AMAZING!"
    elif grade == "great":
        header_emoji = "🏆🔥✨"
        header_title = "OUTSTANDING!"
    elif grade == "good":
        header_emoji = "⭐🌟💫"
        header_title = "GREAT JOB!"
    elif grade == "average":
        header_emoji = "👍😊"
        header_title = "GOOD EFFORT!"
    else:
        header_emoji = "💪🌱"
        header_title = "KEEP PRACTICING!"

    lines.append(f"{header_emoji} *{header_title}*")
    lines.append("")

    # Motivational message based on performance
    if grade == "excellent":
        lines.append("Outstanding performance! You're truly mastering this topic!")
    elif grade == "great":
        lines.append("Fantastic work! Keep up the excellent progress!")
    elif grade == "good":
        lines.append("Good job! A bit more practice and you'll be unstoppable!")
    elif grade == "average":
        lines.append("Nice effort! Review the missed questions and try again!")
    else:
        lines.append("Every expert was once a beginner! Don't give up!")

    lines.append("")
    lines.append("─" * 28)
    lines.append("")

    # Results section
    lines.append("📊 *YOUR RESULTS:*")
    lines.append("")
    lines.append(get_emoji_bar(correct, total))
    lines.append("")
    lines.append(f"📈 *Accuracy:* *{accuracy:.0f}%*")
    lines.append(f"⏱️ *Time:* *{time_spent:.0f}s* ({time_spent/total:.1f}s avg)")
    lines.append("")

    # Progress bar visual
    lines.append(f"📈 Progress: {get_progress_bar(int(accuracy))}")
    lines.append("")

    # Grade badge
    lines.append(f"🏅 Grade: {get_grade_badge(accuracy)}")
    lines.append("")

    # Divider
    lines.append("─" * 28)
    lines.append("")

    # Quiz info
    lines.append(f"📚 *{subject_name}*")
    lines.append(f"📖 *{chapter_name}*")
    lines.append(f"⚡ *{difficulty.capitalize()}*")
    lines.append("")

    # Footer with encouragement
    lines.append("─" * 28)
    lines.append("")

    if grade == "excellent":
        lines.append("🎊 Incredible! Try a harder difficulty next time!")
    elif grade == "great":
        lines.append("⭐ Amazing progress! Keep going!")
    elif grade == "good":
        lines.append("🌱 Every session makes you stronger!")
    else:
        lines.append("💪 Keep practicing — you're improving!")

    return "\n".join(lines)

