"""
Telegram utilities for safe message sending with proper escaping.
"""

from typing import Optional, Union
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest


async def safe_answer(
    obj: Union[Message, CallbackQuery],
    text: str,
    parse_mode: Optional[str] = "Markdown",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    **kwargs
):
    """
    Safely send a message, escaping Markdown special characters.
    
    This function handles the common case where you need to send a message
    that may contain user-provided or dynamic content that could include
    Markdown special characters.
    
    Args:
        obj: Message or CallbackQuery object
        text: Text to send (will be escaped if parse_mode is Markdown/MarkdownV2)
        parse_mode: Parse mode ("Markdown", "MarkdownV2", "HTML", or None)
        reply_markup: Optional inline keyboard
        **kwargs: Additional arguments for answer/edit_text
        
    Returns:
        The sent message object
        
    Raises:
        TelegramBadRequest: If the message still fails to send (rare edge cases)
    """
    from app.utils.helpers import escape_markdown_content
    
    # Handle None parse_mode explicitly
    actual_parse_mode = None if parse_mode == "None" else parse_mode
    
    # Escape content for Markdown-based modes - use comprehensive escaping
    if parse_mode in ("Markdown", "MarkdownV2"):
        text = escape_markdown_content(text)
    
    # Use appropriate method based on object type
    if isinstance(obj, CallbackQuery):
        # For callbacks, edit the message or answer
        if kwargs.pop('edit', False):
            return await obj.message.edit_text(
                text,
                parse_mode=actual_parse_mode,
                reply_markup=reply_markup,
                **kwargs
            )
        else:
            return await obj.message.answer(
                text,
                parse_mode=actual_parse_mode,
                reply_markup=reply_markup,
                **kwargs
            )
    else:
        # For regular messages
        return await obj.answer(
            text,
            parse_mode=actual_parse_mode,
            reply_markup=reply_markup,
            **kwargs
        )


async def safe_edit_text(
    message: Message,
    text: str,
    parse_mode: Optional[str] = "Markdown",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    **kwargs
):
    """
    Safely edit a message's text with proper escaping.
    
    Args:
        message: The message to edit
        text: New text content (will be escaped if using Markdown)
        parse_mode: Parse mode ("Markdown", "MarkdownV2", "HTML", or None)
        reply_markup: Optional inline keyboard
        **kwargs: Additional arguments
        
    Returns:
        The edited message object
    """
    from app.utils.helpers import escape_markdown_content
    
    actual_parse_mode = None if parse_mode == "None" else parse_mode
    
    if parse_mode in ("Markdown", "MarkdownV2"):
        text = escape_markdown_content(text)
    
    return await message.edit_text(
        text,
        parse_mode=actual_parse_mode,
        reply_markup=reply_markup,
        **kwargs
    )


def make_safe_text(
    text: str,
    parse_mode: Optional[str] = "Markdown"
) -> str:
    """
    Escape Markdown special characters in text.
    
    This is a synchronous utility for when you need to prepare text
    before sending.
    
    Args:
        text: Text to escape
        parse_mode: The parse mode that will be used (only Markdown/V2 needs escaping)
        
    Returns:
        Escaped text safe for the specified parse mode
    """
    from app.utils.helpers import escape_markdown_content
    
    if parse_mode in ("Markdown", "MarkdownV2"):
        return escape_markdown_content(text)
    return text
