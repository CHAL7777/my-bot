"""
Admin Handler - Telegram Quiz Bot
Core admin panel entry points and main menu
Note: Detailed admin functionality is now in separate handlers:
- admin_questions.py: Question management
- admin_users.py: User management
- admin_subjects.py: Subject management
- admin_payments.py: Payment management
- admin_stats.py: Statistics and settings
- admin_logs.py: Activity logs
- admin_manage.py: Admin management (superadmin only)
"""

from aiogram import Router, types, F
from aiogram.filters import Command

from app.keyboards.admin import AdminKeyboard
from app.keyboards.menu import MainMenuKeyboard
from app.utils.constants import EMOJIS

router = Router()


@router.message(Command("admin"))
async def admin_command(message: types.Message, is_admin: bool = False,
                       is_superadmin: bool = False):
    """Handle /admin command - show admin panel"""
    if not is_admin:
        await message.answer(
            f"❌ *Access Denied*\n\n"
            f"This command is for administrators only.",
            parse_mode='Markdown',
            reply_markup=MainMenuKeyboard.get_main_menu()
        )
        return
    
    await message.answer(
        f"{EMOJIS['admin']} *Admin Panel*\n\n"
        f"Welcome to the administration dashboard.\n"
        f"Choose an option to manage the bot:",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_admin_panel(is_superadmin=is_superadmin)
    )


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_callback(callback: types.CallbackQuery, is_admin: bool = False,
                                is_superadmin: bool = False):
    """Go back to admin panel"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['admin']} *Admin Panel*\n\n"
        f"Welcome to the administration dashboard.\n"
        f"Choose an option to manage the bot:",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_admin_panel(is_superadmin=is_superadmin)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_user_menu")
async def back_to_user_menu_callback(callback: types.CallbackQuery, is_admin: bool = False,
                                     is_superadmin: bool = False):
    """Go back to user main menu from admin panel"""
    await callback.message.edit_text(
        "Main Menu\n\n"
        "Choose what you'd like to do:",
        parse_mode=None,
        reply_markup=MainMenuKeyboard.get_main_menu_inline(is_admin=is_admin)
    )
    await callback.answer()


# These callbacks are handled by the specialized admin handlers:
# - admin_questions.py handles: admin_questions, admin_questions_list, etc.
# - admin_users.py handles: admin_users, admin_users_list, etc.
# - admin_subjects.py handles: admin_subjects, admin_subjects_list, etc.
# - admin_payments.py handles: admin_payments, admin_payments_pending, etc.
# - admin_stats.py handles: admin_stats, admin_stats_dashboard, admin_settings, etc.
# - admin_logs.py handles: admin_logs, admin_logs_recent, etc.
# - admin_manage.py handles: admin_manage_admins, admin_list_all_admins, admin_referrals_leaderboard, etc.

