from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from app.keyboards.menu import MainMenuKeyboard
from app.keyboards.quiz import QuizKeyboard
from app.services.user_service import UserService
from app.services.quiz_service import QuizService
from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.question_repo import QuestionRepository
from app.utils.helpers import format_time, generate_progress_bar
from app.utils.constants import EMOJIS
from app.utils.safe_edit import safe_edit_message

router = Router()

class ProgressStates(StatesGroup):
    viewing_details = State()


@router.message(Command("progress"))
async def command_progress(message: types.Message, state: FSMContext,
                          has_active_subscription: bool = False):
    """
    Handle /progress command - show progress overview.
    
    FIX: Added has_active_subscription parameter injected by SubscriptionMiddleware.
    """
    user_id = message.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        attempt_repo = AttemptRepository(session)
        question_repo = QuestionRepository(session)
        
        user_service = UserService(user_repo, payment_repo, attempt_repo, question_repo)
        
        try:
            # Get user profile with statistics
            profile = await user_service.get_user_profile(user_id)
            
            # Prepare progress message
            progress_msg = (
                f"📊 *Your Learning Progress*\n\n"
                f"👤 Student: {profile.get('name', 'User')}\n"
                f"📅 Member since: {profile.get('created_at', datetime.now()).strftime('%d %b %Y')}\n\n"
            )
            
            # Add statistics
            stats = profile.get('stats', {})
            if stats:
                progress_msg += (
                    f"📈 *Overall Statistics:*\n"
                    f"• Total attempts: {stats.get('total_attempts', 0)}\n"
                    f"• Correct answers: {stats.get('total_correct', 0)}\n"
                    f"• Average accuracy: {stats.get('avg_accuracy', 0)}%\n"
                    f"• Time spent: {format_time(stats.get('total_time_spent', 0))}\n"
                    f"• Chapters attempted: {stats.get('chapters_attempted', 0)}\n"
                    f"• Success rate: {stats.get('success_rate', 0)}%\n\n"
                )
            
            # Add subscription info
            subscription = profile.get('subscription')
            if subscription:
                status_emoji = "✅" if subscription.get('active') else "❌"
                trial_text = " (Trial)" if subscription.get('is_trial') else ""
                progress_msg += (
                    f"{status_emoji} *Subscription{trial_text}:*\n"
                    f"• Status: {'Active' if subscription.get('active') else 'Inactive'}\n"
                    f"• Days remaining: {subscription.get('days_left', 0)}\n"
                    f"• Expires: {subscription.get('end_date', datetime.now()).strftime('%d %b %Y')}\n\n"
                )
            else:
                # Show subscription status based on middleware data
                if has_active_subscription:
                    progress_msg += (
                        f"✅ *Subscription:*\n"
                        f"• Status: Active\n"
                        f"• Access: All difficulty levels\n\n"
                    )
                else:
                    progress_msg += (
                        f"❌ *Subscription:*\n"
                        f"• Status: No active subscription\n"
                        f"• Access: Simple level only\n"
                        f"• Use /payment to upgrade\n\n"
                    )
            
            # Add daily limits
            daily_limits = profile.get('daily_limits', {})
            if daily_limits:
                progress_msg += (
                    f"📅 *Today's Activity:*\n"
                    f"• Quizzes taken: {daily_limits.get('quiz_count', 0)}/{daily_limits.get('max_quizzes', 0)}\n"
                    f"• Questions answered: {daily_limits.get('question_count', 0)}\n"
                    f"• Remaining quizzes: {daily_limits.get('remaining_quizzes', 0)}\n\n"
                )
            
            # Add weak areas if available
            weak_chapters = profile.get('weak_chapters', [])
            if weak_chapters:
                progress_msg += f"📚 *Areas Needing Improvement:*\n"
                for i, chapter in enumerate(weak_chapters[:3], 1):
                    progress_bar = generate_progress_bar(chapter.get('accuracy', 0))
                    progress_msg += f"{i}. Accuracy: {progress_bar}\n"
                progress_msg += "\n"
            
            progress_msg += "Choose an option below for more details:"
            
            await message.answer(
                progress_msg,
                parse_mode='Markdown',
                reply_markup=MainMenuKeyboard.get_progress_options_keyboard()
            )
            
        except Exception as e:
            # Friendly handling for missing user vs generic errors
            err_str = str(e)
            if "User not found" in err_str:
                reply_text = (
                    "❌ Error loading progress: You are not registered.\n"
                    "Please send /start to register and try again."
                )
            else:
                reply_text = f"❌ Error loading progress: {err_str}\nPlease try again later."

            await message.answer(
                reply_text,
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )


@router.callback_query(F.data == "progress_overview")
async def progress_overview_callback(callback: types.CallbackQuery, state: FSMContext,
                                    has_active_subscription: bool = False):
    """
    Show progress overview (same as /progress).
    
    FIX: Use safe_edit_message to prevent 'message is not modified' errors.
    """
    user_id = callback.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        attempt_repo = AttemptRepository(session)
        question_repo = QuestionRepository(session)
        
        user_service = UserService(user_repo, payment_repo, attempt_repo, question_repo)
        
        try:
            profile = await user_service.get_user_profile(user_id)
            
            progress_msg = (
                f"📊 *Your Learning Progress*\n\n"
                f"👤 Student: {profile.get('name', 'User')}\n"
                f"📅 Member since: {profile.get('created_at', datetime.now()).strftime('%d %b %Y')}\n\n"
            )
            
            stats = profile.get('stats', {})
            if stats:
                progress_msg += (
                    f"📈 *Overall Statistics:*\n"
                    f"• Total attempts: {stats.get('total_attempts', 0)}\n"
                    f"• Correct answers: {stats.get('total_correct', 0)}\n"
                    f"• Average accuracy: {stats.get('avg_accuracy', 0)}%\n"
                    f"• Time spent: {format_time(stats.get('total_time_spent', 0))}\n\n"
                )
            
            # Add subscription info
            subscription = profile.get('subscription')
            if subscription:
                status_emoji = "✅" if subscription.get('active') else "❌"
                progress_msg += (
                    f"{status_emoji} *Subscription:*\n"
                    f"• Days remaining: {subscription.get('days_left', 0)}\n\n"
                )
            elif has_active_subscription:
                progress_msg += (
                    f"✅ *Subscription:*\n"
                    f"• Status: Active\n\n"
                )
            else:
                progress_msg += (
                    f"❌ *Subscription:*\n"
                    f"• Status: No active subscription\n"
                    f"• Access: Simple level only\n\n"
                )
            
            progress_msg += "Choose an option below:"
            
            await safe_edit_message(
                callback.message,
                progress_msg,
                new_markup=MainMenuKeyboard.get_progress_options_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            err_str = str(e)
            if "User not found" in err_str:
                reply_text = (
                    "❌ Error loading progress: You are not registered.\n"
                    "Please send /start to register and try again."
                )
            else:
                reply_text = f"❌ Error loading progress: {err_str}"

            await safe_edit_message(
                callback.message,
                reply_text,
                new_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(F.data == "progress_daily")
async def daily_progress_callback(callback: types.CallbackQuery, state: FSMContext,
                                 has_active_subscription: bool = False):
    """Show daily progress statistics"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        attempt_repo = AttemptRepository(session)
        question_repo = QuestionRepository(session)
        
        user_service = UserService(user_repo, payment_repo, attempt_repo, question_repo)
        
        try:
            daily_progress = await user_service.get_daily_progress(user_id)
            today = daily_progress.get('date', datetime.now().date())
            
            daily_msg = (
                f"📅 *Daily Progress - {today.strftime('%d %b %Y')}*\n\n"
                f"📊 *Today's Activity:*\n"
                f"• Questions attempted: {daily_progress.get('attempts', 0)}\n"
                f"• Correct answers: {daily_progress.get('correct', 0)}\n"
                f"• Accuracy: {daily_progress.get('accuracy', 0)}%\n"
                f"• Quizzes taken: {daily_progress.get('quiz_count', 0)}\n"
                f"• Remaining quizzes: {daily_progress.get('remaining_quizzes', 0)}\n\n"
                f"🎯 *Daily Goal:*\n"
                f"• Target: 10 questions/day\n"
                f"• Status: {'✅ Achieved' if daily_progress.get('attempts', 0) >= 10 else '📊 In Progress'}\n\n"
                f"Keep up the good work! Consistency is key to improvement. 💪"
            )
            
            await safe_edit_message(
                callback.message,
                daily_msg,
                new_markup=MainMenuKeyboard.get_progress_options_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await safe_edit_message(
                callback.message,
                f"❌ Error loading daily progress: {str(e)}",
                new_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(F.data == "progress_weak")
async def weak_areas_callback(callback: types.CallbackQuery, state: FSMContext,
                             has_active_subscription: bool = False):
    """Show weak areas needing improvement"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        try:
            weak_chapters = await question_repo.get_weak_chapters(user_id, limit=10)
            
            if not weak_chapters:
                weak_msg = (
                    f"✅ *No Weak Areas Identified!*\n\n"
                    f"Great job! You don't have any identified weak areas yet.\n\n"
                    f"Keep practicing and the system will identify areas "
                    f"where you can improve as you answer more questions."
                )
                
                await safe_edit_message(
                    callback.message,
                    weak_msg,
                    new_markup=MainMenuKeyboard.get_progress_options_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                weak_msg = (
                    f"📚 *Areas Needing Improvement*\n\n"
                    f"Based on your performance, here are areas where you can focus:\n\n"
                )
                
                for i, chapter in enumerate(weak_chapters, 1):
                    accuracy = chapter.get('accuracy', 0)
                    progress_bar = generate_progress_bar(accuracy)
                    difficulty_emoji = {
                        'simple': EMOJIS['easy'],
                        'medium': EMOJIS['medium'],
                        'hard': EMOJIS['hard']
                    }.get(chapter.get('difficulty', 'simple'), '')
                    
                    weak_msg += (
                        f"{i}. *{chapter.get('subject_name', 'Unknown')} - {chapter.get('chapter_name', 'Unknown')}*\n"
                        f"   {difficulty_emoji} {chapter.get('difficulty', '').capitalize()} | "
                        f"Accuracy: {progress_bar}\n\n"
                    )
                
                weak_msg += (
                    f"💡 *Recommendations:*\n"
                    f"• Practice these chapters more\n"
                    f"• Start with Simple difficulty\n"
                    f"• Review explanations carefully\n"
                )
                
                # Use the proper weak areas keyboard that handles practice callbacks
                keyboard = QuizKeyboard.get_weak_areas_keyboard(weak_chapters)
                
                await safe_edit_message(
                    callback.message,
                    weak_msg,
                    new_markup=keyboard,
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            await safe_edit_message(
                callback.message,
                f"❌ Error loading weak areas: {str(e)}",
                new_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(F.data == "progress_recommendations")
async def learning_recommendations_callback(callback: types.CallbackQuery, state: FSMContext,
                                            has_active_subscription: bool = False):
    """Show personalized learning recommendations"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        user_repo = UserRepository(session)
        
        quiz_service = QuizService(question_repo, attempt_repo, user_repo)
        
        try:
            recommendation = await quiz_service.get_recommended_quiz(user_id)
            
            if not recommendation:
                rec_msg = (
                    f"🎯 *Personalized Recommendations*\n\n"
                    f"Start your learning journey! We recommend:\n\n"
                    f"1. Begin with Simple difficulty quizzes\n"
                    f"2. Try different subjects and chapters\n"
                    f"3. Aim for at least 5 quizzes per week\n"
                    f"4. Review explanations for wrong answers\n\n"
                    f"Tap 'Start Quiz' to begin!"
                )
                
                await safe_edit_message(
                    callback.message,
                    rec_msg,
                    new_markup=MainMenuKeyboard.get_progress_options_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                difficulty_emoji = {
                    'simple': EMOJIS['easy'],
                    'medium': EMOJIS['medium'],
                    'hard': EMOJIS['hard']
                }.get(recommendation.get('difficulty', 'simple'), '')
                
                rec_msg = (
                    f"🎯 *Recommended Next Quiz*\n\n"
                    f"Based on your learning pattern, we recommend:\n\n"
                    f"📚 *Subject:* {recommendation.get('subject_name', 'Unknown')}\n"
                    f"📖 *Chapter:* {recommendation.get('chapter_name', 'Unknown')}\n"
                    f"{difficulty_emoji} *Difficulty:* {recommendation.get('difficulty', '').capitalize()}\n\n"
                    f"💡 *Why this recommendation?*\n"
                    f"{recommendation.get('reason', 'Keep practicing to improve!')}\n\n"
                    f"Tap below to start this quiz!"
                )
                
                # Use the proper start recommended keyboard with correct callback format
                keyboard = QuizKeyboard.get_start_recommended_keyboard(
                    subject_id=recommendation.get('subject_id', 0),
                    chapter_id=recommendation.get('chapter_id', 0),
                    difficulty=recommendation.get('difficulty', 'simple')
                )
                
                await safe_edit_message(
                    callback.message,
                    rec_msg,
                    new_markup=keyboard,
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            await safe_edit_message(
                callback.message,
                f"❌ Error loading recommendations: {str(e)}",
                new_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_chapter_progress_"))
async def view_chapter_progress(callback: types.CallbackQuery):
    """View detailed progress for a specific chapter"""
    parts = callback.data.split("_")
    if len(parts) != 5:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    subject_id = int(parts[3])
    chapter_id = int(parts[4])
    
    await callback.answer(
        "Chapter progress details feature coming soon!",
        show_alert=True
    )


@router.callback_query(F.data == "learning_path")
async def learning_path_callback(callback: types.CallbackQuery, state: FSMContext,
                                has_active_subscription: bool = False):
    """Show personalized learning path"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        attempt_repo = AttemptRepository(session)
        question_repo = QuestionRepository(session)
        
        user_service = UserService(user_repo, payment_repo, attempt_repo, question_repo)
        
        try:
            learning_path = await user_service.get_learning_path(user_id)
            
            if not learning_path:
                path_msg = (
                    f"🛣️ *Personalized Learning Path*\n\n"
                    f"Start your learning journey with these steps:\n\n"
                    f"1. Complete 5 Simple difficulty quizzes\n"
                    f"2. Achieve 80% accuracy in 3 different chapters\n"
                    f"3. Try Medium difficulty in your best subject\n"
                    f"4. Practice daily for consistent improvement\n\n"
                    f"Start with your first quiz today!"
                )
            else:
                path_msg = (
                    f"🛣️ *Your Learning Path*\n\n"
                    f"Recommended order for optimal learning:\n\n"
                )
                
                for i, step in enumerate(learning_path[:5], 1):
                    status_emoji = {
                        'not_started': '🔘',
                        'needs_improvement': '🔄',
                        'good': '✅',
                        'mastered': '🏆'
                    }.get(step.get('status', 'not_started'), '🔘')
                    
                    priority_emoji = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(step.get('priority', 'medium'), '⚪')
                    
                    path_msg += (
                        f"{i}. {status_emoji} {priority_emoji} "
                        f"*{step.get('subject', 'Unknown')} - {step.get('chapter', 'Unknown')}*\n"
                        f"   Status: {step.get('status', '').replace('_', ' ').title()}\n"
                        f"   Recommended: {step.get('recommended_difficulty', '').capitalize()}\n"
                    )
                    
                    if step.get('accuracy'):
                        path_msg += f"   Accuracy: {step['accuracy']:.1f}%\n"
                    
                    path_msg += "\n"
                
                path_msg += (
                    f"💡 *Tips:*\n"
                    f"• Follow the recommended order\n"
                    f"• Focus on high priority areas first\n"
                    f"• Review explanations carefully\n"
                )
            
            await safe_edit_message(
                callback.message,
                path_msg,
                new_markup=MainMenuKeyboard.get_progress_options_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await safe_edit_message(
                callback.message,
                f"❌ Error loading learning path: {str(e)}",
                new_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()

