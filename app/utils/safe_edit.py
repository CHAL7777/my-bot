"""
Safe message editing utilities for aiogram v3.

This module provides robust utilities for editing Telegram messages
without causing 'message is not modified' errors.

Usage:
    from app.utils.safe_edit import safe_edit_message, edit_guard
    
    # Simple usage
    await safe_edit_message(
        callback.message,
        "New text content",
        reply_markup=new_keyboard
    )
    
    # With duplicate protection
    async with edit_guard(state, "processing_key"):
        await callback.message.edit_text("Processing...")
"""

from typing import Optional, Any
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram import types
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


def normalize_text_for_comparison(text: str) -> str:
    """
    Normalize text for comparison by removing extra whitespace.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text suitable for comparison
    """
    if not text:
        return ""
    # Remove extra whitespace, leading/trailing newlines
    return ' '.join(text.split())


def normalize_markup_for_comparison(
    markup: Optional[InlineKeyboardMarkup]
) -> Optional[str]:
    """
    Normalize inline keyboard markup to a comparable string.
    
    Args:
        markup: Inline keyboard markup or None
        
    Returns:
        JSON string representation or None
    """
    if markup is None:
        return None
    
    if not hasattr(markup, 'inline_keyboard'):
        return None
    
    # Convert to serializable format
    keyboard_data = []
    for row in markup.inline_keyboard:
        row_data = []
        for button in row:
            row_data.append({
                'text': button.text,
                'callback_data': button.callback_data if hasattr(button, 'callback_data') else ''
            })
        keyboard_data.append(row_data)
    
    return json.dumps(keyboard_data, sort_keys=True)


async def safe_edit_message(
    message: Message,
    new_text: str,
    new_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown",
    allow_empty: bool = False
) -> bool:
    """
    Safely edit a message, only if content actually changed.
    
    This function prevents 'message is not modified' errors by:
    1. Comparing current text with new text
    2. Comparing current markup with new markup
    3. Only calling edit_text if something actually changed
    
    Args:
        message: The message to edit
        new_text: New text content
        new_markup: New inline keyboard (optional)
        parse_mode: Parse mode for the text
        allow_empty: If True, allow editing even if text is empty
        
    Returns:
        True if message was edited, False if no changes needed
        
    Raises:
        TelegramBadRequest: If the edit fails for other reasons
    """
    if not allow_empty and not new_text:
        logger.warning("Attempted to edit message with empty text, skipping")
        return False
    
    # Get current content
    current_text = message.text or message.caption or ""
    current_markup = message.reply_markup
    
    # Normalize for comparison
    normalized_current = normalize_text_for_comparison(current_text)
    normalized_new = normalize_text_for_comparison(new_text)
    
    new_markup_str = normalize_markup_for_comparison(new_markup)
    current_markup_str = normalize_markup_for_comparison(current_markup)
    
    # Check if anything actually changed
    text_changed = normalized_current != normalized_new
    markup_changed = current_markup_str != new_markup_str
    
    if not text_changed and not markup_changed:
        logger.debug(
            f"No changes detected for message {message.message_id}, "
            f"skipping edit (text={text_changed}, markup={markup_changed})"
        )
        return False
    
    logger.debug(
        f"Message {message.message_id} has changes: "
        f"text={text_changed}, markup={markup_changed}"
    )
    
    try:
        # If only markup changed, edit just the markup
        if not text_changed and markup_changed:
            try:
                await message.edit_reply_markup(reply_markup=new_markup)
                logger.debug(f"Updated markup for message {message.message_id}")
                return True
            except TelegramBadRequest as e:
                # Handle edge case where markup is actually the same
                if "message is not modified" in str(e):
                    logger.debug(f"Markup actually same for message {message.message_id}")
                    return False
                raise
        
        # Full edit needed
        await message.edit_text(
            text=new_text,
            reply_markup=new_markup,
            parse_mode=parse_mode
        )
        logger.debug(f"Edited message {message.message_id}")
        return True
        
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        
        if "message is not modified" in error_msg:
            logger.debug(f"Message {message.message_id} already has same content")
            return False
        
        if "message to edit not found" in error_msg:
            logger.warning(f"Message {message.message_id} not found for editing")
            return False
        
        if "chat not found" in error_msg:
            logger.warning(f"Chat not found for message {message.message_id}")
            return False
        
        # Re-raise other errors
        logger.error(f"Failed to edit message {message.message_id}: {e}")
        raise


async def safe_edit_callback(
    callback: CallbackQuery,
    new_text: str,
    new_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown",
    answer_callback: bool = True
) -> bool:
    """
    Safely edit a callback query's message.
    
    This is a convenience function that:
    1. Calls safe_edit_message on callback.message
    2. Optionally answers the callback
    
    Args:
        callback: The callback query
        new_text: New text content
        new_markup: New inline keyboard (optional)
        parse_mode: Parse mode for the text
        answer_callback: Whether to answer the callback
        
    Returns:
        True if message was edited, False if no changes needed
    """
    result = await safe_edit_message(
        message=callback.message,
        new_text=new_text,
        new_markup=new_markup,
        parse_mode=parse_mode
    )
    
    if answer_callback:
        try:
            await callback.answer()
        except Exception as e:
            # Ignore errors from answering callback
            logger.debug(f"Could not answer callback: {e}")
    
    return result


class EditGuard:
    """
    Context manager to prevent duplicate edit attempts for the same action.
    
    This prevents issues when users double-click buttons or when
    the same callback is processed multiple times.
    
    Usage:
        async with EditGuard(state, "updating_profile"):
            await callback.message.edit_text("Updating...")
            # Perform update
            await callback.message.edit_text("Done!")
    
    Attributes:
        state: FSMContext for storing guard state
        guard_key: Unique key for this guard (will be prefixed with 'guard_')
        ttl_seconds: Time-to-live for the guard (default: 30 seconds)
    """
    
    def __init__(
        self,
        state: FSMContext,
        guard_key: str,
        ttl_seconds: int = 30
    ):
        """
        Initialize the edit guard.
        
        Args:
            state: FSMContext to store guard state
            guard_key: Unique identifier for this guard
            ttl_seconds: How long the guard lasts before timing out
        """
        self.state = state
        self.guard_key = f"guard_{guard_key}"
        self.ttl_seconds = ttl_seconds
    
    async def __aenter__(self) -> 'EditGuard':
        """Check if guard is active and activate it."""
        data = await self.state.get_data()
        
        # Check if guard is already active
        guard_info = data.get(self.guard_key)
        if guard_info:
            # Check if guard has expired
            import time
            if isinstance(guard_info, dict):
                guard_time = guard_info.get('time', 0)
                if time.time() - guard_time < self.ttl_seconds:
                    logger.debug(f"Guard '{self.guard_key}' is active, skipping")
                    raise EditInProgressError(
                        f"Edit operation '{self.guard_key}' is already in progress"
                    )
            # Guard expired, allow new edit
        
        # Activate guard
        import time
        await self.state.update_data({
            self.guard_key: {
                'time': time.time(),
                'active': True
            }
        })
        
        logger.debug(f"Activated guard '{self.guard_key}'")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Deactivate the guard."""
        data = await self.state.get_data()
        
        # Clear the guard
        current = data.get(self.guard_key, {})
        if isinstance(current, dict):
            current['active'] = False
        
        await self.state.update_data({self.guard_key: current})
        logger.debug(f"Deactivated guard '{self.guard_key}'")
        
        # Re-raise any exception
        if exc_type:
            raise exc_val


class EditInProgressError(Exception):
    """
    Raised when an edit operation is already in progress.
    
    This prevents duplicate edits when users double-click buttons
    or when the same callback is processed multiple times.
    """
    pass


def create_hash_key(*args) -> str:
    """
    Create a unique hash key from arguments for state storage.
    
    Args:
        *args: Arguments to hash
        
    Returns:
        MD5 hash string
    """
    key_string = ':'.join(str(arg) for arg in args)
    return hashlib.md5(key_string.encode()).hexdigest()[:16]


async def compare_and_edit(
    message: Message,
    state: FSMContext,
    state_key: str,
    new_text: str,
    new_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown"
) -> bool:
    """
    Compare message content with state and edit only if different.
    
    This is useful when you want to ensure the message content
    matches what's in state before attempting an edit.
    
    Args:
        message: The message to potentially edit
        state: FSMContext with stored message content
        state_key: Key for the stored content in state
        new_text: New text content
        new_markup: New inline keyboard
        parse_mode: Parse mode for text
        
    Returns:
        True if message was edited, False if already matches
    """
    data = await state.get_data()
    stored_content = data.get(state_key, {})
    
    # Get stored values or defaults
    stored_text = stored_content.get('text', '')
    stored_markup = stored_content.get('markup')
    
    # Check if we need to edit
    needs_edit = False
    
    # Compare text (normalized)
    if normalize_text_for_comparison(stored_text) != normalize_text_for_comparison(new_text):
        needs_edit = True
    
    # Compare markup
    stored_markup_str = normalize_markup_for_comparison(stored_markup)
    new_markup_str = normalize_markup_for_comparison(new_markup)
    if stored_markup_str != new_markup_str:
        needs_edit = True
    
    if not needs_edit:
        logger.debug(f"No edit needed for state key '{state_key}'")
        return False
    
    # Perform the edit
    result = await safe_edit_message(
        message=message,
        new_text=new_text,
        new_markup=new_markup,
        parse_mode=parse_mode
    )
    
    # Update state with new content
    if result:
        await state.update_data({
            state_key: {
                'text': new_text,
                'markup': new_markup
            }
        })
    
    return result


# Convenience function for common use case
async def edit_text_safe(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown"
) -> bool:
    """
    Convenience wrapper for safe editing in callback handlers.
    
    This is the most common use case - safely editing a message
    from within a callback query handler.
    
    Args:
        callback: The callback query
        text: New text content
        reply_markup: New inline keyboard
        parse_mode: Parse mode for text
        
    Returns:
        True if message was edited, False if no changes needed
    """
    return await safe_edit_message(
        message=callback.message,
        new_text=text,
        new_markup=reply_markup,
        parse_mode=parse_mode
    )

