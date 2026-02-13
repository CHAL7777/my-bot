from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from typing import Dict, Any

from app.keyboards.menu import MainMenuKeyboard
from app.services.user_service import UserService
from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.contact_repo import ContactMessageRepository
from app.config import settings
from app.utils.safe_edit import edit_text_safe
from app.utils.helpers import escape_markdown
from app.keyboards.menu import (
    generate_progress_bar, get_time_of_day_greeting,
    format_streak_days, get_subscription_badge
)

import logging
logger = logging.getLogger(__name__)

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()


class ContactStates(StatesGroup):
    """FSM states for contact message flow"""
    waiting_for_category = State()
    waiting_for_message = State()


@router.message(CommandStart())
async def command_start(message: Message, state: FSMContext, is_admin: bool = False):
    """
    Handle /start command - initial user registration.
    
    Note: is_admin is injected by AuthMiddleware, has_active_subscription by SubscriptionMiddleware.
    
    IMPORTANT: New users are now auto-registered by the SubscriptionMiddleware
    before this handler is called. This handler just shows the welcome message.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        attempt_repo = AttemptRepository(session)
        
        from app.repositories.question_repo import QuestionRepository
        question_repo = QuestionRepository(session)
        user_service = UserService(user_repo, payment_repo, attempt_repo, question_repo)
        
        # Get or create user (middleware already registered them)
        # This is idempotent - safe to call again
        result = await user_service.register_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        user = result.get('user')
        is_new_user = result.get('is_new', False)
        
        # ================================================================
        # Process referral code if present in /start command
        # OPTIMIZED: Check for existing referral FIRST to avoid redundant processing
        # ================================================================
        referral_processed = False
        referral_debug_info = {'code_found': False, 'referrer_found': False, 'referral_created': False}
        
        if is_new_user and message.text:
            # Import here to avoid circular imports
            from app.services.referral_service import ReferralService
            from app.repositories.referral_repo import ReferralRepository
            
            referral_service = ReferralService(
                referral_repo=ReferralRepository(session), 
                user_repo=user_repo
            )
            
            # Parse referral code from the command text
            referral_code = await referral_service.parse_referral_code_from_start(message.text)
            
            if referral_code:
                referral_debug_info['code_found'] = True
                referral_debug_info['code'] = referral_code
                print(f"[START DEBUG] Found referral code: {referral_code} for user {user_id}")
                
                # OPTIMIZATION: Check if user was already referred BEFORE looking up referrer
                # This saves a DB query if the user already has a referral record
                existing_referral_status = await referral_service.get_referral_status(user_id)
                
                if existing_referral_status:
                    # User already has a referral - skip processing
                    referral_debug_info['already_referred'] = True
                    print(f"[START] User {user_id} already has referral status: {existing_referral_status}")
                else:
                    # No existing referral - proceed with processing
                    referrer = await referral_service.get_user_by_referral_code(referral_code)
                    
                    if referrer:
                        referral_debug_info['referrer_found'] = True
                        referral_debug_info['referrer_id'] = referrer.user_id
                        print(f"[START] Found referrer: user_id={referrer.user_id}, username={getattr(referrer, 'username', None)}")
                        
                        # Update user's referred_by field immediately
                        await user_repo.update_user(user_id, referred_by=referrer.user_id)
                        print(f"[START] Updated user {user_id} with referred_by={referrer.user_id}")
                        
                        # Process the referral
                        process_result = await referral_service.process_referral(
                            referrer_id=referrer.user_id,
                            referred_id=user_id
                        )
                        
                        if process_result.get('success') and process_result.get('referral_created'):
                            referral_processed = True
                            referral_debug_info['referral_created'] = True
                            print(f"[START] Referral processed: referrer={referrer.user_id}, referred={user_id}")
                        else:
                            print(f"[START] Referral processing result: {process_result}")
                    else:
                        print(f"[START] Referral code {referral_code} not found - user might have invalid code")
            
            # Log all referral debug info
            print(f"[START REFERRAL DEBUG] user_id={user_id}, data={referral_debug_info}")
        
        # Escape first_name to prevent Markdown parse errors
        # (e.g., underscores in names like "John_Smith" would break Markdown)
        safe_first_name = escape_markdown(first_name or 'there')
        
        # Welcome message based on user status
        if is_new_user:
            welcome_msg = (
                f"Welcome {safe_first_name}!\n\n"
                "I'm your Quiz Bot, ready to help you learn through practice quizzes!\n\n"
                "What I offer:\n"
                "- Chapter-wise quizzes (Simple/Medium/Hard)\n"
                "- Track progress & identify weak areas\n"
                "- Compete on leaderboards\n"
                "- Free Simple level | Premium for Medium/Hard\n\n"
            )
            
            if result.get('has_trial'):
                welcome_msg += (
                    f"Free Trial Activated!\n"
                    f"You have {result.get('trial_days', 0)} days of premium access!\n\n"
                )
            
            welcome_msg += "Tap the buttons below to get started!"
            
            # Log new user registration
            print(f"[START] New user registered: user_id={user_id}, username={username}")
            
        else:
            welcome_msg = (
                f"Welcome back, {safe_first_name}!\n\n"
                "Ready for another learning session? 🚀\n\n"
                "🎯 Start Quiz - Test your knowledge\n"
                "📊 My Progress - View your performance\n"
                "🏆 Leaderboard - Compete with others\n"
                "💰 Upgrade - Get full access\n\n"
                "What would you like to do today?"
            )
        
        # Send welcome message - use ReplyKeyboard for initial /start command
        await message.answer(
            welcome_msg,
            parse_mode=None,  # Send as plain text to avoid parse errors
            reply_markup=MainMenuKeyboard.get_main_menu(is_admin)
        )
        
        await state.clear()


@router.message(Command("help"))
async def command_help(message: Message, is_admin: bool = False):
    """
    Handle /help command.
    
    Note: is_admin is injected by AuthMiddleware.
    """
    help_text = (
        "Quiz Bot Help Guide\n\n"
        "Getting Started:\n"
        "1. Tap Start Quiz or use /quiz\n"
        "2. Choose Subject -> Chapter -> Difficulty level\n"
        "3. Answer multiple-choice questions\n"
        "4. Get instant feedback with explanations\n\n"
        "Subscription & Payment:\n"
        "- Simple quizzes are FREE\n"
        "- Premium (Medium/Hard): One-time lifetime access\n"
        "- Use /payment to subscribe\n\n"
        "How to Pay:\n"
        "1. Use /payment to get payment details\n"
        "2. Transfer payment\n"
        "3. Send screenshot here\n"
        "4. Admin will verify and activate your access\n\n"
        "Need more help? Just ask!"
    )
    
    if is_admin:
        help_text += "\nAdmin Commands:\n"
        help_text += "/admin - Admin dashboard\n"
        help_text += "/admin_stats - System statistics\n"
        help_text += "/admin_users - Manage users\n"
    
    await message.answer(
        help_text,
        parse_mode=None
    )


@router.message(Command("about"))
async def command_about(message: Message):
    """Handle /about command"""
    about_text = (
        "Quiz Bot for Remedial Students\n\n"
        "Purpose:\n"
        "Help students improve through targeted practice quizzes with instant feedback.\n\n"
        "Features:\n"
        "- Adaptive learning paths\n"
        "- Progress analytics\n"
        "- Competitive leaderboards\n"
        "- Chapter-wise difficulty levels\n\n"
        "Developer:\n"
        "Built with love for educational purposes\n"
        "Using Python, aiogram, and PostgreSQL\n\n"
        "Support:\n"
        "Contact admin for assistance or feature requests."
    )
    
    await message.answer(
        about_text,
        parse_mode=None
    )


@router.message(Command("contact"))
async def command_contact(message: Message):
    """Handle /contact command - Start support contact flow"""
    contact_text = (
        "💬 *Contact Support*\n\n"
        "Need help? Our team is here to assist you with:\n\n"
        "• Payment or subscription issues\n"
        "• Premium access problems\n"
        "• Quiz errors or bugs\n"
        "• General questions\n"
        "• Feedback or suggestions\n\n"
        "Tap *Send Message* to proceed!"
    )

    await message.answer(
        contact_text,
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_contact_start_keyboard()
    )


@router.message(lambda message: message.text and "Main Menu" in message.text)
async def main_menu_handler(message: Message, is_admin: bool = False):
    """Handle main menu button - uses ReplyKeyboard for consistency"""
    await message.answer(
        "Main Menu\n\n"
        "Choose what you'd like to do:",
        parse_mode=None,
        reply_markup=MainMenuKeyboard.get_main_menu(is_admin)
    )


@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """
    Handle back to menu callback.
    
    FIX: Use get_main_menu_inline() instead of get_main_menu() because
    edit_text() requires InlineKeyboardMarkup, not ReplyKeyboardMarkup.
    """
    await callback.message.edit_text(
        "Main Menu\n\n"
        "Choose what you'd like to do:",
        parse_mode=None,
        reply_markup=MainMenuKeyboard.get_main_menu_inline(is_admin)
    )
    await callback.answer()


@router.message(lambda message: message.text and "My Progress" in message.text)
async def progress_button_handler(message: Message, state: FSMContext,
                                  has_active_subscription: bool = False):
    """
    Handle progress button from main menu (reply keyboard).
    
    Note: has_active_subscription is injected by SubscriptionMiddleware.
    """
    from app.handlers.progress import command_progress
    await command_progress(message, state, has_active_subscription)


@router.message(lambda message: message.text and "Leaderboard" in message.text)
async def leaderboard_button_handler(message: Message):
    """Handle leaderboard button from main menu"""
    from app.handlers.leaderboard import command_leaderboard
    await command_leaderboard(message)


@router.message(lambda message: message.text and "Subscription" in message.text)
async def payment_button_handler(message: Message, state: FSMContext,
                                  has_active_subscription: bool = False):
    """
    Handle payment button from main menu (reply keyboard).
    
    Note: has_active_subscription is injected by SubscriptionMiddleware
    via the data dict. We pass it through to payment_command.
    """
    from app.handlers.payment import payment_command
    # The handler will receive has_active_subscription from middleware
    await payment_command(message, state, has_active_subscription)


@router.message(lambda message: message.text and "Admin Panel" in message.text)
async def admin_button_handler(message: Message, is_admin: bool = False,
                               is_superadmin: bool = False):
    """Handle admin button from main menu"""
    if not is_admin:
        await message.answer("Access denied. Admin only.")
        return
    
    from app.handlers.admin import admin_command
    await admin_command(message, is_admin, is_superadmin)


@router.message(lambda message: message.text and "Referrals" in message.text)
async def referral_button_handler(message: types.Message, is_admin: bool = False):
    """Handle referrals button from main menu (reply keyboard)"""
    from app.handlers.referral import referral_command
    await referral_command(message, is_admin)


# ============================================================================
# Referral Reply Keyboard Button Handlers
# These handle buttons from the referral reply keyboard
# ============================================================================

@router.message(lambda message: message.text and "Share Link" in message.text)
async def share_link_handler(message: types.Message, is_admin: bool = False):
    """Handle Share Link button from referral reply keyboard"""
    from app.keyboards.menu import MainMenuKeyboard
    from app.services.referral_service import ReferralService
    from app.repositories.referral_repo import ReferralRepository
    from app.repositories.user_repo import UserRepository
    from app.db.base import get_db
    from app.config import settings

    user_id = message.from_user.id

    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)

        referral_link = await referral_service.get_referral_link(user_id)
        referral_code = await referral_service.get_referral_code(user_id)

    reward_per_student = getattr(settings, 'REFERRAL_REWARD_PER_STUDENT', 20)
    currency_symbol = getattr(settings, 'CURRENCY_SYMBOL', 'Birr')

    # Create share text for Telegram
    share_text = (
        f"🎯 Join Quiz Bot!\n"
        f"Use my referral link to join:\n"
        f"{referral_link}\n\n"
        f"💰 Earn {reward_per_student} {currency_symbol} per student!"
    )

    # URL encode for Telegram share URL
    from urllib.parse import quote
    encoded_text = quote(share_text, safe='')
    encoded_url = quote(referral_link, safe='')

    # Create Telegram share URL
    telegram_share_url = f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"

    await message.answer(
        f"📤 Share your referral link:\n\n"
        f"Your link: `{referral_link}`\n\n"
        f"Tap the button below to share on Telegram!",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_referral_keyboard(referral_link, referral_code)
    )


@router.message(lambda message: message.text and "Copy Code" in message.text)
async def copy_code_handler(message: types.Message, is_admin: bool = False):
    """Handle Copy Code button from referral reply keyboard"""
    from app.keyboards.menu import MainMenuKeyboard
    from app.services.referral_service import ReferralService
    from app.repositories.referral_repo import ReferralRepository
    from app.repositories.user_repo import UserRepository
    from app.db.base import get_db

    user_id = message.from_user.id

    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)

        referral_code = await referral_service.get_referral_code(user_id)

    await message.answer(
        f"📋 Your Referral Code:\n\n"
        f"`{referral_code}`\n\n"
        f"Tap to copy!",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_referral_reply_keyboard()
    )


@router.message(lambda message: message.text and "Copy Link" in message.text)
async def copy_link_handler(message: types.Message, is_admin: bool = False):
    """Handle Copy Link button from referral reply keyboard"""
    from app.keyboards.menu import MainMenuKeyboard
    from app.services.referral_service import ReferralService
    from app.repositories.referral_repo import ReferralRepository
    from app.repositories.user_repo import UserRepository
    from app.db.base import get_db

    user_id = message.from_user.id

    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)

        referral_link = await referral_service.get_referral_link(user_id)

    await message.answer(
        f"🔗 Your Referral Link:\n\n"
        f"`{referral_link}`\n\n"
        f"Tap to copy!",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_referral_reply_keyboard()
    )


@router.message(lambda message: message.text and "Leaderboard" in message.text)
async def referral_leaderboard_handler(message: types.Message, is_admin: bool = False):
    """Handle Leaderboard button from referral reply keyboard"""
    from app.keyboards.menu import MainMenuKeyboard
    from app.services.referral_service import ReferralService
    from app.repositories.referral_repo import ReferralRepository
    from app.repositories.user_repo import UserRepository
    from app.db.base import get_db
    from app.config import settings

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

    await message.answer(
        leaderboard_text,
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_referral_reply_keyboard()
    )


@router.message(lambda message: message.text and "Back to Menu" in message.text)
async def referral_back_to_menu_handler(message: types.Message, is_admin: bool = False):
    """Handle Back to Menu button from referral reply keyboard"""
    await message.answer(
        "Main Menu\n\n"
        "Choose what you'd like to do:",
        parse_mode=None,
        reply_markup=MainMenuKeyboard.get_main_menu(is_admin)
    )


@router.message(lambda message: message.text and "Help" in message.text)
async def help_button_handler(message: Message, is_admin: bool = False):
    """Handle help button from main menu (reply keyboard)"""
    help_text = (
        "Quiz Bot Help Guide\n\n"
        "Getting Started:\n"
        "1. Tap Start Quiz or use /quiz\n"
        "2. Choose Subject -> Chapter -> Difficulty level\n"
        "3. Answer multiple-choice questions\n"
        "4. Get instant feedback with explanations\n\n"
        "Subscription & Payment:\n"
        "- Simple quizzes are FREE\n"
        "- Premium (Medium/Hard): One-time lifetime access\n"
        "- Use /payment to subscribe\n\n"
        "How to Pay:\n"
        "1. Use /payment to get payment details\n"
        "2. Transfer payment\n"
        "3. Send screenshot here\n"
        "4. Admin will verify and activate your access\n\n"
        "Need more help? Just ask!"
    )
    
    await message.answer(
        help_text,
        parse_mode=None,
        reply_markup=MainMenuKeyboard.get_main_menu(is_admin)
    )


@router.message(lambda message: message.text and "Contact" in message.text)
async def contact_button_handler(message: Message):
    """Handle contact button from main menu (reply keyboard)"""
    # Reuse the command_contact function logic
    await command_contact(message)


@router.message(lambda message: message.text and "Weak Areas" in message.text)
async def weak_areas_button_handler(message: Message, state: FSMContext,
                                   has_active_subscription: bool = False):
    """Handle Weak Areas button from main menu (reply keyboard)
    
    FIX: Send a NEW message instead of trying to edit the old one.
    ReplyKeyboard buttons send a NEW message, so we must use answer() not edit_text().
    """
    from app.keyboards.menu import MainMenuKeyboard
    from app.keyboards.quiz import QuizKeyboard
    from app.repositories.question_repo import QuestionRepository
    from app.db.base import get_db
    from app.utils.helpers import generate_progress_bar
    from app.utils.constants import EMOJIS
    
    user_id = message.from_user.id
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        try:
            weak_chapters = await question_repo.get_weak_chapters(user_id, limit=10)
            
            if not weak_chapters:
                weak_msg = (
                    "✅ *No Weak Areas Identified!*\n\n"
                    "Great job! You don't have any identified weak areas yet.\n\n"
                    "Keep practicing and the system will identify areas "
                    "where you can improve as you answer more questions."
                )
                
                await message.answer(
                    weak_msg,
                    parse_mode='Markdown',
                    reply_markup=MainMenuKeyboard.get_progress_options_keyboard()
                )
            else:
                weak_msg = (
                    "📚 *Areas Needing Improvement*\n\n"
                    "Based on your performance, here are areas where you can focus:\n\n"
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
                    "💡 *Recommendations:*\n"
                    "• Practice these chapters more\n"
                    "• Start with Simple difficulty\n"
                    "• Review explanations carefully\n"
                )
                
                # Use the proper weak areas keyboard that handles practice callbacks
                keyboard = QuizKeyboard.get_weak_areas_keyboard(weak_chapters)
                
                await message.answer(
                    weak_msg,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            await message.answer(
                f"❌ Error loading weak areas: {str(e)}",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )


@router.message(lambda message: message.text and "Start Quiz" in message.text)
async def start_quiz_button_handler(message: Message, state: FSMContext,
                                    data: Dict[str, Any] = None):
    """
    Handle Start Quiz button from main menu (reply keyboard).
    
    FIX: Now receives data dict from SubscriptionMiddleware which contains
    access_result, to ensure consistent authorization with inline handler.
    
    Args:
        message: The message object
        state: FSMContext for state management
        data: Full data dict from middleware (contains access_result)
    """
    from app.handlers.quiz import start_quiz_flow
    
    user_id = message.from_user.id
    
    # Pass user_id for consistent authorization (safe_sender auto-created)
    await start_quiz_flow(message, state, user_id)


# ============================================================================
# NEW: Inline callback handlers for navigation
# These handle the inline keyboard callbacks after edit_text operations
# ============================================================================

@router.callback_query(lambda c: c.data == "start_quiz")
async def inline_start_quiz_callback(callback: types.CallbackQuery, state: FSMContext,
                                     data: Dict[str, Any] = None):
    """
    Handle start_quiz inline callback.
    
    FIX: Now receives data dict from SubscriptionMiddleware which contains
    access_result, to ensure consistent authorization with button handler.
    
    Both this callback and start_quiz_button_handler now use identical authorization flow.
    
    Args:
        callback: The callback query object
        state: FSMContext for state management
        data: Full data dict from middleware (contains access_result)
    """
    from app.handlers.quiz import start_quiz_flow
    
    user_id = callback.from_user.id
    
    # Clear any existing state to ensure clean start
    # IMPORTANT: Do NOT set the state here - let start_quiz_flow do it
    # If we set it before calling start_quiz_flow, it will skip sending the message
    current_state = await state.get_state()
    if current_state is not None:
        logger.info(f"[QUIZ] Clearing existing state {current_state} for user {user_id}")
        await state.clear()
    
    # Call start_quiz_flow - it will set the state and send the subject selection
    try:
        await start_quiz_flow(callback, state, user_id)
    except Exception as e:
        # Handle "message not modified" error gracefully
        if "message is not modified" in str(e).lower():
            logger.debug(f"[QUIZ] Message not modified for user {user_id}")
        else:
            logger.error(f"[QUIZ] Error in start_quiz_flow for user {user_id}: {e}")
            raise  # Re-raise other errors
    await callback.answer()


@router.callback_query(lambda c: c.data == "my_progress")
async def inline_my_progress_callback(callback: types.CallbackQuery, state: FSMContext,
                                      has_active_subscription: bool = False):
    """Handle my_progress inline callback"""
    from app.handlers.progress import progress_overview_callback
    await progress_overview_callback(callback, state, has_active_subscription)


@router.callback_query(lambda c: c.data == "leaderboard")
async def inline_leaderboard_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle leaderboard inline callback"""
    from app.handlers.leaderboard import command_leaderboard
    await command_leaderboard(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "subscription")
async def inline_subscription_callback(callback: types.CallbackQuery, state: FSMContext,
                                       has_active_subscription: bool = False):
    """Handle subscription inline callback"""
    from app.handlers.payment import payment_command
    # The handler will receive has_active_subscription from middleware
    await payment_command(callback.message, state, has_active_subscription)
    await callback.answer()


@router.callback_query(lambda c: c.data == "help")
async def inline_help_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle help inline callback"""
    help_text = (
        "Quiz Bot Help Guide\n\n"
        "Getting Started:\n"
        "1. Tap Start Quiz or use /quiz\n"
        "2. Choose Subject -> Chapter -> Difficulty level\n"
        "3. Answer multiple-choice questions\n"
        "4. Get instant feedback with explanations\n\n"
        "Subscription & Payment:\n"
        "- Simple quizzes are FREE\n"
        "- Premium (Medium/Hard): One-time lifetime access\n"
        "- Use /payment to subscribe\n\n"
        "How to Pay:\n"
        "1. Use /payment to get payment details\n"
        "2. Transfer payment\n"
        "3. Send screenshot here\n"
        "4. Admin will verify and activate your access\n\n"
        "Need more help? Just ask!"
    )
    
    await callback.message.edit_text(
        help_text,
        parse_mode=None,
        reply_markup=MainMenuKeyboard.get_main_menu_inline(is_admin)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "contact")
async def inline_contact_callback(callback: types.CallbackQuery):
    """Handle contact inline callback"""
    # Reuse the command_contact function logic
    await command_contact(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_contact")
async def back_to_contact_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to contact start callback"""
    await state.clear()  # Clear any FSM state
    
    await callback.message.edit_text(
        "💬 *Contact Support*\n\n"
        "Need help? Our team is here to assist you with:\n\n"
        "• Payment or subscription issues\n"
        "• Premium access problems\n"
        "• Quiz errors or bugs\n"
        "• General questions\n"
        "• Feedback or suggestions\n\n"
        "Tap *Send Message* to proceed!",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_contact_start_keyboard()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_contact")
async def cancel_contact_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle cancel contact callback - returns to main contact screen"""
    await state.clear()  # Clear any FSM state
    
    await callback.message.edit_text(
        "💬 *Contact Support*\n\n"
        "Need help? Our team is here to assist you with:\n\n"
        "• Payment or subscription issues\n"
        "• Premium access problems\n"
        "• Quiz errors or bugs\n"
        "• General questions\n"
        "• Feedback or suggestions\n\n"
        "Tap *Send Message* to proceed!",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_contact_start_keyboard()
    )
    await callback.answer()



    """Handle admin_panel inline callback"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    from app.handlers.admin import admin_command
    await admin_command(callback.message, is_admin, is_superadmin)
    await callback.answer()





# ============================================================================
# Contact Message Flow Handlers (FSM-based)
# ============================================================================

@router.callback_query(lambda c: c.data == "contact_new")
async def contact_new_callback(callback: types.CallbackQuery, state: FSMContext):
    """Start new contact message flow"""
    user_id = callback.from_user.id
    
    # Check rate limit in database
    async for session in get_db():
        contact_repo = ContactMessageRepository(session)
        can_send, next_allowed = await contact_repo.can_send_contact_request(user_id)
        
        if not can_send and next_allowed:
            # Calculate remaining time
            from datetime import timedelta
            remaining = next_allowed - callback.message.date.replace(tzinfo=None)
            minutes_left = int(remaining.total_seconds() / 60)
            
            await callback.answer(
                f"You've already submitted a support request recently. "
                f"Please wait {minutes_left} minutes before sending another.",
                show_alert=True
            )
            return
    
    await state.set_state(ContactStates.waiting_for_category)
    await state.update_data({'contact_category': None})

    await callback.message.edit_text(
        "Contact Admin - New Message\n\n"
        "Select a category for your message:\n\n"
        "- Payment Issues - Subscriptions, payments, refunds\n"
        "- Quiz Errors - Bugs, incorrect answers\n"
        "- Access Problems - Account, login, permissions\n"
        "- General Questions - How to use features\n"
        "- Feedback - Suggestions, improvements",
        parse_mode=None,
        reply_markup=MainMenuKeyboard.get_contact_category_keyboard()
    )
    await callback.answer()


@router.callback_query(ContactStates.waiting_for_category)
async def contact_category_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle contact category selection"""
    data = callback.data

    # Map callback data to category names
    category_map = {
        'contact_category_payment': 'Payment Issues',
        'contact_category_quiz_error': 'Quiz Errors',
        'contact_category_access': 'Access Problems',
        'contact_category_general': 'General Questions',
        'contact_category_feedback': 'Feedback'
    }

    if data in category_map:
        category_key = data.replace('contact_category_', '')
        await state.update_data({'contact_category': category_key})

        # Update message to show selected category
        await callback.message.edit_text(
            f"Contact Admin\n\n"
            f"Category: {category_map[data]}\n\n"
            f"Please describe your issue:\n\n"
            f"Be as detailed as possible:\n"
            f"- What happened?\n"
            f"- When did it occur?\n"
            f"- Any error messages?\n"
            f"- Your user ID (if relevant): {callback.from_user.id}\n\n"
            f"Tip: You can also attach screenshots after sending your message.",
            parse_mode=None,
            reply_markup=MainMenuKeyboard.get_cancel_contact_keyboard()
        )

        await state.set_state(ContactStates.waiting_for_message)
        await callback.answer()
    elif data == 'back_to_menu':
        await state.clear()
        await callback.message.edit_text(
            "Main Menu\n\n"
            "Choose what you'd like to do:",
            parse_mode=None,
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
        await callback.answer()


@router.message(ContactStates.waiting_for_message, F.text)
async def contact_message_handler(message: types.Message, state: FSMContext):
    """Handle the contact message text from user"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Unknown"
    username = message.from_user.username

    # Get the selected category from state
    data = await state.get_data()
    category = data.get('contact_category', 'general')

    # Category display names
    category_display = {
        'payment': 'Payment Issues',
        'quiz_error': 'Quiz Errors',
        'access': 'Access Problems',
        'general': 'General Questions',
        'feedback': 'Feedback'
    }

    try:
        # Save the message to database
        async for session in get_db():
            contact_repo = ContactMessageRepository(session)
            contact_message = await contact_repo.create_message(
                user_id=user_id,
                category=category,
                message_text=message.text
            )
            ticket_id = contact_message.ticket_id
            message_id = contact_message.message_id

            # Send confirmation to user with ticket ID
            await message.answer(
                f"Your support request has been received\n\n"
                f"Category: {category_display.get(category, 'General')}\n"
                f"Ticket ID: {ticket_id}\n"
                f"Time: {contact_message.created_at.strftime('%d %b %Y %H:%M')}\n\n"
                f"What happens next?\n"
                f"- Our admin team will review your request\n"
                f"- You'll receive a response within 24 hours\n"
                f"- Response will be sent directly to this chat\n\n"
                f"Please save your Ticket ID ({ticket_id}) for reference!\n\n"
"Rate Limit: You can send another request in 10 minutes.",
                parse_mode=None,
                reply_markup=MainMenuKeyboard.get_contact_message_keyboard()
            )

            # Clear state
            await state.clear()

            # Notify all admins about new contact message
            await notify_admins_about_contact(
                message.bot,
                ticket_id,
                message_id,
                user_id,
                user_name,
                username,
                category,
                message.text
            )

    except Exception as e:
        await message.answer(
            f"Error sending message\n\n"
            f"Details: {str(e)}\n\n"
            f"Please try again or contact support directly.",
            parse_mode=None
        )
        await state.clear()


@router.message(ContactStates.waiting_for_message)
async def contact_invalid_handler(message: types.Message):
    """Handle invalid input in contact message state"""
    await message.answer(
        "Invalid Input\n\n"
        "Please type your message as text.\n\n"
        "Describe your issue in detail and send it as a message.",
        parse_mode=None
    )


async def notify_admins_about_contact(
    bot,
    ticket_id: str,
    message_id: int,
    user_id: int,
    user_name: str,
    username: str,
    category: str,
    message_text: str
):
    """Notify all admins about a new contact message - using database + env fallback"""
    from datetime import datetime
    from app.repositories.admin_repo import TelegramAdminRepository

    # Category display names
    category_display = {
        'payment': 'Payment Issues',
        'quiz_error': 'Quiz Errors',
        'access': 'Access Problems',
        'general': 'General Questions',
        'feedback': 'Feedback'
    }

    # Truncate message if too long
    display_text = message_text[:500] + "..." if len(message_text) > 500 else message_text

    # Build notification message
    notification_text = (
        f"🆕 *New Support Ticket: {ticket_id}*\n\n"
        f"👤 *User Info:*\n"
        f"• Name: {user_name}\n"
        f"• Username: @{username or 'N/A'}\n"
        f"• User ID: \`{user_id}\`\n\n"
        f"📁 *Category:* {category_display.get(category, category)}\n"
        f"⏰ *Time:* {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 *Message:*\n{display_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 *Quick Actions:*\n"
        f"• Reply: \`/reply {ticket_id} <your reply>\`\n"
        f"• View all: \`/admin_messages\`\n"
        f"• Close: \`/close {ticket_id}\`"
    )

    # Collect admin IDs from multiple sources
    admin_ids_to_notify = set()

    # 1. First, try to get admins from database (most reliable)
    try:
        async for session in get_db():
            admin_repo = TelegramAdminRepository(session)
            db_admins = await admin_repo.get_active_admins()
            for admin in db_admins:
                if admin.user_id:
                    admin_ids_to_notify.add(admin.user_id)
    except Exception as e:
        print(f"Error fetching admins from database: {e}")

    # 2. Also check settings.ADMIN_IDS (env var fallback)
    try:
        if hasattr(settings, 'ADMIN_IDS') and settings.ADMIN_IDS:
            for admin_id in settings.ADMIN_IDS:
                admin_ids_to_notify.add(admin_id)
    except Exception as e:
        print(f"Error reading ADMIN_IDS from settings: {e}")

    # Send notification to all collected admin IDs
    notified_count = 0
    for admin_id in admin_ids_to_notify:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            notified_count += 1
            print(f"✅ Notified admin {admin_id} about ticket {ticket_id}")
        except Exception as e:
            print(f"❌ Failed to notify admin {admin_id}: {e}")

    if notified_count == 0:
        print(f"⚠️ No admins were notified about ticket {ticket_id}! Check ADMIN_IDS env var or database.")
    else:
        print(f"✅ Notified {notified_count} admins about ticket {ticket_id}")


# ============================================================================
# Enhanced Menu Callback Handlers
# ============================================================================

@router.callback_query(lambda c: c.data == "menu_quick_quiz")
async def menu_quick_quiz_callback(callback: types.CallbackQuery, state: FSMContext,
                                   data: Dict[str, Any] = None):
    """
    Handle quick quiz callback - starts a 5-question quiz.
    
    This is a simplified entry point for users who want to take a quick quiz
    without going through subject/chapter selection.
    """
    from app.handlers.quiz import start_quiz_flow
    
    user_id = callback.from_user.id
    
    # Start quiz flow - now uses 3 args (plain_sender auto-created internally)
    await start_quiz_flow(callback, state, user_id)
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu_continue")
async def menu_continue_callback(callback: types.CallbackQuery, state: FSMContext):
    """
    Handle continue quiz callback - resumes an in-progress quiz.
    
    This is shown when the user has an active quiz session that wasn't completed.
    Uses FSMContext state checking instead of database queries.
    """
    from app.handlers.quiz import QuizStates
    
    # Check current state
    current_state = await state.get_state()
    
    if current_state == QuizStates.quiz_in_progress:
        # Resume the quiz - notify user
        await callback.message.edit_text(
            "Resuming Your Quiz\n\n"
            "Tap the button below to continue where you left off!",
            parse_mode='Markdown',
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
    else:
        # No active quiz - redirect to start quiz
        await callback.message.edit_text(
            "No Active Quiz Found\n\n"
            "You don't have a quiz in progress.\n\n"
            "Tap 'Start Quiz' to begin a new quiz!",
            parse_mode='Markdown',
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
    
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu_daily_goal")
async def menu_daily_goal_callback(callback: types.CallbackQuery, state: FSMContext,
                                   has_active_subscription: bool = False):
    """
    Handle daily goal callback - shows today's progress toward daily goal.
    
    Displays:
    - Quizzes taken today
    - Questions answered today
    - Progress bar toward daily goal (default: 10 questions)
    - Remaining quizzes until goal
    """
    user_id = callback.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        attempt_repo = AttemptRepository(session)
        question_repo = QuestionRepository(session)
        
        user_service = UserService(user_repo, payment_repo, attempt_repo, question_repo)
        
        try:
            daily_progress = await user_service.get_daily_progress(user_id)
            
            # Calculate progress
            quiz_count = daily_progress.get('quiz_count', 0)
            question_count = daily_progress.get('attempts', 0)
            daily_goal = 10  # Default daily goal
            
            # Calculate percentage
            progress_pct = min(100, (question_count / daily_goal) * 100)
            progress_bar = generate_progress_bar(progress_pct)
            
            # Determine status
            if question_count >= daily_goal:
                status_emoji = "Done"
                status_text = "Goal Achieved!"
            elif question_count >= daily_goal * 0.7:
                status_emoji = "Hot"
                status_text = "Almost there!"
            elif question_count >= daily_goal * 0.3:
                status_emoji = "Up"
                status_text = "Keep going!"
            else:
                status_emoji = "New"
                status_text = "Just started"
            
            daily_msg = (
                f"Daily Goal Progress\n\n"
                f"{status_emoji} {status_text}\n\n"
                f"Today's Stats:\n"
                f"- Questions answered: {question_count}\n"
                f"- Quizzes completed: {quiz_count}\n"
                f"- Accuracy: {daily_progress.get('accuracy', 0)}%\n\n"
                f"Daily Goal ({daily_goal} questions):\n"
                f"{progress_bar}\n\n"
                f"Remaining: {max(0, daily_goal - question_count)} questions\n\n"
                f"Tap 'Start Quiz' to continue practicing!"
            )
            
            await callback.message.edit_text(
                daily_msg,
                parse_mode='Markdown',
                reply_markup=MainMenuKeyboard.get_enhanced_main_menu(
                    user_data={'has_active_quiz': False},
                    is_admin=False
                )
            )
            
        except Exception as e:
            await callback.message.edit_text(
                f"Error loading daily progress: {str(e)}\n\n"
                f"Please try again.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu_refresh")
async def menu_refresh_callback(callback: types.CallbackQuery, state: FSMContext,
                                is_admin: bool = False,
                                has_active_subscription: bool = False):
    """
    Handle refresh callback - regenerates the enhanced menu with updated stats.
    
    This allows users to refresh the menu to see their latest progress
    without navigating away and back.
    """
    user_id = callback.from_user.id
    
    async for session in get_db():
        user_repo = UserRepository(session)
        payment_repo = PaymentRepository(session)
        attempt_repo = AttemptRepository(session)
        question_repo = QuestionRepository(session)
        
        user_service = UserService(user_repo, payment_repo, attempt_repo, question_repo)
        
        try:
            # Get fresh user data
            profile = await user_service.get_user_profile(user_id)
            daily_progress = await user_service.get_daily_progress(user_id)
            
            # Check for active quiz using state
            current_state = await state.get_state()
            from app.handlers.quiz import QuizStates
            has_active_quiz = current_state == QuizStates.quiz_in_progress
            
            # Prepare user data for enhanced menu
            user_data = {
                'name': profile.get('name', 'User'),
                'is_premium': has_active_subscription,
                'quiz_today': daily_progress.get('quiz_count', 0),
                'daily_goal': daily_progress.get('remaining_quizzes', 0),
                'streak_days': profile.get('stats', {}).get('streak_days', 0),
                'accuracy': profile.get('stats', {}).get('avg_accuracy', 0),
                'has_active_quiz': has_active_quiz
            }
            
            # Generate personalized message
            greeting = get_time_of_day_greeting()
            safe_name = escape_markdown(user_data.get('name', 'there'))
            streak_text = format_streak_days(user_data.get('streak_days', 0))
            subscription_badge = get_subscription_badge(
                user_data['is_premium'],
                days_left=profile.get('subscription', {}).get('days_left')
            )
            
            # Calculate daily progress
            daily_goal = 10
            question_count = daily_progress.get('attempts', 0)
            progress_pct = min(100, (question_count / daily_goal) * 100)
            progress_bar = generate_progress_bar(progress_pct)
            
            welcome_msg = (
                f"{greeting}, {safe_name}!\n\n"
                f"{subscription_badge} | {streak_text}\n\n"
                f"Today's Progress:\n"
                f"{progress_bar}\n"
                f"Questions: {question_count}/{daily_goal}\n\n"
                f"Choose an action below:"
            )
            
            await callback.message.edit_text(
                welcome_msg,
                parse_mode='Markdown',
                reply_markup=MainMenuKeyboard.get_enhanced_main_menu(
                    user_data=user_data,
                    is_admin=is_admin
                )
            )
            
        except Exception as e:
            # Fallback to standard menu on error
            await callback.message.edit_text(
                "Main Menu\n\n"
                "Choose what you'd like to do:",
                parse_mode=None,
                reply_markup=MainMenuKeyboard.get_main_menu_inline(is_admin)
            )
    
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_enhanced_menu")
async def back_to_enhanced_menu_callback(callback: types.CallbackQuery, state: FSMContext,
                                         is_admin: bool = False,
                                         has_active_subscription: bool = False):
    """
    Handle back to enhanced menu callback.
    
    Regenerates the enhanced menu with fresh user data.
    """
    # Reuse the menu_refresh handler logic
    await menu_refresh_callback(callback, state, is_admin, has_active_subscription)
    await callback.answer()
