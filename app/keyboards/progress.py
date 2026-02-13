from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

class ProgressKeyboard:
    @staticmethod
    def get_progress_dashboard() -> InlineKeyboardMarkup:
        """Get progress dashboard keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📊 Overview",
                    callback_data="progress_overview"
                ),
                InlineKeyboardButton(
                    text="📈 Trends",
                    callback_data="view_trends"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Weak Areas",
                    callback_data="weak_areas"
                ),
                InlineKeyboardButton(
                    text="📊 Compare",
                    callback_data="compare_performance"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Daily Goals",
                    callback_data="daily_goals"
                ),
                InlineKeyboardButton(
                    text="🏆 Achievements",
                    callback_data="milestones"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 Download Report",
                    callback_data="download_progress"
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
    def get_weak_areas_actions() -> InlineKeyboardMarkup:
        """Get weak areas actions keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🎯 Targeted Practice",
                    callback_data="targeted_practice"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 View Trends",
                    callback_data="view_trends"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Progress",
                    callback_data="back_to_progress"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_trends_actions() -> InlineKeyboardMarkup:
        """Get trends actions keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📊 Generate Graph",
                    callback_data="generate_graph"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Weak Areas",
                    callback_data="weak_areas"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Progress",
                    callback_data="back_to_progress"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_comparison_actions() -> InlineKeyboardMarkup:
        """Get comparison actions keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🏆 See Leaderboard",
                    callback_data="see_leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📈 View Trends",
                    callback_data="view_trends"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Progress",
                    callback_data="back_to_progress"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_daily_goals_keyboard(goal=None, claimed=False) -> InlineKeyboardMarkup:
        """Get daily goals keyboard"""
        builder = InlineKeyboardBuilder()

        if goal and not goal.is_completed:
            builder.button(
                text="✅ Mark Complete",
                callback_data="mark_goal_complete"
            )
        elif goal and goal.is_completed and not claimed:
            builder.button(
                text="🎁 Claim Reward",
                callback_data="claim_reward"
            )
        elif claimed:
            builder.button(
                text="🎯 Set New Goal",
                callback_data="set_new_goal"
            )

        builder.button(
            text="📊 View Progress",
            callback_data="view_progress"
        )
        builder.button(
            text="◀️ Back to Progress",
            callback_data="back_to_progress"
        )

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_achievements_keyboard() -> InlineKeyboardMarkup:
        """Get achievements keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🏆 View All",
                    callback_data="view_all_achievements"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Progress Stats",
                    callback_data="progress_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Progress",
                    callback_data="back_to_progress"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
