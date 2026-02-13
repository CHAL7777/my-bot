"""
Safe Message Sender - Wrapper for production-safe Telegram message sending

This module provides SafeMessageSender and safe_send_message which are
imported by handlers. It wraps the PlainTextMessageSender for compatibility.

New features:
- safe_send_long_message: Send messages that exceed Telegram's 4096 char limit
"""

import logging
from typing import Optional, Union, Any, Dict, List
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram import Bot

from app.utils.plain_sender import (
    PlainTextMessageSender,
    clean_text,
    build_message,
    send_plain_message,
    split_long_text
)

logger = logging.getLogger(__name__)


# Alias for PlainTextMessageSender to maintain compatibility with existing imports
SafeMessageSender = PlainTextMessageSender


async def safe_send_message(
    bot: Bot,
    chat_id: Union[int, str],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_notification: bool = False,
    protect_content: bool = False,
    **kwargs
) -> Optional[Message]:
    """
    Convenience function for safe plain text message sending.
    
    This is an alias for send_plain_message from plain_sender module.
    
    Args:
        bot: Bot instance
        chat_id: Target chat ID
        text: Message text
        reply_markup: Optional inline keyboard
        disable_notification: Send silently
        protect_content: Protect from forwarding
        **kwargs: Additional arguments for send_message
        
    Returns:
        Sent Message object or None if failed
    """
    return await send_plain_message(
        bot=bot,
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        disable_notification=disable_notification,
        protect_content=protect_content,
        **kwargs
    )


async def safe_send_long_message(
    bot: Bot,
    chat_id: Union[int, str],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_notification: bool = False,
    protect_content: bool = False,
    **kwargs
) -> Optional[List[Message]]:
    """
    Convenience function for sending long messages that may exceed Telegram's
    4096 character limit. The message will be automatically split into multiple
    parts if needed.
    
    Args:
        bot: Bot instance
        chat_id: Target chat ID
        text: Message text (may be long)
        reply_markup: Optional inline keyboard (only applied to last message)
        disable_notification: Send silently
        protect_content: Protect from forwarding
        **kwargs: Additional arguments for send_message
        
    Returns:
        List of sent Message objects (one per part), or None if all failed
    """
    sender = PlainTextMessageSender(bot)
    return await sender.send_long_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        disable_notification=disable_notification,
        protect_content=protect_content,
        **kwargs
    )


def get_safe_sender(bot: Bot) -> PlainTextMessageSender:
    """
    Factory function to get a SafeMessageSender instance.
    
    Args:
        bot: Bot instance
        
    Returns:
        PlainTextMessageSender instance
    """
    return PlainTextMessageSender(bot)

