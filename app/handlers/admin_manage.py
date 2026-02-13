"""
Admin Management Handler - Telegram Quiz Bot
Handle admin management commands with plain text only.
Maximum reliability with zero parse errors.
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, desc

from app.keyboards.admin import AdminKeyboard, AdminManageKeyboard
from app.keyboards.menu import MainMenuKeyboard
from app.utils.constants import EMOJIS
from app.db.base import get_db
from app.repositories.admin_repo import TelegramAdminRepository
from app.repositories.admin_log_repo import AdminLogRepository
from app.repositories.user_repo import UserRepository
from app.utils.plain_sender import PlainTextMessageSender  # Changed to plain text sender

router = Router()


# ==================== FSM States for Admin Management ====================

class AdminManagementStates(StatesGroup):
    """States for the admin management flow"""
    waiting_for_admin_user_id = State()
    waiting_for_admin_username = State()
    waiting_for_admin_role = State()
    waiting_for_confirm_remove = State()


def _get_plain_sender(update) -> PlainTextMessageSender:
    """Get PlainTextMessageSender instance from update"""
    if isinstance(update, types.CallbackQuery):
        return PlainTextMessageSender(update.bot)
    elif isinstance(update, types.Message):
        return PlainTextMessageSender(update.bot)
    else:
        raise ValueError(f"Unsupported update type: {type(update)}")


@router.message(Command("add_admin"))
async def add_admin_command(message: types.Message, is_superadmin: bool = False,
                           admin_role: str = None):
    """Add a new admin - Super Admin only"""
    sender = _get_plain_sender(message)
    user_id = message.from_user.id
    parts = message.text.split()

    if not is_superadmin:
        await sender.send_message(message.chat.id, "Access denied. Super Admin only.")
        return

    if len(parts) < 2:
        await sender.send_message(message.chat.id, "Usage: /add_admin <user_id> [role]")
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await sender.send_message(message.chat.id, "Invalid user ID")
        return

    role = 'admin'
    if len(parts) >= 3 and parts[2].lower() in ['admin', 'superadmin']:
        role = parts[2].lower()

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        user_repo = UserRepository(session)
        log_repo = AdminLogRepository(session)

        target_user = await user_repo.get_user(target_user_id)
        if not target_user:
            await sender.send_message(message.chat.id, f"User {target_user_id} not found")
            return

        existing = await admin_repo.get_admin(target_user_id)
        if existing and existing.is_active:
            await sender.send_message(message.chat.id, "User is already an admin")
            return

        username = target_user.username
        await admin_repo.create_admin(target_user_id, username, role, user_id)
        await log_repo.log_action(user_id, "Add Admin", f"Added {username} as {role}")

    await sender.send_message(message.chat.id, f"Admin added: @{username} as {role}")


@router.message(Command("remove_admin"))
async def remove_admin_command(message: types.Message, is_superadmin: bool = False):
    """Remove an admin - Super Admin only"""
    sender = _get_plain_sender(message)
    user_id = message.from_user.id
    parts = message.text.split()

    if not is_superadmin:
        await sender.send_message(message.chat.id, "Access denied. Super Admin only.")
        return

    if len(parts) < 2:
        await sender.send_message(message.chat.id, "Usage: /remove_admin <user_id>")
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await sender.send_message(message.chat.id, "Invalid user ID")
        return

    if target_user_id == user_id:
        await sender.send_message(message.chat.id, "Cannot remove yourself")
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        user_repo = UserRepository(session)
        log_repo = AdminLogRepository(session)

        admin = await admin_repo.get_admin(target_user_id)
        if not admin:
            await sender.send_message(message.chat.id, "User is not an admin")
            return

        target_user = await user_repo.get_user(target_user_id)
        username = target_user.username if target_user else None

        await admin_repo.remove_admin(target_user_id)
        await log_repo.log_action(user_id, "Remove Admin", f"Removed {username}")

    await sender.send_message(message.chat.id, f"Admin removed: @{username}")


@router.message(Command("list_admins"))
async def list_admins_command(message: types.Message, is_admin: bool = False):
    """List all admins in plain text"""
    sender = _get_plain_sender(message)
    
    if not is_admin:
        await sender.send_message(message.chat.id, "Access denied.")
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admins = await admin_repo.list_admins()
        stats = await admin_repo.get_admin_stats()

    # Build message with lists for clarity
    lines = [
        "Admin List",
        "",
        f"Total: {stats['total_admins']} | Super: {stats['superadmins']} | Admin: {stats['regular_admins']}",
        ""
    ]

    for admin in admins:
        status = "OK" if admin.is_active else "XX"
        role = "S" if admin.role == 'superadmin' else "A"
        username_display = f"@{admin.username}" if admin.username else "N/A"
        lines.append(f"[{role}] {status} {username_display} (ID: {admin.user_id})")

    await sender.send_message(message.chat.id, "\n".join(lines))


@router.message(Command("admin_help"))
async def admin_help_command(message: types.Message, is_admin: bool = False,
                             is_superadmin: bool = False):
    """Show admin help in plain text"""
    sender = _get_plain_sender(message)
    
    lines = ["Admin Help", ""]
    
    if is_superadmin:
        lines.extend([
            "Super Admin:",
            "/add_admin <id> [role] - Add admin",
            "/remove_admin <id> - Remove admin",
            "/list_admins - List all admins",
            ""
        ])
    
    lines.extend([
        "Admin Commands:",
        "/admin - Admin panel",
        "/admin_stats - Statistics",
        "/admin_users - Manage users",
        "/admin_payments - Manage payments"
    ])

    await sender.send_message(message.chat.id, "\n".join(lines))


# ==================== Cancel Command Handler ====================

@router.message(Command("cancel"))
async def cancel_admin_flow(message: types.Message, state: FSMContext):
    """Cancel the admin creation flow"""
    sender = _get_plain_sender(message)
    
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    
    await sender.send_message(
        message.chat.id,
        "Operation Cancelled\n\nAdmin creation has been cancelled.",
        reply_markup=MainMenuKeyboard.get_main_menu()
    )


# ==================== Message Handlers for FSM Flow ====================

@router.message(StateFilter(AdminManagementStates.waiting_for_admin_user_id))
async def process_admin_user_id(message: types.Message, state: FSMContext, is_superadmin: bool = False):
    """Process user ID input for admin creation"""
    sender = _get_plain_sender(message)
    
    if not is_superadmin:
        await sender.send_message(message.chat.id, "Access denied. Super Admin only.")
        await state.clear()
        return

    user_id = message.from_user.id
    text = message.text.strip()

    try:
        target_user_id = int(text)
    except ValueError:
        await sender.send_message(
            message.chat.id,
            "Invalid User ID\n\nPlease send a valid numeric Telegram User ID.\nExample: 123456789\n\nSend /cancel to cancel."
        )
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        user_repo = UserRepository(session)
        log_repo = AdminLogRepository(session)

        target_user = await user_repo.get_user(target_user_id)
        if not target_user:
            await sender.send_message(
                message.chat.id,
                "User Not Found\n\nUser has not started the bot.\nMake sure the user has started the bot first.\n\nSend /cancel to cancel."
            )
            await state.clear()
            return

        existing = await admin_repo.get_admin(target_user_id)
        if existing and existing.is_active:
            await sender.send_message(
                message.chat.id,
                "Already an Admin\n\nUser is already an admin.\n\nSend /cancel to cancel."
            )
            await state.clear()
            return

        username = target_user.username
        
        # Save target user info in state
        await state.update_data(target_user_id=target_user_id, username=username)
        
        # Ask for role selection
        await state.set_state(AdminManagementStates.waiting_for_admin_role)

    await sender.send_message(
        message.chat.id,
        f"User Found: @{username}\n\nSelect the role for this user:",
        reply_markup=AdminManageKeyboard.get_role_selection_keyboard(for_user_id=target_user_id)
    )


@router.message(StateFilter(AdminManagementStates.waiting_for_admin_role))
async def process_admin_role(message: types.Message, state: FSMContext, is_superadmin: bool = False):
    """Process role selection for admin creation (fallback if keyboard not used)"""
    sender = _get_plain_sender(message)
    
    if not is_superadmin:
        await sender.send_message(message.chat.id, "Access denied. Super Admin only.")
        await state.clear()
        return

    text = message.text.strip().lower()
    
    if text in ['admin', 'a']:
        role = 'admin'
    elif text in ['superadmin', 'super', 's']:
        role = 'superadmin'
    else:
        await sender.send_message(
            message.chat.id,
            "Invalid Role\n\nPlease send 'admin' or 'superadmin'.\n\nSend /cancel to cancel."
        )
        return

    # Get the stored user info
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    username = data.get('username')

    if not target_user_id:
        await sender.send_message(
            message.chat.id,
            "Session Expired\n\nPlease start the admin creation process again.\n\nSend /cancel to cancel."
        )
        await state.clear()
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        log_repo = AdminLogRepository(session)

        await admin_repo.create_admin(target_user_id, username, role, message.from_user.id)
        await log_repo.log_action(
            message.from_user.id, 
            "Add Admin", 
            f"Added @{username} as {role}"
        )

    await state.clear()

    await sender.send_message(
        message.chat.id,
        f"Admin Added Successfully\n\nUser: @{username}\nRole: {role}\nAdded by: You",
        reply_markup=AdminManageKeyboard.get_admin_management()
    )


# ==================== Callback Handlers ====================

@router.callback_query(F.data.startswith("admin_role_"), StateFilter(AdminManagementStates.waiting_for_admin_role))
async def admin_role_selection_fsm_callback(callback: types.CallbackQuery, state: FSMContext, is_superadmin: bool = False):
    """Handle role selection via callback for admin creation (FSM state)"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    # Parse the callback data: admin_role_<role>_<user_id>
    parts = callback.data.split("_")
    role = parts[2] if len(parts) > 2 else 'admin'
    target_user_id = int(parts[3]) if len(parts) > 3 else None

    if not target_user_id:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "Error\n\nInvalid callback data.",
            reply_markup=AdminManageKeyboard.get_admin_management()
        )
        await callback.answer()
        await state.clear()
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        user_repo = UserRepository(session)
        log_repo = AdminLogRepository(session)

        # Get user info
        user = await user_repo.get_user(target_user_id)
        if not user:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                f"User not found with ID: {target_user_id}",
                reply_markup=AdminManageKeyboard.get_add_admin_menu()
            )
            await callback.answer()
            await state.clear()
            return

        username = user.username
        
        # Check if already an admin
        existing = await admin_repo.get_admin(target_user_id)
        if existing and existing.is_active:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Already an Admin\n\nUser is already an admin.",
                reply_markup=AdminManageKeyboard.get_admin_management()
            )
            await callback.answer()
            await state.clear()
            return

        # Create the admin
        await admin_repo.create_admin(target_user_id, username, role, callback.from_user.id)
        await log_repo.log_action(
            callback.from_user.id, 
            "Add Admin", 
            f"Added @{username} as {role}"
        )

    await state.clear()

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        f"Admin Added Successfully\n\nUser: @{username}\nRole: {role}\nAdded by: You",
        reply_markup=AdminManageKeyboard.get_admin_management()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_manage_admins")
async def manage_admins_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Show admin management menu"""
    sender = _get_plain_sender(callback)
    
    # Clear any pending states when entering admin management
    await state.clear()
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Admin Management",
        reply_markup=AdminManageKeyboard.get_admin_management()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_list_all_admins")
async def list_all_admins_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """List all admins with enhanced details in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admins = await admin_repo.get_all_admins_with_details()

    # Build message with lists
    lines = ["Admin List", ""]
    
    for admin in admins:
        status = "OK" if admin['is_active'] else "XX"
        role = "S" if admin['role'] == 'superadmin' else "A"
        adder = admin.get('added_by')
        adder_text = f"by @{adder['username']}" if adder and adder.get('username') else ""
        username_display = f"@{admin['username']}" if admin['username'] else "N/A"
        lines.append(f"[{role}] {status} {username_display} (ID: {admin['user_id']}) {adder_text}")

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
        reply_markup=AdminManageKeyboard.get_admin_list_keyboard(admins)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_referrals_leaderboard")
async def referrals_leaderboard_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show top referrers in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return

    from app.repositories.referral_repo import ReferralRepository

    async for session in get_db():
        referral_repo = ReferralRepository(session)
        top_referrers = await referral_repo.get_top_referrers(20)

    # Build message with lists
    lines = ["Top Referrers", ""]
    
    for i, referrer in enumerate(top_referrers, 1):
        medal = {1: '1st', 2: '2nd', 3: '3rd'}.get(i, f'{i}th')
        lines.append(f"{medal}: {referrer['name']} - {referrer['referral_count']}")

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
        reply_markup=AdminManageKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ==================== ADD ADMIN CALLBACKS ====================

@router.callback_query(F.data == "admin_add_admin_menu")
async def add_admin_menu_callback(callback: types.CallbackQuery, is_superadmin: bool = False):
    """Show add admin menu in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Add New Admin\n\nChoose how to add a new admin:",
        reply_markup=AdminManageKeyboard.get_add_admin_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_by_userid")
async def add_admin_by_userid_callback(callback: types.CallbackQuery, state: FSMContext, is_superadmin: bool = False):
    """Prompt for user ID to add admin in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    # Set FSM state to wait for user ID
    await state.set_state(AdminManagementStates.waiting_for_admin_user_id)

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Add Admin by User ID\n\nPlease send the user's Telegram User ID.\nYou can get this from @userinfobot.\n\nSend /cancel to cancel this operation.",
        reply_markup=AdminManageKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ==================== REMOVE ADMIN CALLBACKS ====================

@router.callback_query(F.data == "admin_remove_admin_menu")
async def remove_admin_menu_callback(callback: types.CallbackQuery, is_superadmin: bool = False):
    """Show remove admin menu with list of admins in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admins = await admin_repo.list_admins()

    # Filter out the current user from the list
    current_user_id = callback.from_user.id
    other_admins = [a for a in admins if a.user_id != current_user_id]

    if not other_admins:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "No Other Admins\n\nThere are no other admins to remove.",
            reply_markup=AdminManageKeyboard.get_admin_management()
        )
        await callback.answer()
        return

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Remove Admin\n\nSelect an admin to remove:",
        reply_markup=AdminManageKeyboard.get_remove_admin_menu(other_admins)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_remove_select_"))
async def remove_admin_select_callback(callback: types.CallbackQuery, is_superadmin: bool = False):
    """Show confirmation for removing a specific admin in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    user_id = int(callback.data.split("_")[-1])

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admin = await admin_repo.get_admin(user_id)

    if not admin:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "Admin not found",
            reply_markup=AdminManageKeyboard.get_admin_management()
        )
        await callback.answer()
        return

    username = admin.username or "Unknown"

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        f"Confirm Remove Admin\n\nAre you sure you want to remove this admin?\n\nUser: @{username}\nRole: {admin.role}\nID: {user_id}",
        reply_markup=AdminManageKeyboard.get_remove_confirmation_keyboard(user_id, username)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_remove_confirm_"))
async def remove_admin_confirm_callback(callback: types.CallbackQuery, is_superadmin: bool = False):
    """Confirm and execute admin removal in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    user_id = int(callback.data.split("_")[-1])

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        user_repo = UserRepository(session)
        log_repo = AdminLogRepository(session)

        admin = await admin_repo.get_admin(user_id)
        if not admin:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Admin not found",
                reply_markup=AdminManageKeyboard.get_admin_management()
            )
            await callback.answer()
            return

        username = admin.username
        await admin_repo.remove_admin(user_id)
        await log_repo.log_action(
            callback.from_user.id,
            "Remove Admin",
            f"Removed @{username} as {admin.role}"
        )

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        f"Admin Removed\n\n@{username} has been removed from the admin list.",
        reply_markup=AdminManageKeyboard.get_admin_management()
    )
    await callback.answer()


# ==================== CHANGE ROLE CALLBACKS ====================

@router.callback_query(F.data == "admin_change_role_menu")
async def change_role_menu_callback(callback: types.CallbackQuery, is_superadmin: bool = False):
    """Show menu for selecting admin to change role in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admins = await admin_repo.list_admins()

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Change Admin Role\n\nSelect an admin to change their role:",
        reply_markup=AdminManageKeyboard.get_change_role_menu(admins)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_change_role_select_"))
async def change_role_select_callback(callback: types.CallbackQuery, is_superadmin: bool = False):
    """Show role selection for specific admin in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    user_id = int(callback.data.split("_")[-1])

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admin = await admin_repo.get_admin(user_id)

    if not admin:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "Admin not found",
            reply_markup=AdminManageKeyboard.get_admin_management()
        )
        await callback.answer()
        return

    username = admin.username or "Unknown"
    current_role = admin.role
    new_role = 'superadmin' if current_role == 'admin' else 'admin'
    new_role_text = "Super Admin" if new_role == 'superadmin' else "Admin"

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        f"Change Role for @{username}\n\nCurrent role: {current_role}\nNew role: {new_role_text}",
        reply_markup=AdminManageKeyboard.get_confirm_role_change_keyboard(user_id, new_role, username)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_role_confirm_"))
async def role_change_confirm_callback(callback: types.CallbackQuery, is_superadmin: bool = False):
    """Confirm and execute role change in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_superadmin:
        await callback.answer("Access denied. Super Admin only.", show_alert=True)
        return

    parts = callback.data.split("_")
    user_id = int(parts[3])
    new_role = parts[4]

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        log_repo = AdminLogRepository(session)

        admin = await admin_repo.get_admin(user_id)
        if not admin:
            await sender.edit_message(
                callback.message.chat.id,
                callback.message.message_id,
                "Admin not found",
                reply_markup=AdminManageKeyboard.get_admin_management()
            )
            await callback.answer()
            return

        old_role = admin.role
        username = admin.username
        await admin_repo.promote_admin(user_id, new_role)
        await log_repo.log_action(
            callback.from_user.id,
            "Change Admin Role",
            f"Changed @{username} role from {old_role} to {new_role}"
        )

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        f"Role Updated\n\n@{username} is now a {new_role}",
        reply_markup=AdminManageKeyboard.get_admin_management()
    )
    await callback.answer()


# ==================== ADMIN DETAIL & LIST CALLBACKS ====================

@router.callback_query(F.data.startswith("admin_view_"))
async def admin_view_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show details for a specific admin in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return

    user_id = int(callback.data.split("_")[-1])

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admin_details = await admin_repo.get_admin_with_adder_info(user_id)

    if not admin_details:
        await sender.edit_message(
            callback.message.chat.id,
            callback.message.message_id,
            "Admin not found",
            reply_markup=AdminManageKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return

    admin = admin_details['admin']
    adder = admin_details['adder']
    adder_text = f"@{adder['username']}" if adder and adder.get('username') else f"ID: {adder['user_id']}" if adder else "Unknown"

    lines = [
        "Admin Details",
        "",
        f"Username: @{admin.username or 'N/A'}",
        f"User ID: {admin.user_id}",
        f"Role: {admin.role}",
        f"Status: {'Active' if admin.is_active else 'Inactive'}",
        f"Added by: {adder_text}",
        f"Created: {admin.created_at.strftime('%d %b %Y %H:%M')}"
    ]

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
        reply_markup=AdminManageKeyboard.get_admin_detail_keyboard(user_id, admin.role)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_list_page_"))
async def admin_list_pagination_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle pagination for admin list in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return

    page = int(callback.data.split("_")[-1])

    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admins = await admin_repo.get_all_admins_with_details()

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "Admin List",
        reply_markup=AdminManageKeyboard.get_admin_list_keyboard(admins, page)
    )
    await callback.answer()


# ==================== USER REFERRALS MANAGEMENT ====================

@router.callback_query(F.data == "admin_users_referrals")
async def users_referrals_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show user referrals management in plain text"""
    sender = _get_plain_sender(callback)
    
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return

    from app.repositories.referral_repo import ReferralRepository

    async for session in get_db():
        referral_repo = ReferralRepository(session)
        
        # Get pending referrals with details
        referral_details = await referral_repo.get_pending_referrals_with_details(20)

    lines = ["User Referrals", ""]
    
    if referral_details:
        lines.append("Recent Referrals (Pending First):\n")
        
        for referral in referral_details:
            status_emoji = "OK" if referral['status'] == 'approved' else "WAIT" if referral['status'] == 'pending' else "XX"
            referrer_name = referral['referrer_user']['first_name'] if referral['referrer_user'] else "Unknown"
            referred_name = referral['referred_user']['first_name'] if referral['referred_user'] else "Unknown"
            
            lines.append(
                f"[{status_emoji}] Ref #{referral['id']}:\n"
                f"   From: {referrer_name} -> To: {referred_name}\n"
                f"   Date: {referral['created_at'].strftime('%d %b %H:%M')}\n"
            )
        
        if len(referral_details) >= 20:
            lines.append("\n... showing 20 of many referrals")
    else:
        lines.append("No pending referrals found.")
        
    lines.append("\nTip: Use /admin_payments to approve payments and complete referrals.")

    await sender.edit_message(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
        reply_markup=AdminManageKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()

