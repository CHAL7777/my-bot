"""
Referral Handler - Telegram Quiz Bot
Handle referral commands and display referral information

FIXED: Now properly gets is_admin from data dict for callback handlers
FIXED: Both inline and reply keyboard buttons now work consistently
FIXED: Added missing handler for copy_referral_link callback
FIXED: Consistent keyboard usage between all handlers
FIXED: All handlers use shared helper functions
FIXED: data parameter is optional for all callback handlers
FIXED: Removed duplicate back_to_menu handler (now handled in start.py)
FIXED: Inline handler now uses answer() instead of edit_text() to avoid message too long error
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from typing import Dict, Any

from app.keyboards.menu import MainMenuKeyboard
from app.db.base import get_db
from app.repositories.referral_repo import ReferralRepository
from app.repositories.user_repo import UserRepository
from app.services.referral_service import ReferralService
from app.utils.constants import EMOJIS
from app.config import settings

router = Router()


# ============================================================================
# Shared Helper Functions
# ============================================================================

async def get_referral_data(user_id: int) -> Dict[str, Any]:
    """
    Get all referral data for a user.
    
    Returns:
        Dict with referral_code, referral_link, stats, top_referrers, and referral_balance
    """
    referral_code = None
    referral_link = None
    stats = None
    top_referrers = []
    referral_balance = 0
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)

        # Get or create referral code
        referral_code = await referral_service.get_referral_code(user_id)
        referral_link = await referral_service.get_referral_link(user_id)
        
        # Get optimized stats
        stats = await referral_repo.get_referral_stats(user_id)
        
        # Get top referrers
        top_referrers = await referral_service.get_top_referrers(5)
        
        # Get user's referral balance
        user = await user_repo.get_user(user_id)
        referral_balance = getattr(user, 'referral_balance', 0) or 0 if user else 0
    
    return {
        'referral_code': referral_code,
        'referral_link': referral_link,
        'stats': stats,
        'top_referrers': top_referrers,
        'referral_balance': referral_balance
    }


def build_referral_message(data: Dict[str, Any]) -> str:
    """Build the comprehensive referral message text."""
    referral_code = data['referral_code']
    referral_link = data['referral_link']
    stats = data['stats']
    top_referrers = data['top_referrers']
    referral_balance = data.get('referral_balance', 0)
    
    currency_symbol = getattr(settings, 'CURRENCY_SYMBOL', 'Birr')
    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    total_earnings = stats['approved'] * reward_per_student
    
    referral_msg = (
        f"{EMOJIS['gift']} Referral Program\n\n"
        f"💰 Earn {reward_per_student} {currency_symbol} per Student!\n"
        f"Invite friends using your referral link.\n\n"
        f"📋 You earn {reward_per_student} {currency_symbol} for each student who joins and gets approved.\n\n"
        f"⏰ Earnings are added after approval only.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Your Referral Code:\n"
        f"`{referral_code}`\n\n"
        f"Your Referral Link:\n"
        f"`{referral_link}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Your Referral Stats:*\n"
        f"• Total Sent: {stats['total_sent']}\n"
        f"• Approved: {stats['approved']}\n"
        f"• Pending: {stats['pending']}\n"
        f"• Cancelled: {stats['cancelled']}\n"
        f"• Success Rate: {stats['success_rate']}%\n\n"
        f"💵 *Total Earnings:* {total_earnings} {currency_symbol}\n"
        f"💰 *Referral Balance:* {referral_balance:.2f} {currency_symbol}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if top_referrers:
        referral_msg += f"🏆 *Top Referrers:*\n"
        for i, referrer in enumerate(top_referrers, 1):
            referral_msg += f"{i}. {referrer['name']} - {referrer['referral_count']} referrals\n"
        referral_msg += "\n"

    how_it_works = (
        f"📖 *How it works:*\n"
        f"1. Share your referral link with friends\n"
        f"2. When they join using your link and get approved\n"
        f"3. You earn {reward_per_student} {currency_symbol} per student!\n\n"
        f"📤 *Share on:*\n"
        f"• Telegram • WhatsApp • Other apps\n\n"
        f"✨ Just send them the link above!"
    )
    referral_msg += how_it_works
    
    return referral_msg


# ============================================================================
# Message Handlers
# ============================================================================

@router.message(Command("referral"))
@router.message(Command("referrals"))
async def referral_command(message: types.Message, is_admin: bool = False):
    """Show user's referral stats and referral link - OPTIMIZED VERSION"""
    user_id = message.from_user.id

    # Use shared helper function to get all data
    data = await get_referral_data(user_id)

    # Build message using shared function
    referral_msg = build_referral_message(data)

    # Use reply keyboard (same buttons as inline but working as text commands)
    await message.answer(
        referral_msg,
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_referral_reply_keyboard()
    )


# ============================================================================
# Callback Query Handlers
# ============================================================================

@router.callback_query(F.data == "my_referrals")
async def my_referrals_callback(callback: types.CallbackQuery, data: Dict[str, Any] = None):
    """
    Handle my referrals inline callback.
    
    FIXED: Now sends a NEW message instead of editing (avoids message too long error).
    Uses the same message and keyboard as referral_command for consistency.
    
    Note: data parameter is optional to handle cases where middleware doesn't inject it.
    """
    user_id = callback.from_user.id
    
    # Use shared helper function to get all data
    referral_data = await get_referral_data(user_id)
    
    # Build message using shared function
    referral_msg = build_referral_message(referral_data)
    
    # Use answer() to send a NEW message (like reply keyboard does)
    # This avoids "message is too long" error that occurs with edit_text()
    await callback.message.answer(
        referral_msg,
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_referral_keyboard(
            referral_data['referral_link'],
            referral_data['referral_code']
        )
    )
    await callback.answer()


@router.callback_query(F.data == "copy_referral_code")
async def copy_referral_code_callback(callback: types.CallbackQuery, data: Dict[str, Any] = None):
    """Handle copy referral code callback - shows alert with code"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)

        referral_code = await referral_service.get_referral_code(user_id)

    await callback.answer(
        f"📋 Your Code: {referral_code}\n\nTap to copy!", 
        show_alert=True
    )


@router.callback_query(F.data == "copy_referral_link")
async def copy_referral_link_callback(callback: types.CallbackQuery, data: Dict[str, Any] = None):
    """Handle copy referral link callback - shows alert with link"""
    user_id = callback.from_user.id

    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)

        referral_link = await referral_service.get_referral_link(user_id)

    await callback.answer(
        f"🔗 Your Link:\n{referral_link}", 
        show_alert=True
    )


@router.callback_query(F.data == "referral_leaderboard")
async def referral_leaderboard_callback(callback: types.CallbackQuery, data: Dict[str, Any] = None):
    """Show top referrers leaderboard"""
    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)

        top_referrers = await referral_service.get_top_referrers(20)

    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    currency_symbol = getattr(settings, 'CURRENCY_SYMBOL', 'Birr')
    
    leaderboard_text = (
        f"{EMOJIS['trophy']} Top Referrers Leaderboard\n\n"
        f"The most active referrers:\n\n"
    )

    if top_referrers:
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, referrer in enumerate(top_referrers, 1):
            medal = medals.get(i, "")
            leaderboard_text += f"{medal} #{i} {referrer['name']} - {referrer['referral_count']} referrals\n"
    else:
        leaderboard_text += f"No referrers yet. Be the first!\n"

    leaderboard_text += (
        f"\n💡 *Tip:* Share your referral link to climb the leaderboard!\n"
        f"Earn {reward_per_student} {currency_symbol} per approved student."
    )

    await callback.message.edit_text(
        leaderboard_text,
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_back_to_referral_keyboard()
    )
    await callback.answer()


# Note: back_to_menu callback is handled in start.py to avoid duplicate handlers
# since start.router is registered before referral.router in bot.py

