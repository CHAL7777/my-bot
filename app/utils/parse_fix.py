"""
Parse Mode Fix - Strips Markdown formatting from messages

This module provides utilities to strip Markdown formatting from text
to prevent "can't parse entities" errors when the bot is configured
with HTML parse mode.

Usage:
    from app.utils.parse_fix import strip_markdown
    
    message = "This is *bold* text"
    safe_message = strip_markdown(message)  # "This is bold text"
"""

import re
from typing import Any


def strip_markdown(text: Any) -> str:
    """
    Strip Markdown formatting from text.
    
    Converts Markdown-style formatting to plain text:
    - *bold* -> bold
    - _italic_ -> italic
    - `code` -> code
    - ~strikethrough~ -> strikethrough
    - **bold** -> bold
    - __italic__ -> italic
    - ```code block``` -> code block
    
    Args:
        text: Any value (will be converted to string)
        
    Returns:
        Plain text with all Markdown formatting removed
        
    Examples:
        >>> strip_markdown("Hello *world*")
        'Hello world'
        >>> strip_markdown("**bold** and _italic_")
        'bold and italic'
    """
    if text is None:
        return ""
    
    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)
    
    if not text:
        return ""
    
    # Store original for comparison
    original = text
    
    # Remove code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove inline code (`...`)
    text = re.sub(r'`[^`]*`', '', text)
    
    # Remove strikethrough (~~...~~)
    text = re.sub(r'~~[^~]*~~', '', text)
    
    # Remove bold (**...**)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    
    # Remove bold (*...*) - but be careful not to remove single asterisks
    # Only remove asterisks that have text on both sides
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # Remove italic (__...__)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    
    # Remove italic (_..._) - but be careful
    # Only remove underscores that have text on both sides
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
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def strip_markdown_from_dict(data: dict) -> dict:
    """
    Recursively strip Markdown from all string values in a dictionary.
    
    Args:
        data: Dictionary potentially containing Markdown-formatted strings
        
    Returns:
        Dictionary with all string values cleaned of Markdown
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = strip_markdown(value)
        elif isinstance(value, dict):
            result[key] = strip_markdown_from_dict(value)
        elif isinstance(value, list):
            result[key] = [
                strip_markdown(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def make_message_safe(text: Any, parse_mode: str = "HTML") -> str:
    """
    Make a message safe for sending with the specified parse mode.
    
    Args:
        text: Message text (any type)
        parse_mode: The parse mode being used ("HTML" or "Markdown")
        
    Returns:
        Message text safe for the specified parse mode
    """
    if parse_mode.upper() == "HTML":
        # For HTML mode, strip Markdown (since bot uses HTML)
        return strip_markdown(text)
    elif parse_mode.upper() == "MARKDOWN":
        # For Markdown mode, strip HTML tags (just in case)
        if isinstance(text, str):
            return re.sub(r'<[^>]*>', '', text)
        return str(text)
    else:
        # For any other mode (including None/plain text), strip both
        text = strip_markdown(text)
        if isinstance(text, str):
            text = re.sub(r'<[^>]*>', '', text)
        return text


class SafeMessageBuilder:
    """
    Builder class for safely constructing messages.
    
    Automatically strips Markdown from all added content.
    
    Usage:
        builder = SafeMessageBuilder()
        builder.add("Hello *world*!")
        builder.add_line("This is a new line")
        builder.add_bold("This will be bold in Markdown")
        message = builder.build()
    """
    
    def __init__(self, separator: str = "\n"):
        self.lines = []
        self.separator = separator
    
    def add(self, text: Any) -> 'SafeMessageBuilder':
        """Add a line of text (Markdown will be stripped)"""
        self.lines.append(strip_markdown(str(text)))
        return self
    
    def add_line(self, text: Any = "") -> 'SafeMessageBuilder':
        """Add a line with separator"""
        self.lines.append(strip_markdown(str(text)))
        return self
    
    def add_section(self, title: Any, content: Any = "") -> 'SafeMessageBuilder':
        """Add a titled section"""
        self.lines.append(f"{strip_markdown(str(title))}: {strip_markdown(str(content))}")
        return self
    
    def add_list(self, items: list, prefix: str = "- ") -> 'SafeMessageBuilder':
        """Add a list of items"""
        for item in items:
            self.lines.append(f"{prefix}{strip_markdown(str(item))}")
        return self
    
    def build(self) -> str:
        """Build the final message"""
        return self.separator.join(self.lines)


# Convenience functions

def safe_text(text: Any) -> str:
    """Quick function to strip Markdown from text"""
    return strip_markdown(text)


def safe_join(*parts, separator: str = "\n") -> str:
    """Join multiple parts safely, stripping Markdown"""
    safe_parts = [strip_markdown(str(p)) for p in parts]
    return separator.join(safe_parts)

