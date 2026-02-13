"""
Admin Logs Handler - Telegram Quiz Bot
View admin activity logs
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from typing import List

from app.keyboards.admin import (
    AdminKeyboard, AdminLogsKeyboard
)
from app.utils.constants import EMOJIS
from app.db.base import get_db
from app.repositories.admin_log_repo import AdminLogRepository
from app.repositories.user_repo import UserRepository

router = Router()

# FSM States for logs
class LogStates(StatesGroup):
    """FSM states for log viewing"""
    waiting_for_admin_search = State()


# ============== Main Menu Handlers ==============

@router.callback_query(F.data == "admin_logs")
async def admin_logs_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show logs menu"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['info']} *Admin Activity Logs*\n\n"
        "View and monitor admin actions:",
        parse_mode='Markdown',
        reply_markup=AdminLogsKeyboard.get_logs_menu()
    )
    await callback.answer()


# ============== Recent Actions ==============

@router.callback_query(F.data == "admin_logs_recent")
async def admin_logs_recent_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show recent admin actions"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        logs = await log_repo.get_logs(limit=50)
    
    if not logs:
        await callback.message.edit_text(
            f"📭 *No Logs Yet*\n\n"
            f"Admin actions will appear here once logged.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    log_count = await log_repo.get_log_count()
    
    logs_text = (
        f"{EMOJIS['list']} *Recent Admin Actions*\n\n"
        f"📊 *Total Logs:* {log_count}\n\n"
    )
    
    await callback.message.edit_text(
        logs_text,
        parse_mode='Markdown',
        reply_markup=AdminLogsKeyboard.get_logs_list_keyboard(logs)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_logs_page_"))
async def admin_logs_page_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle pagination for logs"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    page = int(callback.data.split("_")[-1])
    offset = page * 10
    
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        logs = await log_repo.get_logs(limit=50, offset=offset)
    
    await callback.message.edit_text(
        f"{EMOJIS['list']} *Recent Admin Actions* (Page {page + 1})",
        parse_mode='Markdown',
        reply_markup=AdminLogsKeyboard.get_logs_list_keyboard(logs, page=page)
    )
    await callback.answer()


# ============== Log Summary ==============

@router.callback_query(F.data == "admin_logs_summary")
async def admin_logs_summary_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show action summary"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        
        # Get action summary for last 7 days
        summary = await log_repo.get_action_summary(days=7)
        total_logs = await log_repo.get_log_count()
    
    summary_text = (
        f"{EMOJIS['stats']} *Action Summary* (Last 7 Days)\n\n"
        f"📊 *Total Actions:* {sum(summary.values())}\n\n"
        f"📋 *By Type:*\n"
    )
    
    # Sort by count
    sorted_actions = sorted(summary.items(), key=lambda x: x[1], reverse=True)
    
    for action, count in sorted_actions:
        summary_text += f"• {action}: {count}\n"
    
    summary_text += f"\n📈 *All Time:* {total_logs} total logs"
    
    await callback.message.edit_text(
        summary_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== Search Logs ==============

@router.callback_query(F.data == "admin_logs_search")
async def admin_logs_search_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Start log search"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['search']} *Search Logs*\n\n"
        f"Enter an action type to search:\n\n"
        f"Examples:\n"
        f"• 'Approve Payment'\n"
        f"• 'Block User'\n"
        f"• 'Add Question'\n"
        f"• 'Broadcast'",
        parse_mode='Markdown'
    )
    
    await callback.answer()


@router.callback_query(F.data == "admin_logs_by_admin")
async def admin_logs_by_admin_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show logs by admin"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        user_repo = UserRepository(session)
        
        # Get all unique admin IDs from logs
        all_logs = await log_repo.get_logs(limit=200)
        admin_ids = list(set(log.admin_user_id for log in all_logs))
        
        # Get user info for each admin
        admins = []
        for admin_id in admin_ids:
            user = await user_repo.get_user(admin_id)
            admin_logs = [l for l in all_logs if l.admin_user_id == admin_id]
            admins.append({
                'user_id': admin_id,
                'username': f"@{user.username}" if user and user.username else f"ID: {admin_id}",
                'name': f"{user.first_name or ''} {user.last_name or ''}".strip() if user else "",
                'count': len(admin_logs)
            })
        
        # Sort by activity
        admins.sort(key=lambda x: x['count'], reverse=True)
    
    if not admins:
        await callback.message.edit_text(
            f"📭 *No Admin Logs*\n\n"
            f"No admin actions have been recorded yet.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    admin_text = (
        f"{EMOJIS['user']} *Admin Activity*\n\n"
        f"📊 *Admins by Activity:*\n\n"
    )
    
    for admin in admins:
        admin_text += (
            f"👤 *{admin['username']}*"
        )
        if admin['name']:
            admin_text += f" ({admin['name']})"
        admin_text += f"\n   Actions: {admin['count']}\n\n"
    
    await callback.message.edit_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== View Single Log ==============

@router.callback_query(F.data.startswith("admin_log_view_"))
async def admin_log_view_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View a specific log entry"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    log_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        user_repo = UserRepository(session)
        
        all_logs = await log_repo.get_logs(limit=200)
        log = next((l for l in all_logs if l.id == log_id), None)
        
        if not log:
            await callback.message.edit_text(
                "❌ Log entry not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        user = await user_repo.get_user(log.admin_user_id)
        username = f"@{user.username}" if user and user.username else f"ID: {log.admin_user_id}"
        
        log_text = (
            f"{EMOJIS['info']} *Log Entry #{log.id}*\n\n"
            f"👤 *Admin:* {username}\n"
            f"🆔 *Admin ID:* `{log.admin_user_id}`\n"
            f"📅 *Time:* {log.created_at.strftime('%d %b %Y %H:%M:%S')}\n\n"
            f"📋 *Action:*\n{log.action}\n"
        )
        
        if log.details:
            log_text += f"\n📝 *Details:*\n{log.details}"
        
        await callback.message.edit_text(
            log_text,
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
    
    await callback.answer()

