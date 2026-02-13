from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

class LeaderboardKeyboard:
    @staticmethod
    def get_main_leaderboard_menu() -> InlineKeyboardMarkup:
        """Get main leaderboard menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🌍 Global",
                    callback_data="leaderboard_global"
                ),
                InlineKeyboardButton(
                    text="📅 Weekly",
                    callback_data="leaderboard_weekly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 By Subject",
                    callback_data="leaderboard_subjects"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Speed",
                    callback_data="leaderboard_speed"
                ),
                InlineKeyboardButton(
                    text="🎯 Accuracy",
                    callback_data="leaderboard_accuracy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Friends",
                    callback_data="leaderboard_friends"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 My Ranking",
                    callback_data="my_ranking"
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
    def get_leaderboard_actions() -> InlineKeyboardMarkup:
        """Get general leaderboard actions keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="refresh_leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 My Ranking",
                    callback_data="my_ranking"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Leaderboards",
                    callback_data="back_to_leaderboards"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_global_leaderboard_actions() -> InlineKeyboardMarkup:
        """Get global leaderboard specific actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="refresh_leaderboard"
                ),
                InlineKeyboardButton(
                    text="📅 Weekly",
                    callback_data="leaderboard_weekly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 By Subject",
                    callback_data="leaderboard_subjects"
                ),
                InlineKeyboardButton(
                    text="🎯 Accuracy",
                    callback_data="leaderboard_accuracy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 My Ranking",
                    callback_data="my_ranking"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Leaderboards",
                    callback_data="back_to_leaderboards"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_weekly_leaderboard_actions() -> InlineKeyboardMarkup:
        """Get weekly leaderboard specific actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="refresh_leaderboard"
                ),
                InlineKeyboardButton(
                    text="🌍 Global",
                    callback_data="leaderboard_global"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 My Ranking",
                    callback_data="my_ranking"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Leaderboards",
                    callback_data="back_to_leaderboards"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_subject_leaderboard_menu(subjects: List[Dict]) -> InlineKeyboardMarkup:
        """Get subject leaderboard selection menu"""
        builder = InlineKeyboardBuilder()
        
        for subject in subjects:
            builder.button(
                text=f"📚 {subject['subject_name']}",
                callback_data=f"subject_leaderboard_{subject['subject_id']}"
            )
        
        builder.button(
            text="🔄 Refresh",
            callback_data="refresh_leaderboard"
        )
        builder.button(
            text="◀️ Back to Leaderboards",
            callback_data="back_to_leaderboards"
        )
        
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_subject_leaderboard_actions(subject_id: int) -> InlineKeyboardMarkup:
        """Get subject leaderboard specific actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data=f"refresh_subject_{subject_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 All Subjects",
                    callback_data="leaderboard_subjects"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Leaderboards",
                    callback_data="back_to_leaderboards"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_speed_leaderboard_actions() -> InlineKeyboardMarkup:
        """Get speed leaderboard specific actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="refresh_leaderboard"
                ),
                InlineKeyboardButton(
                    text="🌍 Global",
                    callback_data="leaderboard_global"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Accuracy",
                    callback_data="leaderboard_accuracy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Leaderboards",
                    callback_data="back_to_leaderboards"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_accuracy_leaderboard_actions() -> InlineKeyboardMarkup:
        """Get accuracy leaderboard specific actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="refresh_leaderboard"
                ),
                InlineKeyboardButton(
                    text="⚡ Speed",
                    callback_data="leaderboard_speed"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Global",
                    callback_data="leaderboard_global"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Leaderboards",
                    callback_data="back_to_leaderboards"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_my_ranking_actions() -> InlineKeyboardMarkup:
        """Get my ranking page actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🌍 View Global Rank",
                    callback_data="leaderboard_global"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 View Weekly Rank",
                    callback_data="leaderboard_weekly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Refresh Stats",
                    callback_data="refresh_leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Leaderboards",
                    callback_data="back_to_leaderboards"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
