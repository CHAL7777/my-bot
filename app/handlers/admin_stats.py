"""
Admin Stats Handler - Telegram Quiz Bot
Plain text version - stats dashboard, leaderboard, bot settings
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.admin import (
    AdminKeyboard, AdminStatsKeyboard, AdminSettingsKeyboard
)
from app.utils.constants import EMOJIS
from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.repositories.admin_log_repo import AdminLogRepository
from app.services.analytics_service import AnalyticsService
from app.services.payment_service import PaymentService
from app.utils.plain_sender import PlainTextMessageSender  # Changed to plain text sender

router = Router()

# FSM States for stats and settings
class StatsStates(StatesGroup):
    """FSM states for stats and settings operations"""
    waiting_for_time_limit = State()
    waiting_for_passing_score = State()
    waiting_for_broadcast = State()
    waiting_for_broadcast_confirm = State()


# ============== Utility Functions ==============

async def log_admin_action(admin_id: int, action: str, details: str = None):
    """Log admin action to database"""
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        await log_repo.log_action(admin_id, action, details)


def _get_plain_sender(update) -> PlainTextMessageSender:
    """Get PlainTextMessageSender instance from update"""
    if isinstance(update, types.CallbackQuery):
        return PlainTextMessageSender(update.bot)
    elif isinstance(update, types.Message):
        return PlainTextMessageSender(update.bot)
    else:
        raise ValueError(f"Unsupported update type: {type(update)}")


# ============== Main Menu Handlers ==============

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show stats menu in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['score']} Statistics & Analytics",
            "",
            "Choose a category to view:"
        ]),
        reply_markup=AdminStatsKeyboard.get_stats_menu()
    )
    await callback.answer()


# ============== Dashboard Overview ==============

@router.callback_query(F.data == "admin_stats_dashboard")
async def admin_stats_dashboard_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show dashboard overview in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        user_repo = UserRepository(session)
        question_repo = QuestionRepository(session)
        attempt_repo = AttemptRepository(session)
        payment_repo = PaymentRepository(session)
        
        analytics_service = AnalyticsService(
            user_repo, question_repo, attempt_repo, payment_repo
        )
        
        try:
            stats = await analytics_service.get_dashboard_stats()
            
            # Build message with lists
            lines = [
                f"{EMOJIS['dashboard']} Dashboard Overview",
                "",
                f"📅 Last Updated: {stats['timestamp'].strftime('%d %b %Y %H:%M')}",
                "",
                "👥 Users:",
                f"• Total: {stats.get('users', {}).get('total', 'N/A')}",
                f"• Active (7 days): {stats.get('users', {}).get('active', 'N/A')}",
                f"• Retention: {stats.get('users', {}).get('retention_rate', 'N/A')}%",
                "",
                "❓ Questions:",
                f"• Total: {stats.get('questions', {}).get('total', 'N/A')}",
                f"• Simple: {stats.get('questions', {}).get('by_difficulty', {}).get('simple', 0)}",
                f"• Medium: {stats.get('questions', {}).get('by_difficulty', {}).get('medium', 0)}",
                f"• Hard: {stats.get('questions', {}).get('by_difficulty', {}).get('hard', 0)}",
                "",
                "💰 Revenue (30 days):",
                f"• Total: birr{stats.get('revenue', {}).get('total_revenue', 0):.2f}",
                f"• Payments: {stats.get('revenue', {}).get('payment_count', 0)}",
                f"• Avg: birr{stats.get('revenue', {}).get('avg_revenue_per_payment', 0):.2f}",
                ""
            ]
            
            # Add health score
            health = stats.get('health_score', 0)
            health_emoji = "🟢" if health > 70 else "🟡" if health > 40 else "🔴"
            lines.append(f"{health_emoji} Health Score: {health}/100")
            
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            
        except Exception as e:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    "❌ Error Loading Dashboard",
                    "",
                    "Please try again later."
                ]),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await callback.answer()


# ============== User Statistics ==============

@router.callback_query(F.data == "admin_stats_users")
async def admin_stats_users_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show user statistics in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        user_repo = UserRepository(session)
        
        all_users = await user_repo.get_all_users(limit=500)
        total_users = len(all_users)
        
        # Calculate stats
        blocked = sum(1 for u in all_users if u.blocked)
        unblocked = total_users - blocked
        
        approved = sum(1 for u in all_users if u.approved)
        pending = sum(1 for u in all_users if not u.approved)
        
        # Activity stats
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_7_days = sum(1 for u in all_users if u.created_at and u.created_at > week_ago)
        
        # Build message with lists
        lines = [
            f"{EMOJIS['users']} User Statistics",
            "",
            "📊 Overview:",
            f"• Total Users: {total_users}",
            f"• Active (unblocked): {unblocked}",
            f"• Blocked: {blocked}",
            "",
            "✅ Approval:",
            f"• Approved: {approved}",
            f"• Pending: {pending}",
            "",
            "📅 Activity:",
            f"• New (7 days): {active_7_days}"
        ]
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
    
    await callback.answer()


# ============== Question Statistics ==============

@router.callback_query(F.data == "admin_stats_questions")
async def admin_stats_questions_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show question statistics in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        total = await question_repo.get_question_count()
        simple = await question_repo.get_question_count(difficulty='simple')
        medium = await question_repo.get_question_count(difficulty='medium')
        hard = await question_repo.get_question_count(difficulty='hard')
        
        subjects = await question_repo.get_subjects()
        
        # Build message with lists
        lines = [
            f"{EMOJIS['questions']} Question Statistics",
            "",
            "📊 Overview:",
            f"• Total Questions: {total}",
            "",
            "📈 By Difficulty:",
            f"• Simple: {simple} ({simple/total*100:.1f}%)",
            f"• Medium: {medium} ({medium/total*100:.1f}%)",
            f"• Hard: {hard} ({hard/total*100:.1f}%)",
            "",
            "📚 Subjects:"
        ]
        
        for subject in subjects:
            count = await question_repo.get_question_count(subject_id=subject.subject_id)
            lines.append(f"• {subject.subject_name}: {count}")
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
    
    await callback.answer()


# ============== Quiz Statistics ==============

@router.callback_query(F.data == "admin_stats_quizzes")
async def admin_stats_quizzes_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show quiz statistics with real data in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        attempt_repo = AttemptRepository(session)
        analytics_service = AnalyticsService(
            user_repo=None,
            question_repo=None,
            attempt_repo=attempt_repo,
            payment_repo=None
        )
        
        try:
            # Get comprehensive quiz statistics
            quiz_stats = await analytics_service.get_quiz_statistics(days=30)
            popular_times = await analytics_service.get_popular_times(days=30)
            
            if 'error' in quiz_stats:
                raise Exception(quiz_stats['error'])
            
            # Extract data
            overview = quiz_stats.get('overview', {})
            today = quiz_stats.get('today', {})
            trends = quiz_stats.get('trends', {})
            
            # Format popular times
            periods = popular_times.get('periods', {})
            morning_count = periods.get('morning', {}).get('count', 0)
            morning_pct = periods.get('morning', {}).get('percentage', 0)
            afternoon_count = periods.get('afternoon', {}).get('count', 0)
            afternoon_pct = periods.get('afternoon', {}).get('percentage', 0)
            evening_count = periods.get('evening', {}).get('count', 0)
            evening_pct = periods.get('evening', {}).get('percentage', 0)
            
            # Format trends
            attempt_trend = trends.get('attempt_trend', {})
            attempt_direction = attempt_trend.get('direction', 'stable')
            attempt_change = attempt_trend.get('change_percent', 0)
            trend_emoji = "📈" if attempt_direction == 'up' else "📉" if attempt_direction == 'down' else "➡️"
            
            # Build message with lists
            lines = [
                f"{EMOJIS['score']} Quiz Statistics",
                "",
                "📊 Overview:",
                f"• Total Quiz Attempts: {overview.get('total_attempts', 0):,d}",
                f"• Correct Answers: {overview.get('correct_attempts', 0):,} ({overview.get('accuracy', 0)}%)",
                f"• Avg Time: {overview.get('avg_time_seconds', 0):.1f}s",
                f"• Quiz Sessions: {overview.get('total_sessions', 0):,d}",
                f"• Active Users (30d): {overview.get('active_users_period', 0)}",
                "",
                "📅 Today:",
                f"• Attempts: {today.get('attempts', 0)}",
                f"• Accuracy: {today.get('accuracy', 0)}%",
                "",
                "🕐 Popular Times:",
                f"• Morning (6-12): {morning_count:,} ({morning_pct}%)",
                f"• Afternoon (12-18): {afternoon_count:,} ({afternoon_pct}%)",
                f"• Evening (18-24): {evening_count:,} ({evening_pct}%)",
                "",
                f"{trend_emoji} Trend (vs previous period):",
                f"• Attempts: {attempt_change:+.1f}%",
                f"• Direction: {attempt_direction.capitalize()}"
            ]
            
            # Add peak hour if available
            peak_hour = popular_times.get('peak_hour')
            if peak_hour:
                lines.append(f"")
                lines.append(f"⏰ Peak Hour: {peak_hour}")
            
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(lines),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            
        except Exception as e:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    "❌ Error Loading Quiz Statistics",
                    "",
                    "Please try again later."
                ]),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await callback.answer()


# ============== Revenue Statistics ==============

@router.callback_query(F.data == "admin_stats_revenue")
async def admin_stats_revenue_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show revenue statistics in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        # 30 days revenue
        revenue_30 = await payment_service.get_revenue_analytics(days=30)
        revenue_7 = await payment_service.get_revenue_analytics(days=7)
        
        all_users = await user_repo.get_all_users(limit=500)
        total_users = len(all_users)
        
        # Build message with lists
        lines = [
            f"{EMOJIS['money']} Revenue Statistics",
            "",
            "📊 Last 30 Days:",
            f"• Total Revenue: birr {revenue_30.get('total_revenue', 0):.2f}",
            f"• Payments: {revenue_30.get('payment_count', 0)}",
            f"• Average: birr {revenue_30.get('avg_revenue_per_payment', 0):.2f}",
            "",
            "📊 Last 7 Days:",
            f"• Total Revenue: birr {revenue_7.get('total_revenue', 0):.2f}",
            f"• Payments: {revenue_7.get('payment_count', 0)}",
            "",
            "💰 Conversion:",
            f"• Total Users: {total_users}",
            f"• Conversion Rate: {revenue_30.get('payment_count', 0)/total_users*100:.1f}%"
        ]
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
    
    await callback.answer()


# ============== Leaderboard ==============

@router.callback_query(F.data == "admin_stats_leaderboard")
async def admin_stats_leaderboard_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show leaderboard options in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['trophy']} Leaderboard",
            "",
            "Select a time period:"
        ]),
        reply_markup=AdminStatsKeyboard.get_leaderboard_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("leaderboard_"))
async def leaderboard_period_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show leaderboard for selected period in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    period = callback.data.split("_")[-1]  # daily, weekly, monthly, overall
    
    period_names = {
        'daily': 'Today',
        'weekly': 'This Week',
        'monthly': 'This Month',
        'overall': 'All Time'
    }
    
    async for session in get_db():
        leaderboard_repo = LeaderboardRepository(session)
        user_repo = UserRepository(session)
        
        # Get leaderboard entries
        entries = await leaderboard_repo.get_leaderboard(period, limit=10)
        
        # Build message with lists
        lines = [
            f"{EMOJIS['trophy']} Top 10 Leaderboard",
            f"📅 {period_names.get(period, period)}",
            ""
        ]
        
        if not entries:
            lines.append("📭 No leaderboard data available yet.")
        else:
            for i, entry in enumerate(entries, 1):
                user = await user_repo.get_user(entry.user_id)
                username = f"@{user.username}" if user.username else f"User {entry.user_id}"
                
                if i == 1:
                    emoji = "🥇"
                elif i == 2:
                    emoji = "🥈"
                elif i == 3:
                    emoji = "🥉"
                else:
                    emoji = f"{i}."
                
                lines.append(f"{emoji} {username}")
                lines.append(f"   Score: {entry.total_score} | Accuracy: {entry.total_accuracy:.1f}% | Questions: {entry.total_questions}")
                lines.append("")
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminStatsKeyboard.get_leaderboard_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "admin_leaderboard_clear")
async def admin_leaderboard_clear_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show clear leaderboard confirmation in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['warning']} Clear Leaderboard",
            "",
            "⚠️ Warning: This will delete all leaderboard data!",
            "",
            "This action cannot be undone.",
            "",
            "Confirm clear?"
        ]),
        reply_markup=AdminStatsKeyboard.get_clear_leaderboard_confirmation()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_clear_leaderboard")
async def confirm_clear_leaderboard_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Confirm and clear leaderboard in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        from sqlalchemy import delete
        from app.db.models import Leaderboard
        
        await session.execute(delete(Leaderboard))
        await session.commit()
        
        await log_admin_action(
            callback.from_user.id,
            "Clear Leaderboard",
            "Cleared all leaderboard data"
        )
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "✅ Leaderboard Cleared",
            "",
            "All leaderboard data has been deleted.",
            "New entries will be added as users take quizzes."
        ]),
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_clear_leaderboard")
async def cancel_clear_leaderboard_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Cancel clear leaderboard in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "◀️ Clear Cancelled",
            "",
            "The leaderboard was not cleared."
        ]),
        reply_markup=AdminStatsKeyboard.get_leaderboard_keyboard()
    )
    await callback.answer()


# ============== Settings ==============

@router.callback_query(F.data == "admin_settings")
async def admin_settings_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show settings menu in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['settings']} Bot Settings",
            "",
            "Choose a setting to configure:"
        ]),
        reply_markup=AdminSettingsKeyboard.get_settings_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings_time_limit")
async def admin_settings_time_limit_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show quiz time limit options in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "⏱️ Quiz Time Limit",
            "",
            "Set the time limit per question:",
            "",
            "Current default: 30 seconds"
        ]),
        reply_markup=AdminSettingsKeyboard.get_time_limit_options()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("time_limit_"))
async def time_limit_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle time limit selection in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    limit = callback.data.split("_")[-1]
    
    if limit == "custom":
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join([
                "⏱️ Custom Time Limit",
                "",
                "Enter the time limit in seconds (10-120):"
            ])
        )
        
        await sender.send_message(
            callback.message.chat.id,
            "Type the number of seconds:"
        )
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "✅ Time Limit Updated",
            "",
            f"Quiz time limit set to {limit} seconds.",
            "",
            "💡 This will be the default for all new quizzes."
        ]),
        reply_markup=AdminSettingsKeyboard.get_settings_menu()
    )
    
    await log_admin_action(
        callback.from_user.id,
        "Update Settings",
        f"Set time limit to {limit} seconds"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings_passing_score")
async def admin_settings_passing_score_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show passing score options in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "📊 Passing Score",
            "",
            "Set the minimum score required to pass a quiz:",
            "",
            "Current default: 60%"
        ]),
        reply_markup=AdminSettingsKeyboard.get_passing_score_options()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("passing_score_"))
async def passing_score_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle passing score selection in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    score = callback.data.split("_")[-1]
    
    if score == "custom":
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join([
                "📊 Custom Passing Score",
                "",
                "Enter the passing score percentage (0-100):"
            ])
        )
        
        await sender.send_message(
            callback.message.chat.id,
            "Type the percentage:"
        )
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "✅ Passing Score Updated",
            "",
            f"Passing score set to {score}%.",
            "",
            f"💡 Users need at least {score}% correct to pass."
        ]),
        reply_markup=AdminSettingsKeyboard.get_settings_menu()
    )
    
    await log_admin_action(
        callback.from_user.id,
        "Update Settings",
        f"Set passing score to {score}%"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings_broadcast")
async def admin_settings_broadcast_callback(callback: types.CallbackQuery, state: FSMContext,
                                              is_admin: bool = False):
    """Start broadcast message in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        user_repo = UserRepository(session)
        users = await user_repo.get_all_users(limit=500)
        unblocked_users = [u for u in users if not u.blocked]
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['message']} Broadcast Message",
            "",
            f"📊 Target: {len(unblocked_users)} active users",
            "",
            "Enter the message to send to all users:",
            "",
            "💡 Tips:",
            "• Keep it under 1000 characters",
            "• Don't include sensitive info"
        ])
    )
    
    await state.set_state(StatsStates.waiting_for_broadcast)
    await callback.answer()


@router.message(StateFilter(StatsStates.waiting_for_broadcast))
async def handle_broadcast_message(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Handle broadcast message input in plain text"""
    sender = _get_plain_sender(message)
    
    if not is_admin:
        return
    
    message_text = message.text
    
    if len(message_text) > 1000:
        await sender.send_message(
            message.chat.id,
            "❌ Message is too long (max 1000 characters). Please try again:"
        )
        return
    
    # Show preview with lists
    lines = [
        "📨 Broadcast Preview",
        "",
        "Message:",
        message_text,
        "",
        f"📊 Will be sent to: All active users"
    ]
    
    await sender.send_message(
        message.chat.id,
        "\n".join(lines),
        reply_markup=AdminSettingsKeyboard.get_broadcast_preview_keyboard(message_text)
    )
    
    await state.update_data(broadcast_message=message_text)
    await state.set_state(StatsStates.waiting_for_broadcast_confirm)


@router.callback_query(F.data == "confirm_broadcast_send")
async def confirm_broadcast_send_callback(callback: types.CallbackQuery, state: FSMContext,
                                            is_admin: bool = False):
    """Confirm and send broadcast in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    data = await state.get_data()
    message_text = data.get('broadcast_message')
    
    if not message_text:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join([
                "❌ No message found. Please try again."
            ]),
            reply_markup=AdminSettingsKeyboard.get_settings_menu()
        )
        await state.clear()
        await callback.answer()
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['loading']} Sending Broadcast...",
            "",
            "Please wait while the message is sent to all users."
        ])
    )
    
    async for session in get_db():
        user_repo = UserRepository(session)
        users = await user_repo.get_all_users(limit=500)
        unblocked_users = [u for u in users if not u.blocked]
    
    sent_count = 0
    failed_count = 0
    
    # Send to each user
    for user in unblocked_users:
        try:
            await sender.send_message(
                chat_id=user.user_id,
                text=f"📢 Broadcast Message\n\n{message_text}"
            )
            sent_count += 1
        except Exception:
            failed_count += 1
            # Continue sending to other users
    
    # Log action
    await log_admin_action(
        callback.from_user.id,
        "Broadcast Message",
        f"Sent to {sent_count} users, {failed_count} failed"
    )
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "✅ Broadcast Complete",
            "",
            f"• Sent: {sent_count}",
            f"• Failed: {failed_count}",
            f"• Total: {len(unblocked_users)}"
        ]),
        reply_markup=AdminSettingsKeyboard.get_settings_menu()
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "confirm_broadcast_edit")
async def confirm_broadcast_edit_callback(callback: types.CallbackQuery, state: FSMContext,
                                           is_admin: bool = False):
    """Edit broadcast message in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "✏️ Edit Message",
            "",
            "Enter the new message:"
        ])
    )
    
    await sender.send_message(
        callback.message.chat.id,
        "Type your message:"
    )
    
    await state.set_state(StatsStates.waiting_for_broadcast)
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast_callback(callback: types.CallbackQuery, state: FSMContext,
                                     is_admin: bool = False):
    """Cancel broadcast in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            "◀️ Broadcast Cancelled",
            "",
            "The message was not sent."
        ]),
        reply_markup=AdminSettingsKeyboard.get_settings_menu()
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin_settings_other")
async def admin_settings_other_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show other settings in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Build message with lists
    lines = [
        f"{EMOJIS['settings']} Other Settings",
        "",
        "📋 Available Settings:",
        "• Quiz time limit (see above)",
        "• Passing score (see above)",
        "• Daily quiz limit",
        "• Questions per quiz",
        "• Subscription prices",
        "",
        "💡 Note:",
        "These settings can be configured via:",
        "• Environment variables",
        "• Database configuration",
        "• Admin panel (coming soon)"
    ]
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
        reply_markup=AdminSettingsKeyboard.get_settings_menu()
    )
    await callback.answer()