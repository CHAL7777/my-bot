"""
PlainTextMessageSender - Production-Safe Telegram Message Sending Utility

Plain text only - no HTML, no Markdown, no parse modes.
Maximum reliability for user-generated content.

Features:
- Automatic Markdown stripping (to prevent parse errors)
- Message splitting for long content (>4096 chars)
- Automatic truncation as fallback
- Safe character handling
"""

import asyncio
import re
import logging
from typing import Optional, Union, Any, Dict, List
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError
)
from aiogram import Bot

logger = logging.getLogger(__name__)


# ============================================================================
# Markdown Stripping Utility
# ============================================================================

def _strip_markdown(text: str) -> str:
    """
    Strip Markdown formatting from text.
    
    Converts Markdown-style formatting to plain text:
    - *bold* or **bold** -> bold
    - _italic_ or __italic__ -> italic
    - `code` -> code
    - ~strikethrough~ -> strikethrough
    
    Args:
        text: String potentially containing Markdown formatting
        
    Returns:
        Plain text with all Markdown formatting removed
    """
    if not text:
        return ""
    
    # Remove code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove inline code (`...`)
    text = re.sub(r'`[^`]*`', '', text)
    
    # Remove strikethrough (~~...~~)
    text = re.sub(r'~~[^~]*~~', '', text)
    
    # Remove bold (**...**)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    
    # Remove bold (*...*) - but be careful not to remove single asterisks
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # Remove italic (__...__)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    
    # Remove italic (_..._) - but be careful
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    # Clean up any leftover asterisks that might be single characters
    text = re.sub(r'^\*', '', text)
    text = re.sub(r'\*$', '', text)
    text = re.sub(r'\s\*\s', ' ', text)
    
    # Clean up any leftover underscores
    text = re.sub(r'^_', '', text)
    text = re.sub(r'_$', '', text)
    text = re.sub(r'\s_\s', ' ', text)
    
    # Clean up extra whitespace created by removals
    # NOTE: Use ' +' instead of '\s+' to preserve newlines!
    # This ensures message formatting (newlines) is preserved
    text = re.sub(r' +', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


# ============================================================================
# Message Splitting Utilities
# ============================================================================

def split_long_text(
    text: str,
    max_length: int = 4096,
    max_parts: int = 10,
    prefix: str = "",
    suffix: str = "",
    separator: str = "\n"
) -> List[str]:
    """
    Split long text into multiple parts that fit within Telegram's limits.
    
    This function intelligently splits text to:
    1. Respect Telegram's 4096 character limit per message
    2. Try to split at logical boundaries (newlines, sentences)
    3. Add continuation markers to show which part of the message this is
    
    Args:
        text: The text to split
        max_length: Maximum characters per message (default 4096 for Telegram)
        max_parts: Maximum number of parts to split into
        prefix: Text to add at the start of each part
        suffix: Text to add at the end of each part
        separator: String to use for splitting lines
        
    Returns:
        List of text parts, each within max_length
        
    Examples:
        >>> split_long_text("Short text")
        ['Short text']
        >>> parts = split_long_text("Very long " * 1000)
        >>> len(parts)  # Number of parts
        3
        >>> len(parts[0]) <= 4096  # Each part within limit
        True
    """
    if not text:
        return []
    
    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)
    
    # If text already fits, return as-is
    if len(text) <= max_length:
        return [text]
    
    parts = []
    remaining = text
    
    while remaining and len(parts) < max_parts:
        # Reserve space for continuation marker: "(N/M) " = up to ~12 chars max
        continuation_marker_len = 12
        available_length = max_length - len(prefix) - len(suffix) - continuation_marker_len
        
        if available_length <= 0:
            available_length = max_length - continuation_marker_len
        
        # If remaining text fits in one chunk, just add it
        if len(remaining) <= available_length:
            parts.append(prefix + remaining + suffix)
            break
        
        # Try to find a good splitting point
        chunk = remaining[:available_length]
        
        # First, try to split at the last newline
        last_newline = chunk.rfind('\n')
        if last_newline > available_length * 0.5:
            chunk = chunk[:last_newline]
            remaining = remaining[last_newline + 1:]
        else:
            # Try to split at the last sentence-ending punctuation
            last_sentence = max(
                chunk.rfind('. '),
                chunk.rfind('? '),
                chunk.rfind('! '),
                chunk.rfind(')\n'),
                chunk.rfind('.\n'),
            )
            
            if last_sentence > available_length * 0.5:
                chunk = chunk[:last_sentence + 1]
                remaining = remaining[last_sentence + 1:]
            else:
                # Last resort: split at the last space
                last_space = chunk.rfind(' ')
                
                if last_space > available_length * 0.7:
                    chunk = chunk[:last_space]
                    remaining = remaining[last_space + 1:]
                else:
                    # No good split point found, hard split
                    chunk = chunk[:available_length]
                    remaining = remaining[available_length:]
        
        # Add this part with continuation marker
        part_number = len(parts) + 1
        remaining_chars = len(remaining)
        if remaining_chars > 0:
            estimated_total = part_number + (remaining_chars // available_length) + 1
        else:
            estimated_total = part_number
        total_parts = min(estimated_total, max_parts)
        
        continuation_prefix = f"({part_number}/{total_parts}) {prefix}"
        continuation_suffix = suffix
        
        # Final safety check - truncate if needed
        final_part = continuation_prefix + chunk + continuation_suffix
        if len(final_part) > max_length:
            max_content = max_length - len(continuation_prefix) - len(continuation_suffix)
            if max_content > 0:
                final_part = continuation_prefix + chunk[:max_content] + continuation_suffix
            else:
                final_part = continuation_prefix + chunk[:max_length - len(continuation_prefix)] + continuation_suffix
        
        parts.append(final_part)
    
    # If we hit max_parts, warn about truncation
    if len(remaining) > 0 and len(parts) >= max_parts:
        logger.warning(
            f"Text truncated after {max_parts} parts. "
            f"Original length: {len(text)}, Remaining: {len(remaining)} chars"
        )
    
    return parts


class PlainTextMessageSender:
    """
    Production-safe message sender for Telegram bots using plain text only.
    
    Key Principles:
    1. NO parse modes (HTML or Markdown)
    2. NO formatting tags (<b>, <i>, <code>, etc.)
    3. Use only \n for newlines
    4. Escape problematic characters that could cause issues
    5. Build messages with lists + "\n".join()
    6. Maximum reliability over styling
    """
    
    # Characters that could cause issues even in plain text
    # We'll replace them with safer alternatives
    PROBLEMATIC_CHARS = {
        '`': "'",  # Backtick to single quote
        '~': "-",  # Tilde to hyphen
    }
    
    # Telegram message length limits
    MAX_MESSAGE_LENGTH = 4096
    MAX_CAPTION_LENGTH = 1024
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    # =========================================================================
    # Plain Text Cleaning Functions
    # =========================================================================
    
    @classmethod
    def clean_text(cls, text: Any) -> str:
        """
        Clean text for safe plain-text sending.
        
        Removes or replaces characters that could cause issues.
        Also strips Markdown formatting to prevent parse errors.
        
        Args:
            text: Any value (will be converted to string)
            
        Returns:
            Cleaned string safe for plain text
            
        Examples:
            "<script>" -> "<script>" (unchanged, but safe in plain text)
            "User's `code`" -> "User's 'code'"
            "Price < $10" -> "Price < $10" (unchanged)
            "Special ~ char" -> "Special - char"
            "*bold text*" -> "bold text" (Markdown stripped)
            "**also bold**" -> "also bold" (Markdown stripped)
        """
        if text is None:
            return ""
        
        # Convert to string if not already
        if not isinstance(text, str):
            text = str(text)
        
        if not text:
            return ""
        
        # Replace problematic characters
        result = text
        for char, replacement in cls.PROBLEMATIC_CHARS.items():
            if char in result:
                result = result.replace(char, replacement)
        
        # Strip Markdown formatting to prevent parse errors
        result = _strip_markdown(result)
        
        return result
    
    @classmethod
    def safe_format(cls, text: str, **kwargs) -> str:
        """
        Safely format a string with cleaned parameters.
        
        Args:
            text: Template string with {placeholders}
            **kwargs: Values to insert (will be cleaned)
            
        Returns:
            Formatted and cleaned string
        """
        # Clean all values
        cleaned_kwargs = {k: cls.clean_text(v) for k, v in kwargs.items()}
        
        try:
            return text.format(**cleaned_kwargs)
        except KeyError as e:
            logger.error(f"Missing key in safe_format: {e}")
            # Fallback: replace only available keys
            for key, value in cleaned_kwargs.items():
                placeholder = f'{{{key}}}'
                if placeholder in text:
                    text = text.replace(placeholder, value)
            return text
    
    @classmethod
    def clean_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively clean all string values in a dictionary.
        
        Args:
            data: Dictionary potentially containing user-generated strings
            
        Returns:
            Dictionary with all string values cleaned
        """
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.clean_text(value)
            elif isinstance(value, dict):
                result[key] = cls.clean_dict(value)
            elif isinstance(value, list):
                result[key] = [cls.clean_text(item) if isinstance(item, str) else item for item in value]
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def safe_truncate(cls, text: str, max_length: int, ellipsis: str = "...") -> str:
        """
        Safely truncate text to maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            ellipsis: String to append when truncated
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        # Calculate available space
        available = max_length - len(ellipsis)
        
        if available <= 0:
            return ellipsis[:max_length]
        
        # Truncate to last space before the limit
        truncated = text[:available]
        last_space = truncated.rfind(' ')
        
        # Only break at space if it's reasonably close to the end
        if last_space > available * 0.7:
            truncated = truncated[:last_space]
        
        return truncated + ellipsis
    
    # =========================================================================
    # Message Formatting Helpers - Plain text only
    # =========================================================================
    
    @classmethod
    def format_quiz_question(
        cls,
        question_text: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        question_number: int = 1,
        total_questions: int = 1,
        score: int = 0
    ) -> str:
        """
        Format a quiz question in plain text.
        
        Uses list building for clarity and safety.
        """
        # Clean all user-generated content
        safe_question = cls.clean_text(question_text)
        safe_a = cls.clean_text(option_a)
        safe_b = cls.clean_text(option_b)
        safe_c = cls.clean_text(option_c)
        safe_d = cls.clean_text(option_d)
        
        lines = [
            f"Question {question_number}/{total_questions} | Score: {score}",
            "",  # Empty line for spacing
            safe_question,
            "",  # Empty line for spacing
            f"A. {safe_a}",
            f"B. {safe_b}",
            f"C. {safe_c}",
            f"D. {safe_d}"
        ]
        
        return "\n".join(lines)
    
    @classmethod
    def format_quiz_result(
        cls,
        is_correct: bool,
        selected_option: str,
        correct_option: str,
        explanation: str,
        points_earned: int,
        time_taken: float,
        current_score: int,
        question_number: int,
        total_questions: int
    ) -> str:
        """
        Format a quiz result message in plain text.
        """
        # Build message using list for clarity
        lines = []
        
        # Status section
        if is_correct:
            lines.append("✅ Correct!")
            if points_earned > 0:
                plural = "s" if points_earned > 1 else ""
                lines.append(f"+{points_earned} point{plural}")
        else:
            lines.append("❌ Incorrect")
        
        lines.append(f"⏱️ {time_taken:.1f}s")
        lines.append("")  # Empty line
        
        # Divider
        lines.append("-" * 20)
        lines.append("")  # Empty line
        
        # Answer section
        lines.append(f"You selected: {selected_option}")
        lines.append(f"Correct answer: {correct_option}")
        lines.append("")  # Empty line
        
        # Divider
        lines.append("-" * 20)
        lines.append("")  # Empty line
        
        # Explanation section
        if explanation:
            lines.append("💡 Explanation:")
            lines.append(cls.clean_text(explanation))
            lines.append("")  # Empty line
        else:
            lines.append("ℹ️ No explanation available for this question.")
            lines.append("")  # Empty line
        
        # Divider
        lines.append("-" * 20)
        lines.append("")  # Empty line
        
        # Score section
        lines.append(f"🏆 Score: {current_score}")
        
        # Progress indicator
        if question_number < total_questions:
            lines.append("")  # Empty line
            lines.append("⏳ Loading next question...")
        else:
            lines.append("")  # Empty line
            lines.append("🎉 Quiz Complete!")
        
        return "\n".join(lines)
    
    @classmethod
    def format_chapter_selection(
        cls,
        subject_name: str,
        chapters: List[Dict[str, Any]]
    ) -> str:
        """
        Format chapter selection message in plain text.
        """
        # Clean subject name
        safe_subject = cls.clean_text(subject_name)
        
        lines = [
            f"📚 {safe_subject} - Chapter Selection",
            "",  # Empty line
            "✨ Choose a chapter to start your quiz journey!",
            "",  # Empty line
        ]
        
        # Add each chapter
        for idx, chapter in enumerate(chapters, 1):
            # Clean chapter data
            safe_chapter = cls.clean_dict(chapter)
            chapter_name = safe_chapter.get('chapter_name', f'Chapter {idx}')
            total = chapter.get('total_count', 0)
            
            lines.extend([
                f"📖 {chapter_name}",
                f"   📊 {total} questions available",
                f"   🟢 Simple • 🟡 Medium • 🔴 Hard",
                "",  # Empty line between chapters
            ])
        
        # Add footer
        lines.extend([
            "💡 Tip: Start with chapters you want to improve in!",
            "",  # Empty line
            "-" * 20,
            "◀️ Back to Subjects"
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def format_leaderboard(
        cls,
        title: str,
        entries: List[Dict[str, Any]],
        user_position: Optional[int] = None,
        user_score: Optional[int] = None
    ) -> str:
        """
        Format a leaderboard in plain text.
        """
        lines = [
            "🏆 " + cls.clean_text(title),
            "",  # Empty line
        ]
        
        # Add entries
        for i, entry in enumerate(entries, 1):
            username = cls.clean_text(entry.get('username', 'Unknown'))
            score = entry.get('score', 0)
            lines.append(f"{i}. {username} - {score} pts")
        
        # Add user position if provided
        if user_position is not None and user_score is not None:
            lines.append("")  # Empty line
            lines.append("-" * 20)
            lines.append(f"Your position: #{user_position}")
            lines.append(f"Your score: {user_score} pts")
        
        return "\n".join(lines)
    
    @classmethod
    def format_admin_panel(
        cls,
        stats: Dict[str, Any]
    ) -> str:
        """
        Format admin panel information in plain text.
        """
        lines = [
            "🔧 Admin Panel",
            "",  # Empty line
        ]
        
        # Add statistics
        lines.append(f"Total Users: {stats.get('total_users', 0)}")
        lines.append(f"Active Today: {stats.get('active_today', 0)}")
        lines.append(f"Quizzes Completed: {stats.get('quizzes_completed', 0)}")
        lines.append(f"Questions Answered: {stats.get('questions_answered', 0)}")
        
        # Add commands section
        lines.append("")  # Empty line
        lines.append("-" * 20)
        lines.append("Commands:")
        lines.append("/broadcast - Send message to all users")
        lines.append("/stats - View detailed statistics")
        lines.append("/export - Export user data")
        
        return "\n".join(lines)
    
    # =========================================================================
    # Main Message Sending Methods - Plain text only
    # =========================================================================
    
    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        **kwargs
    ) -> Optional[Message]:
        """
        Safely send a message with NO parse mode (plain text only).
        
        Args:
            chat_id: Target chat ID
            text: Message text
            reply_markup: Optional inline keyboard
            disable_notification: Send silently
            protect_content: Protect from forwarding
            **kwargs: Additional arguments for send_message
            
        Returns:
            Sent Message object or None if failed
        """
        # Validate inputs
        if not text:
            logger.warning(f"Empty text for chat {chat_id}")
            return None
        
        try:
            chat_id = int(chat_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid chat ID: {chat_id}")
            return None
        
        # Clean text (NO HTML escaping, just safe plain text)
        safe_text = self.clean_text(text)
        
        # Truncate if too long
        if len(safe_text) > self.MAX_MESSAGE_LENGTH:
            logger.warning(f"Message too long ({len(safe_text)} chars) for chat {chat_id}, truncating")
            safe_text = self.safe_truncate(safe_text, self.MAX_MESSAGE_LENGTH)
        
        # Attempt to send with NO parse mode (plain text)
        try:
            return await self.bot.send_message(
                chat_id=chat_id,
                text=safe_text,
                parse_mode=None,  # NO parse mode - plain text only
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                protect_content=protect_content,
                **kwargs
            )
            
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            
            # With plain text, we shouldn't get parse errors, but handle other errors
            if "message is too long" in error_msg:
                logger.error(f"Message still too long after truncation for chat {chat_id}")
                return None
            elif "chat not found" in error_msg:
                logger.warning(f"Chat {chat_id} not found")
                return None
            elif "bot was blocked" in error_msg:
                logger.warning(f"Bot blocked by user {chat_id}")
                return None
            else:
                logger.error(f"TelegramBadRequest for chat {chat_id}: {e}")
                return None
                
        except TelegramForbiddenError as e:
            logger.warning(f"Bot blocked by user {chat_id}: {e}")
            return None
            
        except TelegramNetworkError as e:
            logger.error(f"Network error sending to chat {chat_id}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error sending to chat {chat_id}: {e}", exc_info=True)
            return None
    
    async def send_long_message(
        self,
        chat_id: Union[int, str],
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        split_on_newlines: bool = True,
        **kwargs
    ) -> Optional[List[Message]]:
        """
        Safely send a long message by splitting it into multiple parts if needed.
        
        This method is ideal for sending quiz results, leaderboards, or any content
        that might exceed Telegram's 4096 character limit.
        
        Args:
            chat_id: Target chat ID
            text: Message text (may be long)
            reply_markup: Optional inline keyboard (only applied to last message)
            disable_notification: Send silently
            protect_content: Protect from forwarding
            split_on_newlines: If True, prefer splitting at newlines
            **kwargs: Additional arguments for send_message
            
        Returns:
            List of sent Message objects (one per part), or None if all failed
        """
        # Validate inputs
        if not text:
            logger.warning(f"Empty text for chat {chat_id}")
            return None
        
        try:
            chat_id = int(chat_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid chat ID: {chat_id}")
            return None
        
        # Clean text
        safe_text = self.clean_text(text)
        
        # Split the text into parts
        parts = split_long_text(
            safe_text,
            max_length=self.MAX_MESSAGE_LENGTH,
            max_parts=10,
            prefix="",
            suffix=""
        )
        
        if not parts:
            return None
        
        # If only one part, use regular send_message for simplicity
        if len(parts) == 1:
            result = await self.send_message(
                chat_id=chat_id,
                text=parts[0],
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                protect_content=protect_content,
                **kwargs
            )
            return [result] if result else None
        
        # Send multiple parts
        sent_messages = []
        
        for i, part in enumerate(parts):
            # Apply reply_markup only to the last message
            part_reply_markup = reply_markup if i == len(parts) - 1 else None
            
            # Add part indicator if multiple parts
            part_text = part
            if len(parts) > 1:
                part_text = f"[{i+1}/{len(parts)}]\n{part}"
            
            try:
                msg = await self.bot.send_message(
                    chat_id=chat_id,
                    text=part_text,
                    parse_mode=None,  # NO parse mode - plain text only
                    reply_markup=part_reply_markup,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                    **kwargs
                )
                sent_messages.append(msg)
                
                # Small delay between messages to avoid rate limiting
                if i < len(parts) - 1:
                    await asyncio.sleep(0.1)
                    
            except TelegramBadRequest as e:
                error_msg = str(e).lower()
                
                if "message is too long" in error_msg:
                    logger.error(f"Part {i+1} still too long for chat {chat_id}, skipping")
                    # Try to send a truncated version
                    try:
                        truncated = self.safe_truncate(part_text, self.MAX_MESSAGE_LENGTH)
                        msg = await self.bot.send_message(
                            chat_id=chat_id,
                            text=truncated,
                            parse_mode=None,
                            reply_markup=part_reply_markup,
                            disable_notification=disable_notification,
                            **kwargs
                        )
                        sent_messages.append(msg)
                    except Exception:
                        logger.error(f"Failed to send truncated part {i+1}")
                elif "chat not found" in error_msg:
                    logger.warning(f"Chat {chat_id} not found")
                    break
                elif "bot was blocked" in error_msg:
                    logger.warning(f"Bot blocked by user {chat_id}")
                    break
                else:
                    logger.error(f"TelegramBadRequest for chat {chat_id}, part {i+1}: {e}")
                    
            except TelegramForbiddenError as e:
                logger.warning(f"Bot blocked by user {chat_id}: {e}")
                break
                
            except TelegramNetworkError as e:
                logger.error(f"Network error sending part {i+1} to chat {chat_id}: {e}")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error sending part {i+1} to chat {chat_id}: {e}", exc_info=True)
                break
        
        return sent_messages if sent_messages else None
    
    async def edit_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        **kwargs
    ) -> Optional[Message]:
        """
        Safely edit an existing message with NO parse mode.
        """
        if not text:
            logger.warning(f"Empty text for editing message {message_id} in chat {chat_id}")
            return None
        
        # Clean text
        safe_text = self.clean_text(text)
        
        # Truncate if too long
        if len(safe_text) > self.MAX_MESSAGE_LENGTH:
            safe_text = self.safe_truncate(safe_text, self.MAX_MESSAGE_LENGTH)
        
        try:
            return await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=safe_text,
                parse_mode=None,  # NO parse mode - plain text only
                reply_markup=reply_markup,
                **kwargs
            )
            
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            
            # Message not modified is not an error
            if "message is not modified" in error_msg:
                logger.debug(f"Message {message_id} in chat {chat_id} not modified")
                return None
                
            # Message may have been deleted
            elif "message to edit not found" in error_msg:
                logger.warning(f"Message {message_id} not found in chat {chat_id}")
                return None
                
            else:
                logger.error(f"TelegramBadRequest editing message {message_id} in chat {chat_id}: {e}")
                return None
                
        except Exception as e:
            logger.error(
                f"Unexpected error editing message {message_id} in chat {chat_id}: {e}",
                exc_info=True
            )
            return None
    
    async def edit_message_object(
        self,
        message: Message,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        **kwargs
    ) -> Optional[Message]:
        """
        Safely edit a Message object with NO parse mode.
        """
        if not message:
            logger.warning("No message object provided for editing")
            return None
        
        return await self.edit_message(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=text,
            reply_markup=reply_markup,
            **kwargs
        )
    
    async def answer_callback(
        self,
        callback: CallbackQuery,
        text: Optional[str] = None,
        show_alert: bool = False,
        **kwargs
    ) -> bool:
        """
        Safely answer a callback query with plain text.
        """
        if not callback:
            logger.warning("No callback query provided")
            return False
        
        # Clean text if provided
        safe_text = self.clean_text(text) if text else None
        
        try:
            await callback.answer(
                text=safe_text,
                show_alert=show_alert,
                **kwargs
            )
            return True
            
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            if "query is too old" in error_msg or "invalid query id" in error_msg:
                logger.debug(f"Callback query expired or invalid: {e}")
            else:
                logger.error(f"Error answering callback: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error answering callback: {e}")
            return False
    
    # =========================================================================
    # Specialized Sending Methods
    # =========================================================================
    
    async def send_quiz_question(
        self,
        chat_id: Union[int, str],
        question_data: Dict[str, Any],
        question_number: int = 1,
        total_questions: int = 1,
        score: int = 0,
        keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> Optional[Message]:
        """
        Send a quiz question in plain text.
        """
        text = self.format_quiz_question(
            question_text=question_data.get('question_text', ''),
            option_a=question_data.get('option_a', ''),
            option_b=question_data.get('option_b', ''),
            option_c=question_data.get('option_c', ''),
            option_d=question_data.get('option_d', ''),
            question_number=question_number,
            total_questions=total_questions,
            score=score
        )
        
        return await self.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard
        )
    
    async def send_quiz_result(
        self,
        chat_id: Union[int, str],
        result_data: Dict[str, Any],
        keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> Optional[Message]:
        """
        Send a quiz result in plain text.
        """
        text = self.format_quiz_result(
            is_correct=result_data.get('is_correct', False),
            selected_option=result_data.get('selected_option', ''),
            correct_option=result_data.get('correct_option', ''),
            explanation=result_data.get('explanation', ''),
            points_earned=result_data.get('points_earned', 0),
            time_taken=result_data.get('time_taken', 0.0),
            current_score=result_data.get('current_score', 0),
            question_number=result_data.get('question_number', 1),
            total_questions=result_data.get('total_questions', 1)
        )
        
        return await self.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard
        )
    
    async def send_leaderboard(
        self,
        chat_id: Union[int, str],
        title: str,
        entries: List[Dict[str, Any]],
        user_position: Optional[int] = None,
        user_score: Optional[int] = None,
        keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> Optional[Message]:
        """
        Send a leaderboard in plain text.
        """
        text = self.format_leaderboard(
            title=title,
            entries=entries,
            user_position=user_position,
            user_score=user_score
        )
        
        return await self.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard
        )
    
    async def send_admin_panel(
        self,
        chat_id: Union[int, str],
        stats: Dict[str, Any],
        keyboard: Optional[InlineKeyboardMarkup] = None
    ) -> Optional[Message]:
        """
        Send admin panel information in plain text.
        """
        text = self.format_admin_panel(stats)
        
        return await self.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard
        )


# ============================================================================
# Utility functions for direct use
# ============================================================================

def clean_text(text: Any) -> str:
    """
    Utility function to clean text for plain text sending.
    
    Args:
        text: Any value to clean
        
    Returns:
        Cleaned string safe for plain text
    """
    return PlainTextMessageSender.clean_text(text)


def build_message(*lines: str) -> str:
    """
    Helper function to build messages safely.
    
    Args:
        *lines: Lines to join with newlines
        
    Returns:
        Joined message string
    """
    return "\n".join(lines)


async def send_plain_message(
    bot: Bot,
    chat_id: Union[int, str],
    text: str,
    **kwargs
) -> Optional[Message]:
    """
    Convenience function for safe plain text message sending.
    """
    sender = PlainTextMessageSender(bot)
    return await sender.send_message(
        chat_id=chat_id,
        text=text,
        **kwargs
    )

