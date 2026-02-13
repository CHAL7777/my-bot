"""
Learning-Focused Quiz Handler - "Check & Reveal" Pattern
Plain text version for maximum reliability.
"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Any, List
import time
import asyncio
import logging

from app.keyboards.quiz import QuizKeyboard
from app.db.base import get_db
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.user_repo import UserRepository
from app.handlers.quiz import finish_quiz, QuizStates
from app.utils.plain_sender import PlainTextMessageSender  # Changed to plain text sender

logger = logging.getLogger(__name__)

# Create router for learning-focused quiz
router = Router()


# ============================================================================
# KEYBOARD HELPERS - PLAIN TEXT VERSION
# ============================================================================

def get_option_selected_keyboard(question_id: int, selected_option: str) -> InlineKeyboardMarkup:
    """
    Show selected option with "Check Answer → Show Why" button.
    Prevents changing the answer.
    """
    option_labels = ['A', 'B', 'C', 'D']
    keyboard = []
    
    # Show options with selection marker
    for i in range(0, 4, 2):
        row = []
        for j in range(2):
            opt = option_labels[i + j]
            if opt == selected_option:
                # Mark selected option with checkmark
                row.append(InlineKeyboardButton(
                    text=f"✓ {opt}",
                    callback_data=f"noop_{question_id}_{opt}"
                ))
            else:
                # Disable unselected options
                row.append(InlineKeyboardButton(
                    text=opt,
                    callback_data=f"noop_{question_id}_{opt}"
                ))
        keyboard.append(row)
    
    # Add Check Answer button
    keyboard.append([
        InlineKeyboardButton(
            text="✅ Check Answer → Show Why",
            callback_data=f"check_{question_id}_{selected_option}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_check_result_keyboard(question_id: int, is_last: bool = False) -> InlineKeyboardMarkup:
    """
    Show result with explanation.
    For last question: "View Results"
    For others: Auto-advances after delay (no button needed)
    """
    if is_last:
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📊 View Results",
                    callback_data="view_quiz_results"
                )
            ]
        ]
    else:
        # No button - auto-progress after delay
        keyboard = []
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============================================================================
# QUIZ FLOW FUNCTIONS - PLAIN TEXT VERSION
# ============================================================================

async def send_question(
    message: types.Message | types.CallbackQuery,
    state: FSMContext,
    questions: List[Dict[str, Any]],
    current_index: int,
    score: int
) -> None:
    """
    Display a question with 4 option buttons in plain text.
    """
    question = questions[current_index]
    total_questions = len(questions)
    
    # Build question text with lists
    message_lines = [
        f"📊 Question {current_index + 1}/{total_questions} | 🏆 Score: {score}",
        "",
        question['question_text'],
        "",
        f"A. {question['option_a']}",
        f"B. {question['option_b']}",
        f"C. {question['option_c']}",
        f"D. {question['option_d']}"
    ]
    
    # Get keyboard with options
    keyboard = QuizKeyboard.get_question_keyboard(
        question_number=current_index + 1,
        total_questions=total_questions,
        question_id=question['question_id']
    )
    
    # Reset state for this question
    data = await state.get_data()
    answered_questions = data.get('answered_questions', {})
    answered_questions[question['question_id']] = {
        'selected': None,
        'checked': False
    }
    await state.update_data(
        answered_questions=answered_questions,
        question_start_time=time.time()
    )
    
    # Edit message or send new one
    if isinstance(message, types.CallbackQuery):
        try:
            await message.message.edit_text(
                "\n".join(message_lines),
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Failed to edit message for question: {e}")
            await message.message.answer(
                "\n".join(message_lines),
                reply_markup=keyboard
            )
        await message.answer()
    else:
        await message.answer(
            "\n".join(message_lines),
            reply_markup=keyboard
        )


async def select_option(
    callback: types.CallbackQuery,
    state: FSMContext,
    question: Dict[str, Any],
    selected_option: str
) -> None:
    """
    Handle user's initial option selection in plain text.
    """
    sender = PlainTextMessageSender(callback.bot)
    data = await state.get_data()
    current_index = data.get('current_question_index', 0)
    total_questions = data.get('quiz_data', {}).get('total_questions', 0)
    
    # Update state with selected option
    answered_questions = data.get('answered_questions', {})
    if question['question_id'] in answered_questions:
        answered_questions[question['question_id']]['selected'] = selected_option
    
    await state.update_data(answered_questions=answered_questions)
    
    # Build the message with lists
    message_lines = [
        f"📊 Question {current_index + 1}/{total_questions} | 🏆 Score: {data.get('score', 0)}",
        "",
        question['question_text'],
        "",
        f"A. {question['option_a']}",
        f"B. {question['option_b']}",
        f"C. {question['option_c']}",
        f"D. {question['option_d']}"
    ]
    
    # Get keyboard with selected option + Check Answer button
    keyboard = get_option_selected_keyboard(
        question_id=question['question_id'],
        selected_option=selected_option
    )
    
    # Edit message with new keyboard
    try:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(message_lines),
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f"Failed to edit message for option selection: {e}")
    
    await callback.answer(f"Selected {selected_option}. Click to check!")


async def check_answer(
    callback: types.CallbackQuery,
    state: FSMContext,
    question: Dict[str, Any],
    selected_option: str
) -> None:
    """
    Evaluate the answer and show explanation in plain text.
    This is the "Reveal" step in the Check & Reveal pattern.
    """
    sender = PlainTextMessageSender(callback.bot)
    data = await state.get_data()
    current_index = data.get('current_question_index', 0)
    total_questions = data.get('quiz_data', {}).get('total_questions', 0)
    score = data.get('score', 0)
    quiz_session_id = data.get('quiz_session_id')
    subject_id = data.get('subject_id')
    chapter_id = data.get('chapter_id')
    difficulty = data.get('difficulty', 'simple')
    user_id = callback.from_user.id
    
    # Calculate time taken
    start_time = data.get('question_start_time', time.time())
    time_taken = int(time.time() - start_time)
    
    # Evaluate answer
    is_correct = (selected_option == question['correct_option'])
    if is_correct:
        points = {'simple': 1, 'medium': 2, 'hard': 3}.get(difficulty, 1)
        score += points
    
    # Mark as checked in state
    answered_questions = data.get('answered_questions', {})
    if question['question_id'] in answered_questions:
        answered_questions[question['question_id']]['checked'] = True
    await state.update_data(answered_questions=answered_questions, score=score)
    
    # Save attempt to database
    async for session in get_db():
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        try:
            await attempt_repo.create_attempt(
                user_id=user_id,
                question_id=question['question_id'],
                selected_option=selected_option,
                is_correct=is_correct,
                time_taken=time_taken,
                quiz_session_id=quiz_session_id
            )
            
            await user_repo.update_user_progress(
                user_id=user_id,
                subject_id=subject_id,
                chapter_id=chapter_id,
                difficulty=difficulty,
                is_correct=is_correct,
                time_taken=time_taken
            )
        except Exception as e:
            logger.error(f"Error saving attempt: {e}")
    
    # Update answers list
    answers = data.get('answers', [])
    answers.append({
        'question_id': question['question_id'],
        'selected_option': selected_option,
        'is_correct': is_correct
    })
    await state.update_data(answers=answers)
    
    # Show explanation
    await show_explanation(
        callback=callback,
        state=state,
        question=question,
        selected_option=selected_option,
        is_correct=is_correct,
        current_index=current_index,
        total_questions=total_questions,
        score=score,
        time_taken=time_taken,
        sender=sender
    )


async def show_explanation(
    callback: types.CallbackQuery,
    state: FSMContext,
    question: Dict[str, Any],
    selected_option: str,
    is_correct: bool,
    current_index: int,
    total_questions: int,
    score: int,
    time_taken: int,
    sender: PlainTextMessageSender
) -> None:
    """
    Display the answer evaluation with explanation in plain text.
    Forces user to engage with learning content.
    """
    # Build result header
    emoji = "✅" if is_correct else "❌"
    result_text = "Correct!" if is_correct else "Incorrect"
    
    # Get explanation
    explanation = question.get('explanation', '')
    
    # Build the result message with lists
    message_lines = [
        f"{emoji} {result_text}",
        "",
        f"You selected: {selected_option}",
        f"Correct answer: {question['correct_option']}",
        f"⏱️ Time: {time_taken}s",
        "",
    ]
    
    # Add explanation if available
    if explanation:
        message_lines.extend([
            f"💡 Explanation:",
            explanation,
            "",
        ])
    
    # Update score
    message_lines.append(f"🏆 Score: {score}")
    
    # Determine if this is the last question
    is_last = (current_index >= total_questions - 1)
    
    # Get result keyboard
    keyboard = get_check_result_keyboard(
        question_id=question['question_id'],
        is_last=is_last
    )
    
    # Edit message with result
    try:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(message_lines),
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f"Failed to edit message for explanation: {e}")
        await sender.send_message(
            callback.message.chat.id,
            "\n".join(message_lines),
            reply_markup=keyboard
        )
    
    await callback.answer()
    
    # Auto-progress to next question (if not last)
    if not is_last:
        await next_question(
            callback=callback,
            state=state,
            current_index=current_index,
            total_questions=total_questions,
            score=score
        )


async def next_question(
    callback: types.CallbackQuery,
    state: FSMContext,
    current_index: int,
    total_questions: int,
    score: int
) -> None:
    """
    Automatically load the next question after a delay in plain text.
    Forces user to read explanation before proceeding.
    """
    sender = PlainTextMessageSender(callback.bot)
    
    # Wait for user to read explanation
    await asyncio.sleep(2)
    
    # Check if quiz is still active
    current_state = await state.get_state()
    if current_state != QuizStates.quiz_in_progress:
        return
    
    # Get quiz data
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    questions = quiz_data.get('questions', [])
    
    # Move to next question
    next_index = current_index + 1
    
    if next_index >= len(questions):
        # Quiz complete
        await finish_quiz(callback, state, sender)
        return
    
    # Update state for next question
    await state.update_data(
        current_question_index=next_index,
        question_start_time=time.time()
    )
    
    # Send next question
    await send_question(
        message=callback,
        state=state,
        questions=questions,
        current_index=next_index,
        score=score
    )


# ============================================================================
# CALLBACK HANDLERS - PLAIN TEXT VERSION
# ============================================================================

@router.callback_query(F.data.startswith("answer_"), QuizStates.quiz_in_progress)
async def handle_option_select(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle initial option selection (A, B, C, D) in plain text.
    Changes to "Check Answer → Show Why" button.
    """
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    questions = quiz_data.get('questions', [])
    current_index = data.get('current_question_index', 0)
    
    # Parse callback: answer_{question_id}_{option}
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Invalid option", show_alert=True)
        return
    
    question_id = int(parts[1])
    selected_option = parts[2]
    
    # Check if already answered
    answered_questions = data.get('answered_questions', {})
    if question_id in answered_questions:
        if answered_questions[question_id].get('checked', False):
            await callback.answer("Already checked! Loading next...", show_alert=False)
            return
    
    # Find the question
    question = None
    for q in questions:
        if q['question_id'] == question_id:
            question = q
            break
    
    if not question:
        await callback.answer("Question not found", show_alert=True)
        return
    
    # Handle option selection
    await select_option(callback, state, question, selected_option)


@router.callback_query(F.data.startswith("check_"), QuizStates.quiz_in_progress)
async def handle_check_answer(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle "Check Answer → Show Why" button click in plain text.
    Shows correctness and explanation.
    """
    data = await state.get_data()
    quiz_data = data.get('quiz_data', {})
    questions = quiz_data.get('questions', [])
    
    # Parse callback: check_{question_id}_{selected_option}
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    question_id = int(parts[1])
    selected_option = parts[2]
    
    # Find the question
    question = None
    for q in questions:
        if q['question_id'] == question_id:
            question = q
            break
    
    if not question:
        await callback.answer("Question not found", show_alert=True)
        return
    
    # Check if already checked
    answered_questions = data.get('answered_questions', {})
    if question_id in answered_questions:
        if answered_questions[question_id].get('checked', False):
            await callback.answer("Already checked!", show_alert=False)
            return
    
    # Check the answer
    await check_answer(callback, state, question, selected_option)


@router.callback_query(F.data == "view_quiz_results", QuizStates.quiz_in_progress)
async def handle_view_results(callback: types.CallbackQuery, state: FSMContext):
    """Handle view results button click at end of quiz in plain text"""
    sender = PlainTextMessageSender(callback.bot)
    await finish_quiz(callback, state, sender)


@router.callback_query(F.data.startswith("noop_"), QuizStates.quiz_in_progress)
async def handle_noop(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle disabled button clicks in plain text.
    Provides feedback that action is not allowed.
    """
    data = await state.get_data()
    answered_questions = data.get('answered_questions', {})
    
    for qid, info in answered_questions.items():
        if info.get('checked', False):
            await callback.answer("Answer already checked! Loading next...", show_alert=False)
            return
        if info.get('selected') is not None:
            await callback.answer(f"Click 'Check Answer' to reveal!", show_alert=False)
            return
    
    await callback.answer()


# ============================================================================
# AUTO-PROGRESS HANDLER - PLAIN TEXT VERSION
# ============================================================================

@router.callback_query(F.data == "auto_next", QuizStates.quiz_in_progress)
async def handle_auto_next(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle auto-progress callback in plain text.
    Used when user needs to manually trigger next question after explanation.
    """
    data = await state.get_data()
    current_index = data.get('current_question_index', 0)
    total_questions = data.get('quiz_data', {}).get('total_questions', 0)
    score = data.get('score', 0)
    
    await next_question(
        callback=callback,
        state=state,
        current_index=current_index,
        total_questions=total_questions,
        score=score
    )