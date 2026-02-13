"""
Admin Referral Management Handler - Telegram Quiz Bot
Manage referral payments: view stats, process payouts, track payments

FIXED: Now properly gets is_admin from middleware injection (injected by AuthMiddleware)
FIXED: Changed stats['completed'] to stats['approved'] to match repository return value
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from typing import Optional

from app.keyboards.admin import AdminKeyboard, AdminReferralKeyboard
from app.utils.constants import EMOJIS
from app.db.base import get_db
from app.repositories.referral_repo import ReferralRepository
from app.repositories.user_repo import UserRepository
from app.services.referral_service import ReferralService
from app.config import settings
from app.utils.helpers import escape_markdown_content

router = Router()

# FSM States for referral payment management
class ReferralPaymentStates(StatesGroup):
    waiting_for_payout_amount = State()
    waiting_for_payout_note = State()


# ============== Main Menu ==============

@router.callback_query(F.data == "admin_referrals")
async def admin_referrals_callback(callback: types.CallbackQuery, is_admin: bool = False, is_superadmin: bool = False):
    """
    Show referral management menu.
    
    FIXED: Now properly gets is_admin from middleware injection instead of data dict.
    """
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        # Get overall stats
        all_users = await user_repo.get_all_users(limit=500)
        total_referrals = 0
        completed_referrals = 0
        pending_referrals = 0
        
        for user in all_users:
            stats = await referral_repo.get_referral_stats(user.user_id)
            total_referrals += stats['total_sent']
            completed_referrals += stats['approved']
            pending_referrals += stats['pending']
        
        # Calculate total earnings
        reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
        total_earnings = completed_referrals * reward_per_student
        
        menu_text = (
            f"{EMOJIS['gift']} *Referral Management*\n\n"
            f"📊 *Overview:*\n"
            f"• Total Referrals: {total_referrals}\n"
            f"• Completed: {completed_referrals}\n"
            f"• Pending: {pending_referrals}\n"
            f"• Total Paid Out: {total_earnings} {settings.CURRENCY_SYMBOL}\n\n"
            f"💰 *Reward:* {reward_per_student} {settings.CURRENCY_SYMBOL} per approved student\n\n"
            f"Choose an option:"
        )
        
        await callback.message.edit_text(
            menu_text,
            parse_mode='Markdown',
            reply_markup=AdminReferralKeyboard.get_referral_management()
        )
    
    await callback.answer()


# ============== View Top Referrers ==============

@router.callback_query(F.data == "admin_referrals_top")
async def admin_referrals_top_callback(callback: types.CallbackQuery, is_admin: bool = False, is_superadmin: bool = False):
    """Show top referrers with earnings"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        top_referrers = await referral_service.get_top_referrers(20)
    
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    
    top_text = (
        f"{EMOJIS['trophy']} *Top Referrers*\n\n"
        f"💰 Reward: {reward_per_student} {settings.CURRENCY_SYMBOL} per student\n\n"
    )
    
    if top_referrers:
        for i, referrer in enumerate(top_referrers, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "🔹")
            earnings = referrer['referral_count'] * reward_per_student
            top_text += (
                f"{medal} #{i} {escape_markdown_content(referrer['name'])}\n"
                f"   Referrals: {referrer['referral_count']} | "
                f"Earnings: {earnings} {settings.CURRENCY_SYMBOL}\n\n"
            )
    else:
        top_text += "No referrers yet.\n"
    
    await callback.message.edit_text(
        top_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


# ============== View All Referrers ==============

@router.callback_query(F.data == "admin_referrals_all")
async def admin_referrals_all_callback(callback: types.CallbackQuery, is_admin: bool = False, is_superadmin: bool = False):
    """Show all users with their referral counts"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        top_referrers = await referral_service.get_top_referrers(50)
    
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    
    all_text = (
        f"{EMOJIS['list']} *All Referrers*\n\n"
        f"Sort by referral count (highest first):\n\n"
    )
    
    if top_referrers:
        for i, referrer in enumerate(top_referrers, 1):
            earnings = referrer['referral_count'] * reward_per_student
            user_id = referrer['user_id']
            username = referrer.get('username', '')
            
            all_text += (
                f"{i}. {escape_markdown_content(referrer['name'])}\n"
                f"   👤 ID: `{user_id}` | "
                f"Referrals: {referrer['referral_count']} | "
                f"Earnings: {earnings} {settings.CURRENCY_SYMBOL}\n\n"
            )
    else:
        all_text += "No referrers found.\n"
    
    await callback.message.edit_text(
        all_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


# ============== View Pending Referrals ==============

@router.callback_query(F.data == "admin_referrals_pending")
async def admin_referrals_pending_callback(callback: types.CallbackQuery, is_admin: bool = False, is_superadmin: bool = False):
    """Show pending referrals (referred users who haven't been approved)"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        
        pending_referrals = await referral_repo.get_pending_referrals(limit=100)
    
    pending_text = (
        f"{EMOJIS['pending']} *Pending Referrals*\n\n"
        f"These referrals will be counted when the referred user gets approved.\n\n"
    )
    
    if pending_referrals:
        for i, referral in enumerate(pending_referrals[:20], 1):
            referrer = await user_repo.get_user(referral.referrer_id)
            referred = await user_repo.get_user(referral.referred_id)
            
            referrer_name = f"{referrer.first_name or ''} {referrer.last_name or ''}".strip() if referrer else "Unknown"
            referred_name = f"{referred.first_name or ''} {referred.last_name or ''}".strip() if referred else "Unknown"
            
            created_at = referral.created_at.strftime('%d %b %Y') if referral.created_at else "N/A"
            
            pending_text += (
                f"{i}. {referrer_name} → {referred_name}\n"
                f"   📅 Referred: {created_at}\n"
                f"   👤 Referred User ID: `{referral.referred_id}`\n\n"
            )
        
        if len(pending_referrals) > 20:
            pending_text += f"...and {len(pending_referrals) - 20} more\n"
    else:
        pending_text += "No pending referrals.\n"
    
    pending_text += (
        f"\n💡 *Tip:* Approve the referred user's payment to count this referral.\n"
        f"Use /admin_payments to find pending payments."
    )
    
    await callback.message.edit_text(
        pending_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


# ============== Process Payout ==============

@router.callback_query(F.data.startswith("admin_referral_payout_"))
async def admin_referral_payout_callback(callback: types.CallbackQuery, state: FSMContext,
                                         is_admin: bool = False, is_superadmin: bool = False):
    """Start payout process for a specific user"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        
        user = await user_repo.get_user(user_id)
        stats = await referral_repo.get_referral_stats(user_id)
    
    if not user:
        await callback.message.edit_text(
            "❌ User not found!",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    total_earnings = stats['approved'] * reward_per_student
    
    user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or f"User {user_id}"
    
    payout_text = (
        f"{EMOJIS['money']} *Process Payout*\n\n"
        f"👤 *User:* {user_name}\n"
        f"🆔 *User ID:* `{user_id}`\n\n"
        f"📊 *Referral Stats:*\n"
        f"• Total Referrals: {stats['total_sent']}\n"
        f"• Completed: {stats['approved']}\n"
        f"• Pending: {stats['pending']}\n"
        f"• Cancelled: {stats['cancelled']}\n\n"
        f"💰 *Earnings:* {total_earnings} {settings.CURRENCY_SYMBOL}\n"
        f"   ({stats['approved']} × {reward_per_student} {settings.CURRENCY_SYMBOL})\n\n"
    )
    
    # Store user_id in state for payout processing
    await state.update_data(payout_user_id=user_id, payout_amount=total_earnings)
    
    await callback.message.edit_text(
        payout_text,
        parse_mode='Markdown',
        reply_markup=AdminReferralKeyboard.get_payout_confirmation_keyboard(user_id)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_payout_"))
async def confirm_payout_callback(callback: types.CallbackQuery, state: FSMContext,
                                   is_admin: bool = False, is_superadmin: bool = False):
    """Confirm payout for user"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        
        user = await user_repo.get_user(user_id)
        stats = await referral_repo.get_referral_stats(user_id)
    
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    total_earnings = stats['approved'] * reward_per_student
    
    user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() if user else f"User {user_id}"
    
    confirm_text = (
        f"⚠️ *Confirm Payout*\n\n"
        f"You are about to mark payout for:\n"
        f"👤 {user_name} (ID: `{user_id}`)\n"
        f"💰 Amount: {total_earnings} {settings.CURRENCY_SYMBOL}\n\n"
        f"This will:\n"
        f"• Record the payout in the database\n"
        f"• Notify the user about their referral earnings\n\n"
        f"Continue?"
    )
    
    await state.update_data(payout_user_id=user_id, payout_amount=total_earnings)
    
    await callback.message.edit_text(
        confirm_text,
        parse_mode='Markdown',
        reply_markup=AdminReferralKeyboard.get_confirm_payout_keyboard(user_id)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("process_payout_"))
async def process_payout_callback(callback: types.CallbackQuery, state: FSMContext,
                                   is_admin: bool = False, is_superadmin: bool = False):
    """Process the actual payout"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        
        user = await user_repo.get_user(user_id)
        stats = await referral_repo.get_referral_stats(user_id)
    
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    total_earnings = stats['approved'] * reward_per_student
    
    user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() if user else f"User {user_id}"
    
    try:
        # Notify user about payout
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                f"💰 *Referral Payout Processed*\n\n"
                f"Great news! Your referral earnings have been processed.\n\n"
                f"📊 *Details:*\n"
                f"• Completed Referrals: {stats['approved']}\n"
                f"• Earnings: {total_earnings} {settings.CURRENCY_SYMBOL}\n"
                f"• Date: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                f"💵 The admin will contact you for payment details.\n\n"
                f"Keep referring to earn more! 🎉"
            ),
            parse_mode='Markdown'
        )
        
        result_text = (
            f"✅ *Payout Processed*\n\n"
            f"User {user_name} (ID: `{user_id}`) has been notified.\n\n"
            f"💰 Payout Amount: {total_earnings} {settings.CURRENCY_SYMBOL}\n"
            f"📊 Referrals: {stats['approved']} completed\n\n"
            f"Contact the user to arrange the actual payment transfer."
        )
        
    except Exception as e:
        result_text = (
            f"⚠️ *Payout Recorded (Notification Failed)*\n\n"
            f"User {user_name} (ID: `{user_id}`) payout recorded.\n\n"
            f"💰 Amount: {total_earnings} {settings.CURRENCY_SYMBOL}\n"
            f"❌ Could not notify user: {str(e)}\n\n"
            f"Please contact the user manually."
        )
    
    await callback.message.edit_text(
        result_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_payout")
async def cancel_payout_callback(callback: types.CallbackQuery, state: FSMContext,
                                is_admin: bool = False, is_superadmin: bool = False):
    """Cancel payout process"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await state.clear()
    
    await callback.message.edit_text(
        "◀️ *Payout Cancelled*\n\nThe payout process was cancelled.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


# ============== View User Referrals ==============

@router.callback_query(F.data.startswith("admin_view_user_referrals_"))
async def admin_view_user_referrals_callback(callback: types.CallbackQuery, is_admin: bool = False, is_superadmin: bool = False):
    """View detailed referrals for a specific user"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        user = await user_repo.get_user(user_id)
        user_referrals = await referral_service.get_user_referrals(user_id)
        stats = await referral_repo.get_referral_stats(user_id)
    
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    total_earnings = stats['approved'] * reward_per_student
    
    user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() if user else f"User {user_id}"
    
    detail_text = (
        f"{EMOJIS['gift']} *Referrals for {user_name}*\n\n"
        f"🆔 User ID: `{user_id}`\n\n"
        f"📊 *Stats:*\n"
        f"• Total: {stats['total_sent']}\n"
        f"• Completed: {stats['approved']} (+{stats['approved'] * reward_per_student} {settings.CURRENCY_SYMBOL})\n"
        f"• Pending: {stats['pending']}\n"
        f"• Cancelled: {stats['cancelled']}\n"
        f"• Success Rate: {stats['success_rate']}%\n\n"
    )
    
    if user_referrals:
        detail_text += f"📋 *Recent Referrals:*\n\n"
        for ref in user_referrals[:10]:
            status_emoji = {
                'approved': '✅',
                'pending': '⏳',
                'cancelled': '❌'
            }.get(ref['status'], '❓')
            
            referred_name = ref['referred_user'].get('first_name') or ref['referred_user'].get('username') or 'Unknown'
            created_at = ref['created_at'].strftime('%d %b %Y') if ref['created_at'] else 'N/A'
            earnings = f"+{reward_per_student} {settings.CURRENCY_SYMBOL}" if ref['status'] == 'approved' else ''
            
            detail_text += (
                f"{status_emoji} {referred_name}\n"
                f"   📅 {created_at} {earnings}\n\n"
            )
    else:
        detail_text += "No referrals yet.\n"
    
    await callback.message.edit_text(
        detail_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


# ============== Export Referral Data ==============

@router.callback_query(F.data == "admin_referrals_export")
async def admin_referrals_export_callback(callback: types.CallbackQuery, is_admin: bool = False, is_superadmin: bool = False):
    """Export referral data for accounting"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        top_referrers = await referral_service.get_top_referrers(100)
    
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    
    # Build CSV-like export
    export_text = (
        f"{EMOJIS['file']} *Referral Export*\n\n"
        f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
        f"Format: Rank | User | User ID | Referrals | Earnings\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if top_referrers:
        for i, referrer in enumerate(top_referrers, 1):
            earnings = referrer['referral_count'] * reward_per_student
            export_text += (
                f"{i}. | {escape_markdown_content(referrer['name'])} | `{referrer['user_id']}` | "
                f"{referrer['referral_count']} | {earnings} {settings.CURRENCY_SYMBOL}\n"
            )
        
        total_referrals = sum(r['referral_count'] for r in top_referrers)
        total_earnings = total_referrals * reward_per_student
        export_text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"TOTAL: {total_referrals} referrals | {total_earnings} {settings.CURRENCY_SYMBOL}\n"
        )
    else:
        export_text += "No referral data to export.\n"
    
    export_text += (
        f"\n💡 *Note:* Copy this data for your accounting records.\n"
        f"Use /admin_referrals_payout to process payments."
    )
    
    await callback.message.edit_text(
        export_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()


# ============== Help ==============

@router.callback_query(F.data == "admin_referrals_help")
async def admin_referrals_help_callback(callback: types.CallbackQuery, is_admin: bool = False, is_superadmin: bool = False):
    """Show help for referral management"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    help_text = (
        f"{EMOJIS['help']} *Referral Management Help*\n\n"
        f"📚 *How it works:*\n"
        f"1. Users share their referral code/link\n"
        f"2. New users join using the code\n"
        f"3. When referred user is approved → referral is counted\n"
        f"4. Admin processes payouts periodically\n\n"
        
        f"💰 *Reward System:*\n"
        f"• Each completed referral: {getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)} {settings.CURRENCY_SYMBOL}\n"
        f"• Referrals count only after payment approval\n\n"
        
        f"🔄 *Workflow:*\n"
        f"1. User A shares code with User B\n"
        f"2. User B joins with code → pending referral\n"
        f"3. Admin approves User B's payment → referral completed\n"
        f"4. User A's referral_count incremented\n"
        f"5. Admin views top referrers and processes payouts\n\n"
        
        f"📋 *Menu Options:*\n"
        f"• Top Referrers → View best performers\n"
        f"• All Referrers → Full list with earnings\n"
        f"• Pending → Referrals awaiting approval\n"
        f"• Export → Copy data for accounting\n"
        f"• Payout → Process payment for user"
    )
    
    await callback.message.edit_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await callback.answer()

