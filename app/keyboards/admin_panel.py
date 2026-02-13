"""
Admin Panel Keyboard for Telegram Quiz Bot
Simple, clean admin panel with essential admin functions
"""

from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class AdminPanelKeyboard:
    """
    Admin panel keyboard with essential admin functions.
    
    Features:
    - View All Users
    - Approve Pending Users
    - Add Questions via CSV
    - View Reports / Stats
    - Manage Payments
    - Broadcast Message to Users
    - Settings
    - Back to Main Menu
    """
    
    # Emoji mappings with fallbacks
    EMOJIS = {
        'users': '👥',
        'approve': '✅',
        'csv': '📁',
        'stats': '📊',
        'payments': '💰',
        'broadcast': '📢',
        'settings': '⚙️',
        'back': '🔙',
        'main_menu': '🏠',
        'default': '📌'
    }
    
    # Callback data prefixes
    CALLBACKS = {
        'view_users': 'admin_view_users',
        'approve_users': 'admin_approve_users',
        'add_csv': 'admin_add_csv',
        'view_stats': 'admin_view_stats',
        'manage_payments': 'admin_manage_payments',
        'broadcast': 'admin_broadcast',
        'settings': 'admin_settings',
        'back_menu': 'back_to_menu',
        'main_menu': 'main_menu'
    }
    
    @classmethod
    def _get_emoji(cls, key: str, default: Optional[str] = None) -> str:
        """Get emoji with fallback to default or empty string"""
        return cls.EMOJIS.get(key, default or '')
    
    @classmethod
    def get_menu(cls) -> InlineKeyboardMarkup:
        """
        Create the main admin panel keyboard.
        
        Returns:
            InlineKeyboardMarkup: Admin panel with all menu options
        """
        # Get emojis with fallbacks
        emoji_users = cls._get_emoji('users', '👥')
        emoji_approve = cls._get_emoji('approve', '✅')
        emoji_csv = cls._get_emoji('csv', '📁')
        emoji_stats = cls._get_emoji('stats', '📊')
        emoji_payments = cls._get_emoji('payments', '💰')
        emoji_broadcast = cls._get_emoji('broadcast', '📢')
        emoji_settings = cls._get_emoji('settings', '⚙️')
        emoji_back = cls._get_emoji('back', '🔙')
        emoji_main = cls._get_emoji('main_menu', '🏠')
        
        # Build keyboard layout
        keyboard = [
            # Row 1: User Management
            [
                InlineKeyboardButton(
                    text=f"{emoji_users} View All Users",
                    callback_data=cls.CALLBACKS['view_users']
                ),
                InlineKeyboardButton(
                    text=f"{emoji_approve} Approve Pending Users",
                    callback_data=cls.CALLBACKS['approve_users']
                )
            ],
            # Row 2: Questions & Stats
            [
                InlineKeyboardButton(
                    text=f"{emoji_csv} Add Questions via CSV",
                    callback_data=cls.CALLBACKS['add_csv']
                ),
                InlineKeyboardButton(
                    text=f"{emoji_stats} View Reports / Stats",
                    callback_data=cls.CALLBACKS['view_stats']
                )
            ],
            # Row 3: Payments & Broadcast
            [
                InlineKeyboardButton(
                    text=f"{emoji_payments} Manage Payments",
                    callback_data=cls.CALLBACKS['manage_payments']
                ),
                InlineKeyboardButton(
                    text=f"{emoji_broadcast} Broadcast Message",
                    callback_data=cls.CALLBACKS['broadcast']
                )
            ],
            # Row 4: Settings & Back
            [
                InlineKeyboardButton(
                    text=f"{emoji_settings} Settings",
                    callback_data=cls.CALLBACKS['settings']
                ),
                InlineKeyboardButton(
                    text=f"{emoji_back} Back to Main Menu",
                    callback_data=cls.CALLBACKS['back_menu']
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @classmethod
    def get_users_submenu(cls) -> InlineKeyboardMarkup:
        """Get submenu for user management actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔍 Search User",
                    callback_data="admin_search_user"
                ),
                InlineKeyboardButton(
                    text="🚫 Block User",
                    callback_data="admin_block_user"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 User Statistics",
                    callback_data="admin_user_stats"
                ),
                InlineKeyboardButton(
                    text="◀️ Back to Admin",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @classmethod
    def get_csv_submenu(cls) -> InlineKeyboardMarkup:
        """Get submenu for CSV import actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📤 Upload CSV",
                    callback_data="admin_upload_csv"
                ),
                InlineKeyboardButton(
                    text="📋 Download Template",
                    callback_data="admin_download_template"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Validate CSV",
                    callback_data="admin_validate_csv"
                ),
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @classmethod
    def get_stats_submenu(cls) -> InlineKeyboardMarkup:
        """Get submenu for statistics/viewing actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📈 Dashboard",
                    callback_data="admin_dashboard"
                ),
                InlineKeyboardButton(
                    text="💰 Revenue Stats",
                    callback_data="admin_revenue_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 Leaderboard",
                    callback_data="admin_leaderboard"
                ),
                InlineKeyboardButton(
                    text="📊 Quiz Analytics",
                    callback_data="admin_quiz_analytics"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Admin",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @classmethod
    def get_payments_submenu(cls) -> InlineKeyboardMarkup:
        """Get submenu for payment management"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⏳ Pending Payments",
                    callback_data="admin_pending_payments"
                ),
                InlineKeyboardButton(
                    text="📋 All Payments",
                    callback_data="admin_all_payments"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Approve All",
                    callback_data="admin_approve_all"
                ),
                InlineKeyboardButton(
                    text="📊 Revenue Report",
                    callback_data="admin_payment_report"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Admin",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @classmethod
    def get_settings_submenu(cls) -> InlineKeyboardMarkup:
        """Get submenu for bot settings"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⏱️ Quiz Time Limit",
                    callback_data="admin_time_limit"
                ),
                InlineKeyboardButton(
                    text="📊 Passing Score",
                    callback_data="admin_passing_score"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔢 Questions Per Quiz",
                    callback_data="admin_questions_limit"
                ),
                InlineKeyboardButton(
                    text="📅 Daily Quiz Limit",
                    callback_data="admin_daily_limit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Admin",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @classmethod
    def get_confirmation_keyboard(cls, action: str, target: str = "") -> InlineKeyboardMarkup:
        """Get confirmation keyboard for destructive actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Confirm",
                    callback_data=f"confirm_{action}_{target}" if target else f"confirm_{action}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_action"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @classmethod
    def get_back_button(cls, callback_data: str = "back_to_admin", text: str = "◀️ Back") -> InlineKeyboardMarkup:
        """Get a simple back button keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=callback_data
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Example usage:
"""
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

bot = Bot(token="YOUR_TOKEN")
dp = Dispatcher(bot)

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    keyboard = AdminPanelKeyboard.get_menu()
    await message.answer(
        "👑 *Admin Panel*\n\nSelect an option:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query()
async def admin_callback(callback: types.CallbackQuery):
    if callback.data == "admin_view_users":
        # Handle view users
        pass
    elif callback.data == "admin_add_csv":
        # Handle CSV upload
        pass
    # ... handle other callbacks
"""

