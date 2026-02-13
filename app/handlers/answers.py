"""
Beautiful Interactive Quiz Answers Handler

This module provides enhanced quiz experience with:
- Beautiful result messages with emojis and celebration
- Interactive answer checking with visual feedback
- Streak tracking and encouragement
- Learning-focused explanation display
"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import time
import asyncio
import logging

from app.handlers.quiz import QuizStates
from app.keyboards.quiz import QuizKeyboard
from app.keyboards.menu import MainMenuKeyboard
from app.services.quiz_service import QuizService
from app.services.feedback_service import FeedbackService, FeedbackResult
from app.db.base import get_db
from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.user_repo import UserRepository
from app.utils.constants import EMOJIS
from app.utils.plain_sender import PlainTextMessageSender
from app.utils.feedback_messages import (
    get_beautiful_result_header,
    get_correct_answer_celebration,
    get_wrong_answer_encouragement,
    build_beautiful_result_message,
    build_single_answer_result,
    get_check_answer_button_text,
    get_progress_indicator,
    get_difficulty_emoji,
)

logger = logging.getLogger(__name__)

router = Router()

# Initialize feedback service (singleton for streak tracking)
_feedback_service = FeedbackService()

# Auto-progress delay in seconds - gives user time to read explanation
AUTO_PROGRESS_DELAY = 2


# ============================================================================
# HELPER FUNCTIONS FOR LEARNING FLOW
# ============================================================================

def _get_plain_sender(update) -> PlainTextMessageSender:
    """Get PlainTextMessageSender instance from update"""
    if isinstance(update, CallbackQuery):
        return PlainTextMessageSender(update.bot)
    elif isinstance(update, types.Message):
        return PlainTextMessageSender(update.bot)
    else:
        raise ValueError(f"Unsupported update type: {type(update)}")


def _build_question_text(
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    question_number: int,
    total_questions: int,
    score: int
) -> str:
    """Build the question message text with beautiful formatting."""
    lines = [
        f"📊 Question {question_number}/{total_questions} | 🏆 Score: {score}",
        "",
        question_text,
        "",
        "🔵 A. " + option_a,
        "🟢 B. " + option_b,
        "🟡 C. " + option_c,
        "🔴 D. " + option_d
    ]
    return "\n".join(lines)


def _build_result_text(
    is_correct: bool,
    selected_option: str,
    correct_option: str,
    explanation: str,
    points_earned: int,
    time_taken: float,
    current_score: int,
    question_number: int,
    total_questions: int,
    streak: int = 0
) -> str:
    """
    Build a beautiful result message with celebration or encouragement.
    
    This is the core of the learning experience - user MUST see:
    1. Whether they were correct/incorrect with celebration
    2. Points earned
    3. The correct answer
    4. An explanation of why (optional)
    5. Streak if applicable
    """
    lines = []
    
    # Correct answer celebration
    if is_correct:
        celebration = get_correct_answer_celebration()
        lines.append(f"{celebration['emoji']} *{celebration['message']}*")
        if points_earned > 0:
            lines.append("")
            lines.append(f"✨ +{points_earned} point{'s' if points_earned > 1 else ''}")
    else:
        # Wrong answer encouragement (no shaming!)
        encouragement = get_wrong_answer_encouragement(correct_option)
        lines.append(f"{encouragement['emoji']} *{encouragement['message']}*")
    
    lines.append("")
    lines.append(f"⏱️ *{time_taken:.1f}s*")
    
    # Streak indicator
    if streak >= 2:
        lines.append("")
        lines.append(f"🔥 *{streak} streak!*")
    
    lines.append("")
    lines.append("─" * 20)
    lines.append("")
    
    # Show correct answer
    lines.append(f"📚 *Correct Answer: {correct_option}*")
    lines.append("")
    
    # MANDATORY EXPLANATION
    if explanation:
        lines.append("─" * 20)
        lines.append("")
        lines.append("💡 *EXPLANATION:*")
        lines.append("")
        # Truncate long explanations
        if len(explanation) > 300:
            explanation = explanation[:300] + "..."
        lines.append(explanation)
    
    lines.append("")
    lines.append("─" * 20)
    lines.append("")
    
    # Score and progress
    lines.append(f"🏆 Score: {current_score}")
    
    # Progress indicator
    if question_number < total_questions:
        lines.append("")
        lines.append(f"📊 {get_progress_indicator(question_number, total_questions)}")
        lines.append("")
        lines.append("⏭️ Loading next question...")
    else:
        lines.append("")
        lines.append("🎊 *QUIZ COMPLETE!*")
    
    return "\n".join(lines)


async def _is_duplicate_callback(
    user_id: int,
    callback_data: str,
    state: FSMContext
) -> bool:
    """
    Check if this callback has already been processed.
    Prevents double-clicks and race conditions.
    """
    data = await state.get_data()
    processed_callbacks = data.get('processed_callbacks', [])
    
    # Clean old callbacks (older than 30 seconds)
    current_time = time.time()
    processed_callbacks = [
        cb for cb in processed_callbacks
        if current_time - cb.get('time', 0) < 30
    ]
    
    # Check if this callback was processed
    for cb in processed_callbacks:
        if cb.get('data') == callback_data:
            return True
    
    # Add this callback to processed list
    processed_callbacks.append({
        'data': callback_data,
        'time': current_time
    })
    
    await state.update_data(processed_callbacks=processed_callbacks)
    return False


async def _get_question_by_id(
    questions: list,
    question_id: int
) -> dict:
    """Find a question by ID in the questions list."""
    for q in questions:
        if q.get('question_id') == question_id:
            return q
    return None


# ============================================================================
# CALLBACK HANDLERS - LEARNING FLOW
# ============================================================================

@router.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext,
                       has_active_subscription: bool = False):
    """
    QUESTION PHASE: Handle user's initial option selection.
    
    Instead of immediately showing correctness, this triggers the LOCK PHASE:
    - Stores the selected option in FSM
    - Replaces option buttons with "Check Answer → Learn Why"
    - Prevents changing the answer
    
    This forces user to engage with the learning content before proceeding.
    """
    plain_sender = _get_plain_sender(callback)
    
    # Parse callback: answer_{question_id}_{option}
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Invalid answer format", show_alert=True)
        return
    
    question_id = int(parts[1])
    selected_option = parts[2]
    user_id = callback.from_user.id
    
    # Check for duplicate callback (prevent double-clicks)
    if await _is_duplicate_callback(user_id, callback.data, state):
        await callback.answer("Already processed!", show_alert=False)
        return
    
    # Get current state data
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    questions = quiz_data.get('questions', [])
    current_index = data.get('current_question_index', 0)
    total_questions = len(questions)
    score = data.get('score', 0)
    
    # Validate quiz state
    if not questions or current_index >= len(questions):
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "❌ QUIZ SESSION LOST\n\n"
            "Your quiz session expired or was reset.\n"
            "Please start a new quiz!",
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Find the current question
    question = None
    for q in questions:
        if q.get('question_id') == question_id:
            question = q
            break
    
    if not question:
        await callback.answer("Question not found", show_alert=True)
        return
    
    # Check if question already answered (prevent re-answering)
    answered_questions = data.get('answered_questions', {})
    if answered_questions.get(str(question_id), {}).get('locked', False):
        await callback.answer("Already answered! Check your answer.", show_alert=False)
        return
    
    # LOCK PHASE: Store selection and update keyboard
    await state.update_data({
        'selected_option': selected_option,
        'question_start_time': time.time()
    })
    
    # Mark question as locked
    answered_questions[str(question_id)] = {
        'selected': selected_option,
        'locked': True,
        'checked': False
    }
    await state.update_data(answered_questions=answered_questions)
    
    # Build the keyboard for LOCK phase
    keyboard = QuizKeyboard.get_locked_keyboard(
        question_number=current_index + 1,
        total_questions=total_questions,
        question_id=question_id,
        selected_option=selected_option
    )
    
    # Build question text (keep same format)
    question_text = _build_question_text(
        question_text=question['question_text'],
        option_a=question['option_a'],
        option_b=question['option_b'],
        option_c=question['option_c'],
        option_d=question['option_d'],
        question_number=current_index + 1,
        total_questions=total_questions,
        score=score
    )
    
    # Edit message to show locked state
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        question_text,
        reply_markup=keyboard
    )
    
    await callback.answer(f"✓ Selected {selected_option}. Click to check!")


@router.callback_query(F.data.startswith("check_"))
async def handle_check_answer(callback: types.CallbackQuery, state: FSMContext,
                             has_active_subscription: bool = False):
    """
    REVEAL PHASE: Handle "Check Answer → Learn Why" button click.
    
    This is the core learning moment:
    - Evaluate correctness
    - Show correct/incorrect status
    - Show the correct answer
    - Show the explanation (MANDATORY)
    - Auto-progress to next question after delay
    """
    plain_sender = _get_plain_sender(callback)
    
    # Parse callback: check_{question_id}_{selected_option}
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    question_id = int(parts[1])
    selected_option = parts[2]
    user_id = callback.from_user.id
    
    # Check for duplicate callback
    if await _is_duplicate_callback(user_id, callback.data, state):
        await callback.answer("Already checked!", show_alert=False)
        return
    
    # Get current state data
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    questions = quiz_data.get('questions', [])
    current_index = data.get('current_question_index', 0)
    total_questions = len(questions)
    score = data.get('score', 0)
    quiz_session_id = data.get('quiz_session_id')
    subject_id = data.get('subject_id')
    chapter_id = data.get('chapter_id')
    difficulty = data.get('difficulty', 'simple')
    
    # Validate quiz state
    if not questions or current_index >= len(questions):
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "❌ QUIZ SESSION LOST\n\n"
            "Your quiz session expired or was reset.",
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Find the question
    question = await _get_question_by_id(questions, question_id)
    if not question:
        await callback.answer("Question not found", show_alert=True)
        return
    
    # Check if already checked
    answered_questions = data.get('answered_questions', {})
    question_key = str(question_id)
    if answered_questions.get(question_key, {}).get('checked', False):
        await callback.answer("Already checked!", show_alert=False)
        return
    
    # Calculate time taken
    start_time = data.get('question_start_time', time.time())
    time_taken = time.time() - start_time
    
    # Evaluate answer
    correct_option = question.get('correct_option', '')
    is_correct = (selected_option == correct_option)
    
    # Calculate points
    points = {'simple': 1, 'medium': 2, 'hard': 3}.get(difficulty, 1)
    points_earned = points if is_correct else 0
    new_score = score + points_earned
    
    # Get streak count
    streak = _feedback_service.get_current_streak(user_id)
    if is_correct:
        _feedback_service.get_correct_answer_feedback(user_id)
    else:
        _feedback_service.reset_streak(user_id)
    
    # Save attempt to database (async, don't wait for completion)
    async def save_attempt():
        """Save the quiz attempt to database."""
        try:
            async for session in get_db():
                attempt_repo = AttemptRepository(session)
                user_repo = UserRepository(session)
                
                await attempt_repo.create_attempt(
                    user_id=user_id,
                    question_id=question_id,
                    selected_option=selected_option,
                    is_correct=is_correct,
                    time_taken=int(time_taken),
                    quiz_session_id=quiz_session_id
                )
                
                await user_repo.update_user_progress(
                    user_id=user_id,
                    subject_id=subject_id,
                    chapter_id=chapter_id,
                    difficulty=difficulty,
                    is_correct=is_correct,
                    time_taken=int(time_taken)
                )
        except Exception as e:
            logger.error(f"Error saving attempt: {e}")
    
    # Start saving in background (fire and forget)
    asyncio.create_task(save_attempt())
    
    # Mark as checked
    answered_questions[question_key] = {
        'selected': selected_option,
        'locked': True,
        'checked': True,
        'is_correct': is_correct
    }
    
    # Update answers list
    answers = data.get('answers', [])
    answers.append({
        'question_id': question_id,
        'selected_option': selected_option,
        'is_correct': is_correct,
        'time_taken': time_taken,
        'points': points_earned
    })
    
    # Update state
    next_index = current_index + 1
    is_last_question = (next_index >= len(questions))
    
    await state.update_data({
        'answered_questions': answered_questions,
        'answers': answers,
        'score': new_score,
        'current_question_index': next_index,
        'question_start_time': time.time()
    })
    
    # Build result text with streak
    result_text = _build_result_text(
        is_correct=is_correct,
        selected_option=selected_option,
        correct_option=correct_option,
        explanation=question.get('explanation', ''),
        points_earned=points_earned,
        time_taken=time_taken,
        current_score=new_score,
        question_number=current_index + 1,
        total_questions=total_questions,
        streak=streak
    )
    
    # Get keyboard for result (empty for auto-progress)
    keyboard = QuizKeyboard.get_result_keyboard(
        question_number=current_index + 1,
        total_questions=total_questions,
        question_id=question_id,
        is_last=is_last_question,
        quiz_session_id=quiz_session_id
    )
    
    # Edit message with result
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        result_text,
        reply_markup=keyboard
    )
    
    await callback.answer()
    
    # Log the answer
    logger.info(
        f"[QUIZ] User {user_id} answered Q{current_index + 1}: "
        f"{'CORRECT' if is_correct else 'INCORRECT'} ({selected_option})"
    )
    
    # AUTO-PROGRESS: After delay, load next question
    if not is_last_question:
        await asyncio.sleep(AUTO_PROGRESS_DELAY)
        
        # Verify quiz is still active
        current_state = await state.get_state()
        if current_state != QuizStates.quiz_in_progress:
            return
        
        await _send_next_question(
            message=callback.message,
            state=state,
            questions=questions,
            next_index=next_index,
            score=new_score,
            plain_sender=plain_sender
        )
    else:
        # Quiz complete - show results
        await asyncio.sleep(AUTO_PROGRESS_DELAY)
        await _finish_quiz(callback.message, state, plain_sender)


async def _send_next_question(
    message: types.Message,
    state: FSMContext,
    questions: list,
    next_index: int,
    score: int,
    plain_sender: PlainTextMessageSender
) -> None:
    """
    Send the next question after auto-progress delay.
    
    This is called automatically after the user views the explanation.
    """
    total_questions = len(questions)
    question = questions[next_index]
    
    # Build question text
    question_text = _build_question_text(
        question_text=question['question_text'],
        option_a=question['option_a'],
        option_b=question['option_b'],
        option_c=question['option_c'],
        option_d=question['option_d'],
        question_number=next_index + 1,
        total_questions=total_questions,
        score=score
    )
    
    # Get fresh keyboard
    keyboard = QuizKeyboard.get_question_keyboard(
        question_number=next_index + 1,
        total_questions=total_questions,
        question_id=question['question_id']
    )
    
    await plain_sender.edit_message(
        message.chat.id,
        message.message_id,
        question_text,
        reply_markup=keyboard
    )


async def _finish_quiz(message: types.Message, state: FSMContext, plain_sender: PlainTextMessageSender) -> None:
    """Finish the quiz and show results."""
    from app.handlers.quiz import finish_quiz
    
    # Create a mock callback for finish_quiz
    class MockCallback:
        """
        Mock callback object to simulate CallbackQuery for finish_quiz.
        
        This is needed because _finish_quiz is called from a non-callback context
        (after auto-progress delay) but finish_quiz expects a callback object.
        """
        def __init__(self, msg, sender):
            self.message = msg
            self.bot = msg.bot
            
        async def answer(self, text: str = None, show_alert: bool = False):
            """
            Mock answer method to satisfy CallbackQuery interface.
            
            In production, this would answer the callback query to remove
            the loading state. For mock purposes, this is a no-op.
            """
            pass
    
    mock_callback = MockCallback(message, plain_sender)
    await finish_quiz(mock_callback, state, plain_sender)


# ============================================================================
# LEGACY HANDLERS (MODIFIED FOR NEW FLOW)
# ============================================================================

@router.callback_query(F.data.startswith("next_question_"))
async def show_next_question(callback: types.CallbackQuery, state: FSMContext):
    """
    Legacy handler - now delegates to new flow or shows message.
    
    This handler exists for backward compatibility but the new flow
    uses auto-progress instead of manual "Next Question" buttons.
    """
    plain_sender = _get_plain_sender(callback)
    
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    current_index = data.get('current_question_index', 0)
    questions = quiz_data.get('questions', [])
    score = data.get('score', 0)
    
    if current_index >= len(questions):
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "🎊 QUIZ COMPLETE\n\n"
            "You've answered all questions!",
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Send question using new flow
    await _send_next_question(
        message=callback.message,
        state=state,
        questions=questions,
        next_index=current_index,
        score=score,
        plain_sender=plain_sender
    )
    
    await state.update_data({'question_start_time': time.time()})
    await callback.answer()


@router.callback_query(F.data == "continue_quiz")
async def continue_quiz(callback: types.CallbackQuery, state: FSMContext):
    """
    Generic continue button - now shows next question.
    
    In the new learning flow, this is less commonly used since
    auto-progress handles most transitions.
    """
    plain_sender = _get_plain_sender(callback)
    
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    current_index = data.get('current_question_index', 0)
    questions = quiz_data.get('questions', [])
    score = data.get('score', 0)
    
    if current_index >= len(questions):
        # Quiz complete
        await _finish_quiz(callback.message, state, plain_sender)
        return
    
    # Check if question is locked (waiting for check)
    answered_questions = data.get('answered_questions', {})
    question = questions[current_index]
    
    if answered_questions.get(str(question['question_id']), {}).get('locked', False):
        # Question answered but not checked - show locked keyboard
        selected = answered_questions[str(question['question_id'])]['selected']
        keyboard = QuizKeyboard.get_locked_keyboard(
            question_number=current_index + 1,
            total_questions=len(questions),
            question_id=question['question_id'],
            selected_option=selected
        )
        
        question_text = _build_question_text(
            question_text=question['question_text'],
            option_a=question['option_a'],
            option_b=question['option_b'],
            option_c=question['option_c'],
            option_d=question['option_d'],
            question_number=current_index + 1,
            total_questions=len(questions),
            score=score
        )
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            question_text,
            reply_markup=keyboard
        )
    else:
        # Send fresh question
        await _send_next_question(
            message=callback.message,
            state=state,
            questions=questions,
            next_index=current_index,
            score=score,
            plain_sender=plain_sender
        )
    
    await state.update_data({'question_start_time': time.time()})
    await callback.answer()


@router.callback_query(F.data == "view_results")
async def view_quiz_results(callback: types.CallbackQuery, state: FSMContext):
    """View quiz results after completion - retrieves from database since state is cleared"""
    from app.utils.plain_sender import PlainTextMessageSender
    from app.repositories.attempt_repo import AttemptRepository
    from app.db.base import get_db
    
    plain_sender = PlainTextMessageSender(callback.bot)
    
    # Get the quiz session ID from state data (if still available)
    data = await state.get_data()
    quiz_session_id = data.get('quiz_session_id')
    
    if not quiz_session_id:
        # State was already cleared, show expired message
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "❌ SESSION EXPIRED\n\n"
            "Your quiz session has expired. Please start a new quiz to see results.",
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Get quiz details from database
    async for session in get_db():
        attempt_repo = AttemptRepository(session)
        quiz_details = await attempt_repo.get_quiz_session_details(quiz_session_id)
        
        if not quiz_details:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "❌ QUIZ NOT FOUND\n\n"
                "The quiz session could not be found. It may have expired.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
            await callback.answer()
            return
        
        # Build result message with beautiful formatting
        subject_name = quiz_details.get('subject_name', 'Unknown')
        chapter_name = quiz_details.get('chapter_name', 'Unknown')
        difficulty = quiz_details.get('difficulty', 'simple').capitalize()
        correct_answers = quiz_details.get('correct_answers', 0)
        total_questions = quiz_details.get('total_questions', 0)
        accuracy = quiz_details.get('accuracy', 0)
        total_time = quiz_details.get('total_time', 0)
        
        # Determine performance message
        if accuracy >= 80:
            performance = "🎉 EXCELLENT!"
            emoji = "🏆"
        elif accuracy >= 60:
            performance = "👍 GOOD JOB!"
            emoji = "⭐"
        elif accuracy >= 40:
            performance = "💪 KEEP LEARNING!"
            emoji = "🌱"
        else:
            performance = "🌟 KEEP PRACTICING!"
            emoji = "💪"
        
        # Get beautiful result header
        header = get_beautiful_result_header(accuracy)
        
        result_message = (
            f"{header['emoji']} *{header['title']}*\n\n"
            f"✨ {header['message']}\n\n"
            f"📚 *{subject_name}*\n"
            f"📖 *{chapter_name}*\n"
            f"{get_difficulty_emoji(difficulty.lower())} *{difficulty}*\n\n"
            f"─" * 25 + "\n\n"
            f"📊 *Quiz Results:*\n\n"
            f"  🏆 *Score:* {correct_answers} points\n"
            f"  ✅ *Correct:* {correct_answers}/{total_questions}\n"
            f"  📈 *Accuracy:* {accuracy:.1f}%\n"
            f"  ⏱️ *Time:* {total_time:.0f}s\n\n"
            f"─" * 25 + "\n\n"
            f"{emoji} *{performance}*\n\n"
            "Click below to review your answers!"
        )
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            result_message,
            reply_markup=QuizKeyboard.get_quiz_results_keyboard(quiz_session_id)
        )
    
    await state.clear()
    await callback.answer()


# ============================================================================
# LEGACY HANDLERS (UNCHANGED)
# ============================================================================

@router.callback_query(F.data.startswith("retry_"))
async def retry_same_quiz(callback: types.CallbackQuery, state: FSMContext,
                          has_active_subscription: bool = False):
    """Retry the same quiz with same settings."""
    plain_sender = _get_plain_sender(callback)
    
    # Parse: retry_subjectId_chapterId_difficulty
    parts = callback.data.split("_")
    if len(parts) != 4:
        await callback.answer("Invalid retry request", show_alert=True)
        return
    
    subject_id = int(parts[1])
    chapter_id = int(parts[2])
    difficulty = parts[3]
    
    await state.clear()
    await state.set_state(QuizStates.selecting_difficulty)
    await state.update_data({
        'subject_id': subject_id,
        'chapter_id': chapter_id,
        'user_id': callback.from_user.id
    })
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        subject = await question_repo.get_subject(subject_id)
        chapter = await question_repo.get_chapter(chapter_id)
        
        subject_name = subject.subject_name if subject else f"Subject {subject_id}"
        chapter_name = chapter.chapter_name if chapter else f"Chapter {chapter_id}"
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "🔄 RETRYING QUIZ\n\n"
            f"📚 Subject: {subject_name}\n"
            f"📖 Chapter: {chapter_name}\n"
            f"⚡ Difficulty: {difficulty.capitalize()}\n\n"
            f"Starting new quiz..."
        )
        
        from aiogram.types import CallbackQuery as AiogramCallbackQuery
        mock_callback = AiogramCallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            chat_instance=callback.chat_instance,
            message=callback.message,
            data=f"difficulty_{difficulty}"
        )
        
        from app.handlers.quiz import select_difficulty
        await select_difficulty(mock_callback, state, has_active_subscription)
    
    await callback.answer()


@router.callback_query(F.data == "different_chapter")
async def choose_different_chapter(callback: types.CallbackQuery, state: FSMContext,
                                   has_active_subscription: bool = False):
    """Choose a different chapter for new quiz"""
    plain_sender = _get_plain_sender(callback)
    
    await state.clear()
    
    from app.handlers.quiz import start_quiz_flow
    await start_quiz_flow(callback.message, state, callback.from_user.id)
    
    await callback.answer()


@router.callback_query(F.data.startswith("higher_difficulty_"))
async def try_higher_difficulty(callback: types.CallbackQuery, state: FSMContext,
                               has_active_subscription: bool = False):
    """Try same quiz with higher difficulty."""
    plain_sender = _get_plain_sender(callback)
    
    # Parse: higher_difficulty_subjectId_chapterId_currentDifficulty
    parts = callback.data.split("_")
    if len(parts) != 4:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    current_difficulty = parts[1]
    subject_id = int(parts[2])
    chapter_id = int(parts[3])
    
    difficulty_order = ['simple', 'medium', 'hard']
    current_index = difficulty_order.index(current_difficulty)
    
    if current_index >= len(difficulty_order) - 1:
        await callback.answer("Already at highest difficulty!", show_alert=True)
        return
    
    next_difficulty = difficulty_order[current_index + 1]
    
    if next_difficulty in ['medium', 'hard'] and not has_active_subscription:
        await callback.answer(
            "🔒 Premium Feature!\n\n"
            f"{next_difficulty.capitalize()} level requires subscription.\n"
            "Use /payment to subscribe!",
            show_alert=True
        )
        return
    
    await state.clear()
    await state.set_state(QuizStates.selecting_difficulty)
    await state.update_data({
        'subject_id': subject_id,
        'chapter_id': chapter_id,
        'user_id': callback.from_user.id
    })
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        subject = await question_repo.get_subject(subject_id)
        chapter = await question_repo.get_chapter(chapter_id)
        
        subject_name = subject.subject_name if subject else f"Subject {subject_id}"
        chapter_name = chapter.chapter_name if chapter else f"Chapter {chapter_id}"
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "⚡ HIGHER DIFFICULTY\n\n"
            f"📚 Subject: {subject_name}\n"
            f"📖 Chapter: {chapter_name}\n"
            f"🚀 New Difficulty: {next_difficulty.capitalize()}\n\n"
            f"Starting quiz..."
        )
        
        from aiogram.types import CallbackQuery as AiogramCallbackQuery
        mock_callback = AiogramCallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            chat_instance=callback.chat_instance,
            message=callback.message,
            data=f"difficulty_{next_difficulty}"
        )
        
        from app.handlers.quiz import select_difficulty
        await select_difficulty(mock_callback, state, has_active_subscription)
    
    await callback.answer()


@router.callback_query(F.data.startswith("noop"))
async def handle_noop(callback: types.CallbackQuery):
    """
    Handle disabled button clicks gracefully.
    Provides feedback that action is not allowed.
    """
    await callback.answer("Please check your answer first!", show_alert=False)

