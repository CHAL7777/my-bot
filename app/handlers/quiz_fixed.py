"""
Learning-Focused Quiz Handler with "Check & Reveal" Pattern.

4-Phase Quiz Flow:
1. QUESTION: Send question with A/B/C/D options
2. LOCK: User selects option, buttons lock, show "🧠 Check Answer → Learn Why"
3. REVEAL: Show ✅/❌, answers, explanation (user MUST see this)
4. AUTO-PROGRESS: Wait 1-2 seconds, automatically load next question
"""

import uuid
import time
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
import logging

logger = logging.getLogger(__name__)

router = Router()
_feedback_service = FeedbackService()
AUTO_PROGRESS_DELAY = 1.5  # seconds to wait before auto-loading next question

# Anti-spam: Track processed callbacks
_callback_processed: Dict[str, datetime] = {}
_CALLBACK_DUPLICATE_WINDOW = 2.0


def _get_callback_key(user_id: int, callback_data: str) -> str:
    return f"{user_id}:{callback_data}"


def _is_callback_duplicate(user_id: int, callback_data: str) -> bool:
    key = _get_callback_key(user_id, callback_data)
    now = datetime.now()

    if key in _callback_processed:
        last_processed = _callback_processed[key]
        if now - last_processed < timedelta(seconds=_CALLBACK_DUPLICATE_WINDOW):
            return True

    _callback_processed[key] = now

    cleanup_threshold = now - timedelta(seconds=10)
    _callback_processed.update(
        {k: v for k, v in _callback_processed.items() if v > cleanup_threshold}
    )

    return False


async def _safe_answer_callback(callback: types.CallbackQuery, text: str = None, show_alert: bool = False) -> None:
    try:
        await callback.answer(text, show_alert=show_alert)
    except Exception:
        pass


class QuizStates(StatesGroup):
    """FSM states for the learning quiz flow"""
    selecting_subject = State()
    selecting_chapter = State()
    selecting_difficulty = State()
    quiz_in_progress = State()      # Phase 1: User sees question, can select option
    waiting_for_check = State()     # Phase 2: User selected, waiting to click "Check Answer"
    viewing_explanation = State()   # Phase 3: User seeing explanation (auto-progress soon)


ACCESS_DENIED_MESSAGE = "❌ Access Denied\n\nYour account is not approved yet."


async def check_quiz_access(user_id: int) -> Dict[str, Any]:
    """Check if user can access quiz (must be approved)"""
    try:
        async for db_session in get_db():
            query = text("SELECT user_id, approved FROM users WHERE user_id = :user_id")
            result = await db_session.execute(query, {"user_id": user_id})
            row = result.fetchone()
            if not row:
                return {'allowed': False, 'user_id': user_id}
            return {'allowed': row[1] == True, 'user_id': user_id}
    except Exception as e:
        logger.error(f"Error checking quiz access for user {user_id}: {e}")
        return {'allowed': False, 'user_id': user_id}


async def send_access_denied(message, use_inline: bool):
    """Send access denied message"""
    if use_inline:
        try:
            await message.edit_text(ACCESS_DENIED_MESSAGE, parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_main_menu_inline())
        except Exception:
            await message.answer(ACCESS_DENIED_MESSAGE, parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_main_menu())
    else:
      access_result = data.get('access_result') if data else None
    
    if access_result and access_result.get('allowed'):
        await start_quiz_flow(message, state, user_id)
    else:
        access_check = await check_quiz_access(user_id)
        if not access_check['allowed']:
            await send_access_denied(message, False)
        else:
            await start_quiz_flow(message, state, user_id)


async def start_quiz_flow(update: types.Update, state: FSMContext, user_id: int):
    is_callback = isinstance(update, CallbackQuery)
    message = update.message if is_callback else update
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subjects = await question_repo.get_subjects()
        
        if not subjects:
            await send_access_denied(message, is_callback)
            return
        
        subject_list = [{'subject_id': s.subject_id, 'subject_name': s.subject_name} for s in subjects]
        
        await state.set_state(QuizStates.selecting_subject)
        await state.update_data({
            'subjects': subject_list, 'user_id': user_id, 'quiz_session_id': str(uuid.uuid4()),
            'score': 0, 'answers': [], 'start_time': time.time()
        })
        
        await _send_quiz_subjects(message, subject_list, is_callback)


async def _send_quiz_subjects(message, subjects: list, use_inline_keyboard: bool):
    text = "📚 *Quiz - Learning Mode*\n\nThis quiz uses the *Check & Reveal* pattern:\n• Select your answer\n• Click 'Check Answer' to see if you're right\n• Read the explanation\n• Automatically move to the next question\n\nSelect a subject to begin:"
    if use_inline_keyboard:
        await message.edit_text(text, parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_subjects_keyboard(subjects))
    else:
        await message.answer(text, parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_subjects_keyboard(subjects))


@router.callback_query(F.data.startswith("subject_"), QuizStates.selecting_subject)
async def select_subject(callback: types.CallbackQuery, state: FSMContext, data: Dict[str, Any] = None):
    user_id = callback.from_user.id
    access_granted = data.get('access_result', {}).get('allowed') if data else None
    if access_granted is None:
        access_check = await check_quiz_access(user_id)
        access_granted = access_check['allowed']
    
    if not access_granted:
        await send_access_denied(callback.message, True)
        await callback.answer()
        return
    
    subject_id = int(callback.data.split("_")[1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        chapters = await question_repo.get_chapters(subject_id)
        
        if not chapters:
            await callback.message.edit_text("No chapters available.", reply_markup=MainMenuKeyboard.get_subjects_keyboard([]))
            await callback.answer()
            return
        
        subject = await question_repo.get_subject(subject_id)
        subject_name = subject.subject_name if subject else f"Subject {subject_id}"
        chapter_list = [{'chapter_id': c.chapter_id, 'chapter_name': c.chapter_name} for c in chapters]
        
        await state.set_state(QuizStates.selecting_chapter)
        await state.update_data({'subject_id': subject_id, 'subject_name': subject_name, 'chapters': chapter_list})
        
        await callback.message.edit_text(
            f"Select a Chapter\n\nSubject: {subject_name}\nChoose the chapter:",
            parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_chapters_keyboard(chapter_list)
        )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_subjects", QuizStates.selecting_chapter)
async def back_to_subjects(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(QuizStates.selecting_subject)
    await _send_quiz_subjects(callback.message, data.get('subjects', []), is_callback=True)
    await callback.answer()


@router.callback_query(F.data.startswith("chapter_"), QuizStates.selecting_chapter)
async def select_chapter(callback: types.CallbackQuery, state: FSMContext, data: Dict[str, Any] = None):
    user_id = callback.from_user.id
    access_granted = data.get('access_result', {}).get('allowed') if data else None
    if access_granted is None:
        access_check = await check_quiz_access(user_id)
        access_granted = access_check['allowed']
    
    if not access_granted:
        await send_access_denied(callback.message, True)
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
        await state.update_data({'chapter_id': chapter_id, 'chapter_name': chapter_name})
        
        simple_count = await question_repo.get_question_count(subject_id=subject_id, chapter_id=chapter_id, difficulty='simple')
        medium_count = await question_repo.get_question_count(subject_id=subject_id, chapter_id=chapter_id, difficulty='medium')
        hard_count = await question_repo.get_question_count(subject_id=subject_id, chapter_id=chapter_id, difficulty='hard')
        
        await callback.message.edit_text(
            f"Select Difficulty\n\nSubject: {subject_name}\nChapter: {chapter_name}\n\nAvailable questions:\n{EMOJIS['easy']} Simple: {simple_count}\n{EMOJIS['medium']} Medium: {medium_count}\n{EMOJIS['hard']} Hard: {hard_count}\n\nChoose difficulty:",
            parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_difficulty_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_chapters", QuizStates.selecting_difficulty)
async def back_to_chapters(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(QuizStates.selecting_chapter)
    await callback.message.edit_text(
        f"Select a Chapter\n\nSubject: {data.get('subject_name', '')}\nChoose the chapter:",
        parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_chapters_keyboard(data.get('chapters', []))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("difficulty_"), QuizStates.selecting_difficulty)
async def select_difficulty(callback: types.CallbackQuery, state: FSMContext, data: Dict[str, Any] = None):
    user_id = callback.from_user.id
    access_granted = data.get('access_result', {}).get('allowed') if data else None
    if access_granted is None:
        access_check = await check_quiz_access(user_id)
        access_granted = access_check['allowed']
    
    if not access_granted:
        await send_access_denied(callback.message, True)
        await callback.answer()
        return
    
    difficulty = callback.data.split("_")[1]
    data = await state.get_data()
    subject_id, subject_name = data.get('subject_id'), data.get('subject_name', '')
    chapter_id, chapter_name = data.get('chapter_id'), data.get('chapter_name', '')
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        try:
            quiz_data = await quiz_service.start_quiz(user_id=user_id, subject_id=subject_id, chapter_id=chapter_id, difficulty=difficulty)
            questions = quiz_data['questions']
            if not questions:
                await callback.message.edit_text("No questions available.", parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_main_menu_inline())
                await callback.answer()
                return
            
            first_question = questions[0]
            quiz_session_id = quiz_data['quiz_session_id']
            
            await state.set_state(QuizStates.quiz_in_progress)
            await state.update_data({
                'quiz_data': quiz_data, 'current_question_index': 0, 'quiz_session_id': quiz_session_id,
                'start_time': time.time(), 'score': 0, 'answers': [], 'subject_name': subject_name,
                'chapter_name': chapter_name, 'difficulty': difficulty, 'user_id': user_id,
                'selected_option': None, 'question_start_time': time.time()
            })
            
            difficulty_emoji = {"simple": "🟢", "medium": "🟡", "hard": "🔴"}.get(difficulty, "⚡")
            start_message = _feedback_service.get_quiz_start_message()
            
            text = (
                f"{start_message['emoji']} *Quiz Started!*\n\n{start_message['message']}\n\n{'─' * 25}\n\n"
                f"📚 *{subject_name}*\n📖 *{chapter_name}*\n{difficulty_emoji} *{difficulty.capitalize()}*\n❓ *{len(questions)} questions*\n\n"
                f"{'─' * 25}\n\n📊 *Question 1/{len(questions)}* | 🏆 *Score: 0*\n\n"
                f"{first_question['question_text']}\n\n"
                f"A. {first_question['option_a']}\nB. {first_question['option_b']}\nC. {first_question['option_c']}\nD. {first_question['option_d']}"
            )
            
            await callback.message.edit_text(
                text, parse_mode='Markdown',
                reply_markup=QuizKeyboard.get_question_keyboard(question_number=1, total_questions=len(questions), question_id=first_question['question_id'])
            )
            
        except Exception as e:
            error_msg = str(e)
            if "Daily quiz limit reached" in error_msg:
                await callback.message.edit_text("Daily Limit Reached!", parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_main_menu_inline())
            else:
                logger.error(f"Error starting quiz: {e}")
                await callback.message.edit_text("Error starting quiz. Please try again.", parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_main_menu_inline())
    
    await callback.answer()


@router.callback_query(F.data.startswith("learn_opt_"), QuizStates.quiz_in_progress)
async def select_option(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if _is_callback_duplicate(user_id, callback.data):
        await _safe_answer_callback(callback, "Already processing...", show_alert=False)
        return
    
    parts = callback.data.split("_")
    if len(parts) != 4:
        await callback.answer("Invalid option", show_alert=False)
        return
    
    question_id = int(parts[2])
    selected_option = parts[3]
    
    data = await state.get_data()
    quiz_data, questions = data.get('quiz_data', {}), data.get('quiz_data', {}).get('questions', [])
    current_index, total_questions, score = data.get('current_question_index', 0), len(questions), data.get('score', 0)
    
    if current_index >= len(questions):
        await callback.answer("Quiz finished!", show_alert=False)
        return
    
    current_question = questions[current_index]
    if current_question['question_id'] != question_id:
        await callback.answer("Please wait for the next question", show_alert=False)
        return
    
    await state.update_data({'selected_option': selected_option, 'question_start_time': time.time()})
    await state.set_state(QuizStates.waiting_for_check)
    
    question_text = f"📊 *Question {current_index + 1}/{total_questions}* | 🏆 *Score: {score}*\n\n{current_question['question_text']}\n\nA. {current_question['option_a']}\nB. {current_question['option_b']}\nC. {current_question['option_c']}\nD. {current_question['option_d']}"
    
    await callback.message.edit_text(
        question_text, parse_mode='Markdown',
        reply_markup=QuizKeyboard.get_check_answer_keyboard(question_number=current_index + 1, total_questions=total_questions, question_id=question_id, selected_option=selected_option)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("learn_check_"), QuizStates.waiting_for_check)
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if _is_callback_duplicate(user_id, callback.data):
        await _safe_answer_callback(callback, "Already processing...", show_alert=False)
        return
    
    parts = callback.data.split("_")
    if len(parts) != 3:
        await _safe_answer_callback(callback, "Invalid request", show_alert=False)
        return
    
    question_id = int(parts[2])
    data = await state.get_data()
    quiz_data, questions = data.get('quiz_data', {}), data.get('quiz_data', {}).get('questions', [])
    current_index, total_questions = data.get('current_question_index', 0), len(questions)
    selected_option, quiz_session_id = data.get('selected_option'), data.get('quiz_session_id')
    user_id, score, answers = data.get('user_id'), data.get('score', 0), data.get('answers', [])
    
    if current_index >= len(questions):
        await callback.answer("Quiz finished!", show_alert=False)
        return
    
    current_question = questions[current_index]
    if current_question['question_id'] != question_id or not selected_option:
        await callback.answer("Question mismatch", show_alert=False)
        return
    
    is_correct = (selected_option == current_question['correct_option'])
    correct_option = current_question['correct_option']
    explanation = current_question.get('explanation', 'No explanation available.')
    time_taken = int(time.time() - data.get('question_start_time', time.time()))
    new_score = score + (1 if is_correct else 0)
    
    async for session in get_db():
        attempt_repo = AttemptRepository(session)
        await attempt_repo.create_learning_attempt(user_id=user_id, question_id=question_id, selected_option=selected_option, is_correct=is_correct, time_taken=time_taken, quiz_session_id=quiz_session_id)
    
    new_answers = answers + [{'question_id': question_id, 'selected_option': selected_option, 'is_correct': is_correct, 'time_taken': time_taken}]
    
    option_map = {'A': current_question.get('option_a', ''), 'B': current_question.get('option_b', ''), 'C': current_question.get('option_c', ''), 'D': current_question.get('option_d', '')}
    result_header = "✅ Correct!" if is_correct else "❌ Incorrect"
    
    message_text = (
        f"{result_header}\n\nYour answer: {selected_option} — {option_map.get(selected_option, '')}\n"
        f"Correct answer: {correct_option} — {option_map.get(correct_option, '')}\n\n{'─' * 30}\n\n"
        f"📘 Explanation:\n{explanation}\n\n{'─' * 30}\n\n⏳ Loading next question..."
    )
    
    await state.update_data({'score': new_score, 'answers': new_answers, 'current_question_index': current_index})
    await state.set_state(QuizStates.viewing_explanation)
    
    try:
        await callback.message.edit_text(
            message_text, parse_mode='Markdown',
            reply_markup=QuizKeyboard.get_disabled_learning_keyboard(question_number=current_index + 1, total_questions=total_questions)
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
    
    await callback.answer()
    asyncio.create_task(_auto_next_question(callback.message, state, new_score))


async def _auto_next_question(message: types.Message, state: FSMContext, current_score: int):
    await asyncio.sleep(MIN_EXPLANATION_DELAY)
    
    data = await state.get_data()
    quiz_data, questions = data.get('quiz_data', {}), data.get('quiz_data', {}).get('questions', [])
    current_index, total_questions = data.get('current_question_index', 0), len(questions)
    next_index = current_index + 1
    
    if next_index >= len(questions):
        await finish_quiz(message, state, current_score, total_questions, data.get('quiz_session_id'), data.get('user_id'), data.get('subject_name', ''), data.get('chapter_name', ''), data.get('difficulty', 'simple'), data.get('answers', []))
        return
    
    next_question = questions[next_index]
    
    await state.update_data({'current_question_index': next_index, 'selected_option': None, 'question_start_time': time.time()})
    await state.set_state(QuizStates.quiz_in_progress)
    
    question_text = f"📊 *Question {next_index + 1}/{total_questions}* | 🏆 *Score: {current_score}*\n\n{next_question['question_text']}\n\nA. {next_question['option_a']}\nB. {next_question['option_b']}\nC. {next_question['option_c']}\nD. {next_question['option_d']}"
    
    try:
        await message.edit_text(
            question_text, parse_mode='Markdown',
            reply_markup=QuizKeyboard.get_learning_question_keyboard(question_number=next_index + 1, total_questions=total_questions, question_id=next_question['question_id'])
        )
    except Exception as e:
        logger.error(f"Error showing next question: {e}")


async def finish_quiz(message: types.Message, state: FSMContext, score: int, total_questions: int, quiz_session_id: str, user_id: int, subject_name: str, chapter_name: str, difficulty: str, answers: List[Dict[str, Any]]):
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
        await message.answer(result_message, parse_mode='Markdown', reply_markup=QuizKeyboard.get_quiz_results_keyboard(quiz_session_id))



@router.callback_query(F.data == "learn_cancel", QuizStates.quiz_in_progress)
async def cancel_quiz_confirmation(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Cancel Quiz?\n\nAre you sure you want to cancel this quiz?", parse_mode='Markdown', reply_markup=QuizKeyboard.get_quiz_cancel_confirmation())
    await callback.answer()


@router.callback_query(F.data == "learn_confirm_cancel")
async def confirm_cancel_quiz(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Quiz cancelled.", reply_markup=MainMenuKeyboard.get_main_menu_inline())
    await callback.answer()


@router.callback_query(F.data == "learn_continue")
async def continue_quiz(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    quiz_data, questions = data.get('quiz_data', {}), data.get('quiz_data', {}).get('questions', [])
    current_index, total_questions, score = data.get('current_question_index', 0), len(questions), data.get('score', 0)
    selected_option = data.get('selected_option')
    
    if current_index >= len(questions):
        await callback.answer("Quiz finished!", show_alert=False)
        return
    
    current_question = questions[current_index]
    
    if selected_option:
        await state.set_state(QuizStates.waiting_for_check)
        question_text = f"📊 *Question {current_index + 1}/{total_questions}* | 🏆 *Score: {score}*\n\n{current_question['question_text']}\n\nA. {current_question['option_a']}\nB. {current_question['option_b']}\nC. {current_question['option_c']}\nD. {current_question['option_d']}"
        await callback.message.edit_text(question_text, parse_mode='Markdown', reply_markup=QuizKeyboard.get_check_answer_keyboard(question_number=current_index + 1, total_questions=total_questions, question_id=current_question['question_id'], selected_option=selected_option))
    else:
        await state.set_state(QuizStates.quiz_in_progress)
        question_text = f"📊 *Question {current_index + 1}/{total_questions}* | 🏆 *Score: {score}*\n\n{current_question['question_text']}\n\nA. {current_question['option_a']}\nB. {current_question['option_b']}\nC. {current_question['option_c']}\nD. {current_question['option_d']}"
        await callback.message.edit_text(question_text, parse_mode='Markdown', reply_markup=QuizKeyboard.get_learning_question_keyboard(question_number=current_index + 1, total_questions=total_questions, question_id=current_question['question_id']))
    
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    await _safe_answer_callback(callback, "This question has expired.", show_alert=False)


@router.callback_query()
async def handle_expired_callback(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state in [QuizStates.quiz_in_progress, QuizStates.waiting_for_check, QuizStates.viewing_explanation]:
        await _safe_answer_callback(callback, "This quiz has moved on.", show_alert=False)
    else:
        await _safe_answer_callback(callback)


@router.callback_query(F.data.startswith("quiz_details_"))
async def show_quiz_details(callback: types.CallbackQuery, state: FSMContext):
    """Handle quiz_details_{quiz_session_id} callback from quiz results"""
    quiz_session_id = callback.data.split("_")[2]
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        quiz_details = await quiz_service.get_quiz_session_details(quiz_session_id)
        
        if not quiz_details:
            await callback.message.edit_text("Quiz session not found.", reply_markup=MainMenuKeyboard.get_main_menu_inline())
            await callback.answer()
            return
        
        questions = quiz_details.get('questions', [])
        if not questions:
            await callback.message.edit_text("No questions found.", reply_markup=MainMenuKeyboard.get_main_menu_inline())
            await callback.answer()
            return
        
        await _display_question_for_review(callback, quiz_details, questions[0], 0)
    
    await callback.answer()


@router.callback_query(F.data.startswith("learn_details_"))
async def learn_quiz_details(callback: types.CallbackQuery, state: FSMContext):
    """Handle learn_details_{quiz_session_id} callback from learning quiz results"""
    # This is the same as show_quiz_details - just a different callback name
    quiz_session_id = callback.data.split("_")[2]
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        quiz_details = await quiz_service.get_quiz_session_details(quiz_session_id)
        
        if not quiz_details:
            await callback.message.edit_text("Quiz session not found.", reply_markup=MainMenuKeyboard.get_main_menu_inline())
            await callback.answer()
            return
        
        questions = quiz_details.get('questions', [])
        if not questions:
            await callback.message.edit_text("No questions found.", reply_markup=MainMenuKeyboard.get_main_menu_inline())
            await callback.answer()
            return
        
        await _display_question_for_review(callback, quiz_details, questions[0], 0)
    
    await callback.answer()


@router.callback_query(F.data == "learn_retry")
async def learn_retry(callback: types.CallbackQuery, state: FSMContext):
    """Handle learn_retry callback - restart quiz with same settings"""
    data = await state.get_data()
    subject_id = data.get('subject_id')
    chapter_id = data.get('chapter_id')
    subject_name = data.get('subject_name', '')
    chapter_name = data.get('chapter_name', '')
    difficulty = data.get('difficulty', 'simple')
    user_id = callback.from_user.id
    
    if subject_id and chapter_id:
        # Restart with difficulty selection
        await state.set_state(QuizStates.selecting_difficulty)
        await callback.message.edit_text(
            f"🔄 *Try Again*\n\nSubject: {subject_name}\nChapter: {chapter_name}\n\nChoose difficulty:",
            parse_mode='Markdown',
            reply_markup=MainMenuKeyboard.get_difficulty_keyboard()
        )
    else:
        # No saved settings, go back to main menu
        await state.clear()
        await callback.message.edit_text(
            "🔄 *Start New Quiz*\n\nSelect a subject to begin:",
            parse_mode='Markdown',
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("review_"))
async def review_question(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) != 4:
        await callback.answer("Invalid request", show_alert=False)
        return
    
    quiz_session_id, current_index = parts[1], int(parts[2])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        quiz_details = await quiz_service.get_quiz_session_details(quiz_session_id)
        if not quiz_details:
            await callback.answer("Quiz session not found", show_alert=False)
            return
        
        questions = quiz_details.get('questions', [])
        if not questions or current_index >= len(questions):
            await callback.answer("Invalid question", show_alert=False)
            return
        
        await _display_question_for_review(callback, quiz_details, questions[current_index], current_index)
    
    await callback.answer()


async def _display_question_for_review(callback: types.CallbackQuery, quiz_details: Dict[str, Any], question_data: Dict[str, Any], current_index: int):
    quiz_session_id, total_questions = quiz_details['quiz_session_id'], quiz_details['total_questions']
    options, correct_option = question_data['options'], question_data['correct_option']
    user_selected, is_correct = question_data['user_selected'], question_data['is_correct']
    
    option_icons = {'A': '○', 'B': '○', 'C': '○', 'D': '○'}
    if is_correct:
        option_icons[correct_option] = '✅'
    else:
        option_icons[correct_option] = '✅'
        option_icons[user_selected] = '❌'
    
    option_lines = [f"{option_icons[opt]} {opt}. {options[opt]} {'👤' if opt == user_selected else ''}" for opt in ['A', 'B', 'C', 'D']]
    emoji = EMOJIS['correct'] if is_correct else EMOJIS['wrong']
    
    message_text = f"📋 Quiz Details\n{'─' * 20}\n\n📚 {quiz_details['subject_name']}\n📖 Chapter: {quiz_details['chapter_name']}\n📊 Difficulty: {quiz_details['difficulty'].capitalize()}\n{'─' * 20}\n\nQuestion {current_index + 1}/{total_questions}\n{emoji} | ⏱️ {question_data['time_taken']}s\n\n{question_data['question_text']}\n\n" + "\n".join(option_lines)
    
    explanation = question_data.get('explanation')
    if explanation:
        message_text += f"\n{'─' * 20}\n\n📘 Explanation:\n{explanation}"
    
    await callback.message.edit_text(message_text, parse_mode='Markdown', reply_markup=QuizKeyboard.get_question_review_keyboard(quiz_session_id=quiz_session_id, current_index=current_index, total=total_questions))


@router.callback_query(F.data == "weak_areas")
async def show_weak_areas(callback: types.CallbackQuery, state: FSMContext):
    """Show weak areas with navigation back to quiz results"""
    data = await state.get_data()
    quiz_session_id = data.get('quiz_session_id', '')
    
    weak_message = "📊 *Your Weak Areas*\n\nBased on your quiz performance:\n\n🔴 *High Priority:* Topics with multiple incorrect answers\n🟡 *Medium Priority:* Topics with some incorrect answers\n\n💡 *Recommendations:* Practice these topics with simpler questions first.\n\n" + "─" * 25 + "\n\n📚 *Suggested Practice:*\n• Review explanations\n• Try easier difficulty levels\n• Focus on understanding concepts"
    
    # Create a custom keyboard with navigation back to results
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔄 Get Recommendations",
                callback_data="get_recommendations"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Back to Results",
                callback_data=f"quiz_results_{quiz_session_id}" if quiz_session_id else "back_to_menu"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Back to Menu",
                callback_data="back_to_menu"
            )
        ]
    ]
    
    await callback.message.edit_text(weak_message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data == "try_again")
async def try_again(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get('subject_id') and data.get('chapter_id'):
        await state.set_state(QuizStates.selecting_difficulty)
        await callback.message.edit_text("🔄 *Try Again*\n\nChoose difficulty:", parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_difficulty_keyboard())
    else:
        await callback.message.edit_text("🔄 *Start New Quiz*\n\nSelect a subject:", parse_mode='Markdown', reply_markup=MainMenuKeyboard.get_main_menu_inline())
    await callback.answer()


@router.callback_query(F.data == "get_recommendations")
async def get_recommendations(callback: types.CallbackQuery, state: FSMContext):
    """Show recommendations with navigation back to quiz results"""
    data = await state.get_data()
    quiz_session_id = data.get('quiz_session_id', '')
    
    recommendations = "🎯 *Personalized Recommendations*\n\n" + "─" * 25 + "\n\n📈 *Based on your performance:*\n\n1️⃣ *Continue with current progress*\n   Keep practicing!\n\n2️⃣ *Challenge yourself"
