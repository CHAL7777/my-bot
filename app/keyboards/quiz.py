"""
Quiz Keyboard Utilities - Enhanced for Learning-First Experience

This module provides keyboards for the quiz flow with three phases:
1. QUESTION PHASE: 4 option buttons (A, B, C, D)
2. LOCK PHASE: Single "Check Answer → Learn Why" button after selection
3. REVEAL PHASE: Result display with explanation (auto-progresses)
"""

from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.constants import EMOJIS


class QuizKeyboard:
    """Quiz keyboard utilities with learning-first design."""
    
    # =========================================================================
    # KEYBOARD FACTORIES FOR LEARNING FLOW
    # =========================================================================
    
    @staticmethod
    def get_question_keyboard(question_number: int, total_questions: int, 
                            question_id: int) -> InlineKeyboardMarkup:
        """
        QUESTION PHASE: Get keyboard for answering a question.
        
        Shows 4 option buttons (A, B, C, D) for selection.
        User must select one option to proceed.
        
        Args:
            question_number: Current question number (1-based)
            total_questions: Total questions in quiz
            question_id: Unique question identifier
            
        Returns:
            InlineKeyboardMarkup with A, B, C, D options
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔵 A",
                    callback_data=f"answer_{question_id}_A"
                ),
                InlineKeyboardButton(
                    text="🟢 B",
                    callback_data=f"answer_{question_id}_B"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🟡 C",
                    callback_data=f"answer_{question_id}_C"
                ),
                InlineKeyboardButton(
                    text="🔴 D",
                    callback_data=f"answer_{question_id}_D"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"❌ Cancel Quiz ({question_number}/{total_questions})",
                    callback_data="cancel_quiz"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_locked_keyboard(question_number: int, total_questions: int,
                           question_id: int, selected_option: str) -> InlineKeyboardMarkup:
        """
        LOCK PHASE: Get keyboard after user selects an option.
        
        Prevents changing answer by disabling other options.
        Shows selected option with ✓ marker and other options dimmed.
        Shows beautiful "✅ Check Answer → Learn Why" button.
        
        Args:
            question_number: Current question number
            total_questions: Total questions in quiz
            question_id: Unique question identifier
            selected_option: The option user selected (A, B, C, or D)
            
        Returns:
            InlineKeyboardMarkup with locked options + check button
        """
        # Option colors - green for selected, gray for others
        option_colors = {
            'A': ('🔵', '⚪'),  # Blue
            'B': ('🟢', '⚪'),  # Green
            'C': ('🟡', '⚪'),  # Yellow
            'D': ('🔴', '⚪'),  # Red
        }
        
        option_labels = ['A', 'B', 'C', 'D']
        keyboard = []
        
        # Show options with selection marker on selected, disabled others
        for i in range(0, 4, 2):
            row = []
            for j in range(2):
                opt = option_labels[i + j]
                color, dim = option_colors.get(opt, ('⚪', '⚪'))
                
                if opt == selected_option:
                    # Selected option - show with checkmark
                    row.append(InlineKeyboardButton(
                        text=f"✓ {color} {opt}",
                        callback_data=f"locked_{question_id}_{opt}"
                    ))
                else:
                    # Unselected options - dimmed
                    row.append(InlineKeyboardButton(
                        text=f"{dim} {opt}",
                        callback_data=f"disabled_{question_id}_{opt}"
                    ))
            keyboard.append(row)
        
        # Single check button with arrow - forces user to learn
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Check Answer → Learn Why",
                callback_data=f"check_{question_id}_{selected_option}"
            )
        ])
        
        # Cancel option (still available)
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ Cancel Quiz",
                callback_data="cancel_quiz"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_result_keyboard(question_number: int, total_questions: int,
                           question_id: int, is_last: bool = False,
                           quiz_session_id: str = None) -> InlineKeyboardMarkup:
        """
        REVEAL PHASE: Get keyboard after answer is checked.
        
        Shows result status. For last question: "View Results".
        For others: Empty (auto-progresses after delay).
        
        Args:
            question_number: Current question number
            total_questions: Total questions in quiz
            question_id: Unique question identifier
            is_last: Whether this is the last question
            quiz_session_id: The quiz session ID (REQUIRED for is_last=True)
            
        Returns:
            InlineKeyboardMarkup with appropriate action button
        """
        if is_last:
            # Use quiz_session_id in callback to retrieve results even after state cleared
            callback_data = f"view_results_{quiz_session_id}" if quiz_session_id else "view_results"
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="📊 View Results",
                        callback_data=callback_data
                    )
                ]
            ]
        else:
            # No button - auto-progresses after delay
            # This forces user to read explanation
            keyboard = []
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # =========================================================================
    # RESULT & NAVIGATION KEYBOARDS (UNCHANGED)
    # =========================================================================
    
    @staticmethod
    def get_quiz_results_keyboard(quiz_session_id: str) -> InlineKeyboardMarkup:
        """Get keyboard after finishing a quiz"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📋 View Details",
                    callback_data=f"quiz_details_{quiz_session_id}"
                ),
                InlineKeyboardButton(
                    text="📊 Weak Areas",
                    callback_data="weak_areas"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Try Again",
                    callback_data="try_again"
                ),
                InlineKeyboardButton(
                    text="🎯 Recommendations",
                    callback_data="get_recommendations"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_quiz_cancel_confirmation() -> InlineKeyboardMarkup:
        """Get confirmation for quiz cancellation"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="❌ Yes, Cancel",
                    callback_data="confirm_cancel_quiz"
                ),
                InlineKeyboardButton(
                    text="◀️ Continue Quiz",
                    callback_data="continue_quiz"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_quiz_retry_keyboard(subject_id: int, chapter_id: int, 
                              difficulty: str) -> InlineKeyboardMarkup:
        """Get keyboard for retrying a quiz"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔄 Same Difficulty",
                    callback_data=f"retry_{subject_id}_{chapter_id}_{difficulty}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Higher Difficulty",
                    callback_data=f"higher_difficulty_{subject_id}_{chapter_id}_{difficulty}"
                ),
                InlineKeyboardButton(
                    text="📚 Different Chapter",
                    callback_data="different_chapter"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_quiz_pagination_keyboard(current_index: int, total: int, 
                                   quiz_session_id: str) -> InlineKeyboardMarkup:
        """Get pagination keyboard for quiz review"""
        builder = InlineKeyboardBuilder()
        
        # Previous button
        if current_index > 0:
            builder.button(
                text="◀️ Previous",
                callback_data=f"review_{quiz_session_id}_{current_index - 1}"
            )
        
        # Current position
        builder.button(
            text=f"{current_index + 1}/{total}",
            callback_data="no_action"
        )
        
        # Next button
        if current_index < total - 1:
            builder.button(
                text="Next ▶️",
                callback_data=f"review_{quiz_session_id}_{current_index + 1}"
            )
        
        # Back to results
        builder.row(
            InlineKeyboardButton(
                text="📊 Back to Results",
                callback_data=f"quiz_results_{quiz_session_id}"
            )
        )
        
        builder.adjust(3)
        return builder.as_markup()
    
    @staticmethod
    def get_question_review_keyboard(quiz_session_id: str, current_index: int, 
                                    total: int) -> InlineKeyboardMarkup:
        """
        Get keyboard for question review during quiz details view.
        
        Args:
            quiz_session_id: The unique session ID for the quiz
            current_index: Current question index (0-based)
            total: Total number of questions
        
        Returns:
            InlineKeyboardMarkup with navigation buttons
        """
        keyboard = []
        
        # Navigation row
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Prev",
                    callback_data=f"review_{quiz_session_id}_{current_index - 1}"
                )
            )
        
        # Position indicator (non-clickable, shows current position)
        nav_buttons.append(
            InlineKeyboardButton(
                text=f"{current_index + 1}/{total}",
                callback_data="no_op"
            )
        )
        
        if current_index < total - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Next ▶️",
                    callback_data=f"review_{quiz_session_id}_{current_index + 1}"
                )
            )
        
        keyboard.append(nav_buttons)
        
        # Bottom action buttons
        keyboard.append([
            InlineKeyboardButton(
                text="📋 Full Summary",
                callback_data=f"quiz_summary_{quiz_session_id}"
            ),
            InlineKeyboardButton(
                text="📊 Back to Results",
                callback_data=f"quiz_results_{quiz_session_id}"
            )
        ])
        
        # Home button
        keyboard.append([
            InlineKeyboardButton(
                text="🏠 Back to Menu",
                callback_data="back_to_menu"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_start_recommended_keyboard(subject_id: int, chapter_id: int, 
                                      difficulty: str) -> InlineKeyboardMarkup:
        """Get keyboard to start recommended quiz"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🎯 Start This Quiz",
                    callback_data=f"start_recommended_{subject_id}_{chapter_id}_{difficulty}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Get Another Recommendation",
                    callback_data="get_recommendations"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_weak_areas_keyboard(weak_chapters: List[dict]) -> InlineKeyboardMarkup:
        """
        Get keyboard with options to practice weak areas.
        
        Args:
            weak_chapters: List of dicts with subject_id, chapter_id, difficulty
            
        Returns:
            InlineKeyboardMarkup with practice buttons
        """
        keyboard = []
        
        # Add practice button for each weak area (max 3 to avoid too many buttons)
        for chapter in weak_chapters[:3]:
            subject_id = chapter.get('subject_id')
            chapter_id = chapter.get('chapter_id')
            difficulty = chapter.get('difficulty', 'simple')
            subject_name = chapter.get('subject_name', 'Unknown')
            chapter_name = chapter.get('chapter_name', 'Unknown')
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"💪 Practice: {subject_name} - {chapter_name} ({difficulty})",
                    callback_data=f"practice_weak_{subject_id}_{chapter_id}_{difficulty}"
                )
            ])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton(
                text="🔄 Get Recommendations",
                callback_data="get_recommendations"
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🏠 Back to Menu",
                callback_data="back_to_menu"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_disabled_keyboard(question_number: int, total_questions: int,
                             question_id: int) -> InlineKeyboardMarkup:
        """
        Get keyboard with all buttons disabled (fallback).
        
        Args:
            question_number: Current question number
            total_questions: Total questions in quiz
            question_id: Unique question identifier
            
        Returns:
            InlineKeyboardMarkup with disabled buttons
        """
        keyboard = [
            [
                InlineKeyboardButton(text="A", callback_data="noop"),
                InlineKeyboardButton(text="B", callback_data="noop")
            ],
            [
                InlineKeyboardButton(text="C", callback_data="noop"),
                InlineKeyboardButton(text="D", callback_data="noop")
            ],
            [
                InlineKeyboardButton(
                    text=f"⏳ Answered ({question_number}/{total_questions})",
                    callback_data="noop"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def get_quiz_summary_keyboard(quiz_session_id: str) -> InlineKeyboardMarkup:
        """
        Get keyboard for full quiz summary view.
        
        Args:
            quiz_session_id: The unique session ID for the quiz
            
        Returns:
            InlineKeyboardMarkup with navigation options
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📊 Quiz Results",
                    callback_data=f"quiz_results_{quiz_session_id}"
                ),
                InlineKeyboardButton(
                    text="📋 Question Details",
                    callback_data=f"quiz_details_{quiz_session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Try Again",
                    callback_data="try_again"
                ),
                InlineKeyboardButton(
                    text="🏠 Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
