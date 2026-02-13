"""
Admin Users Handler - Telegram Quiz Bot
Plain text version - Manage users: view, approve, block/unblock, search

FIXED: Added referral counting when admin approves a user
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.admin import (
    AdminKeyboard, AdminUsersKeyboard
)
from app.utils.constants import EMOJIS
from app.config import settings
from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.admin_log_repo import AdminLogRepository
from app.services.referral_service import ReferralService
from app.utils.plain_sender import PlainTextMessageSender

router = Router()

# FSM States for user management
class UserStates(StatesGroup):
    """FSM states for user management operations"""
    waiting_for_search_term = State()
    waiting_for_user_id = State()
    waiting_for_broadcast_message = State()


# ============== Utility Functions ==============

async def log_admin_action(admin_id: int, action: str, details: str = None):
    """Log admin action to database"""
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        await log_repo.log_action(admin_id, action, details)


async def get_user_stats_text() -> str:
    """Get user statistics as formatted text in plain text"""
    async for session in get_db():
        user_repo = UserRepository(session)
        
        all_users = await user_repo.get_all_users()
        total_users = len(all_users)
        
        # Get counts
        blocked_count = sum(1 for u in all_users if u.blocked)
        unblocked_count = total_users - blocked_count
        
        # Active users (joined in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users = sum(1 for u in all_users if u.created_at and u.created_at > week_ago)
        
        # Approved users
        approved_count = sum(1 for u in all_users if u.approved)
        pending_approval = sum(1 for u in all_users if not u.approved)
        
        # Build message with lists
        lines = [
            f"{EMOJIS['user']} User Statistics",
            "",
            "📊 Overview:",
            f"• Total Users: {total_users}",
            f"• Active (unblocked): {unblocked_count}",
            f"• Blocked: {blocked_count}",
            "",
            "📅 Activity:",
            f"• New (7 days): {new_users}",
            "",
            "✅ Approval Status:",
            f"• Approved: {approved_count}",
            f"• Pending: {pending_approval}"
        ]
        
        return "\n".join(lines)


def _get_plain_sender(update) -> PlainTextMessageSender:
    """Get PlainTextMessageSender instance from update"""
    if isinstance(update, types.CallbackQuery):
        return PlainTextMessageSender(update.bot)
    elif isinstance(update, types.Message):
        return PlainTextMessageSender(update.bot)
    else:
        raise ValueError(f"Unsupported update type: {type(update)}")


# ============== Main Menu Handlers ==============

@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show user management menu in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['user']} User Management",
            "",
            "Choose an option to manage users:"
        ]),
        reply_markup=AdminUsersKeyboard.get_user_management()
    )
    await callback.answer()


# ============== View Users ==============

@router.callback_query(F.data == "admin_users_list")
async def admin_users_list_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show list of all users in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        user_repo = UserRepository(session)
        users = await user_repo.get_all_users(limit=100)
    
    if not users:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join([
                f"{EMOJIS['warning']} No Users Found",
                "",
                "There are no users in the database yet."
            ]),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['list']} Users List",
            "",
            f"Total users: {len(users)}",
            "",
            "Select a user to view or manage:"
        ]),
        reply_markup=AdminUsersKeyboard.get_users_list_keyboard(users)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users_page_"))
async def admin_users_page_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle pagination for users list in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    page = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        users = await user_repo.get_all_users(limit=100)
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['list']} Users List",
            "",
            f"Total users: {len(users)}",
            "",
            "Select a user:"
        ]),
        reply_markup=AdminUsersKeyboard.get_users_list_keyboard(users, page=page)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users_stats")
async def admin_users_stats_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show user statistics in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    stats_text = await get_user_stats_text()
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        stats_text,
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== View Single User ==============

@router.callback_query(F.data.startswith("admin_user_view_"))
async def admin_user_view_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View a specific user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        
        user = await user_repo.get_user(user_id)
        
        if not user:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        # Get user statistics
        stats = await user_repo.get_user_statistics(user_id)
        
        # Get subscription status
        subscription = await payment_repo.get_active_subscription(user_id)
        
        # Get payment history
        payments = await payment_repo.get_user_payments(user_id)
        
        # Build message with lists
        lines = [
            f"{EMOJIS['user']} User Profile",
            "",
            f"ID: {user.user_id}",
            f"Username: @{user.username if user.username else 'N/A'}",
            f"Name: {user.first_name or ''} {user.last_name or ''}".strip(),
            f"Role: {user.role.capitalize()}",
            f"Status: {'🚫 Blocked' if user.blocked else '✅ Active'}",
            f"Approved: {'✅ Yes' if user.approved else '⏳ Pending'}",
            f"Joined: {user.created_at.strftime('%d %b %Y') if user.created_at else 'N/A'}",
            "",
            f"{EMOJIS['stats']} Statistics:",
            f"• Total Attempts: {stats['total_attempts']}",
            f"• Correct: {stats['total_correct']}",
            f"• Accuracy: {stats['avg_accuracy']}%",
            f"• Time Spent: {stats['total_time_spent']}s"
        ]
        
        if subscription:
            lines.extend([
                "",
                f"{EMOJIS['trophy']} Subscription:",
                f"• Status: {subscription.status.capitalize()}",
                f"• Ends: {subscription.end_date.strftime('%d %b %Y')}"
            ])
        else:
            lines.extend([
                "",
                f"{EMOJIS['warning']} No Active Subscription"
            ])
        
        lines.extend([
            "",
            f"💰 Payments: {len(payments)} total"
        ])
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminUsersKeyboard.get_user_action_keyboard(user_id, user.blocked)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_stats_"))
async def admin_user_stats_detail_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View detailed statistics for a specific user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        
        user = await user_repo.get_user(user_id)
        if not user:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        stats = await user_repo.get_user_statistics(user_id)
        progress = await user_repo.get_user_progress(user_id)
        
        username_display = f"@{user.username}" if user.username else f"ID: {user.user_id}"
        
        # Build message with lists
        lines = [
            f"{EMOJIS['stats']} User Statistics",
            "",
            f"User: {username_display}",
            "",
            "📊 Performance:",
            f"• Total Attempts: {stats['total_attempts']}",
            f"• Correct Answers: {stats['total_correct']}",
            f"• Accuracy: {stats['avg_accuracy']}%",
            f"• Success Rate: {stats['success_rate']}%",
            f"• Total Time: {stats['total_time_spent']} seconds"
        ]
        
        if progress:
            lines.extend([
                "",
                f"📚 Subjects Attempted: {len(progress)}"
            ])
            for p in progress[:5]:
                lines.append(f"• Subject {p.subject_id} ({p.difficulty}): {p.accuracy:.1f}%")
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminUsersKeyboard.get_user_action_keyboard(user_id, user.blocked)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_progress_"))
async def admin_user_progress_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View progress for a specific user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        
        user = await user_repo.get_user(user_id)
        if not user:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        progress = await user_repo.get_user_progress(user_id)
        
        if not progress:
            username_display = f"@{user.username}" if user.username else f"ID: {user.user_id}"
            
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    f"{EMOJIS['warning']} No Progress Data",
                    "",
                    f"User {username_display} has not attempted any questions yet."
                ]),
                reply_markup=AdminUsersKeyboard.get_user_action_keyboard(user_id, user.blocked)
            )
            await callback.answer()
            return
        
        username_display = f"@{user.username}" if user.username else f"ID: {user.user_id}"
        
        # Build message with lists
        lines = [
            f"{EMOJIS['progress']} User Progress",
            "",
            f"User: {username_display}",
            f"Subjects: {len(progress)}",
            ""
        ]
        
        for p in progress:
            lines.extend([
                f"📚 Subject #{p.subject_id} ({p.difficulty}):",
                f"• Attempts: {p.total_attempts}",
                f"• Correct: {p.correct_attempts}",
                f"• Accuracy: {p.accuracy:.1f}%",
                f"• Time: {p.total_time_spent}s",
                ""
            ])
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminUsersKeyboard.get_user_action_keyboard(user_id, user.blocked)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_payments_"))
async def admin_user_payments_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View payments for a specific user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        
        user = await user_repo.get_user(user_id)
        if not user:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        payments = await payment_repo.get_user_payments(user_id)
        
        if not payments:
            username_display = f"@{user.username}" if user.username else f"ID: {user.user_id}"
            
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    f"{EMOJIS['warning']} No Payment History",
                    "",
                    f"User {username_display} has no payment records."
                ]),
                reply_markup=AdminUsersKeyboard.get_user_action_keyboard(user_id, user.blocked)
            )
            await callback.answer()
            return
        
        username_display = f"@{user.username}" if user.username else f"ID: {user.user_id}"
        
        # Build message with lists
        lines = [
            f"{EMOJIS['payment']} Payment History",
            "",
            f"User: {username_display}",
            f"Total Payments: {len(payments)}",
            ""
        ]
        
        for payment in payments[:10]:
            lines.extend([
                f"• #{payment.payment_id}: ETB{payment.amount} - {payment.status.capitalize()}",
                f"  {payment.created_at.strftime('%d %b %Y')}"
            ])
        
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join(lines),
            reply_markup=AdminUsersKeyboard.get_user_action_keyboard(user_id, user.blocked)
        )
    
    await callback.answer()


# ============== Search Users ==============

@router.callback_query(F.data == "admin_users_search")
async def admin_users_search_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Start user search in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['search']} Search Users",
            "",
            "Enter a username, name, or user ID to search."
        ]),
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await sender.send_message(
        callback.message.chat.id,
        "Type your search term:"
    )
    
    await callback.answer()


@router.message(F.text, StateFilter(UserStates.waiting_for_search_term))
async def handle_user_search(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Handle user search input in plain text"""
    sender = _get_plain_sender(message)
    
    if not is_admin:
        return
    
    search_term = message.text.strip()
    
    # Check if it's a numeric user ID
    try:
        user_id = int(search_term)
        async for session in get_db():
            user_repo = UserRepository(session)
            user = await user_repo.get_user(user_id)
            users = [user] if user else []
    except ValueError:
        async for session in get_db():
            user_repo = UserRepository(session)
            users = await user_repo.search_users(search_term)
    
    if not users:
        await sender.send_message(
            message.chat.id,
            "\n".join([
                "🔍 No Results",
                "",
                f"No users found matching '{search_term}'."
            ]),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    # Build message with lists
    lines = [
        "🔍 Search Results",
        "",
        f"Found {len(users)} users matching '{search_term}':",
        ""
    ]
    
    await sender.send_message(
        message.chat.id,
        "\n".join(lines),
        reply_markup=AdminUsersKeyboard.get_users_list_keyboard(users)
    )
    
    await state.clear()


# ============== Block/Unblock Users ==============

@router.callback_query(F.data.startswith("admin_user_block_"))
async def admin_user_block_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show block confirmation for user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        user = await user_repo.get_user(user_id)
        
        if not user:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        username_display = f"@{user.username}" if user.username else f"ID: {user.user_id}"
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['warning']} Block User?",
            "",
            "Are you sure you want to block this user?",
            "",
            f"User: {username_display}",
            f"Name: {full_name}",
            "",
            "⚠️ Blocked users will not be able to use the bot!"
        ]),
        reply_markup=AdminUsersKeyboard.get_block_confirmation_keyboard(user_id, user.username)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_block_user_"))
async def confirm_block_user_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Confirm user block in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        
        blocked = await user_repo.block_user(user_id)
        
        if blocked:
            # Log action
            await log_admin_action(
                callback.from_user.id,
                "Block User",
                f"Blocked user {user_id}"
            )
            
            # Try to notify the user
            try:
                await sender.send_message(
                    chat_id=user_id,
                    text="\n".join([
                        "🚫 Your account has been blocked by an administrator.",
                        "",
                        "Please contact support if you believe this is a mistake."
                    ])
                )
            except Exception:
                pass
            
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    "✅ User Blocked",
                    "",
                    f"User {user_id} has been blocked successfully."
                ]),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
        else:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    "❌ Block Failed",
                    "",
                    f"Could not block user {user_id}."
                ]),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_unblock_"))
async def admin_user_unblock_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Unblock a user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        
        unblocked = await user_repo.unblock_user(user_id)
        
        if unblocked:
            # Log action
            await log_admin_action(
                callback.from_user.id,
                "Unblock User",
                f"Unblocked user {user_id}"
            )
            
            # Try to notify the user
            try:
                await sender.send_message(
                    chat_id=user_id,
                    text="\n".join([
                        "✅ Your account has been unblocked!",
                        "",
                        "You can now use the bot again."
                    ])
                )
            except Exception:
                pass
            
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    "✅ User Unblocked",
                    "",
                    f"User {user_id} has been unblocked successfully."
                ]),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
        else:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    "❌ Unblock Failed",
                    "",
                    f"Could not unblock user {user_id}."
                ]),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await callback.answer()


@router.callback_query(F.data == "admin_users_block")
async def admin_users_block_main_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show block options in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['block']} Block User",
            "",
            "Enter the user ID to block:"
        ]),
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


@router.callback_query(F.data == "admin_users_unblock")
async def admin_users_unblock_main_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show unblock options in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['unblock']} Unblock User",
            "",
            "Enter the user ID to unblock:"
        ]),
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


# ============== Approve Users ==============

@router.callback_query(F.data == "admin_users_approve")
async def admin_users_approve_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show pending approvals in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        user_repo = UserRepository(session)
        all_users = await user_repo.get_all_users(limit=100)
        pending_users = [u for u in all_users if not u.approved]
    
    if not pending_users:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "\n".join([
                "✅ No Pending Approvals",
                "",
                "All users have been approved."
            ]),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    # Build message with lists
    lines = [
        f"{EMOJIS['approve']} Pending Approvals",
        "",
        f"Users waiting for approval: {len(pending_users)}",
        ""
    ]
    
    keyboard = []
    for user in pending_users[:10]:
        username = f"@{user.username}" if user.username else f"ID: {user.user_id}"
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        lines.append(f"• {username} ({name})")
        keyboard.append([
            InlineKeyboardButton(
                text=f"Approve {username}",
                callback_data=f"approve_user_{user.user_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Back", callback_data="admin_users")
    ])
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_user_"))
async def approve_user_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Approve a specific user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        
        # 🚨 CRITICAL: Set BOTH approved=1 AND is_premium=1
        updated = await user_repo.update_user(user_id, approved=True, is_premium=True)
        
        if updated:
            # Log action
            await log_admin_action(
                callback.from_user.id,
                "Approve User",
                f"Approved user {user_id}"
            )
            
            # ============================================================
            # FIX: Complete referral counting when user is approved
            # This credits the referrer when a referred user gets approved
            # ============================================================
            referral_result = None
            try:
                # Use complete_referral_with_session which handles its own session management
                referral_service = ReferralService(
                    referral_repo=ReferralRepository(session),
                    user_repo=user_repo
                )
                # Call with self-contained session management
                referral_result = await referral_service.complete_referral_with_session(user_id)
                
                if referral_result.get('success'):
                    if referral_result.get('count_incremented'):
                        referrer_id = referral_result.get('referrer_id')
                        print(f"[APPROVE] ✅ Referral counted: referrer={referrer_id}, referred={user_id}")
                    elif referral_result.get('already_completed'):
                        print(f"[APPROVE] ℹ️ Referral already completed for user {user_id}")
                    else:
                        print(f"[APPROVE] ℹ️ No pending referral for user {user_id}")
                else:
                    print(f"[APPROVE] ❌ Referral completion failed: {referral_result.get('message', 'Unknown error')}")
            except Exception as referral_error:
                # Don't fail approval for referral errors
                print(f"[APPROVE] ⚠️ Referral completion error (non-critical): {referral_error}")

            # Try to notify the user
            try:
                await sender.send_message(
                    chat_id=user_id,
                    text="\n".join([
                        "🎉 Your account has been approved!",
                        "",
                        "You can now access all features of the quiz bot."
                    ])
                )
            except Exception:
                pass
            
            # Build admin message
            admin_msg_lines = [
                "✅ User Approved",
                "",
                f"User {user_id} has been approved successfully."
            ]
            
            # Add referral info to admin message
            if referral_result:
                if referral_result.get('count_incremented'):
                    admin_msg_lines.extend([
                        "",
                        "🎁 Referral Credit Info:",
                        f"• Referrer ID: {referral_result.get('referrer_id')}",
                        "• Referral counted for referrer!",
                        f"• Reward granted: {'Yes' if referral_result.get('reward_granted') else 'No'}"
                    ])
                elif referral_result.get('already_completed'):
                    admin_msg_lines.extend([
                        "",
                        "ℹ️ Referral Info:",
                        "• Referral was already counted (idempotent)"
                    ])
                elif referral_result.get('referrer_id') is None:
                    admin_msg_lines.extend([
                        "",
                        "ℹ️ Referral Info:",
                        "• User was not referred by anyone"
                    ])
            
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join(admin_msg_lines),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
        else:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "\n".join([
                    "❌ Approval Failed",
                    "",
                    f"Could not approve user {user_id}."
                ]),
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await callback.answer()


# ============== Send Message to User ==============

@router.callback_query(F.data.startswith("admin_user_message_"))
async def admin_user_message_callback(callback: types.CallbackQuery, state: FSMContext,
                                       is_admin: bool = False):
    """Start sending message to user in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join([
            f"{EMOJIS['message']} Send Message to User",
            "",
            f"User ID: {user_id}",
            "",
            "Enter the message to send:"
        ]),
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.update_data(target_user_id=user_id)
    await state.set_state(UserStates.waiting_for_broadcast_message)
    
    await callback.answer()


@router.message(StateFilter(UserStates.waiting_for_broadcast_message))
async def handle_user_message(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Handle message to send to user in plain text"""
    sender = _get_plain_sender(message)
    
    if not is_admin:
        return
    
    data = await state.get_data()
    user_id = data.get('target_user_id')
    
    if not user_id:
        await sender.send_message(
            message.chat.id,
            "❌ Error: User ID not found.",
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    try:
        # Send message to user
        await sender.send_message(
            chat_id=user_id,
            text="\n".join([
                "📨 Message from Admin:",
                "",
                message.text
            ])
        )
        
        await sender.send_message(
            message.chat.id,
            "\n".join([
                "✅ Message Sent",
                "",
                f"Message sent to user {user_id}."
            ]),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        
        # Log action
        await log_admin_action(
            message.from_user.id,
            "Send Message",
            f"Sent message to user {user_id}: {message.text[:100]}..."
        )
        
    except Exception as e:
        await sender.send_message(
            message.chat.id,
            "\n".join([
                "❌ Send Failed",
                "",
                f"Could not send message to user {user_id}.",
                f"Error: {str(e)}"
            ]),
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
    
    await state.clear()

