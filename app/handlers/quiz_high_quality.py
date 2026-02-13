"""
Beautiful Interactive Quiz Handler - "Check & Reveal" Pattern

This module provides a beautiful, interactive quiz experience:
1. User selects an answer option with colored buttons
2. Button changes to "✅ Check Answer → Learn Why"
3. User clicks to reveal correctness + celebration message
4. Auto-progress to next question

Features:
- 🎨 Colored option buttons with emoji markers
- 🎉 Celebration messages for correct answers
- 💪 Encouragement for wrong answers
- 🔥 Streak tracking
- ⏱️ Auto-progress after explanation
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
from app.utils.plain_sender import PlainTextMessageSender
from app.utils.feedback_messages import (
    get_correct_answer_celebration,
    get_wrong_answer_encouragement,
    get_progress_indicator,
)

logger = logging.getLogger(__name__)

# Create router for beautiful interactive quiz
router = Router()


# ============================================================================
# KEYBOARD HELPERS - Beautiful & Colored
# ============================================================================

def get_option_selected_keyboard(question_id: int, selected_option: str) -> InlineKeyboardMarkup:
    """
    Show selected option with colored marker and "✅ Check Answer → Learn Why" button.
    Prevents changing the answer.
    """
    # Option colors - green for selected, gray for others
    option_colors = {
        'A': ('🔵', '⚪'),  # Blue
        'B': ('🟢', '⚪'),  # Green
        'C': ('🟡', '⚪'),  # Yellow
        'D': ('🔴', '⚪'),  # Red
    }
    
    option_labels = ['A', 'B', 'C', 'D']
    keyboard = []
    
    # Show options with colored markers
    for i in range(0, 4, 2):
        row = []
        for j in range(2):
            opt = option_labels[i + j]
            color, dim = option_colors.get(opt, ('⚪', '⚪'))
            
            if opt == selected_option:
                # Selected option - show with checkmark
                row.append(InlineKeyboardButton(
                    text=f"✓ {color} {opt}",
                    callback_data=f"noop_{question_id}_{opt}"
                ))
            else:
                # Unselected options - dimmed
                row.append(InlineKeyboardButton(
                    text=f"{dim} {opt}",
                    callback_data=f"noop_{question_id}_{opt}"
                ))
        keyboard.append(row)
    
    # Add beautiful Check Answer button
    keyboard.append([
        InlineKeyboardButton(
            text="✅ Check Answer → Learn Why",
            callback_data=f"check_{question_id}_{selected_option}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_check_result_keyboard(question_id: int, is_last: bool = False) -> InlineKeyboardMarkup:
    """
    Show result with explanation.
    For last question: "📊 View Results"
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
# QUIZ FLOW FUNCTIONS - Beautiful Messages
# ============================================================================

async def send_question(
    message: types.Message | types.CallbackQuery,
    state: FSMContext,
    questions: List[Dict[str, Any]],
    current_index: int,
    score: int
) -> None:
    """
    Display a question with 4 colored option buttons.
    """
    plain_sender = PlainTextMessageSender(message.bot if hasattr(message, 'bot') else message.message.bot)
    
    question = questions[current_index]
    total_questions = len(questions)
    
    # Build beautiful question text
    lines = [
        f"📊 Question {current_index + 1}/{total_questions} | 🏆 Score: {score}",
        "",
        question['question_text'],
        "",
        "A. " + question['option_a'],
        "B. " + question['option_b'],
        "C. " + question['option_c'],
        "D. " + question['option_d']
    ]
    question_text = "\n".join(lines)
    
    # Get keyboard with colored options
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
            await plain_sender.edit_message(
                message.message.chat.id,
                message.message.message_id,
                question_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Failed to edit message for question: {e}")
            await plain_sender.send_message(
                message.message.chat.id,
                question_text,
                reply_markup=keyboard
            )
        await message.answer()
    else:
        await plain_sender.send_message(
            message.chat.id,
            question_text,
            reply_markup=keyboard
        )


async def select_option(
    callback: types.CallbackQuery,
    state: FSMContext,
    question: Dict[str, Any],
    selected_option: str
) -> None:
    """
    Handle user's initial option selection.
    Changes buttons to "✅ Check Answer → Learn Why" with colored markers.
    """
    plain_sender = PlainTextMessageSender(callback.bot)
    
    data = await state.get_data()
    current_index = data.get('current_question_index', 0)
    total_questions = data.get('quiz_data', {}).get('total_questions', 0)
    score = data.get('score', 0)
    
    # Update state with selected option
    answered_questions = data.get('answered_questions', {})
    if question['question_id'] in answered_questions:
        answered_questions[question['question_id']]['selected'] = selected_option
    
    await state.update_data(answered_questions=answered_questions)
    
    # Build the message (keep format, just update keyboard)
    lines = [
        f"📊 Question {current_index + 1}/{total_questions} | 🏆 Score: {score}",
        "",
        question['question_text'],
        "",
        "🔵 A. " + question['option_a'],
        "🟢 B. " + question['option_b'],
        "🟡 C. " + question['option_c'],
        "🔴 D. " + question['option_d']
    ]
    question_text = "\n".join(lines)
    
    # Get keyboard with colored selected option + Check Answer button
    keyboard = get_option_selected_keyboard(
        question_id=question['question_id'],
        selected_option=selected_option
    )
    
    # Edit message with new keyboard
    try:
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            question_text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f"Failed to edit message for option selection: {e}")
    
    await callback.answer(f"✓ Selected {selected_option}. Click to check!")


async def check_answer(
    callback: types.CallbackQuery,
    state: FSMContext,
    question: Dict[str, Any],
    selected_option: str
) -> None:
    """
    Evaluate the answer and show beautiful explanation.
    This is the "Reveal" step with celebration or encouragement.
    """
    plain_sender = PlainTextMessageSender(callback.bot)
    
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
    correct_option = question['correct_option']
    
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
    
    # Show beautiful explanation
    await show_explanation(
        callback=callback,
        state=state,
        question=question,
        selected_option=selected_option,
        is_correct=is_correct,
        current_index=current_index,
        total_questions=total_questions,
        score=score,
        time_taken=time_taken
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
    time_taken: int
) -> None:
    """
    Display the answer evaluation with beautiful celebration/encouragement.
    Forces user to engage with learning content.
    """
    plain_sender = PlainTextMessageSender(callback.bot)
    
    # Build the beautiful result message
    lines = []
    
    if is_correct:
        # Correct answer celebration!
        celebration = get_correct_answer_celebration()
        lines.append(f"{celebration['emoji']} {celebration['message']}")
        lines.append("")
        lines.append(f"✨ +1 point")
    else:
        # Wrong answer encouragement (no shaming!)
        encouragement = get_wrong_answer_encouragement(correct_option=question['correct_option'])
        lines.append(f"{encouragement['emoji']} {encouragement['message']}")
    
    lines.append("")
    lines.append(f"⏱️ {time_taken}s")
    lines.append("")
    lines.append("─" * 20)
    lines.append("")
    
    # Show correct answer
    lines.append(f"📚 Correct Answer: {question['correct_option']}")
    lines.append("")
    
    # Add explanation if available
    explanation = question.get('explanation', '')
    if explanation:
        lines.append("─" * 20)
        lines.append("")
        lines.append("💡 EXPLANATION:")
        lines.append("")
        # Truncate long explanations
        if len(explanation) > 300:
            explanation = explanation[:300] + "..."
        lines.append(explanation)
    
    lines.append("")
    lines.append("─" * 20)
    lines.append("")
    
    # Score and progress
    lines.append(f"🏆 Score: {score}")
    
    # Progress indicator
    if current_index < total_questions - 1:
        lines.append("")
        lines.append(f"📊 {get_progress_indicator(current_index + 1, total_questions)}")
        lines.append("")
        lines.append("⏭️ Loading next question...")
    else:
        lines.append("")
        lines.append("🎊 QUIZ COMPLETE!")
    
    message_text = "\n".join(lines)
    
    # Determine if this is the last question
    is_last = (current_index >= total_questions - 1)
    
    # Get result keyboard
    keyboard = get_check_result_keyboard(
        question_id=question['question_id'],
        is_last=is_last
    )
    
    # Edit message with result
    try:
        await plain_sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            message_text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f"Failed to edit message for explanation: {e}")
        await plain_sender.send_message(
            callback.message.chat.id,
            message_text,
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
    Automatically load the next question after a delay.
    Forces user to read explanation before proceeding.
    """
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
        plain_sender = PlainTextMessageSender(callback.bot)
        await finish_quiz(callback, state, plain_sender)
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
# CALLBACK HANDLERS - Beautiful & Interactive
# ============================================================================

@router.callback_query(F.data.startswith("answer_"), QuizStates.quiz_in_progress)
async def handle_option_select(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle initial option selection (A, B, C, D).
    Changes to colored button with "✅ Check Answer → Learn Why".
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
    
    # Handle option selection with beautiful feedback
    await select_option(callback, state, question, selected_option)


@router.callback_query(F.data.startswith("check_"), QuizStates.quiz_in_progress)
async def handle_check_answer(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle "✅ Check Answer → Learn Why" button click.
    Shows beautiful celebration or encouragement.
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
    
    # Check the answer with beautiful feedback
    await check_answer(callback, state, question, selected_option)


@router.callback_query(F.data == "view_quiz_results", QuizStates.quiz_in_progress)
async def handle_view_results(callback: types.CallbackQuery, state: FSMContext):
    """Handle view results button click at end of quiz"""
    plain_sender = PlainTextMessageSender(callback.bot)
    await finish_quiz(callback, state, plain_sender)


@router.callback_query(F.data.startswith("noop_"), QuizStates.quiz_in_progress)
async def handle_noop(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle disabled button clicks gracefully.
    Provides helpful feedback.
    """
    data = await state.get_data()
    answered_questions = data.get('answered_questions', {})
    
    for qid, info in answered_questions.items():
        if info.get('checked', False):
            await callback.answer("Answer already checked! Loading next...", show_alert=False)
            return
        if info.get('selected') is not None:
            await callback.answer("Click '✅ Check Answer' to reveal!", show_alert=False)
            return
    
    await callback.answer()


# ============================================================================
# AUTO-PROGRESS HANDLER
# ============================================================================

@router.callback_query(F.data == "auto_next", QuizStates.quiz_in_progress)
async def handle_auto_next(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle auto-progress callback.
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

