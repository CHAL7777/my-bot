from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from aiogram.types import Message, CallbackQuery
from typing import Dict, Any, Optional, List
import time
import uuid
import asyncio
from sqlalchemy import text

from app.keyboards.menu import MainMenuKeyboard
from app.keyboards.quiz import QuizKeyboard
from app.services.quiz_service import QuizService
from app.services.feedback_service import FeedbackService
from app.db.base import get_db
from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.user_repo import UserRepository
from app.utils.constants import EMOJIS
from app.utils.plain_sender import PlainTextMessageSender
import logging

logger = logging.getLogger(__name__)

router = Router()

# Initialize feedback service for enhanced quiz experience
_feedback_service = FeedbackService()

# Initialize PlainTextMessageSender for plain text message sending
_plain_sender = None

def get_plain_sender():
    """Get or create PlainTextMessageSender instance"""
    global _plain_sender
    if _plain_sender is None:
        # Bot will be set when handlers are registered with the router
        pass
    return _plain_sender


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_chapter_selection_message(subject_name: str, chapter_list: list) -> str:
    """
    Build enhanced chapter selection message with beautiful formatting.
    
    Args:
        subject_name: Name of the subject
        chapter_list: List of chapter dicts with question counts
        
    Returns:
        Formatted plain text message string with beautiful styling
    """
    lines = []
    
    # Beautiful header with subject emoji and formatting
    lines.append(f"📚 *{subject_name}* - Chapter Selection")
    lines.append("")
    lines.append("✨ Choose a chapter to start your quiz journey!")
    lines.append("")
    
    # Decorative divider
    lines.append("─" * 30)
    lines.append("")
    
    # Chapter details with question counts and difficulty breakdown
    for i, chapter_data in enumerate(chapter_list, 1):
        chapter_name = chapter_data['chapter_name']
        total = chapter_data['total_count']
        simple = chapter_data.get('simple_count', 0)
        medium = chapter_data.get('medium_count', 0)
        hard = chapter_data.get('hard_count', 0)
        
        lines.append(f"📖 *{chapter_name}*")
        lines.append(f"   📊 *{total}* questions available")
        lines.append(f"   🟢 {simple}  🟡 {medium}  🔴 {hard}")
        lines.append("")
    
    # Decorative divider
    lines.append("─" * 30)
    lines.append("")
    
    # Tip section with sparkle emoji
    lines.append("💡 *Tip:* Start with chapters you want to improve in!")
    lines.append("")
    
    # Footer with back button indicator
    lines.append("◀️ Back to Subjects")
    
    return "\n".join(lines)


class QuizStates(StatesGroup):
    selecting_subject = State()
    selecting_chapter = State()
    selecting_difficulty = State()
    quiz_in_progress = State()
    waiting_for_answer = State()


# ============================================================================
# QUIZ ACCESS CONTROL - SINGLE SOURCE OF TRUTH
# ============================================================================

ACCESS_DENIED_MESSAGE = (
    "ACCESS DENIED\n\n"
    "Your account is not approved yet.\n"
    "Please complete payment and wait for admin approval."
)


async def check_quiz_access(
    user_id: int,
) -> Dict[str, Any]:
    """
    Check if user can access quiz using the STRICT single source of truth.
    
    Uses RAW SQL to bypass any ORM caching issues.
    
    Returns:
        dict with:
        - allowed: bool (True ONLY if user.approved = 1)
        - user_id: int
    """
    try:
        # Use async for with get_db() - creates fresh session each time
        async for db_session in get_db():
            # Use RAW SQL to get fresh data
            query = text(
                "SELECT user_id, approved FROM users WHERE user_id = :user_id"
            )
            result = await db_session.execute(query, {"user_id": user_id})
            row = result.fetchone()
            
            if not row:
                return {'allowed': False, 'user_id': user_id}
            
            approved = row[1]
            return {'allowed': approved == True, 'user_id': user_id}
    except Exception as e:
        logger.error(f"Error checking quiz access for user {user_id}: {e}")
        return {'allowed': False, 'user_id': user_id}


async def send_access_denied(message, plain_sender: PlainTextMessageSender, use_inline: bool):
    """Send access denied message"""
    if use_inline:
        try:
            await plain_sender.edit_message(
                message.chat.id,
                message.message_id,
                ACCESS_DENIED_MESSAGE,
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
        except Exception:
            await plain_sender.send_message(
                message.chat.id,
                ACCESS_DENIED_MESSAGE,
                reply_markup=MainMenuKeyboard.get_main_menu()
            )
    else:
        await plain_sender.send_message(
            message.chat.id,
            ACCESS_DENIED_MESSAGE,
            reply_markup=MainMenuKeyboard.get_main_menu()
        )


# ============================================================================
# REFACTORED HANDLERS
# ============================================================================

@router.message(Command("quiz"))
async def command_quiz(message: types.Message, state: FSMContext,
                      data: Dict[str, Any] = None):
    """
    Handle /quiz command with STRICT access control.
    
    Access is granted ONLY if user.approved = 1
    """
    plain_sender = PlainTextMessageSender(message.bot)
    
    # Check if user is already in a quiz
    current_state = await state.get_state()
    if current_state == QuizStates.quiz_in_progress:
        await plain_sender.send_message(
            message.chat.id,
            "You already have a quiz in progress!\n"
            "Please finish or cancel your current quiz first.",
            reply_markup=MainMenuKeyboard.get_main_menu()
        )
        return
    
    user_id = message.from_user.id
    
    # STRICT access check - ONLY approved = 1 grants access
    # Use data from middleware first (should be fresh)
    access_result = data.get('access_result') if data else None
    
    if access_result and access_result.get('allowed'):
        # User is approved - proceed with quiz
        await start_quiz_flow(message, state, user_id)
    else:
        # Verify with fresh check
        access_check = await check_quiz_access(user_id)
        if not access_check['allowed']:
            await send_access_denied(message, plain_sender, False)
        else:
            await start_quiz_flow(message, state, user_id)


async def start_quiz_flow(
    update: types.Update, 
    state: FSMContext,
    user_id: int
):
    """
    Start the quiz selection flow.
    
    User must already be verified as approved before calling this.
    
    Args:
        update: The update object (Message or CallbackQuery)
        state: FSMContext for state management
        user_id: The user's Telegram ID
    """
    is_callback = isinstance(update, CallbackQuery)
    message = update.message if is_callback else update
    
    # Create plain_sender internally (auto-created from update's bot)
    plain_sender = PlainTextMessageSender(message.bot)
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        # Get available subjects
        subjects = await question_repo.get_subjects()
        
        if not subjects:
            await send_access_denied(message, plain_sender, is_callback)
            return
        
        # Format subjects for display
        subject_list = [
            {'subject_id': s.subject_id, 'subject_name': s.subject_name}
            for s in subjects
        ]
        
        await state.set_state(QuizStates.selecting_subject)
        await state.update_data({
            'subjects': subject_list,
            'user_id': user_id
        })
        
        await _send_quiz_subjects(message, subject_list, is_callback, plain_sender)


async def _send_quiz_subjects(message, subjects: list, use_inline_keyboard: bool, plain_sender: PlainTextMessageSender):
    """Send subject selection message"""
    subject_text = "Select a Subject\n\nChoose the subject you want to practice:"
    
    if use_inline_keyboard:
        await plain_sender.edit_message(
            message.chat.id,
            message.message_id,
            subject_text,
            reply_markup=MainMenuKeyboard.get_subjects_keyboard(subjects)
        )
    else:
        await plain_sender.send_message(
            message.chat.id,
            subject_text,
            reply_markup=MainMenuKeyboard.get_subjects_keyboard(subjects)
        )


@router.callback_query(F.data.startswith("subject_"), QuizStates.selecting_subject)
async def select_subject(callback: types.CallbackQuery, state: FSMContext,
                        data: Dict[str, Any] = None):
    """Handle subject selection"""
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    # Verify access from middleware data first
    access_result = data.get('access_result') if data else None
    access_granted = access_result.get('allowed') if access_result else None
    
    if access_granted is None:
        # Verify with fresh check
        access_check = await check_quiz_access(user_id)
        access_granted = access_check['allowed']
    
    if not access_granted:
        await send_access_denied(callback.message, plain_sender, True)
        await callback.answer()
        return
    
    subject_id = int(callback.data.split("_")[1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        chapters = await question_repo.get_chapters(subject_id)
        
        if not chapters:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "No chapters available for this subject.\n"
                "Please select another subject or contact admin.",
                reply_markup=MainMenuKeyboard.get_subjects_keyboard([])
            )
            await callback.answer()
            return
        
        subject = await question_repo.get_subject(subject_id)
        subject_name = subject.subject_name if subject else f"Subject {subject_id}"
        
        # OPTIMIZED: Get all chapter counts in a single batch query
        chapter_ids = [c.chapter_id for c in chapters]
        chapter_counts = await question_repo.get_chapter_counts_batch(subject_id, chapter_ids)
        
        # Build chapter list with question counts from batch result
        chapter_list = []
        for chapter in chapters:
            counts = chapter_counts.get(chapter.chapter_id, {'total': 0, 'simple': 0, 'medium': 0, 'hard': 0})
            chapter_list.append({
                'chapter_id': chapter.chapter_id,
                'chapter_name': chapter.chapter_name,
                'total_count': counts['total'],
                'simple_count': counts['simple'],
                'medium_count': counts['medium'],
                'hard_count': counts['hard']
            })
        
        await state.set_state(QuizStates.selecting_chapter)
        await state.update_data({
            'subject_id': subject_id,
            'subject_name': subject_name,
            'chapters': chapter_list
        })
        
        # Use helper function to build enhanced chapter selection message
        enhanced_message = _build_chapter_selection_message(subject_name, chapter_list)
        
        # Create simple chapter list for keyboard (without counts)
        keyboard_chapters = [
            {'chapter_id': c['chapter_id'], 'chapter_name': c['chapter_name']}
            for c in chapter_list
        ]
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            enhanced_message,
            reply_markup=MainMenuKeyboard.get_chapters_keyboard(keyboard_chapters)
        )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_subjects", QuizStates.selecting_chapter)
async def back_to_subjects(callback: types.CallbackQuery, state: FSMContext):
    """Go back to subject selection"""
    plain_sender = PlainTextMessageSender(callback.bot)
    data = await state.get_data()
    subjects = data.get('subjects', [])
    
    await state.set_state(QuizStates.selecting_subject)
    
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Select a Subject\n\nChoose the subject you want to practice:",
        reply_markup=MainMenuKeyboard.get_subjects_keyboard(subjects)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("chapter_"), QuizStates.selecting_chapter)
async def select_chapter(callback: types.CallbackQuery, state: FSMContext,
                        data: Dict[str, Any] = None):
    """Handle chapter selection"""
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    # Verify access
    access_result = data.get('access_result') if data else None
    access_granted = access_result.get('allowed') if access_result else None
    
    if access_granted is None:
        access_check = await check_quiz_access(user_id)
        access_granted = access_check['allowed']
    
    if not access_granted:
        await send_access_denied(callback.message, plain_sender, True)
        await callback.answer()
        return
    
    chapter_id = int(callback.data.split("_")[1])
    
    data = await state.get_data()
    subject_id = data.get('subject_id')
    subject_name = data.get('subject_name', '')
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        chapter = await question_repo.get_chapter(chapter_id)
        chapter_name = chapter.chapter_name if chapter else f"Chapter {chapter_id}"
        
        await state.set_state(QuizStates.selecting_difficulty)
        await state.update_data({
            'chapter_id': chapter_id,
            'chapter_name': chapter_name
        })
        
        simple_count = await question_repo.get_question_count(
            subject_id=subject_id,
            chapter_id=chapter_id,
            difficulty='simple'
        )
        
        medium_count = await question_repo.get_question_count(
            subject_id=subject_id,
            chapter_id=chapter_id,
            difficulty='medium'
        )
        
        hard_count = await question_repo.get_question_count(
            subject_id=subject_id,
            chapter_id=chapter_id,
            difficulty='hard'
        )
        
        lines = [
            "Select Difficulty",
            "",
            f"Subject: {subject_name}",
            f"Chapter: {chapter_name}",
            "",
            "Available questions:",
            f"Simple: {simple_count} questions",
            f"Medium: {medium_count} questions",
            f"Hard: {hard_count} questions",
            "",
            "Choose difficulty level:"
        ]
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=MainMenuKeyboard.get_difficulty_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_chapters", QuizStates.selecting_difficulty)
async def back_to_chapters(callback: types.CallbackQuery, state: FSMContext):
    """Go back to chapter selection with enhanced message and question counts"""
    plain_sender = PlainTextMessageSender(callback.bot)
    data = await state.get_data()
    subject_id = data.get('subject_id')
    subject_name = data.get('subject_name', '')
    
    if not subject_id:
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "Session expired. Please start a new quiz.",
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
        await callback.answer()
        return
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        # Fetch fresh chapters from database
        chapters = await question_repo.get_chapters(subject_id)
        
        if not chapters:
            lines = [
                f"{subject_name} - Chapter Selection",
                "",
                "No chapters available for this subject.",
                "Please go back and select another subject."
            ]
            
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=MainMenuKeyboard.get_subjects_keyboard([])
            )
            await callback.answer()
            return
        
        # OPTIMIZED: Get all chapter counts in a single batch query
        chapter_ids = [c.chapter_id for c in chapters]
        chapter_counts = await question_repo.get_chapter_counts_batch(subject_id, chapter_ids)
        
        # Build chapter list with question counts from batch result
        chapter_list = []
        for chapter in chapters:
            counts = chapter_counts.get(chapter.chapter_id, {'total': 0, 'simple': 0, 'medium': 0, 'hard': 0})
            chapter_list.append({
                'chapter_id': chapter.chapter_id,
                'chapter_name': chapter.chapter_name,
                'total_count': counts['total'],
                'simple_count': counts['simple'],
                'medium_count': counts['medium'],
                'hard_count': counts['hard']
            })
        
        # Update state with fresh chapter data
        await state.set_state(QuizStates.selecting_chapter)
        await state.update_data({
            'chapters': chapter_list
        })
        
        # Use helper function to build enhanced chapter selection message
        enhanced_message = _build_chapter_selection_message(subject_name, chapter_list)
        
        # Create simple chapter list for keyboard (without counts)
        keyboard_chapters = [
            {'chapter_id': c['chapter_id'], 'chapter_name': c['chapter_name']}
            for c in chapter_list
        ]
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            enhanced_message,
            reply_markup=MainMenuKeyboard.get_chapters_keyboard(keyboard_chapters)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("difficulty_"), QuizStates.selecting_difficulty)
async def select_difficulty(callback: types.CallbackQuery, state: FSMContext,
                           data: Dict[str, Any] = None):
    """
    Handle difficulty selection and start quiz.
    
    CRITICAL: All difficulty levels require approved = 1
    """
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    # Verify access - ALL users must be approved
    access_result = data.get('access_result') if data else None
    access_granted = access_result.get('allowed') if access_result else None
    
    if access_granted is None:
        access_check = await check_quiz_access(user_id)
        access_granted = access_check['allowed']
    
    if not access_granted:
        await send_access_denied(callback.message, plain_sender, True)
        await callback.answer()
        return
    
    difficulty = callback.data.split("_")[1]
    
    data = await state.get_data()
    subject_id = data.get('subject_id')
    subject_name = data.get('subject_name', '')
    chapter_id = data.get('chapter_id')
    chapter_name = data.get('chapter_name', '')
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        try:
            quiz_data = await quiz_service.start_quiz(
                user_id=user_id,
                subject_id=subject_id,
                chapter_id=chapter_id,
                difficulty=difficulty
            )
            
            questions = quiz_data['questions']
            if not questions:
                await plain_sender.edit_message(
                    callback.message.chat.id,
                    callback.message.message_id,
                    "No questions available for this selection.\n"
                    "Please choose a different chapter or difficulty.",
                    reply_markup=MainMenuKeyboard.get_main_menu_inline()
                )
                await callback.answer()
                return
            
            first_question = questions[0]
            quiz_session_id = quiz_data['quiz_session_id']
            
            await state.set_state(QuizStates.quiz_in_progress)
            await state.update_data({
                'quiz_data': quiz_data,
                'current_question_index': 0,
                'quiz_session_id': quiz_session_id,
                'start_time': time.time(),
                'score': 0,
                'answers': [],
                'answered_questions': {},  # Track answered/locked questions for learning flow
                'subject_name': subject_name,
                'chapter_name': chapter_name,
                'difficulty': difficulty
            })
            
            # Get quiz start message from feedback service
            start_message = _feedback_service.get_quiz_start_message()
            
            # Get difficulty display
            difficulty_display = difficulty.capitalize()
            
            # Send first question
            lines = [
                "QUIZ STARTED!",
                "",
                start_message['message'],
                "",
                "-" * 25,
                "",
                f"Subject: {subject_name}",
                f"Chapter: {chapter_name}",
                f"Difficulty: {difficulty_display}",
                f"Questions: {len(questions)}",
                "",
                "-" * 25,
                "",
                f"Question 1/{len(questions)} | Score: 0",
                "",
                first_question['question_text'],
                "",
                f"A. {first_question['option_a']}",
                f"B. {first_question['option_b']}",
                f"C. {first_question['option_c']}",
                f"D. {first_question['option_d']}"
            ]
            
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=QuizKeyboard.get_question_keyboard(
                    question_number=1,
                    total_questions=len(questions),
                    question_id=first_question['question_id']
                )
            )
            
        except Exception as e:
            error_msg = str(e)
            if "Daily quiz limit reached" in error_msg:
                await plain_sender.edit_message(
                    callback.message.chat.id,
                    callback.message.message_id,
                    "Daily Limit Reached!\n\n"
                    "You've reached your daily quiz limit.\n"
                    "Please try again tomorrow or upgrade your subscription.",
                    reply_markup=MainMenuKeyboard.get_main_menu_inline()
                )
            else:
                await plain_sender.edit_message(
                    callback.message.chat.id,
                    callback.message.message_id,
                    f"Error starting quiz: {error_msg}\n\n"
                    "Please try again or contact support.",
                    reply_markup=MainMenuKeyboard.get_main_menu_inline()
                )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_quiz", QuizStates.quiz_in_progress)
async def cancel_quiz_confirmation(callback: types.CallbackQuery):
    """Show confirmation for quiz cancellation"""
    plain_sender = PlainTextMessageSender(callback.bot)
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Cancel Quiz?\n\n"
        "Are you sure you want to cancel this quiz?\n"
        "Your progress will be lost.",
        reply_markup=QuizKeyboard.get_quiz_cancel_confirmation()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_cancel_quiz")
async def confirm_cancel_quiz(callback: types.CallbackQuery, state: FSMContext):
    """Confirm quiz cancellation"""
    plain_sender = PlainTextMessageSender(callback.bot)
    await state.clear()
    
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Quiz cancelled.\n\n"
        "Your progress has been discarded.",
        reply_markup=MainMenuKeyboard.get_main_menu_inline()
    )
    await callback.answer()


@router.callback_query(F.data == "continue_quiz", QuizStates.quiz_in_progress)
async def continue_quiz(callback: types.CallbackQuery, state: FSMContext):
    """Continue to next question after answer feedback"""
    plain_sender = PlainTextMessageSender(callback.bot)
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    current_index = data.get('current_question_index', 0)
    questions = quiz_data.get('questions', [])
    score = data.get('score', 0)
    
    if current_index >= len(questions):
        await finish_quiz(callback, state, plain_sender)
        return
    
    question = questions[current_index]
    total_questions = len(questions)

    lines = [
        f"Question {current_index + 1}/{total_questions} | Score: {score}",
        "",
        question['question_text'],
        "",
        f"A. {question['option_a']}",
        f"B. {question['option_b']}",
        f"C. {question['option_c']}",
        f"D. {question['option_d']}"
    ]
    
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
        reply_markup=QuizKeyboard.get_question_keyboard(
            question_number=current_index + 1,
            total_questions=total_questions,
            question_id=question['question_id']
        )
    )
    await callback.answer()


async def finish_quiz(callback: types.CallbackQuery, state: FSMContext, plain_sender: PlainTextMessageSender):
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
    await callback.answer()




# ============================================================================
# QUESTION REVIEW FUNCTION
# ============================================================================

async def _display_question_for_review(
    callback: types.CallbackQuery,
    plain_sender: PlainTextMessageSender,
    quiz_details: Dict[str, Any],
    question_data: Dict[str, Any],
    current_index: int
):
    """
    Display a question for review with user's answer, correct answer, and explanation.
    
    Args:
        callback: The callback query object
        plain_sender: PlainTextMessageSender instance
        quiz_details: Dictionary containing quiz session details
        question_data: Dictionary containing question data with user answer
        current_index: Current question index in the review
    """
    quiz_session_id = quiz_details.get('quiz_session_id', '')
    total_questions = quiz_details.get('total_questions', 0)
    
    # Extract question data
    question_text = question_data.get('question_text', '')
    options = question_data.get('options', {})
    correct_option = question_data.get('correct_option', '')
    user_selected = question_data.get('user_selected', '')
    is_correct = question_data.get('is_correct', False)
    time_taken = question_data.get('time_taken', 0)
    explanation = question_data.get('explanation', '')
    
    # Build option display with icons
    option_icons = {'A': '○', 'B': '○', 'C': '○', 'D': '○'}
    if is_correct:
        option_icons[correct_option] = '✅'
    else:
        option_icons[correct_option] = '✅'
        if user_selected:
            option_icons[user_selected] = '❌'
    
    option_lines = []
    for opt in ['A', 'B', 'C', 'D']:
        opt_text = options.get(opt, '')
        icon = option_icons[opt]
        user_marker = ' 👤' if opt == user_selected else ''
        option_lines.append(f"{icon} {opt}. {opt_text}{user_marker}")
    
    # Build message
    emoji = "✅" if is_correct else "❌"
    subject_name = quiz_details.get('subject_name', 'Unknown')
    chapter_name = quiz_details.get('chapter_name', 'Unknown')
    difficulty = quiz_details.get('difficulty', 'simple').capitalize()
    
    lines = [
        "📋 Quiz Details",
        "─" * 20,
        "",
        f"📚 {subject_name}",
        f"📖 Chapter: {chapter_name}",
        f"📊 Difficulty: {difficulty}",
        "─" * 20,
        "",
        f"Question {current_index + 1}/{total_questions}",
        f"{emoji} | ⏱️ {time_taken}s",
        "",
        question_text,
        "",
    ] + option_lines
    
    if explanation:
        lines.extend([
            "",
            "─" * 20,
            "",
            "📘 Explanation:",
            explanation
        ])
    
    message_text = "\n".join(lines)
    
    # Get keyboard for navigation
    keyboard = QuizKeyboard.get_question_review_keyboard(
        quiz_session_id=quiz_session_id,
        current_index=current_index,
        total=total_questions
    )
    
    try:
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            message_text,
            reply_markup=keyboard
        )
    except Exception as e:
        if "Message is too long" in str(e):
            # Truncate if too long
            if explanation and len(message_text) > 4000:
                truncated_explanation = explanation[:200] + "..."
                message_text = message_text.replace(
                    f"📘 Explanation:\n{explanation}",
                    f"📘 Explanation:\n{truncated_explanation}"
                )
                await plain_sender.edit_message(
                    callback.message.chat.id,
                    callback.message.message_id,
                    message_text,
                    reply_markup=keyboard
                )
        else:
            raise

@router.callback_query(F.data.startswith("quiz_details_"))
async def show_quiz_details(callback: types.CallbackQuery, state: FSMContext):
    """Show detailed quiz results with question review."""
    plain_sender = PlainTextMessageSender(callback.bot)
    quiz_session_id = callback.data.split("_")[2]
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        quiz_details = await quiz_service.get_quiz_session_details(quiz_session_id)
        
        if not quiz_details:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Quiz session not found.\n\n"
                "The quiz details may have expired or don't exist.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
            await callback.answer()
            return
        
        questions = quiz_details.get('questions', [])
        if not questions:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "No questions found for this quiz session.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
            await callback.answer()
            return
        
        first_question = questions[0]
        await _display_question_for_review(
            callback=callback,
            plain_sender=plain_sender,
            quiz_details=quiz_details,
            question_data=first_question,
            current_index=0
        )
    
    await callback.answer()




@router.callback_query(F.data.startswith("review_"))
async def review_question(callback: types.CallbackQuery, state: FSMContext):
    """Handle question review navigation."""
    plain_sender = PlainTextMessageSender(callback.bot)
    
    # Parse callback data in format: review_{quiz_session_id}_{question_index}
    callback_data = callback.data
    
    # Remove "review_" prefix and split
    after_prefix = callback_data[7:]  # Remove "review_" (7 chars)
    
    # Find the last underscore to split quiz_session_id and question_index
    last_underscore = after_prefix.rfind("_")
    if last_underscore == -1:
        await callback.answer("Invalid callback data", show_alert=True)
        return
    
    quiz_session_id = after_prefix[:last_underscore]
    question_index_str = after_prefix[last_underscore + 1:]
    
    try:
        question_index = int(question_index_str)
    except ValueError:
        await callback.answer("Invalid question index", show_alert=True)
        return
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        quiz_details = await quiz_service.get_quiz_session_details(quiz_session_id)
        
        if not quiz_details:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Quiz session not found.\n\n"
                "The quiz details may have expired or don't exist.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
            await callback.answer("Quiz session not found", show_alert=True)
            return
        
        questions = quiz_details.get('questions', [])
        if question_index < 0 or question_index >= len(questions):
            await callback.answer("Invalid question index", show_alert=True)
            return
        
        question_data = questions[question_index]
        await _display_question_for_review(
            callback=callback,
            plain_sender=plain_sender,
            quiz_details=quiz_details,
            question_data=question_data,
            current_index=question_index
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("quiz_results_"))
async def back_to_quiz_results(callback: types.CallbackQuery, state: FSMContext):
    """Return to the quiz results summary view."""
    plain_sender = PlainTextMessageSender(callback.bot)
    quiz_session_id = callback.data.split("_")[2]
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        quiz_details = await quiz_service.get_quiz_session_details(quiz_session_id)
        
        if not quiz_details:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Quiz session not found.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
            await callback.answer()
            return
        
        accuracy = quiz_details['accuracy']
        if accuracy >= 80:
            performance = "Excellent!"
        elif accuracy >= 60:
            performance = "Good job!"
        else:
            performance = "Keep practicing!"
        
        score = quiz_details['correct_answers']
        max_score = quiz_details['total_questions']
        
        lines = [
            "Quiz Results",
            "-" * 25,
            "",
            f"Subject: {quiz_details['subject_name']}",
            f"Chapter: {quiz_details['chapter_name']}",
            f"Difficulty: {quiz_details['difficulty'].capitalize()}",
            "",
            "-" * 25,
            "Results:",
            f"Score: {score}/{max_score}",
            f"Accuracy: {accuracy}%",
            f"Correct: {quiz_details['correct_answers']}",
            f"Wrong: {quiz_details['incorrect_answers']}",
            f"Time: {quiz_details['total_time']}s ({quiz_details['average_time']}s avg)",
            "",
            "-" * 25,
            f"Performance: {performance}"
        ]
        
        message_text = "\n".join(lines)
        
        keyboard = QuizKeyboard.get_quiz_results_keyboard(quiz_session_id)
        
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            message_text,
            reply_markup=keyboard
        )
    
    await callback.answer()


@router.callback_query(F.data == "try_again")
async def try_again_quiz(callback: types.CallbackQuery, state: FSMContext,
                         data: Dict[str, Any] = None):
    """Try the same quiz again"""
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    # Verify access before retrying
    access_result = data.get('access_result') if data else None
    access_granted = access_result.get('allowed') if access_result else None
    
    if access_granted is None:
        access_check = await check_quiz_access(user_id)
        access_granted = access_check['allowed']
    
    if not access_granted:
        await send_access_denied(callback.message, plain_sender, True)
        await callback.answer()
        return
    
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Starting new quiz...",
        reply_markup=MainMenuKeyboard.get_main_menu_inline()
    )
    
    await state.clear()
    await start_quiz_flow(callback, state, user_id)
    await callback.answer()


@router.callback_query(F.data == "weak_areas")
async def show_weak_areas(callback: types.CallbackQuery, state: FSMContext):
    """Show user's weak areas based on performance history."""
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        weak_chapters = await question_repo.get_weak_chapters(user_id, limit=3)
        
        if weak_chapters:
            lines = [
                "Your Weak Areas",
                "",
                "Based on your quiz performance, here are areas to improve:",
                ""
            ]
            
            for i, chapter in enumerate(weak_chapters, 1):
                subject_name = chapter.get('subject_name', 'Unknown')
                chapter_name = chapter.get('chapter_name', 'Unknown')
                accuracy = chapter.get('accuracy', 0)
                difficulty = chapter.get('difficulty', 'simple')
                
                lines.append(f"{i}. {subject_name} - {chapter_name}")
                lines.append(f"   {difficulty.capitalize()} | Accuracy: {accuracy}%")
                lines.append("")
            
            lines.append("Click below to start practicing:")
            
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=QuizKeyboard.get_weak_areas_keyboard(weak_chapters)
            )
        else:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Weak Areas Analysis\n\n"
                "Great news! You don't have any weak areas yet.\n\n"
                "Keep taking quizzes to discover areas where you can improve!\n\n"
                "Try different subjects and difficulty levels to challenge yourself.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(F.data == "get_recommendations")
async def get_recommendations(callback: types.CallbackQuery, state: FSMContext):
    """Get personalized recommendations based on user performance"""
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        # Get recommended quiz
        recommendation = await quiz_service.get_recommended_quiz(user_id)
        
        if recommendation:
            subject_name = recommendation.get('subject_name', 'Unknown')
            chapter_name = recommendation.get('chapter_name', 'Unknown')
            difficulty = recommendation.get('difficulty', 'simple')
            reason = recommendation.get('reason', '')
            
            lines = [
                "Personalized Recommendation",
                "",
                reason,
                "",
                f"Subject: {subject_name}",
                f"Chapter: {chapter_name}",
                f"Difficulty: {difficulty.capitalize()}",
                "",
                "Start this quiz to improve your skills!"
            ]
            
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=QuizKeyboard.get_start_recommended_keyboard(
                    subject_id=recommendation['subject_id'],
                    chapter_id=recommendation['chapter_id'],
                    difficulty=recommendation['difficulty']
                )
            )
        else:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Recommendations\n\n"
                "Keep taking quizzes to get personalized recommendations!\n\n"
                "Try different chapters and difficulty levels to discover your strengths and weaknesses.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("start_recommended_"))
async def start_recommended_quiz(callback: types.CallbackQuery, state: FSMContext,
                                  data: Dict[str, Any] = None):
    """Start the recommended quiz"""
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    # Parse the callback data: start_recommended_subjectId_chapterId_difficulty
    parts = callback.data.split("_")
    if len(parts) != 5:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    subject_id = int(parts[2])
    chapter_id = int(parts[3])
    difficulty = parts[4]
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        try:
            quiz_data = await quiz_service.start_quiz(
                user_id=user_id,
                subject_id=subject_id,
                chapter_id=chapter_id,
                difficulty=difficulty
            )
            
            # Get subject and chapter names
            subject = await question_repo.get_subject(subject_id)
            chapter = await question_repo.get_chapter(chapter_id)
            subject_name = subject.subject_name if subject else "Unknown"
            chapter_name = chapter.chapter_name if chapter else "Unknown"
            
            questions = quiz_data['questions']
            first_question = questions[0]
            quiz_session_id = quiz_data['quiz_session_id']
            
            await state.set_state(QuizStates.quiz_in_progress)
            await state.update_data({
                'quiz_data': quiz_data,
                'current_question_index': 0,
                'quiz_session_id': quiz_session_id,
                'start_time': time.time(),
                'score': 0,
                'answers': [],
                'answered_questions': {},  # Track answered/locked questions for learning flow
                'subject_name': subject_name,
                'chapter_name': chapter_name,
                'difficulty': difficulty
            })
            
            lines = [
                "Recommended Quiz Started!",
                "",
                "Based on your performance, we recommend this quiz.",
                "",
                "-" * 25,
                "",
                f"Subject: {subject_name}",
                f"Chapter: {chapter_name}",
                f"Difficulty: {difficulty.capitalize()}",
                f"Questions: {len(questions)}",
                "",
                "-" * 25,
                "",
                f"Question 1/{len(questions)} | Score: 0",
                "",
                first_question['question_text'],
                "",
                f"A. {first_question['option_a']}",
                f"B. {first_question['option_b']}",
                f"C. {first_question['option_c']}",
                f"D. {first_question['option_d']}"
            ]
            
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=QuizKeyboard.get_question_keyboard(
                    question_number=1,
                    total_questions=len(questions),
                    question_id=first_question['question_id']
                )
            )
            
        except Exception as e:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                f"Error starting quiz: {str(e)}\n\n"
                "Please try again or select a different quiz.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("practice_weak_"))
async def practice_weak_area(callback: types.CallbackQuery, state: FSMContext):
    """Start practicing a specific weak area"""
    plain_sender = PlainTextMessageSender(callback.bot)
    user_id = callback.from_user.id
    
    # Parse: practice_weak_subjectId_chapterId_difficulty
    parts = callback.data.split("_")
    if len(parts) != 5:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    subject_id = int(parts[2])
    chapter_id = int(parts[3])
    difficulty = parts[4]
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        try:
            quiz_data = await quiz_service.start_quiz(
                user_id=user_id,
                subject_id=subject_id,
                chapter_id=chapter_id,
                difficulty=difficulty
            )
            
            # Get subject and chapter names
            subject = await question_repo.get_subject(subject_id)
            chapter = await question_repo.get_chapter(chapter_id)
            subject_name = subject.subject_name if subject else "Unknown"
            chapter_name = chapter.chapter_name if chapter else "Unknown"
            
            questions = quiz_data['questions']
            first_question = questions[0]
            quiz_session_id = quiz_data['quiz_session_id']
            
            await state.set_state(QuizStates.quiz_in_progress)
            await state.update_data({
                'quiz_data': quiz_data,
                'current_question_index': 0,
                'quiz_session_id': quiz_session_id,
                'start_time': time.time(),
                'score': 0,
                'answers': [],
                'answered_questions': {},  # Track answered/locked questions for learning flow
                'subject_name': subject_name,
                'chapter_name': chapter_name,
                'difficulty': difficulty,
                'user_id': user_id
            })
            
            lines = [
                "Practice Mode: Weak Area",
                "",
                "Focusing on your weak areas to improve!",
                "",
                "-" * 25,
                "",
                f"Subject: {subject_name}",
                f"Chapter: {chapter_name}",
                f"Difficulty: {difficulty.capitalize()}",
                f"Questions: {len(questions)}",
                "",
                "-" * 25,
                "",
                f"Question 1/{len(questions)} | Score: 0",
                "",
                first_question['question_text'],
                "",
                f"A. {first_question['option_a']}",
                f"B. {first_question['option_b']}",
                f"C. {first_question['option_c']}",
                f"D. {first_question['option_d']}"
            ]
            
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=QuizKeyboard.get_question_keyboard(
                    question_number=1,
                    total_questions=len(questions),
                    question_id=first_question['question_id']
                )
            )
            
        except Exception as e:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                f"Error starting practice quiz: {str(e)}\n\n"
                "Please try again or select a different area.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


# ============================================================================
# FULL SUMMARY FEATURE
# ============================================================================

@router.callback_query(F.data.startswith("quiz_summary_"))
async def show_quiz_summary(callback: types.CallbackQuery, state: FSMContext):
    """
    Display full quiz summary with all questions in a single message.
    
    This handler fixes the "Update is not handled" error by properly
    processing the quiz_summary callback pattern.
    """
    plain_sender = PlainTextMessageSender(callback.bot)
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    quiz_session_id = parts[2]
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        
        quiz_details = await attempt_repo.get_quiz_session_details(quiz_session_id)
        
        if not quiz_details:
            await plain_sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Quiz Summary\n\n"
                "Quiz session not found or has expired.",
                reply_markup=QuizKeyboard.get_quiz_summary_keyboard(quiz_session_id)
            )
            await callback.answer()
            return
        
        summary_message = _build_full_summary(quiz_details)
        
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await plain_sender.send_message(
            callback.message.chat.id,
            summary_message,
            reply_markup=QuizKeyboard.get_quiz_summary_keyboard(quiz_session_id)
        )
    
    await callback.answer()


def _build_full_summary(quiz_details: Dict[str, Any]) -> str:
    """Build a comprehensive full summary message with all questions."""
    subject_name = quiz_details.get('subject_name', 'Unknown')
    chapter_name = quiz_details.get('chapter_name', 'Unknown')
    difficulty = quiz_details.get('difficulty', 'simple').capitalize()
    correct_answers = quiz_details.get('correct_answers', 0)
    incorrect_answers = quiz_details.get('incorrect_answers', 0)
    accuracy = quiz_details.get('accuracy', 0)
    total_time = quiz_details.get('total_time', 0)
    average_time = quiz_details.get('average_time', 0)
    questions = quiz_details.get('questions', [])
    
    lines = [
        "FULL QUIZ SUMMARY",
        "=" * 30,
        "",
        f"Subject: {subject_name}",
        f"Chapter: {chapter_name}",
        f"Difficulty: {difficulty}",
        "",
        "-" * 30,
        "Overall Results:",
        "",
        f"Correct: {correct_answers}",
        f"Incorrect: {incorrect_answers}",
        f"Accuracy: {accuracy}%",
        f"Total Time: {total_time}s ({average_time}s avg)",
        "",
        "=" * 30,
        "Question Review:",
        ""
    ]
    
    for i, q in enumerate(questions, 1):
        question_text = q.get('question_text', '')
        if len(question_text) > 200:
            question_text = question_text[:197] + "..."
        
        user_selected = q.get('user_selected', '')
        correct_option = q.get('correct_option', '')
        is_correct = q.get('is_correct', False)
        time_taken = q.get('time_taken', 0)
        explanation = q.get('explanation', '')
        options = q.get('options', {})
        
        status = "CORRECT" if is_correct else "INCORRECT"
        
        lines.append(f"{i}. {question_text}")
        lines.append("")
        
        for opt in ['A', 'B', 'C', 'D']:
            opt_text = options.get(opt, '')
            if len(opt_text) > 50:
                opt_text = opt_text[:47] + "..."
            
            if opt == user_selected and opt == correct_option:
                marker = " (Your choice - Correct)"
            elif opt == user_selected:
                marker = " (Your choice)"
            elif opt == correct_option:
                marker = " (Correct answer)"
            else:
                marker = ""
            
            lines.append(f"  {opt}. {opt_text}{marker}")
        
        lines.append("")
        lines.append(f"{status} | You: {user_selected} -> Correct: {correct_option} | {time_taken}s")
        
        if explanation:
            if len(explanation) > 150:
                explanation = explanation[:147] + "..."
            lines.append(f"Explanation: {explanation}")
        
        lines.append("-" * 30)
    
    if accuracy >= 80:
        grade = "Excellent!"
        encouragement = "Outstanding performance! You're mastering this topic."
    elif accuracy >= 60:
        grade = "Good Job!"
        encouragement = "Great work! Keep practicing to improve further."
    elif accuracy >= 40:
        grade = "Keep Learning!"
        encouragement = "Good effort! Review the explanations and try again."
    else:
        grade = "Keep Practicing!"
        encouragement = "Don't give up! Review the material and try again."
    
    lines.append("=" * 30)
    lines.append(f"{grade}")
    lines.append("")
    lines.append(encouragement)
    
    return "\n".join(lines)


@router.callback_query(F.data == "back_to_menu", QuizStates.selecting_subject)
async def back_to_menu_from_subjects(callback: types.CallbackQuery, state: FSMContext):
    """Go back to main menu from subject selection"""
    plain_sender = PlainTextMessageSender(callback.bot)
    await state.clear()
    
    await plain_sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Quiz Bot\n\nWelcome! Choose an option below:",
        reply_markup=MainMenuKeyboard.get_main_menu_inline()
    )
    await callback.answer()
    