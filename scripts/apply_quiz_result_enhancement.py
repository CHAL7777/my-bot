"""
Patch Script: Enhanced Quiz Results with Beautiful Learning Journey UI

This script patches the quiz handlers to use beautiful result templates
with progress bars, grade badges, and interactive buttons.
"""

import os
import re

def patch_quiz_fixed():
    """Patch quiz_fixed.py to use beautiful result templates"""
    
    file_path = "/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot/app/handlers/quiz_fixed.py"
    
    with open(file_path, "r") as f:
        content = f.read()
    
    # Check if already patched
    if "build_learning_journey_result" in content:
        print("✅ quiz_fixed.py already patched")
        return
    
    # Find and replace the finish_quiz function
    old_pattern = r'async def finish_quiz\(message: types\.Message.*?(?=\n\n@router\.callback_query)'
    
    new_function = '''async def finish_quiz(message: types.Message, state: FSMContext, score: int, total_questions: int, quiz_session_id: str, user_id: int, subject_name: str, chapter_name: str, difficulty: str, answers: List[Dict[str, Any]]):
    """Finish quiz and show results with beautiful learning journey UI"""
    from app.utils.feedback_messages import (
        build_learning_journey_result,
        build_enhanced_result_message,
        get_performance_grade
    )
    
    correct_count = sum(1 for a in answers if a.get('is_correct', False))
    accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0
    state_data = await state.get_data()
    start_time = state_data.get('start_time', time.time())
    total_time = time.time() - start_time
    
    # Use beautiful learning journey result message
    grade = get_performance_grade(accuracy)
    
    # Choose template based on performance
    if grade in ["excellent", "great"]:
        # High performers get celebratory message
        result_message = build_enhanced_result_message(
            correct=correct_count,
            total=total_questions,
            accuracy=accuracy,
            time_spent=total_time,
            subject_name=subject_name,
            chapter_name=chapter_name,
            difficulty=difficulty
        )
    else:
        # Learning-focused message for lower scores
        result_message = build_learning_journey_result(
            correct=correct_count,
            total=total_questions,
            accuracy=accuracy,
            time_spent=total_time,
            subject_name=subject_name,
            chapter_name=chapter_name,
            difficulty=difficulty
        )
    
    await state.clear()
    
    try:
        await message.edit_text(result_message, parse_mode='Markdown', reply_markup=QuizKeyboard.get_quiz_results_keyboard(quiz_session_id))
    except Exception as e:
        logger.error(f"Error showing results: {e}")
        await message.answer(result_message, parse_mode='Markdown', reply_markup=QuizKeyboard.get_quiz_results_keyboard(quiz_session_id))'''
    
    # Replace the function
    new_content = re.sub(old_pattern, new_function + '\n\n', content, flags=re.DOTALL)
    
    with open(file_path, "w") as f:
        f.write(new_content)
    
    print("✅ quiz_fixed.py patched successfully")


def patch_quiz_py():
    """Patch quiz.py to use beautiful result templates"""
    
    file_path = "/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot/app/handlers/quiz.py"
    
    with open(file_path, "r") as f:
        content = f.read()
    
    # Check if already patched
    if "build_learning_journey_result" in content:
        print("✅ quiz.py already patched")
        return
    
    # Find and replace the finish_quiz function
    old_pattern = r'async def finish_quiz\(callback: types\.CallbackQuery.*?(?=\n\n@router\.callback_query)'
    
    new_function = '''async def finish_quiz(callback: types.CallbackQuery, state: FSMContext, plain_sender: PlainTextMessageSender):
    """Finish quiz and show results with beautiful learning journey UI"""
    from app.utils.feedback_messages import (
        build_learning_journey_result,
        build_enhanced_result_message,
        get_performance_grade
    )
    
    data = await state.get_data()
    quiz_session_id = data.get('quiz_session_id')
    score = data.get('score', 0)
    answers = data.get('answers', [])
    subject_name = data.get('subject_name', '')
    chapter_name = data.get('chapter_name', '')
    difficulty = data.get('difficulty', 'simple')
    
    # Calculate statistics
    total_questions = len(answers)
    correct_answers = sum(1 for answer in answers if answer.get('is_correct', False))
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Get time spent
    start_time = data.get('start_time', time.time())
    time_spent = time.time() - start_time
    
    # Use beautiful learning journey result message
    grade = get_performance_grade(accuracy)
    
    # Choose template based on performance
    if grade in ["excellent", "great"]:
        # High performers get celebratory message
        result_message = build_enhanced_result_message(
            correct=correct_answers,
            total=total_questions,
            accuracy=accuracy,
            time_spent=time_spent,
            subject_name=subject_name,
            chapter_name=chapter_name,
            difficulty=difficulty
        )
    else:
        # Learning-focused message for lower scores
        result_message = build_learning_journey_result(
            correct=correct_answers,
            total=total_questions,
            accuracy=accuracy,
            time_spent=time_spent,
            subject_name=subject_name,
            chapter_name=chapter_name,
            difficulty=difficulty
        )
    
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        result_message,
        reply_markup=QuizKeyboard.get_quiz_results_keyboard(quiz_session_id)
    )
    
    await state.clear()
    await callback.answer()'''
    
    # Replace the function
    new_content = re.sub(old_pattern, new_function + '\n\n', content, flags=re.DOTALL)
    
    with open(file_path, "w") as f:
        f.write(new_content)
    
    print("✅ quiz.py patched successfully")


if __name__ == "__main__":
    print("🎨 Patching quiz handlers with beautiful result templates...")
    patch_quiz_fixed()
    patch_quiz_py()
    print("\n✨ Patch complete! The quiz results now feature:")
    print("  - Beautiful Learning Journey header with emojis")
    print("  - Visual progress bar (🟩🟩🟨⬜⬜)")
    print("  - Emoji bar showing correct/incorrect (✅✅❌❌)")
    print("  - Grade badge (👑 Quiz Master, 🌱 Rising Star)")
    print("  - Interactive action buttons")

