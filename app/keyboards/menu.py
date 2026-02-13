from typing import List, Optional, Dict, Any
from datetime import datetime
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.constants import EMOJIS


# ============================================================================
# Progress Bar Helper Functions
# ============================================================================

def generate_progress_bar(percentage: float, length: int = 10, filled_char: str = '█', empty_char: str = '░') -> str:
    """
    Generate an ASCII progress bar.
    
    Args:
        percentage: 0-100 value representing progress
        length: Number of characters in the bar
        filled_char: Character for filled portion
        empty_char: Character for empty portion
    
    Returns:
        Progress bar string like '[████░░░░░░] 40%'
    """
    # Clamp percentage between 0 and 100
    percentage = max(0, min(100, percentage))
    
    # Calculate filled segments
    filled_length = int(length * percentage / 100)
    empty_length = length - filled_length
    
    # Build the bar
    bar = f"{filled_char * filled_length}{empty_char * empty_length}"
    
    return f"[{bar}] {percentage:.0f}%"


def get_time_of_day_greeting() -> str:
    """Get appropriate greeting based on time of day"""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    elif 17 <= hour < 21:
        return "Good Evening"
    else:
        return "Good Night"


def get_time_of_day_emoji() -> str:
    """Get appropriate emoji based on time of day"""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "🌅"
    elif 12 <= hour < 17:
        return "☀️"
    elif 17 <= hour < 21:
        return "🌇"
    else:
        return "🌙"


def format_streak_days(days: int) -> str:
    """Format streak days with appropriate emoji and message"""
    if days == 0:
        return f"{EMOJIS['fire']} Just getting started!"
    elif days < 3:
        return f"{EMOJIS['fire']} {days} day streak - Keep going! 💪"
    elif days < 7:
        return f"{EMOJIS['fire']} {days} day streak - On fire! 🔥"
    elif days < 30:
        return f"{EMOJIS['trophy']} {days} day streak - Amazing dedication! 🏆"
    elif days < 100:
        return f"{EMOJIS['crown']} {days} day streak - You're a champion! 👑"
    else:
        return f"{EMOJIS['star']} {days} day streak - LEGENDARY! 🌟"


def get_subscription_badge(is_premium: bool, days_left: int = None, has_pending: bool = False) -> str:
    """Generate subscription status badge with beautiful formatting"""
    if has_pending:
        return f"{EMOJIS['pending']} Pending Approval"
    if is_premium:
        if days_left and days_left > 365:
            return f"{EMOJIS['premium']} LIFETIME"
        elif days_left:
            return f"{EMOJIS['premium']} {days_left}d left"
        return f"{EMOJIS['premium']} PREMIUM"
    return f"{EMOJIS['free']} Free Tier"


def generate_welcome_message(
    user_name: str,
    is_premium: bool = False,
    streak_days: int = 0,
    quizzes_today: int = 0,
    daily_goal: int = 5,
    accuracy: float = 0.0
) -> str:
    """Generate a beautiful personalized welcome message"""
    greeting = get_time_of_day_greeting()
    time_emoji = get_time_of_day_emoji()
    
    # Build the welcome message
    message = f"{time_emoji} {greeting}, {user_name}!\n\n"
    
    # Add streak info
    if streak_days > 0:
        message += f"{format_streak_days(streak_days)}\n\n"
    
    # Add daily progress if quizzes done
    if quizzes_today > 0:
        progress = min(100, (quizzes_today / daily_goal) * 100)
        progress_bar = generate_progress_bar(progress, length=15)
        message += f"📊 Daily Goal: {quizzes_today}/{daily_goal} quizzes\n"
        message += f"{progress_bar}\n\n"
    
    # Add accuracy
    if accuracy > 0:
        if accuracy >= 80:
            message += f"🎯 Your Accuracy: {accuracy:.0f}% (Excellent!)\n"
        elif accuracy >= 60:
            message += f"📈 Your Accuracy: {accuracy:.0f}% (Good!)\n"
        else:
            message += f"📉 Your Accuracy: {accuracy:.0f}% (Keep practicing!)\n"
    
    # Add subscription badge
    message += f"\n{get_subscription_badge(is_premium)}"
    
    return message


def generate_daily_goal_message(quizzes_done: int, daily_goal: int, accuracy: float) -> str:
    """Generate daily goal progress message"""
    if daily_goal == 0:
        daily_goal = 5  # Default
    
    progress = min(100, (quizzes_done / daily_goal) * 100)
    remaining = max(0, daily_goal - quizzes_done)
    
    message = f"🎯 Daily Goal Progress\n\n"
    message += f"📊 Quizzes: {quizzes_done}/{daily_goal}\n"
    message += f"{generate_progress_bar(progress, length=15)}\n\n"
    
    if remaining == 0:
        message += f"🎉 Amazing! You've reached your daily goal!\n"
        if accuracy > 0:
            message += f"📈 Accuracy: {accuracy:.0f}%"
    else:
        message += f"💪 {remaining} more quiz{'zes' if remaining > 1 else ''} to go!"
    
    return message


def get_quality_emoji(accuracy: float) -> str:
    """Get emoji based on accuracy level"""
    if accuracy >= 90:
        return "🌟"
    elif accuracy >= 80:
        return "🏆"
    elif accuracy >= 70:
        return "👍"
    elif accuracy >= 60:
        return "📈"
    else:
        return "💪"


class MainMenuKeyboard:
    """Enhanced interactive main menu keyboard with beautiful design"""
    
    @staticmethod
    def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Get main menu keyboard with 2-column grid layout for better visual appearance"""
        keyboard = [
            # Row 1: Primary Actions
            [
                KeyboardButton(text=f"{EMOJIS['learn']} Start Quiz"),
                KeyboardButton(text=f"{EMOJIS['gift']} Referrals")
            ],
            # Row 2: Progress & Stats
            [
                KeyboardButton(text=f"{EMOJIS['accuracy']} My Progress"),
                KeyboardButton(text=f"{EMOJIS['score']} Leaderboard")
            ],
            # Row 3: Account & Support
            [
                KeyboardButton(text=f"{EMOJIS['payment']} Subscription"),
                KeyboardButton(text=f"{EMOJIS['contact']} Contact")
            ],
            # Row 4: Help & Info
            [
                KeyboardButton(text=f"{EMOJIS['info']} Help"),
                KeyboardButton(text="📊 Weak Areas")
            ]
        ]

        if is_admin:
            keyboard.append([KeyboardButton(text=f"{EMOJIS['admin']} Admin Panel")])

        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            input_field_placeholder="Choose an option..."
        )
    
    @staticmethod
    def get_main_menu_inline(is_admin: bool = False) -> InlineKeyboardMarkup:
        """
        Get main menu inline keyboard with 2-column grid layout for better visual appearance.
        
        IMPORTANT: Use this method when editing a message with callback_query.edit_text()
        instead of get_main_menu() which returns ReplyKeyboardMarkup.
        """
        builder = InlineKeyboardBuilder()
        
        # Row 1: Primary Actions (2 columns)
        builder.button(
            text=f"{EMOJIS['learn']} Start Quiz",
            callback_data="start_quiz"
        )
        builder.button(
            text=f"{EMOJIS['gift']} Referrals",
            callback_data="my_referrals"
        )
        
        # Row 2: Progress & Stats (2 columns)
        builder.button(
            text=f"{EMOJIS['accuracy']} My Progress",
            callback_data="my_progress"
        )
        builder.button(
            text=f"{EMOJIS['score']} Leaderboard",
            callback_data="leaderboard"
        )
        
        # Row 3: Account & Support (2 columns)
        builder.button(
            text=f"{EMOJIS['payment']} Subscription",
            callback_data="subscription"
        )
        builder.button(
            text=f"{EMOJIS['contact']} Contact",
            callback_data="contact"
        )
        
        # Row 4: Help & Weak Areas (2 columns)
        builder.button(
            text=f"{EMOJIS['info']} Help",
            callback_data="help"
        )
        builder.button(
            text="📊 Weak Areas",
            callback_data="progress_weak"
        )
        
        # Admin panel (full width at bottom if admin)
        if is_admin:
            builder.button(
                text=f"{EMOJIS['admin']} Admin Panel",
                callback_data="admin_panel"
            )
        
        # Adjust to 2 columns for all buttons
        builder.adjust(2)
        return builder.as_markup()
    
    @staticmethod
    def get_main_menu_compact(is_admin: bool = False) -> InlineKeyboardMarkup:
        """
        Get compact main menu inline keyboard - smaller buttons for more options.
        Uses 3-column grid for maximum efficiency.
        """
        builder = InlineKeyboardBuilder()
        
        # Row 1: Quiz & Progress (3 columns)
        builder.button(text="🎯 Quiz", callback_data="start_quiz")
        builder.button(text="📊 Progress", callback_data="my_progress")
        builder.button(text="🏆 Rank", callback_data="leaderboard")
        
        # Row 2: Rewards & Subscription (3 columns)
        builder.button(text="🎁 Refer", callback_data="my_referrals")
        builder.button(text="💳 Premium", callback_data="subscription")
        builder.button(text="📈 Stats", callback_data="progress_overview")
        
        # Row 3: Support & Help (3 columns)
        builder.button(text="💬 Contact", callback_data="contact")
        builder.button(text="❓ Help", callback_data="help")
        builder.button(text="⚠️ Issues", callback_data="progress_weak")
        
        # Admin panel (full width)
        if is_admin:
            builder.button(
                text=f"⚙️ {EMOJIS['admin']} Admin Panel",
                callback_data="admin_panel"
            )
        
        # First 3 rows are 3 columns, admin is full width
        builder.adjust(3, repeat=True)
        return builder.as_markup()
    
    @staticmethod
    def get_subjects_keyboard(subjects: List[dict]) -> InlineKeyboardMarkup:
        """Get subjects selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        for subject in subjects:
            builder.button(
                text=f"{EMOJIS['subject']} {subject['subject_name']}",
                callback_data=f"subject_{subject['subject_id']}"
            )
        
        builder.adjust(2)
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back to Menu",
                callback_data="back_to_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_chapters_keyboard(chapters: List[dict]) -> InlineKeyboardMarkup:
        """Get chapters selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        for chapter in chapters:
            builder.button(
                text=f"{EMOJIS['chapter']} {chapter['chapter_name']}",
                callback_data=f"chapter_{chapter['chapter_id']}"
            )
        
        builder.adjust(2)
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back to Subjects",
                callback_data="back_to_subjects"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_difficulty_keyboard() -> InlineKeyboardMarkup:
        """Get difficulty selection keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['easy']} Simple",
                    callback_data="difficulty_simple"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['medium']} Medium",
                    callback_data="difficulty_medium"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['hard']} Hard",
                    callback_data="difficulty_hard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Chapters",
                    callback_data="back_to_chapters"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_payment_options_keyboard() -> InlineKeyboardMarkup:
        """Get payment options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="💰 One-time • Lifetime Access - 150 birr",
                    callback_data="buy_premium"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 View Instructions",
                    callback_data="payment_instructions"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Check Status",
                    callback_data="payment_status"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
        """Get leaderboard options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📅 Daily",
                    callback_data="leaderboard_daily"
                ),
                InlineKeyboardButton(
                    text="📊 Weekly",
                    callback_data="leaderboard_weekly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📈 Monthly",
                    callback_data="leaderboard_monthly"
                ),
                InlineKeyboardButton(
                    text="🏆 Overall",
                    callback_data="leaderboard_overall"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_progress_options_keyboard() -> InlineKeyboardMarkup:
        """Get progress options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📊 Overview",
                    callback_data="progress_overview"
                ),
                InlineKeyboardButton(
                    text="📈 Daily Progress",
                    callback_data="progress_daily"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 Weak Areas",
                    callback_data="progress_weak"
                ),
                InlineKeyboardButton(
                    text="🎯 Recommendations",
                    callback_data="progress_recommendations"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_confirmation_keyboard(action: str, item_id: int = None) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for various actions"""
        callback_data = f"{action}_{item_id}" if item_id else action
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Yes",
                    callback_data=f"confirm_{callback_data}"
                ),
                InlineKeyboardButton(
                    text="❌ No",
                    callback_data=f"cancel_{callback_data}"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_payment_screenshot_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard for payment screenshot upload"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📸 Upload Screenshot",
                    callback_data="upload_screenshot"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel Payment",
                    callback_data="cancel_payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="back_to_payment"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_cancel_payment_keyboard() -> InlineKeyboardMarkup:
        """Get cancel payment keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Cancel Payment",
                    callback_data="cancel_payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="back_to_buy_premium"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_contact_start_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard to start contact message flow"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text="💬 Send Message",
            callback_data="contact_new"
        )
        
        builder.button(
            text="◀️ Back to Menu",
            callback_data="back_to_menu"
        )
        
        builder.adjust(1, 1)
        return builder.as_markup()

    @staticmethod
    def get_contact_category_keyboard() -> InlineKeyboardMarkup:
        """Get contact category selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text="💳 Payment Issues",
            callback_data="contact_category_payment"
        )
        builder.button(
            text="🐛 Quiz Errors",
            callback_data="contact_category_quiz_error"
        )
        builder.button(
            text="🔒 Access Problems",
            callback_data="contact_category_access"
        )
        builder.button(
            text="💡 General Questions",
            callback_data="contact_category_general"
        )
        builder.button(
            text="💬 Feedback",
            callback_data="contact_category_feedback"
        )
        builder.button(
            text="◀️ Back",
            callback_data="back_to_contact"
        )
        
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_contact_message_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard for after sending a contact message"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="◀️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 Send Another",
                    callback_data="contact_new"
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_cancel_contact_keyboard() -> InlineKeyboardMarkup:
        """Get cancel contact keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_contact"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="back_to_contact"
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_referral_keyboard(referral_link: str = None, referral_code: str = None) -> InlineKeyboardMarkup:
        """
        Get referral keyboard with share options.
        
        FIXED: Now consistent with reply keyboard - includes both Copy Code and Copy Link buttons.
        Back button now uses back_to_menu callback to properly return to main menu.
        
        Args:
            referral_link: Optional referral link for Telegram share URL
            referral_code: Optional referral code for share text
        """
        # FIXED: Use short share text to avoid MESSAGE_TOO_LONG error
        reward_per_student = 20  # Default, can be from settings
        # Shortened from ~200 chars to ~80 chars for shorter URLs
        share_text = (
            f"🎯 Join Quiz Bot!\n"
            f"Link: {referral_link or 'https://t.me/your_bot?start='}{(referral_code or 'CODE')}\n"
            f"Code: {referral_code or 'CODE'}\n"
            f"💰 Earn {reward_per_student} Birr!"
        )
        
        # URL encode the share text
        from urllib.parse import quote
        encoded_text = quote(share_text, safe='')
        encoded_url = quote(referral_link or '', safe='')
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['share']} Share on Telegram",
                    url=f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['gift']} Copy Code",
                    callback_data="copy_referral_code"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['copy']} Copy Link",
                    callback_data="copy_referral_link"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['trophy']} Leaderboard",
                    callback_data="referral_leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Menu",
                    callback_data="back_to_menu"  # FIXED: Now properly goes to main menu
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_my_referrals_keyboard(referral_code: str, referral_link: str) -> InlineKeyboardMarkup:
        """Get my referrals detail keyboard with share options"""
        # FIXED: Use short share text to avoid MESSAGE_TOO_LONG error
        from urllib.parse import quote
        reward_per_student = 20
        # Shortened from ~200 chars to ~80 chars for shorter URLs
        share_text = (
            f"🎯 Join Quiz Bot!\n"
            f"Link: {referral_link}\n"
            f"Code: {referral_code}\n"
            f"💰 Earn {reward_per_student} Birr!"
        )
        encoded_text = quote(share_text, safe='')
        encoded_url = quote(referral_link, safe='')
        
        # Build Telegram share URL
        telegram_share_url = f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['share']} Share Link",
                    url=telegram_share_url
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['gift']} Copy Code",
                    callback_data="copy_referral_code"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['trophy']} Top Referrers",
                    callback_data="referral_leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_share_keyboard(referral_link: str, share_text: str) -> InlineKeyboardMarkup:
        """Get share referral keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['share']} Share on Telegram",
                    url=f"https://t.me/share/url?url={referral_link}&text={share_text}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['copy']} Copy Link",
                    callback_data=f"copy_referral_link"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="my_referrals"
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_back_to_referral_keyboard() -> InlineKeyboardMarkup:
        """Get back to referral keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="◀️ Back to Referrals",
                    callback_data="my_referrals"
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_referral_reply_keyboard() -> ReplyKeyboardMarkup:
        """
        Get referral reply keyboard with the same buttons as inline keyboard.
        These buttons send text when clicked, working as commands.
        
        Returns:
            ReplyKeyboardMarkup with:
            - Share on Telegram (text)
            - Copy Code (text)
            - Copy Link (text)
            - Leaderboard (text)
            - Back to Menu (text)
        """
        keyboard = [
            # Row 1: Share and Copy options
            [
                KeyboardButton(text=f"{EMOJIS['share']} Share Link"),
                KeyboardButton(text=f"{EMOJIS['gift']} Copy Code")
            ],
            # Row 2: More actions
            [
                KeyboardButton(text=f"{EMOJIS['copy']} Copy Link"),
                KeyboardButton(text=f"{EMOJIS['trophy']} Leaderboard")
            ],
            # Row 3: Navigation
            [
                KeyboardButton(text="◀️ Back to Menu")
            ]
        ]

        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            input_field_placeholder="Choose an option..."
        )

    # ============================================================================
    # Enhanced Interactive Main Menu Methods
    # ============================================================================

    @staticmethod
    def get_enhanced_main_menu(
        user_data: Dict[str, Any] = None,
        is_admin: bool = False
    ) -> InlineKeyboardMarkup:
        """
        Get enhanced interactive main menu with personalized content.
        
        Args:
            user_data: Dict containing user stats and status
                - name: User's first name
                - is_premium: Whether user has premium subscription
                - quiz_today: Number of quizzes taken today
                - daily_goal: Daily quiz goal
                - streak_days: Current streak in days
                - accuracy: Overall accuracy percentage
                - has_active_quiz: Whether user has a quiz in progress
            is_admin: Whether user is an admin
        
        Returns:
            InlineKeyboardMarkup with enhanced layout and quick actions
        """
        builder = InlineKeyboardBuilder()
        
        # Row 1: Quick Actions (2 columns)
        if user_data and user_data.get('has_active_quiz'):
            builder.button(
                text="▶️ Continue Quiz",
                callback_data="menu_continue"
            )
        else:
            builder.button(
                text="⚡ Quick Quiz",
                callback_data="menu_quick_quiz"
            )
        
        builder.button(
            text="📊 Today",
            callback_data="menu_daily_goal"
        )
        
        # Row 2: Main Actions (2 columns)
        builder.button(
            text=f"{EMOJIS['learn']} Start Quiz",
            callback_data="start_quiz"
        )
        builder.button(
            text=f"{EMOJIS['accuracy']} Progress",
            callback_data="my_progress"
        )
        
        # Row 3: Stats & Rewards (2 columns)
        builder.button(
            text=f"{EMOJIS['score']} Leaderboard",
            callback_data="leaderboard"
        )
        builder.button(
            text=f"{EMOJIS['gift']} Referrals",
            callback_data="my_referrals"
        )
        
        # Row 4: Account & Support (2 columns)
        builder.button(
            text=f"{EMOJIS['payment']} Premium",
            callback_data="subscription"
        )
        builder.button(
            text=f"{EMOJIS['contact']} Contact",
            callback_data="contact"
        )
        
        # Row 5: Refresh & Help (2 columns)
        builder.button(
            text="🔄 Refresh",
            callback_data="menu_refresh"
        )
        builder.button(
            text=f"{EMOJIS['info']} Help",
            callback_data="help"
        )
        
        # Admin panel (full width at bottom if admin)
        if is_admin:
            builder.button(
                text=f"{EMOJIS['admin']} Admin Panel",
                callback_data="admin_panel"
            )
        
        # Adjust layout: 2 columns for most rows
        builder.adjust(2, 2, 2, 2, 2, 1 if is_admin else 2)
        return builder.as_markup()
    
    @staticmethod
    def get_quick_actions_keyboard(
        has_active_quiz: bool = False,
        show_daily_goal: bool = True
    ) -> InlineKeyboardMarkup:
        """
        Get quick actions keyboard for main menu context.
        
        Args:
            has_active_quiz: Whether user has a quiz in progress
            show_daily_goal: Whether to show daily goal progress
        
        Returns:
            InlineKeyboardMarkup with quick action buttons
        """
        builder = InlineKeyboardBuilder()
        
        # Primary quick action
        if has_active_quiz:
            builder.button(
                text="▶️ Continue Quiz",
                callback_data="menu_continue"
            )
        else:
            builder.button(
                text="⚡ Quick 5-Question Quiz",
                callback_data="menu_quick_quiz"
            )
        
        # Daily goal
        if show_daily_goal:
            builder.button(
                text="🎯 Daily Goal",
                callback_data="menu_daily_goal"
            )
        
        # Refresh stats
        builder.button(
            text="🔄 Refresh",
            callback_data="menu_refresh"
        )
        
        builder.adjust(2 if show_daily_goal else 2)
        return builder.as_markup()
    
    @staticmethod
    def get_back_to_enhanced_menu_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard with back to enhanced menu option"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text="◀️ Back to Menu",
            callback_data="back_to_enhanced_menu"
        )
        builder.button(
            text="🔄 Refresh",
            callback_data="menu_refresh"
        )
        
        builder.adjust(2)
        return builder.as_markup()
    
    # ============================================================================
    # Beauty & Interactive Methods
    # ============================================================================
    
    @staticmethod
    def get_beautiful_daily_goal_keyboard(
        quizzes_done: int,
        daily_goal: int,
        accuracy: float
    ) -> InlineKeyboardMarkup:
        """Get a beautiful daily goal keyboard with progress visualization"""
        builder = InlineKeyboardBuilder()
        
        # Progress display
        progress = min(100, (quizzes_done / daily_goal) * 100) if daily_goal > 0 else 0
        remaining = max(0, daily_goal - quizzes_done)
        
        # Status message based on progress
        if remaining == 0:
            status_text = "🎉 Goal Completed!"
            action_text = "Start New Quiz"
            action_callback = "start_quiz"
        else:
            status_text = f"🎯 {remaining} more to go!"
            action_text = "⚡ Quick Quiz"
            action_callback = "menu_quick_quiz"
        
        # Main action button
        builder.button(
            text=action_text,
            callback_data=action_callback
        )
        
        # Daily goal button
        builder.button(
            text="📊 View Progress",
            callback_data="my_progress"
        )
        
        # Refresh button
        builder.button(
            text="🔄 Update",
            callback_data="menu_refresh"
        )
        
        # Back to menu
        builder.button(
            text="◀️ Back to Menu",
            callback_data="back_to_enhanced_menu"
        )
        
        builder.adjust(2, 1, 1)
        return builder.as_markup()
    
    @staticmethod
    def get_streak_celebration_keyboard(streak_days: int) -> InlineKeyboardMarkup:
        """Get a celebration keyboard when user has a streak"""
        builder = InlineKeyboardBuilder()
        
        # Streak celebration message
        if streak_days >= 7:
            builder.button(
                text="🔥 Amazing Streak!",
                callback_data="start_quiz"
            )
        elif streak_days >= 3:
            builder.button(
                text="💪 Keep It Up!",
                callback_data="start_quiz"
            )
        else:
            builder.button(
                text="🚀 Start Your Streak!",
                callback_data="start_quiz"
            )
        
        # View progress
        builder.button(
            text="📊 My Progress",
            callback_data="my_progress"
        )
        
        # Back
        builder.button(
            text="◀️ Back",
            callback_data="back_to_enhanced_menu"
        )
        
        builder.adjust(2, 1)
        return builder.as_markup()
    
    @staticmethod
    def get_help_keyboard() -> InlineKeyboardMarkup:
        """Get help menu keyboard with common questions"""
        builder = InlineKeyboardBuilder()
        
        # Help sections
        builder.button(
            text="❓ How to Take Quiz",
            callback_data="help_quiz"
        )
        builder.button(
            text="💳 Subscription Info",
            callback_data="help_subscription"
        )
        
        builder.button(
            text="🎁 Referrals",
            callback_data="help_referral"
        )
        builder.button(
            text="📊 Progress Tracking",
            callback_data="help_progress"
        )
        
        # Contact support
        builder.button(
            text="💬 Contact Support",
            callback_data="contact"
        )
        
        # Back
        builder.button(
            text="◀️ Back to Menu",
            callback_data="back_to_enhanced_menu"
        )
        
        builder.adjust(2, 2, 1, 1)
        return builder.as_markup()

    @staticmethod
    def get_premium_feature_keyboard() -> InlineKeyboardMarkup:
        """Get premium features showcase keyboard"""
        builder = InlineKeyboardBuilder()
        
        # Premium features
        builder.button(
            text="💎 Unlimited Quizzes",
            callback_data="premium_unlimited"
        )
        builder.button(
            text="🎯 All Difficulties",
            callback_data="premium_difficulty"
        )
        
        builder.button(
            text="📈 Advanced Analytics",
            callback_data="premium_analytics"
        )
        builder.button(
            text="🏆 All Leaderboards",
            callback_data="premium_leaderboard"
        )
        
        # Get premium button
        builder.button(
            text="💳 Get Premium",
            callback_data="subscription"
        )
        
        # Back
        builder.button(
            text="◀️ Back to Menu",
            callback_data="back_to_enhanced_menu"
        )
        
        builder.adjust(2, 2, 1, 1)
        return builder.as_markup()
    
    @staticmethod
    def get_welcome_back_keyboard(
        user_name: str,
        streak_days: int,
        quizzes_today: int,
        daily_goal: int,
        is_premium: bool
    ) -> InlineKeyboardMarkup:
        """Get personalized welcome back keyboard"""
        builder = InlineKeyboardBuilder()
        
        # Personalized greeting with name
        greeting = get_time_of_day_greeting()
        time_emoji = get_time_of_day_emoji()
        
        # Main action - Start Quiz
        if quizzes_today >= daily_goal and daily_goal > 0:
            # Goal reached - encourage break or new quiz
            builder.button(
                text="🎉 Goal Reached!",
                callback_data="start_quiz"
            )
        else:
            builder.button(
                text="🎯 Take a Quiz",
                callback_data="start_quiz"
            )
        
        # Quick stats
        if streak_days > 0:
            builder.button(
                text=f"🔥 {streak_days} Day Streak",
                callback_data="my_progress"
            )
        else:
            builder.button(
                text="📊 View Progress",
                callback_data="my_progress"
            )
        
        # Daily goal progress
        if daily_goal > 0:
            goal_progress = f"📊 {quizzes_today}/{daily_goal}"
        else:
            goal_progress = "📊 Daily Goal"
        
        builder.button(
            text=goal_progress,
            callback_data="menu_daily_goal"
        )
        
        # Subscription status
        if is_premium:
            builder.button(
                text="💎 Premium",
                callback_data="subscription"
            )
        else:
            builder.button(
                text="💳 Upgrade",
                callback_data="subscription"
            )
        
        # Secondary actions
        builder.button(
            text="🏆 Leaderboard",
            callback_data="leaderboard"
        )
        builder.button(
            text="🎁 Referrals",
            callback_data="my_referrals"
        )
        
        # Help and refresh
        builder.button(
            text="❓ Help",
            callback_data="help"
        )
        builder.button(
            text="🔄 Refresh",
            callback_data="menu_refresh"
        )
        
        # Adjust layout
        builder.adjust(2, 2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def get_admin_quick_actions_keyboard() -> InlineKeyboardMarkup:
        """Get admin quick actions keyboard"""
        builder = InlineKeyboardBuilder()
        
        # Dashboard
        builder.button(
            text="📊 Dashboard",
            callback_data="admin_dashboard"
        )
        builder.button(
            text="👥 Users",
            callback_data="admin_users"
        )
        
        # Payments
        builder.button(
            text="💰 Payments",
            callback_data="admin_payments"
        )
        builder.button(
            text="❓ Questions",
            callback_data="admin_questions"
        )
        
        # Stats & Logs
        builder.button(
            text="📈 Stats",
            callback_data="admin_stats"
        )
        builder.button(
            text="📝 Logs",
            callback_data="admin_logs"
        )
        
        # Back to user menu
        builder.button(
            text="◀️ Back to User Menu",
            callback_data="back_to_user_menu"
        )
        
        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()

