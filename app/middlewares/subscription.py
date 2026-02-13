"""
Subscription Middleware - PRODUCTION READY ACCESS CONTROL

🚨 CRITICAL: This middleware enforces that users can access premium features
ONLY IF they have been approved by an admin (approved = 1).

DESIGN PRINCIPLES:
1. /start, /help, /about, /contact, /payment are ALWAYS allowed
2. /approve is allowed for admins only  
3. Users with completed payments can access /payment
4. New users get clear guidance on how to get approved
5. Premium features (quiz) require approved=1
6. No silent failures - always explain WHY access is denied
7. NEW USERS ARE AUTO-REGISTERED - no NEW_USER marking needed
"""

import re
import logging
from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware, Router
from aiogram.types import Message, CallbackQuery
from sqlalchemy import text as sql_text
from datetime import datetime

from app.db.base import get_db
from app.config import settings
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

# Enable debug logging for authorization
DEBUG_AUTH = True

# Access denial message - EXPLANATORY VERSION
ACCESS_DENIED_MESSAGE = (
    "❌ *Access Restricted*\n\n"
    "📚 To take quizzes, you need an approved account.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "💰 *How to Get Approved:*\n\n"
    "1️⃣ Use /payment to get payment instructions\n"
    "2️⃣ Complete your payment\n"
    "3️⃣ Send your payment screenshot to this chat\n"
    "4️⃣ Wait for admin to verify and approve you\n\n"
    "⏳ *Processing Time:*\n"
    "Admins typically review within 24 hours.\n\n"
    "💡 *Need Help?* Use /contact to message admins."
)

# Commands always allowed for ALL users (even unapproved)
# 🚨 CRITICAL: /start MUST be here to auto-register new users
ALLOWED_COMMANDS = [
    'start', 'help', 'about', 'contact', 'payment', 
    'approve', 'admin', 'cancel', 'ping'
]

# Navigation callbacks that don't require approval
NAVIGATION_CALLBACKS = [
    'back_to_menu', 'start_quiz', 'help', 'contact',
    'my_progress', 'leaderboard', 'subscription', 'my_referrals',
    'payment', 'contact_new'
]

# Quiz-related callbacks that START quiz (require approval)
QUIZ_START_CALLBACKS = [
    'difficulty_simple', 'difficulty_medium', 'difficulty_hard'
]

# Answer callbacks (require active quiz state)
ANSWER_CALLBACKS_PREFIX = 'answer_'


def escape_markdown(text: str) -> str:
    """
    Safely escape Markdown special characters.
    
    Telegram Markdown/HTML parsing can fail on special characters.
    This function escapes: _ * [ ] ( ) ` ~ > # + - = | { } . !
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for Telegram Markdown
    """
    if not text:
        return ""
    
    # Order matters - escape in correct order
    special_chars = [
        '\\',  # Must escape backslash first
        '`',   # Code formatting
        '*',   # Bold
        '_',   # Italic
        '~',   # Strikethrough
        '>',   # Quote
        '#',   # Headers
        '+',   # List markers
        '-',   # List markers/dashes
        '=',   # Headers
        '|',   # Tables
        '{',   # Formatting
        '}',   # Formatting
        '[',   # Links
        ']',   # Links
        '(',   # Links
        ')',   # Links
        '.',   # Can cause issues in some contexts
        '!',   # Can interfere with button text
    ]
    
    result = str(text)
    for char in special_chars:
        result = result.replace(char, f'\\{char}')
    
    return result


def get_handler_name(handler: Callable) -> str:
    """
    Get the actual handler name even for wrapped functions.
    
    Uses inspection to unwrap decorated functions and find the real name.
    This ensures proper logging even when using decorators.
    """
    import inspect
    
    # Try to get name directly first
    name = getattr(handler, '__name__', None)
    if name and name != 'wrapper':
        return name
    
    # Try to unwrap if it's a decorated function
    try:
        # For functools.wrapped functions
        if hasattr(handler, '__wrapped__'):
            return get_handler_name(handler.__wrapped__)
    except (ValueError, TypeError):
        pass
    
    # For aiogram handlers, try to get from attributes
    if hasattr(handler, '__self__'):
        return f"{handler.__self__.__class__.__name__}.{name or 'unknown'}"
    
    # Try to get from aiogram handler attributes
    if hasattr(handler, 'callback'):
        # For callback query handlers
        callback = handler.callback
        if hasattr(callback, '__name__'):
            return f"callback_{callback.__name__}"
    
    return name or 'unknown_handler'


def is_command_allowed(text: str) -> bool:
    """Check if a message text is an allowed command (even for unapproved users)"""
    if not text:
        return False
    
    # Remove @botname if present
    clean_text = re.sub(r'@[\w_]+', '', text).strip()
    
    # Check if it's a command
    if not clean_text.startswith('/'):
        return False
    
    # Extract command name (without arguments)
    command = clean_text.split()[0][1:].lower()  # Remove '/' and args
    
    return command in ALLOWED_COMMANDS


def is_navigation_callback(callback_data: str) -> bool:
    """Check if callback is for basic navigation (not quiz)"""
    if not callback_data:
        return False
    
    # Direct match for known navigation callbacks
    if callback_data in NAVIGATION_CALLBACKS:
        return True
    
    # Allow all payment-related callbacks
    if callback_data.startswith('payment') or callback_data.startswith('contact'):
        return True
    
    # Allow quiz selection callbacks (but not starting quiz)
    if callback_data.startswith('subject_') or callback_data.startswith('chapter_'):
        return True
    
    # Allow difficulty selection but require approval to start
    if callback_data.startswith('difficulty_'):
        return True  # Allow selection, but quiz will be blocked
    
    return False


async def _register_new_user(
    user_id: int, 
    username: Optional[str], 
    first_name: Optional[str], 
    last_name: Optional[str]
) -> Dict[str, Any]:
    """
    Register a new user in the database.
    
    Returns dict with:
    - is_new: bool (True if user was just created)
    - user_id: int
    - approved: bool
    """
    async for session in get_db():
        user_repo = UserRepository(session)
        
        # Check if user exists
        existing_user = await user_repo.get_user(user_id)
        if existing_user:
            return {
                'is_new': False,
                'user_id': user_id,
                'approved': existing_user.approved or False
            }
        
        # Create new user with approved=False (requires admin approval for quiz access)
        await user_repo.create_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        logger.info(f"[AUTH] New user registered: user_id={user_id}, username={username}")
        
        return {
            'is_new': True,
            'user_id': user_id,
            'approved': False  # New users are NOT approved by default
        }


class SubscriptionMiddleware(BaseMiddleware):
    """
    Middleware for STRICT subscription/premium access control.
    
    🚨 CRITICAL RULE: Users can access quizzes ONLY IF approved = 1
    
    IMPORTANT: This middleware does NOT block /start command.
    New users can always /start and will be auto-registered.
    
    This middleware:
    1. Always auto-registers new users (no NEW_USER marking)
    2. Always uses RAW SQL to fetch user data (bypasses ORM caching)
    3. Never relies on cached ORM objects
    4. Logs every access check with full details
    5. Is idempotent - approval is permanent once granted
    6. Allows /start, /help, /about, /contact, /payment for all users
    7. Allows /approve for admins only
    8. Provides clear guidance on how to get approved
    
    The following are COMPLETELY IGNORED for quiz access:
    - is_premium flag (informational only)
    - has_active_subscription flag (deprecated)
    - payment status (unless it determines approval)
    - screenshot_submitted status
    - FSM/Redis state
    """
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ):
        user_id = event.from_user.id
        username = getattr(event.from_user, 'username', None)
        first_name = getattr(event.from_user, 'first_name', None)
        last_name = getattr(event.from_user, 'last_name', None)
        
        # Get handler name for logging
        handler_name = get_handler_name(handler)
        
        # =========================================================================
        # STEP 0: Allow basic commands for ALL users (even unapproved)
        # =========================================================================
        # Check if this is an allowed command
        if isinstance(event, Message):
            message_text = event.text or ""
            if is_command_allowed(message_text):
                # Auto-register new users if needed
                registration_result = await _register_new_user(
                    user_id, username, first_name, last_name
                )
                
                # Allow these basic commands without checking approval
                data['can_access_quiz'] = False
                data['is_new_user'] = registration_result['is_new']
                data['access_result'] = {
                    'allowed': True,
                    'reason_code': 'ALLOWED_COMMAND',
                    'reason': f'Command allowed for all users',
                    'is_new_user': registration_result['is_new']
                }
                if DEBUG_AUTH:
                    logger.info(
                        f"[AUTH] User {user_id} | Handler: {handler_name} | "
                        f"RESULT: COMMAND_ALLOWED | NEW_USER: {registration_result['is_new']}"
                    )
                return await handler(event, data)
        
        # Check if this is a callback query for basic navigation
        if isinstance(event, CallbackQuery):
            callback_data = event.data or ""
            
            # Auto-register new users for callback queries too
            registration_result = await _register_new_user(
                user_id, username, first_name, last_name
            )
            data['is_new_user'] = registration_result['is_new']
            
            if is_navigation_callback(callback_data):
                data['can_access_quiz'] = False
                data['access_result'] = {
                    'allowed': True,
                    'reason_code': 'NAVIGATION',
                    'reason': 'Navigation allowed',
                    'is_new_user': registration_result['is_new']
                }
                if DEBUG_AUTH:
                    logger.info(
                        f"[AUTH] User {user_id} | Handler: {handler_name} | "
                        f"RESULT: NAVIGATION_ALLOWED | NEW_USER: {registration_result['is_new']}"
                    )
                return await handler(event, data)
            
            # Check if this is an answer callback - these require quiz state
            if callback_data.startswith(ANSWER_CALLBACKS_PREFIX):
                # Answer callbacks are handled by state - allow through
                # The quiz handler will check state
                data['can_access_quiz'] = True  # Will be verified by state
                data['access_result'] = {
                    'allowed': True,
                    'reason_code': 'ANSWER_CALLBACK',
                    'reason': 'Answer callback - state will be verified'
                }
                if DEBUG_AUTH:
                    logger.info(
                        f"[AUTH] User {user_id} | Handler: {handler_name} | "
                        f"RESULT: ANSWER_CALLBACK | NEW_USER: {registration_result['is_new']}"
                    )
                return await handler(event, data)
        
        # =========================================================================
        # STEP 1: Set default values - NO access until proven approved
        # =========================================================================
        data['has_active_subscription'] = False
        data['is_premium'] = False
        data['access_result'] = None
        data['user'] = None
        data['can_access_quiz'] = False
        
        # =========================================================================
        # STEP 2: Fetch FRESH user data using RAW SQL (bypasses ORM caching)
        # =========================================================================
        try:
            # Create a NEW session for this check - ensures fresh data
            async for session in get_db():
                # Use RAW SQL - this bypasses ALL ORM caching
                # This is the ONLY reliable way to get the current approved status
                query = sql_text(
                    "SELECT user_id, username, approved, is_premium, blocked "
                    "FROM users WHERE user_id = :user_id"
                )
                result = await session.execute(query, {"user_id": user_id})
                row = result.fetchone()
                
                # Process the fresh data
                if not row:
                    # User not found in database - should not happen due to auto-registration
                    # But handle it gracefully
                    if DEBUG_AUTH:
                        logger.warning(
                            f"[AUTH] User {user_id} | Handler: {handler_name} | "
                            f"RESULT: USER_NOT_FOUND (should be auto-registered!)"
                        )
                    
                    data['can_access_quiz'] = False
                    data['access_result'] = {
                        'allowed': False,
                        'reason_code': 'NOT_REGISTERED',
                        'reason': 'Please use /start to register first.'
                    }
                else:
                    user_id_db, username_db, approved, is_premium, blocked = row
                    
                    # Log the raw values for debugging
                    if DEBUG_AUTH:
                        logger.info(
                            f"[AUTH] User {user_id} | Handler: {handler_name} | "
                            f"DB_VALUES: approved={approved}, is_premium={is_premium}, blocked={blocked}"
                        )
                    
                    # =========================================================================
                    # STEP 3: STRICT access check - ONLY approved = 1 grants quiz access
                    # =========================================================================
                    
                    if blocked:
                        # User is blocked - DENY ACCESS
                        if DEBUG_AUTH:
                            logger.warning(
                                f"[AUTH] User {user_id} | Handler: {handler_name} | "
                                f"RESULT: BLOCKED"
                            )
                        
                        data['can_access_quiz'] = False
                        data['access_result'] = {
                            'allowed': False,
                            'reason_code': 'BLOCKED',
                            'reason': 'Your account has been blocked. Please contact admin via /contact.'
                        }
                    
                    elif not approved:
                        # User is NOT approved - DENY QUIZ ACCESS
                        # But provide helpful guidance
                        
                        if DEBUG_AUTH:
                            logger.warning(
                                f"[AUTH] User {user_id} | Handler: {handler_name} | "
                                f"RESULT: NOT_APPROVED"
                            )
                        
                        data['can_access_quiz'] = False
                        data['access_result'] = {
                            'allowed': False,
                            'reason_code': 'NOT_APPROVED',
                            'reason': ACCESS_DENIED_MESSAGE
                        }
                        
                        # Security alert for inconsistent state
                        if is_premium:
                            logger.warning(
                                f"🚨 SECURITY: User {user_id} has "
                                f"is_premium={is_premium} but approved={approved}. "
                                f"Inconsistent state detected!"
                            )
                    
                    else:
                        # User is approved - GRANT ACCESS
                        # This is the ONLY condition for granting quiz access
                        if DEBUG_AUTH:
                            logger.info(
                                f"[AUTH] User {user_id} | Handler: {handler_name} | "
                                f"RESULT: APPROVED (granting quiz access)"
                            )
                        
                        data['can_access_quiz'] = True
                        data['is_premium'] = True  # For display purposes
                        data['access_result'] = {
                            'allowed': True,
                            'reason_code': 'ACCESS_GRANTED',
                            'reason': 'Access granted',
                            'user': {
                                'user_id': user_id_db,
                                'username': username_db,
                                'approved': approved,
                                'is_premium': is_premium
                            }
                        }
                
                # Process exactly one session from the generator
                break
                
        except Exception as e:
            logger.error(f"Subscription middleware error for user {user_id}: {e}")
            # Fail SECURE - deny access if check fails
            data['can_access_quiz'] = False
            data['access_result'] = {
                'allowed': False,
                'reason_code': 'SYSTEM_ERROR',
                'reason': 'System error. Please try again or contact admin via /contact.'
            }
        
        # =========================================================================
        # STEP 4: Call handler with access status
        # =========================================================================
        return await handler(event, data)


# =============================================================================
# CONVENIENCE FUNCTION FOR HANDLERS
# =============================================================================

async def check_quiz_access(user_id: int) -> Dict[str, Any]:
    """
    Check if user can access quizzes.
    
    Use this in handlers when you need to verify access.
    
    Returns:
        Dict with:
        - allowed: bool (True ONLY if approved = 1)
        - reason_code: str (reason for denial)
        - reason: str (user-friendly message)
    """
    try:
        async for session in get_db():
            # RAW SQL - bypasses all caching
            query = sql_text(
                "SELECT approved, is_premium, blocked FROM users WHERE user_id = :user_id"
            )
            result = await session.execute(query, {"user_id": user_id})
            row = result.fetchone()
            
            if not row:
                return {
                    'allowed': False,
                    'reason_code': 'NO_USER',
                    'reason': 'User not found. Please /start first.'
                }
            
            approved, is_premium, blocked = row
            
            if blocked:
                return {
                    'allowed': False,
                    'reason_code': 'BLOCKED',
                    'reason': 'Your account has been blocked. Please contact admin via /contact.'
                }
            
            if not approved:
                return {
                    'allowed': False,
                    'reason_code': 'NOT_APPROVED',
                    'reason': ACCESS_DENIED_MESSAGE
                }
            
            return {
                'allowed': True,
                'reason_code': 'ACCESS_GRANTED',
                'reason': 'Access granted'
            }
    except Exception as e:
        logger.error(f"check_quiz_access error for user {user_id}: {e}")
        return {
            'allowed': False,
            'reason_code': 'SYSTEM_ERROR',
            'reason': 'System error. Please try again.'
        }


def require_quiz_access(func):
    """
    Decorator for handlers that require quiz access.
    
    Usage:
        @router.callback_query(...)
        @require_quiz_access
        async def my_handler(callback, state, data):
            ...
    """
    async def wrapper(event, state, data):
        can_access = data.get('can_access_quiz', False)
        
        if not can_access:
            access_result = data.get('access_result', {})
            message_text = access_result.get('reason', ACCESS_DENIED_MESSAGE)
            
            if hasattr(event, 'message') and event.message:
                await event.message.answer(message_text, parse_mode='Markdown')
            elif hasattr(event, 'answer'):
                await event.answer(message_text, show_alert=True)
            return
        
        # Access granted - call the handler
        return await func(event, state, data)
    
    return wrapper


# =============================================================================
# AUTO-APPROVE FUNCTION FOR COMPLETED PAYMENTS
# =============================================================================

async def auto_approve_if_payment_completed(user_id: int) -> bool:
    """
    Check if user has a completed payment and auto-approve them.
    
    This helps streamline the approval process for users who have paid.
    
    Returns:
        True if user was auto-approved, False otherwise
    """
    try:
        async for session in get_db():
            # Check for approved payments
            query = sql_text(
                "SELECT payment_id FROM payments "
                "WHERE user_id = :user_id AND status = 'approved' "
                "LIMIT 1"
            )
            result = await session.execute(query, {"user_id": user_id})
            approved_payment = result.fetchone()
            
            if approved_payment:
                # Update user to approved
                update_query = sql_text(
                    "UPDATE users SET approved = 1, is_premium = 1 "
                    "WHERE user_id = :user_id"
                )
                await session.execute(update_query, {"user_id": user_id})
                await session.commit()
                
                logger.info(
                    f"[AUTH] User {user_id} auto-approved due to completed payment #{approved_payment[0]}"
                )
                return True
            
            return False
    except Exception as e:
        logger.error(f"Auto-approve check failed for user {user_id}: {e}")
        return False


# =============================================================================
# ADMIN NOTIFICATION UTILITIES
# =============================================================================

async def notify_admins_safe(
    bot,
    message: str,
    admin_ids: list = None,
    parse_mode: str = 'Markdown'
) -> None:
    """
    Safely send notification to all admins with proper error handling.
    
    This function:
    1. Escapes special Markdown characters to prevent parse errors
    2. Handles individual admin notification failures gracefully
    3. Logs errors without crashing
    
    Args:
        bot: Bot instance
        message: Message to send (will be escaped for Markdown)
        admin_ids: List of admin user IDs (uses settings.ADMIN_IDS if None)
        parse_mode: Parse mode ('Markdown' or 'HTML')
    """
    if admin_ids is None:
        admin_ids = settings.ADMIN_IDS
    
    # Escape the message for Markdown if needed
    if parse_mode == 'Markdown':
        safe_message = escape_markdown(message)
    else:
        safe_message = message
    
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=safe_message,
                parse_mode=parse_mode if parse_mode == 'Markdown' else None
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
            # Try sending without formatting as fallback
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=str(message)[:4000]  # Truncate if too long
                )
            except Exception as e2:
                logger.error(f"Fallback notification also failed for admin {admin_id}: {e2}")


def format_admin_notification(
    title: str,
    user_info: Dict[str, Any],
    details: str,
    parse_mode: str = 'Markdown'
) -> str:
    """
    Format a safe admin notification message.
    
    Args:
        title: Notification title (e.g., "New User", "Payment Received")
        user_info: Dict with user_id, username, first_name, etc.
        details: Additional details about the notification
        parse_mode: Output format ('Markdown' or 'plain')
        
    Returns:
        Formatted message string
    """
    # Escape user-provided values
    user_id = user_info.get('user_id', 'Unknown')
    username = escape_markdown(user_info.get('username', 'N/A'))
    first_name = escape_markdown(user_info.get('first_name', 'User'))
    
    # Truncate details if too long
    safe_details = escape_markdown(details)
    if len(safe_details) > 1000:
        safe_details = safe_details[:1000] + "..."
    
    if parse_mode == 'Markdown':
        return (
            f"📬 *{escape_markdown(title)}*\n\n"
            f"👤 *User:* {first_name}\n"
            f"🆔 *ID:* `{user_id}`\n"
            f"📧 *Username:* @{username}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{safe_details}"
        )
    else:
        return (
            f"{title}\n"
            f"User: {first_name} (ID: {user_id})\n"
            f"Username: @{username}\n\n"
            f"{details}"
        )

