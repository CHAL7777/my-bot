"""
Admin Messages Handler - Telegram Quiz Bot

Handles admin commands for viewing and replying to user contact messages.
Supports ticket system with SUP-XXXX ticket IDs.
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from app.db.base import get_db
from app.repositories.contact_repo import ContactMessageRepository
from app.repositories.user_repo import UserRepository
from app.config import settings
from app.keyboards.menu import MainMenuKeyboard
from app.keyboards.admin import AdminKeyboard

router = Router()

# Admin FSM states for replying to messages
class AdminReplyStates(StatesGroup):
    waiting_for_reply = State()


@router.message(Command("admin_messages"))
async def admin_messages_command(message: types.Message, is_admin: bool = False):
    """
    Handle /admin_messages command - View pending contact messages.
    
    Note: is_admin is injected by AuthMiddleware.
    """
    if not is_admin:
        await message.answer(
            "❌ *Access Denied*\n\n"
            "This command is for administrators only.",
            parse_mode='Markdown'
        )
        return

    async for session in get_db():
        contact_repo = ContactMessageRepository(session)

        # Get open messages (pending)
        pending_messages = await contact_repo.get_pending_messages(limit=20)
        open_count = await contact_repo.get_open_count()

        if not pending_messages:
            await message.answer(
                "📬 *Contact Messages*\n\n"
                "✅ No pending messages!\n\n"
                f"Total open tickets: {open_count}",
                parse_mode='Markdown',
                reply_markup=AdminKeyboard.get_admin_panel()
            )
            return

        # Build message list
        message_text = (
            f"📬 *Contact Messages*\n\n"
            f"📊 *Open Tickets:* {open_count}\n"
            f"📋 *Showing:* Last {len(pending_messages)} messages\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        for msg in pending_messages:
            status_emoji = {
                'open': '🆕',
                'replied': '✅',
                'closed': '🔒'
            }.get(msg.status, '❓')

            # Get user info
            user_repo = UserRepository(session)
            user = await user_repo.get_user(msg.user_id)
            user_name = user.first_name if user else "Unknown"

            # Truncate message if too long
            display_text = msg.message_text[:100] + "..." if len(msg.message_text) > 100 else msg.message_text

            message_text += (
                f"{status_emoji} *{msg.ticket_id}* | {msg.category.upper()}\n"
                f"👤 {user_name} (ID: {msg.user_id})\n"
                f"⏰ {msg.created_at.strftime('%d %b %H:%M')}\n"
                f"📝 {display_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )

        message_text += (
            f"💡 *Commands:*\n"
            f"• `/reply <ticket_id> <message>` - Reply to ticket\n"
            f"• `/view <ticket_id>` - View full message\n"
            f"• `/close <ticket_id>` - Close ticket\n"
        )

        await message.answer(
            message_text,
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_admin_panel()
        )


@router.message(Command("reply"))
async def admin_reply_command(message: types.Message, is_admin: bool = False):
    """
    Handle /reply command - Reply to a user's contact message.
    
    Usage: /reply <ticket_id> <reply_text>
    
    Note: is_admin is injected by AuthMiddleware.
    """
    if not is_admin:
        await message.answer(
            "❌ *Access Denied*\n\n"
            "This command is for administrators only.",
            parse_mode='Markdown'
        )
        return

    # Parse command: /reply <ticket_id> <message>
    # Ticket ID format: SUP-XXXX
    args = message.text.split(None, 2)

    if len(args) < 3:
        await message.answer(
            "❌ *Invalid Format*\n\n"
            "Usage: `/reply <ticket_id> <your reply>`\n\n"
            "Example:\n"
            "`/reply SUP-1001 Your payment has been processed successfully`",
            parse_mode='Markdown'
        )
        return

    ticket_id = args[1]
    reply_text = args[2]

    # Validate ticket ID format
    if not ticket_id.startswith("SUP-") or not ticket_id[4:].isdigit():
        await message.answer(
            "❌ *Invalid Ticket ID*\n\n"
            "Ticket ID must be in format: SUP-XXXX\n\n"
            "Example: SUP-1001",
            parse_mode='Markdown'
        )
        return

    admin_id = message.from_user.id
    admin_name = message.from_user.first_name or "Admin"

    try:
        async for session in get_db():
            contact_repo = ContactMessageRepository(session)

            # Get the original message by ticket_id
            original_msg = await contact_repo.get_message_by_ticket_id(ticket_id)

            if not original_msg:
                await message.answer(
                    f"❌ *Ticket Not Found*\n\n"
                    f"No ticket found with ID: `{ticket_id}`",
                    parse_mode='Markdown'
                )
                return

            # Mark as replied
            updated_msg = await contact_repo.mark_as_replied(
                message_id=original_msg.message_id,
                admin_user_id=admin_id,
                reply_text=reply_text
            )

            # Get user info
            user_repo = UserRepository(session)
            user = await user_repo.get_user(original_msg.user_id)

            user_name = user.first_name if user else "User"
            user_telegram_id = original_msg.user_id

            # Send reply to user
            try:
                await message.bot.send_message(
                    chat_id=user_telegram_id,
                    text=(
                        f"📬 *Admin Reply - {ticket_id}*\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"{reply_text}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👤 *Replied by:* {admin_name}\n"
                        f"⏰ *Time:* {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                        f"💡 Need more help? Send a new message using /contact"
                    ),
                    parse_mode='Markdown'
                )

                user_reply_sent = "✅ User notified"
            except Exception as e:
                user_reply_sent = f"❌ User notification failed: {str(e)}"

            # Confirm to admin
            await message.answer(
                f"✅ *Reply Sent*\n\n"
                f"📤 *To:* {user_name} (ID: {user_telegram_id})\n"
                f"🎫 *Ticket ID:* `{ticket_id}`\n"
                f"📨 *Notification:* {user_reply_sent}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 *Your reply:*\n{reply_text}",
                parse_mode='Markdown'
            )

    except Exception as e:
        await message.answer(
            f"❌ *Error Sending Reply*\n\n"
            f"Details: {str(e)}",
            parse_mode='Markdown'
        )


@router.message(Command("view"))
async def admin_view_message_command(message: types.Message, is_admin: bool = False):
    """
    Handle /view command - View full details of a contact message.
    
    Usage: /view <ticket_id>
    
    Note: is_admin is injected by AuthMiddleware.
    """
    if not is_admin:
        await message.answer(
            "❌ *Access Denied*\n\n"
            "This command is for administrators only.",
            parse_mode='Markdown'
        )
        return

    # Parse command: /view <ticket_id>
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ *Invalid Format*\n\n"
            "Usage: `/view <ticket_id>`",
            parse_mode='Markdown'
        )
        return

    ticket_id = args[1]

    # Validate ticket ID format
    if not ticket_id.startswith("SUP-") or not ticket_id[4:].isdigit():
        await message.answer(
            "❌ *Invalid Ticket ID*\n\n"
            "Ticket ID must be in format: SUP-XXXX",
            parse_mode='Markdown'
        )
        return

    async for session in get_db():
        contact_repo = ContactMessageRepository(session)
        user_repo = UserRepository(session)

        # Get the message by ticket_id
        original_msg = await contact_repo.get_message_by_ticket_id(ticket_id)

        if not original_msg:
            await message.answer(
                f"❌ *Ticket Not Found*\n\n"
                f"No ticket found with ID: `{ticket_id}`",
                parse_mode='Markdown'
            )
            return

        # Get user info
        user = await user_repo.get_user(original_msg.user_id)
        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() if user else "Unknown"
        username = f"@{user.username}" if user and user.username else "N/A"

        # Build full message
        status_emoji = {
            'open': '🆕',
            'replied': '✅',
            'closed': '🔒'
        }.get(original_msg.status, '❓')

        admin_reply_text = original_msg.admin_reply or "(No reply yet)"

        full_message = (
            f"📬 *Ticket Details*\n\n"
            f"{status_emoji} *Status:* {original_msg.status.upper()}\n"
            f"🎫 *Ticket ID:* `{original_msg.ticket_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *User Information:*\n"
            f"• Name: {user_name}\n"
            f"• User ID: `{original_msg.user_id}`\n"
            f"• Username: {username}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📁 *Category:* {original_msg.category}\n"
            f"⏰ *Created:* {original_msg.created_at.strftime('%d %b %Y %H:%M')}\n"
            f"💬 *Replied:* {original_msg.replied_at.strftime('%d %b %Y %H:%M') if original_msg.replied_at else 'Not yet'}\n"
            f"🔒 *Closed:* {original_msg.closed_at.strftime('%d %b %Y %H:%M') if original_msg.closed_at else 'Not yet'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 *Original Message:*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{original_msg.message_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 *Admin Reply:*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{admin_reply_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 *Quick Actions:*\n"
            f"• Reply: `/reply {ticket_id} <text>`\n"
            f"• Close: `/close {ticket_id}`"
        )

        await message.answer(
            full_message,
            parse_mode='Markdown'
        )


@router.message(Command("close"))
async def admin_close_ticket_command(message: types.Message, is_admin: bool = False):
    """
    Handle /close command - Close a ticket thread.
    
    Usage: /close <ticket_id>
    
    Note: is_admin is injected by AuthMiddleware.
    """
    if not is_admin:
        await message.answer(
            "❌ *Access Denied*\n\n"
            "This command is for administrators only.",
            parse_mode='Markdown'
        )
        return

    # Parse command: /close <ticket_id>
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ *Invalid Format*\n\n"
            "Usage: `/close <ticket_id>`",
            parse_mode='Markdown'
        )
        return

    ticket_id = args[1]

    # Validate ticket ID format
    if not ticket_id.startswith("SUP-") or not ticket_id[4:].isdigit():
        await message.answer(
            "❌ *Invalid Ticket ID*\n\n"
            "Ticket ID must be in format: SUP-XXXX",
            parse_mode='Markdown'
        )
        return

    async for session in get_db():
        contact_repo = ContactMessageRepository(session)

        # Get the message by ticket_id
        original_msg = await contact_repo.get_message_by_ticket_id(ticket_id)

        if not original_msg:
            await message.answer(
                f"❌ *Ticket Not Found*\n\n"
                f"No ticket found with ID: `{ticket_id}`",
                parse_mode='Markdown'
            )
            return

        # Mark as closed
        await contact_repo.mark_as_closed(original_msg.message_id)

        await message.answer(
            f"✅ *Ticket Closed*\n\n"
            f"🎫 *Ticket ID:* `{ticket_id}`\n"
            f"👤 *User:* {original_msg.user_id}\n"
            f"📁 *Category:* {original_msg.category}\n\n"
            f"This ticket is now closed.",
            parse_mode='Markdown'
        )


@router.message(Command("message_stats"))
async def admin_message_stats_command(message: types.Message, is_admin: bool = False):
    """
    Handle /message_stats command - Show message statistics.
    
    Note: is_admin is injected by AuthMiddleware.
    """
    if not is_admin:
        await message.answer(
            "❌ *Access Denied*\n\n"
            "This command is for administrators only.",
            parse_mode='Markdown'
        )
        return

    async for session in get_db():
        contact_repo = ContactMessageRepository(session)

        # Get statistics
        open_count = await contact_repo.get_open_count()
        category_counts = await contact_repo.get_message_count_by_category()
        recent_messages = await contact_repo.get_recent_messages(days=7)

        # Build stats message
        stats_text = (
            "📊 *Contact Message Statistics*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📈 *Overview:*\n"
            f"• Open tickets: *{open_count}*\n"
            f"• Messages this week: *{len(recent_messages)}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📁 *By Category:*\n"
        )

        # Add category breakdown
        category_map = {
            'payment': '💳 Payment',
            'quiz_error': '🐛 Quiz Errors',
            'access': '🔒 Access',
            'general': '💡 General',
            'feedback': '💬 Feedback'
        }

        for cat, count in category_counts.items():
            cat_name = category_map.get(cat, cat)
            stats_text += f"• {cat_name}: {count}\n"

        stats_text += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 *Commands:*\n"
            f"• /admin_messages - View messages\n"
            f"• /reply <id> <text> - Reply\n"
        )

        await message.answer(
            stats_text,
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_admin_panel()
        )

