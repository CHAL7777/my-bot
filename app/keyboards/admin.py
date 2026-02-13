"""
Comprehensive Admin Panel Keyboards for Telegram Quiz Bot
All inline keyboards for admin panel operations
"""

from typing import List, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.constants import EMOJIS


class AdminKeyboard:
    """Main admin panel keyboard with all menu options"""
    
    @staticmethod
    def get_admin_panel(is_superadmin: bool = False) -> InlineKeyboardMarkup:
        """Get main admin panel keyboard
        
        Args:
            is_superadmin: If True, shows admin management button for superadmins
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['user']} Manage Users",
                    callback_data="admin_users"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['question']} Manage Questions",
                    callback_data="admin_questions"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['subject']} Manage Subjects",
                    callback_data="admin_subjects"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['payment']} Manage Payments",
                    callback_data="admin_payments"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['gift']} Referral Management",
                    callback_data="admin_referrals"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['score']} View Stats",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['settings']} Bot Settings",
                    callback_data="admin_settings"
                )
            ],
        ]
        
        # Add Admin Management button for superadmins only
        if is_superadmin:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{EMOJIS['admin']} 👑 Admin Management",
                    callback_data="admin_manage_admins"
                )
            ])
        
        # Add Activity Logs and Back to Menu
        keyboard.extend([
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['info']} Activity Logs",
                    callback_data="admin_logs"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Back to Menu",
                    callback_data="back_to_user_menu"
                )
            ]
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_confirmation_keyboard(action: str, target_id: int, 
                                  confirm_text: str = "Confirm",
                                  cancel_text: str = "Cancel") -> InlineKeyboardMarkup:
        """Get confirmation keyboard for destructive actions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"✅ {confirm_text}",
                    callback_data=f"confirm_{action}_{target_id}"
                ),
                InlineKeyboardButton(
                    text=f"❌ {cancel_text}",
                    callback_data=f"cancel_{action}_{target_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard with only back button"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"◀️ Back to Admin",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AdminUsersKeyboard:
    """Keyboard for user management"""
    
    @staticmethod
    def get_user_management() -> InlineKeyboardMarkup:
        """Get user management keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['list']} View All Users",
                    callback_data="admin_users_list"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['search']} Search User",
                    callback_data="admin_users_search"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['approve']} Approve User",
                    callback_data="admin_users_approve"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['block']} Block User",
                    callback_data="admin_users_block"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['unblock']} Unblock User",
                    callback_data="admin_users_unblock"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['stats']} User Stats",
                    callback_data="admin_users_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"◀️ Back to Admin",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_users_list_keyboard(users: List, page: int = 0, 
                                page_size: int = 5) -> InlineKeyboardMarkup:
        """Get paginated user list keyboard"""
        builder = InlineKeyboardBuilder()
        
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        for user in users[start_idx:end_idx]:
            user_text = f"@{user.username}" if user.username else f"{user.first_name}"
            blocked_text = "🚫" if user.blocked else ""
            builder.button(
                text=f"{user_text} {blocked_text}",
                callback_data=f"admin_user_view_{user.user_id}"
            )
        
        # Pagination row
        row_buttons = []
        if page > 0:
            row_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Prev",
                    callback_data=f"admin_users_page_{page - 1}"
                )
            )
        
        row_buttons.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1}",
                callback_data="no_action"
            )
        )
        
        if end_idx < len(users):
            row_buttons.append(
                InlineKeyboardButton(
                    text="Next ▶️",
                    callback_data=f"admin_users_page_{page + 1}"
                )
            )
        
        builder.row(*row_buttons)
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back to User Management",
                callback_data="admin_users"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_user_action_keyboard(user_id: int, is_blocked: bool = False) -> InlineKeyboardMarkup:
        """Get actions for a specific user"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['stats']} View Stats",
                    callback_data=f"admin_user_stats_{user_id}"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['progress']} View Progress",
                    callback_data=f"admin_user_progress_{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['message']} Send Message",
                    callback_data=f"admin_user_message_{user_id}"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['payment']} View Payments",
                    callback_data=f"admin_user_payments_{user_id}"
                )
            ],
        ]
        
        if is_blocked:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ Unblock User",
                    callback_data=f"admin_user_unblock_{user_id}"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🚫 Block User",
                    callback_data=f"admin_user_block_{user_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Back",
                callback_data="admin_users_list"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_block_confirmation_keyboard(user_id: int, username: str = None) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for blocking user"""
        name = username or f"User {user_id}"
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⚠️ Confirm Block",
                    callback_data=f"confirm_block_user_{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_block_user"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data=f"admin_user_view_{user_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_search_keyboard() -> InlineKeyboardMarkup:
        """Get search options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔍 Search by Username",
                    callback_data="search_by_username"
                ),
                InlineKeyboardButton(
                    text="🔍 Search by User ID",
                    callback_data="search_by_userid"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Search by Name",
                    callback_data="search_by_name"
                ),
                InlineKeyboardButton(
                    text="◀️ Cancel",
                    callback_data="admin_users"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AdminQuestionsKeyboard:
    """Keyboard for question management"""
    
    @staticmethod
    def get_question_management() -> InlineKeyboardMarkup:
        """Get question management keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['upload']} Upload CSV",
                    callback_data="admin_questions_import"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['add']} Add Question",
                    callback_data="admin_questions_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['list']} View Questions",
                    callback_data="admin_questions_list"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['search']} Search Questions",
                    callback_data="admin_questions_search"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['edit']} Edit Question",
                    callback_data="admin_questions_edit"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['delete']} Delete Question",
                    callback_data="admin_questions_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['template']} Download Template",
                    callback_data="admin_questions_template"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['stats']} Question Stats",
                    callback_data="admin_questions_stats"
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
    
    @staticmethod
    def get_questions_list_keyboard(questions: List, page: int = 0,
                                    page_size: int = 5) -> InlineKeyboardMarkup:
        """Get paginated questions list keyboard"""
        builder = InlineKeyboardBuilder()
        
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        for question in questions[start_idx:end_idx]:
            preview = question.question_text[:30] + "..." if len(question.question_text) > 30 else question.question_text
            builder.button(
                text=f"Q{question.question_id}: {preview}",
                callback_data=f"admin_question_view_{question.question_id}"
            )
        
        # Pagination
        row_buttons = []
        if page > 0:
            row_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Prev",
                    callback_data=f"admin_questions_list_page_{page - 1}"
                )
            )
        
        row_buttons.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1}",
                callback_data="no_action"
            )
        )
        
        if end_idx < len(questions):
            row_buttons.append(
                InlineKeyboardButton(
                    text="Next ▶️",
                    callback_data=f"admin_questions_list_page_{page + 1}"
                )
            )
        
        builder.row(*row_buttons)
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back to Questions",
                callback_data="admin_questions"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_question_action_keyboard(question_id: int) -> InlineKeyboardMarkup:
        """Get actions for a specific question"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['edit']} Edit",
                    callback_data=f"admin_question_edit_{question_id}"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['view']} View Full",
                    callback_data=f"admin_question_detail_{question_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📊 Question Stats",
                    callback_data=f"admin_question_stats_{question_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Delete Question",
                    callback_data=f"admin_question_delete_confirm_{question_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to List",
                    callback_data="admin_questions_list"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_delete_confirmation_keyboard(question_id: int) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for deleting question"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⚠️ Confirm Delete",
                    callback_data=f"confirm_delete_question_{question_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_delete_question"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data=f"admin_question_view_{question_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_difficulty_keyboard() -> InlineKeyboardMarkup:
        """Get difficulty selection keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🟢 Simple",
                    callback_data="difficulty_simple"
                ),
                InlineKeyboardButton(
                    text="🟡 Medium",
                    callback_data="difficulty_medium"
                ),
                InlineKeyboardButton(
                    text="🔴 Hard",
                    callback_data="difficulty_hard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Cancel",
                    callback_data="admin_questions_add"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_subject_selection_keyboard(subjects: List) -> InlineKeyboardMarkup:
        """Get subject selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        for subject in subjects:
            builder.button(
                text=subject.subject_name,
                callback_data=f"select_subject_{subject.subject_id}"
            )
        
        builder.row(
            InlineKeyboardButton(
                text="➕ Add New Subject",
                callback_data="admin_subjects_add"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="◀️ Cancel",
                callback_data="admin_questions_add"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_chapter_selection_keyboard(chapters: List) -> InlineKeyboardMarkup:
        """Get chapter selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        for chapter in chapters:
            builder.button(
                text=chapter.chapter_name,
                callback_data=f"select_chapter_{chapter.chapter_id}"
            )
        
        builder.row(
            InlineKeyboardButton(
                text="◀️ Change Subject",
                callback_data="admin_questions_add"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_csv_import_keyboard() -> InlineKeyboardMarkup:
        """Get CSV import options keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📤 Upload CSV File",
                    callback_data="admin_questions_csv_upload"
                ),
                InlineKeyboardButton(
                    text="📋 Download Template",
                    callback_data="admin_questions_template"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Validate Before Import",
                    callback_data="admin_questions_validate"
                ),
                InlineKeyboardButton(
                    text="◀️ Cancel",
                    callback_data="admin_questions"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AdminSubjectsKeyboard:
    """Keyboard for subject management"""
    
    @staticmethod
    def get_subjects_list_keyboard(subjects: List, 
                                   subject_counts: Dict[int, int] = None) -> InlineKeyboardMarkup:
        '''
        Get subjects list keyboard with question counts.
        
        This method prevents DetachedInstanceError by accepting
        pre-computed question counts instead of accessing lazy-loaded
        relationships on Subject objects.
        
        Args:
            subjects: List of Subject ORM objects
            subject_counts: Optional dict mapping subject_id -> question_count
                           If provided, displays counts next to subject names
        
        Returns:
            InlineKeyboardMarkup ready to use in bot response
        '''
        builder = InlineKeyboardBuilder()
        
        for subject in subjects:
            # Build display text with or without count
            if subject_counts and subject.subject_id in subject_counts:
                display_text = f"{subject.subject_name} ({subject_counts[subject.subject_id]} questions)"
            else:
                display_text = subject.subject_name
            
            builder.button(
                text=display_text,
                callback_data=f"admin_subject_view_{subject.subject_id}"
            )
        
        builder.row(
            InlineKeyboardButton(
                text="➕ Add New Subject",
                callback_data="admin_subjects_add"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back",
                callback_data="admin_subjects"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_subject_management() -> InlineKeyboardMarkup:
        """Get subject management keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['add']} Add Subject",
                    callback_data="admin_subjects_add"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['list']} View Subjects",
                    callback_data="admin_subjects_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['edit']} Edit Subject",
                    callback_data="admin_subjects_edit"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['delete']} Delete Subject",
                    callback_data="admin_subjects_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['stats']} Subject Stats",
                    callback_data="admin_subjects_stats"
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
    
    @staticmethod
    def get_subject_action_keyboard(subject_id: int) -> InlineKeyboardMarkup:
        """Get actions for a specific subject"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['edit']} Edit Subject",
                    callback_data=f"admin_subject_edit_{subject_id}"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['list']} View Chapters",
                    callback_data=f"admin_subject_chapters_{subject_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['question']} Add Chapter",
                    callback_data=f"admin_subject_add_chapter_{subject_id}"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['stats']} View Stats",
                    callback_data=f"admin_subject_stats_{subject_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Delete Subject",
                    callback_data=f"admin_subject_delete_confirm_{subject_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to List",
                    callback_data="admin_subjects_list"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_delete_subject_confirmation_keyboard(subject_id: int) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for deleting subject"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⚠️ Confirm Delete (Will delete all questions!)",
                    callback_data=f"confirm_delete_subject_{subject_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_delete_subject"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data=f"admin_subject_view_{subject_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AdminPaymentsKeyboard:
    """Keyboard for payment management with inline screenshot review"""
    
    @staticmethod
    def get_payment_management() -> InlineKeyboardMarkup:
        """Get payment management keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['pending']} Pending Payments",
                    callback_data="admin_payments_pending"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['list']} View All Payments",
                    callback_data="admin_payments_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['stats']} Revenue Stats",
                    callback_data="admin_payments_stats"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['approve']} Approve All",
                    callback_data="admin_payments_approve_all"
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
    
    @staticmethod
    def get_pending_payments_keyboard(payments: List, page: int = 0,
                                      page_size: int = 5) -> InlineKeyboardMarkup:
        """Get pending payments list keyboard"""
        builder = InlineKeyboardBuilder()
        
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        for payment in payments[start_idx:end_idx]:
            # Get user info safely - handle case where user might not be loaded
            user_id = getattr(payment, 'user_id', None)
            user_first_name = getattr(payment, 'user_first_name', None) or "Unknown"
            user_username = getattr(payment, 'user_username', None)
            
            if user_username:
                username = f"@{user_username}"
            else:
                username = user_first_name
            
            builder.button(
                text=f"#{payment.payment_id} - {username} - {payment.amount} ETB",
                callback_data=f"admin_payment_view_{payment.payment_id}"
            )
        
        # Pagination
        row_buttons = []
        if page > 0:
            row_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Prev",
                    callback_data=f"admin_payments_pending_page_{page - 1}"
                )
            )
        
        row_buttons.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1}",
                callback_data="no_action"
            )
        )
        
        if end_idx < len(payments):
            row_buttons.append(
                InlineKeyboardButton(
                    text="Next ▶️",
                    callback_data=f"admin_payments_pending_page_{page + 1}"
                )
            )
        
        builder.row(*row_buttons)
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back to Payments",
                callback_data="admin_payments"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def get_payment_action_keyboard(payment_id: int, status: str = 'pending') -> InlineKeyboardMarkup:
        """Get actions for a specific payment"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['screenshot']} View Screenshot",
                    callback_data=f"admin_payment_screenshot_{payment_id}"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['user']} View User",
                    callback_data=f"admin_payment_user_{payment_id}"
                )
            ]
        ]
        
        if status == 'pending':
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ Approve",
                    callback_data=f"admin_payment_approve_{payment_id}"
                ),
                InlineKeyboardButton(
                    text=f"❌ Reject",
                    callback_data=f"admin_payment_reject_{payment_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="📝 Add Note",
                callback_data=f"admin_payment_note_{payment_id}"
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Back to Payments",
                callback_data="admin_payments_pending"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_screenshot_review_inline_keyboard(payment_id: int) -> InlineKeyboardMarkup:
        """
        Get inline keyboard for screenshot review.
        
        This keyboard is sent WITH the screenshot using sendPhoto.
        Admin can approve/reject directly from the screenshot message.
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Approve",
                    callback_data=f"review_approve_{payment_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Reject",
                    callback_data=f"review_reject_{payment_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['user']} User Info",
                    callback_data=f"admin_payment_user_{payment_id}"
                ),
                InlineKeyboardButton(
                    text="📝 Add Note",
                    callback_data=f"admin_payment_note_{payment_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to List",
                    callback_data="admin_payments_pending"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_approve_confirmation_keyboard(payment_id: int) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for approving payment"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Confirm Approve",
                    callback_data=f"confirm_approve_payment_{payment_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_approve_payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data=f"admin_payment_view_{payment_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_reject_confirmation_keyboard(payment_id: int) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for rejecting payment"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Confirm Reject",
                    callback_data=f"confirm_reject_payment_{payment_id}"
                ),
                InlineKeyboardButton(
                    text="◀️ Cancel",
                    callback_data="cancel_reject_payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data=f"admin_payment_view_{payment_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_reject_with_reason_keyboard(payment_id: int) -> InlineKeyboardMarkup:
        """Get keyboard for rejecting with quick reason options"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Unclear Screenshot",
                    callback_data=f"reject_reason_{payment_id}_unclear_screenshot"
                ),
                InlineKeyboardButton(
                    text="💰 Wrong Amount",
                    callback_data=f"reject_reason_{payment_id}_wrong_amount"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔢 No Transaction ID",
                    callback_data=f"reject_reason_{payment_id}_no_transaction_id"
                ),
                InlineKeyboardButton(
                    text="🔄 Duplicate Payment",
                    callback_data=f"reject_reason_{payment_id}_duplicate_payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Custom Reason",
                    callback_data=f"admin_payment_reject_{payment_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Cancel",
                    callback_data=f"admin_payment_view_{payment_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_payment_filter_keyboard() -> InlineKeyboardMarkup:
        """Get payment filter options"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🟡 Pending",
                    callback_data="filter_pending"
                ),
                InlineKeyboardButton(
                    text="🟢 Approved",
                    callback_data="filter_approved"
                ),
                InlineKeyboardButton(
                    text="🔴 Rejected",
                    callback_data="filter_rejected"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Today",
                    callback_data="filter_today"
                ),
                InlineKeyboardButton(
                    text="📅 This Week",
                    callback_data="filter_week"
                ),
                InlineKeyboardButton(
                    text="📅 This Month",
                    callback_data="filter_month"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to Payments",
                    callback_data="admin_payments"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AdminStatsKeyboard:
    """Keyboard for stats and analytics"""
    
    @staticmethod
    def get_stats_menu() -> InlineKeyboardMarkup:
        """Get stats menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['dashboard']} Dashboard Overview",
                    callback_data="admin_stats_dashboard"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['users']} User Statistics",
                    callback_data="admin_stats_users"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['questions']} Question Statistics",
                    callback_data="admin_stats_questions"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['score']} Quiz Statistics",
                    callback_data="admin_stats_quizzes"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['money']} Revenue Statistics",
                    callback_data="admin_stats_revenue"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['trophy']} Leaderboard",
                    callback_data="admin_stats_leaderboard"
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
    
    @staticmethod
    def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
        """Get leaderboard period selection"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📅 Today",
                    callback_data="leaderboard_daily"
                ),
                InlineKeyboardButton(
                    text="📅 This Week",
                    callback_data="leaderboard_weekly"
                ),
                InlineKeyboardButton(
                    text="📅 This Month",
                    callback_data="leaderboard_monthly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 All Time",
                    callback_data="leaderboard_overall"
                ),
                InlineKeyboardButton(
                    text="🧹 Clear Leaderboard",
                    callback_data="admin_leaderboard_clear"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="admin_stats"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_clear_leaderboard_confirmation() -> InlineKeyboardMarkup:
        """Get confirmation for clearing leaderboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⚠️ Confirm Clear All",
                    callback_data="confirm_clear_leaderboard"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_clear_leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="admin_stats_leaderboard"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AdminSettingsKeyboard:
    """Keyboard for bot settings"""
    
    @staticmethod
    def get_settings_menu() -> InlineKeyboardMarkup:
        """Get settings menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"⏱️ Quiz Time Limit",
                    callback_data="admin_settings_time_limit"
                ),
                InlineKeyboardButton(
                    text=f"📊 Passing Score",
                    callback_data="admin_settings_passing_score"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['message']} Broadcast Message",
                    callback_data="admin_settings_broadcast"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['settings']} Other Settings",
                    callback_data="admin_settings_other"
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
    
    @staticmethod
    def get_time_limit_options() -> InlineKeyboardMarkup:
        """Get time limit options"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="15 seconds",
                    callback_data="time_limit_15"
                ),
                InlineKeyboardButton(
                    text="30 seconds",
                    callback_data="time_limit_30"
                )
            ],
            [
                InlineKeyboardButton(
                    text="45 seconds",
                    callback_data="time_limit_45"
                ),
                InlineKeyboardButton(
                    text="60 seconds",
                    callback_data="time_limit_60"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Custom...",
                    callback_data="time_limit_custom"
                ),
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="admin_settings"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_passing_score_options() -> InlineKeyboardMarkup:
        """Get passing score options"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="50%",
                    callback_data="passing_score_50"
                ),
                InlineKeyboardButton(
                    text="60%",
                    callback_data="passing_score_60"
                )
            ],
            [
                InlineKeyboardButton(
                    text="70%",
                    callback_data="passing_score_70"
                ),
                InlineKeyboardButton(
                    text="80%",
                    callback_data="passing_score_80"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Custom...",
                    callback_data="passing_score_custom"
                ),
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="admin_settings"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_broadcast_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Get confirmation for broadcast message"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Send Broadcast",
                    callback_data="confirm_broadcast"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_broadcast"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_broadcast_preview_keyboard(message: str) -> InlineKeyboardMarkup:
        """Get broadcast preview keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Send to All Users",
                    callback_data="confirm_broadcast_send"
                ),
                InlineKeyboardButton(
                    text="✏️ Edit Message",
                    callback_data="confirm_broadcast_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_broadcast"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AdminLogsKeyboard:
    """Keyboard for admin logs viewing"""
    
    @staticmethod
    def get_logs_menu() -> InlineKeyboardMarkup:
        """Get logs menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['list']} Recent Actions",
                    callback_data="admin_logs_recent"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['search']} Search Logs",
                    callback_data="admin_logs_search"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['stats']} Action Summary",
                    callback_data="admin_logs_summary"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['user']} By Admin",
                    callback_data="admin_logs_by_admin"
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
    
    @staticmethod
    def get_logs_list_keyboard(logs: List, page: int = 0,
                               page_size: int = 10) -> InlineKeyboardMarkup:
        """Get paginated logs list"""
        builder = InlineKeyboardBuilder()
        
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        for log in logs[start_idx:end_idx]:
            action_preview = log.action[:40] + "..." if len(log.action) > 40 else log.action
            builder.button(
                text=f"{log.created_at.strftime('%d %b %H:%M')} - {action_preview}",
                callback_data=f"admin_log_view_{log.id}"
            )
        
        # Pagination
        row_buttons = []
        if page > 0:
            row_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Prev",
                    callback_data=f"admin_logs_page_{page - 1}"
                )
            )
        
        row_buttons.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1}",
                callback_data="no_action"
            )
        )
        
        if end_idx < len(logs):
            row_buttons.append(
                InlineKeyboardButton(
                    text="Next ▶️",
                    callback_data=f"admin_logs_page_{page + 1}"
                )
            )
        
        builder.row(*row_buttons)
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back to Logs",
                callback_data="admin_logs"
            )
        )
        
        return builder.as_markup()


# Convenience function to get all admin keyboards
def get_all_admin_keyboards():
    """Get reference to all admin keyboard classes"""
    return {
        'admin': AdminKeyboard,
        'users': AdminUsersKeyboard,
        'questions': AdminQuestionsKeyboard,
        'subjects': AdminSubjectsKeyboard,
        'payments': AdminPaymentsKeyboard,
        'stats': AdminStatsKeyboard,
        'settings': AdminSettingsKeyboard,
        'logs': AdminLogsKeyboard,
    }


class AdminManageKeyboard:
    """Keyboard for admin management - Enhanced with full admin CRUD operations"""

    @staticmethod
    def get_admin_management() -> InlineKeyboardMarkup:
        """Get admin management keyboard with full options"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"👥 List Admins",
                    callback_data="admin_list_all_admins"
                ),
                InlineKeyboardButton(
                    text=f"➕ Add Admin",
                    callback_data="admin_add_admin_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"➖ Remove Admin",
                    callback_data="admin_remove_admin_menu"
                ),
                InlineKeyboardButton(
                    text=f"🔄 Change Role",
                    callback_data="admin_change_role_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"👑 Top Referrers",
                    callback_data="admin_referrals_leaderboard"
                ),
                InlineKeyboardButton(
                    text=f"🔗 User Referrals",
                    callback_data="admin_users_referrals"
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

    @staticmethod
    def get_add_admin_menu() -> InlineKeyboardMarkup:
        """Get menu for adding a new admin"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔢 Add by User ID",
                    callback_data="admin_add_by_userid"
                ),
                InlineKeyboardButton(
                    text="👤 Add by Username",
                    callback_data="admin_add_by_username"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="admin_manage_admins"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_role_selection_keyboard(for_user_id: int = None) -> InlineKeyboardMarkup:
        """Get keyboard for selecting admin role
        
        Args:
            for_user_id: Optional user_id to include in callback data
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    text="👥 Admin",
                    callback_data=f"admin_role_admin_{for_user_id}" if for_user_id else "admin_role_admin"
                ),
                InlineKeyboardButton(
                    text="👑 Super Admin",
                    callback_data=f"admin_role_superadmin_{for_user_id}" if for_user_id else "admin_role_superadmin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Cancel",
                    callback_data="admin_add_admin_menu"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_remove_admin_menu(admins: List) -> InlineKeyboardMarkup:
        """Get keyboard for selecting admin to remove
        
        Args:
            admins: List of TelegramAdmin objects
        """
        builder = InlineKeyboardBuilder()
        
        for admin in admins:
            # Don't allow removing yourself
            role_emoji = "👑" if admin.role == 'superadmin' else "👥"
            status = "✅" if admin.is_active else "❌"
            username = admin.username or "No username"
            builder.button(
                text=f"{role_emoji} {status} @{username}",
                callback_data=f"admin_remove_select_{admin.user_id}"
            )
        
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back",
                callback_data="admin_manage_admins"
            )
        )
        
        return builder.as_markup()

    @staticmethod
    def get_remove_confirmation_keyboard(user_id: int, username: str = None) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for removing an admin
        
        Args:
            user_id: The admin's user ID
            username: The admin's username
        """
        name = username or f"User {user_id}"
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⚠️ Confirm Remove",
                    callback_data=f"admin_remove_confirm_{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="admin_remove_admin_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data="admin_remove_admin_menu"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_admin_list_keyboard(admins: List[Dict], page: int = 0, 
                                page_size: int = 5) -> InlineKeyboardMarkup:
        """Get paginated admin list keyboard with actions
        
        Args:
            admins: List of admin detail dictionaries
            page: Current page number
            page_size: Number of admins per page
        """
        builder = InlineKeyboardBuilder()
        
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        for admin in admins[start_idx:end_idx]:
            role_emoji = "👑" if admin['role'] == 'superadmin' else "👥"
            status = "✅" if admin['is_active'] else "❌"
            username = admin['username'] or "No username"
            
            builder.button(
                text=f"{role_emoji} {status} @{username}",
                callback_data=f"admin_view_{admin['user_id']}"
            )
        
        # Pagination
        row_buttons = []
        if page > 0:
            row_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Prev",
                    callback_data=f"admin_list_page_{page - 1}"
                )
            )
        
        row_buttons.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1}",
                callback_data="no_action"
            )
        )
        
        if end_idx < len(admins):
            row_buttons.append(
                InlineKeyboardButton(
                    text="Next ▶️",
                    callback_data=f"admin_list_page_{page + 1}"
                )
            )
        
        builder.row(*row_buttons)
        builder.row(
            InlineKeyboardButton(
                text="◀️ Back to Management",
                callback_data="admin_manage_admins"
            )
        )
        
        return builder.as_markup()

    @staticmethod
    def get_admin_detail_keyboard(user_id: int, role: str) -> InlineKeyboardMarkup:
        """Get keyboard for admin detail actions
        
        Args:
            user_id: The admin's user ID
            role: Current role ('admin' or 'superadmin')
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Promote to Super Admin" if role == 'admin' else "🔄 Demote to Admin",
                    callback_data=f"admin_toggle_role_{user_id}"
                ),
                InlineKeyboardButton(
                    text="➖ Remove Admin",
                    callback_data=f"admin_remove_select_{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back to List",
                    callback_data="admin_list_all_admins"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_change_role_menu(admins: List) -> InlineKeyboardMarkup:
        """Get menu for selecting admin to change role
        
        Args:
            admins: List of TelegramAdmin objects
        """
        builder = InlineKeyboardBuilder()
        
        for admin in admins:
            role_emoji = "👑" if admin.role == 'superadmin' else "👥"
            username = admin.username or "No username"
            builder.button(
                text=f"{role_emoji} @{username}",
                callback_data=f"admin_change_role_select_{admin.user_id}"
            )
        
        builder.row(
InlineKeyboardButton(
                text="◀️ Back",
                callback_data="admin_manage_admins"
            )
        )
        
        return builder.as_markup()

    @staticmethod
    def get_confirm_role_change_keyboard(user_id: int, new_role: str,
                                         username: str = None) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for role change
        
        Args:
            user_id: The admin's user ID
            new_role: The new role ('admin' or 'superadmin')
            username: The admin's username
        """
        role_text = "Super Admin" if new_role == 'superadmin' else "Admin"
        name = username or f"User {user_id}"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"⚠️ Confirm: {role_text}",
                    callback_data=f"admin_role_confirm_{user_id}_{new_role}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="admin_change_role_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Back",
                    callback_data=f"admin_change_role_select_{user_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
        """Get keyboard with only back button"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="◀️ Back to Admin",
                    callback_data="back_to_admin"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


# =========================================================================
# REFERRAL MANAGEMENT KEYBOARD
# =========================================================================

class AdminReferralKeyboard:
    """Keyboard for referral management"""
    
    @staticmethod
    def get_referral_management() -> InlineKeyboardMarkup:
        """Get referral management main menu"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['trophy']} Top Referrers",
                    callback_data="admin_referrals_top"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['list']} All Referrers",
                    callback_data="admin_referrals_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['pending']} Pending Referrals",
                    callback_data="admin_referrals_pending"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['file']} Export Data",
                    callback_data="admin_referrals_export"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['help']} Help",
                    callback_data="admin_referrals_help"
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
    
    @staticmethod
    def get_payout_confirmation_keyboard(user_id: int) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for payout"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Process Payout",
                    callback_data=f"confirm_payout_{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_payout"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_confirm_payout_keyboard(user_id: int) -> InlineKeyboardMarkup:
        """Get final confirmation keyboard for payout"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⚠️ Confirm Payout",
                    callback_data=f"process_payout_{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_payout"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
