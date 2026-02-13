from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from aiogram.exceptions import TelegramBadRequest
import logging
import re

logger = logging.getLogger(__name__)

# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_time(seconds: Union[int, float]) -> str:
    """Format seconds into human readable time"""
    try:
        seconds = int(seconds)
        if seconds < 0:
            seconds = 0
        
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    except (ValueError, TypeError):
        return "0s"


def format_number(num: Union[int, float]) -> str:
    """Format number with K, M suffixes"""
    try:
        num = float(num)
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        elif num.is_integer():
            return str(int(num))
        else:
            return f"{num:.1f}"
    except (ValueError, TypeError):
        return "0"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not isinstance(text, str):
        return ""
    
    if len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    if not isinstance(dt, datetime):
        return "Unknown date"
    
    now = datetime.now()
    today = now.date()
    dt_date = dt.date()
    
    if dt_date == today:
        time_str = dt.strftime('%I:%M %p').lstrip('0')
        return f"Today at {time_str}"
    elif dt_date == today - timedelta(days=1):
        time_str = dt.strftime('%I:%M %p').lstrip('0')
        return f"Yesterday at {time_str}"
    elif (now - dt).days < 7:
        time_str = dt.strftime('%I:%M %p').lstrip('0')
        return f"{dt.strftime('%A')} at {time_str}"
    else:
        time_str = dt.strftime('%I:%M %p').lstrip('0')
        return f"{dt.strftime('%d %b %Y')} at {time_str}"


def calculate_percentage(part: int, whole: int) -> float:
    """Calculate percentage"""
    try:
        if whole <= 0 or part < 0:
            return 0.0
        return round((part / whole) * 100, 2)
    except (ZeroDivisionError, TypeError):
        return 0.0


def get_difficulty_emoji(difficulty: str) -> str:
    """Get emoji for difficulty level"""
    try:
        from app.utils.constants import EMOJIS
        if difficulty == 'simple':
            return EMOJIS.get('easy', '🟢')
        elif difficulty == 'medium':
            return EMOJIS.get('medium', '🟡')
        elif difficulty == 'hard':
            return EMOJIS.get('hard', '🔴')
        else:
            return '⚪'
    except ImportError:
        # Fallback if EMOJIS not available
        if difficulty == 'simple':
            return '🟢'
        elif difficulty == 'medium':
            return '🟡'
        elif difficulty == 'hard':
            return '🔴'
        else:
            return '⚪'


def format_currency(amount: Union[int, float], currency: str = "ETB") -> str:
    """Format currency amount"""
    try:
        amount = float(amount)
        
        if currency.upper() == "ETB":
            if amount.is_integer():
                return f"{int(amount):,} ETB"
            return f"{amount:,.2f} ETB"
        elif currency.upper() == "USD":
            if amount.is_integer():
                return f"${int(amount):,}"
            return f"${amount:,.2f}"
        else:
            if amount.is_integer():
                return f"{int(amount):,} {currency}"
            return f"{amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return f"0 {currency}"


# ============================================================================
# SAFE DATA ACCESS
# ============================================================================

def safe_get(data: Any, *keys, default: Any = None) -> Any:
    """Safely get nested dictionary values"""
    if not isinstance(data, dict):
        return default
    
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


# ============================================================================
# VISUALIZATION UTILITIES
# ============================================================================

def generate_progress_bar(percentage: float, length: int = 10) -> str:
    """Generate a text-based progress bar"""
    try:
        percentage = float(percentage)
        if percentage < 0:
            percentage = 0
        elif percentage > 100:
            percentage = 100
        
        filled = int(percentage / 100 * length)
        empty = length - filled
        return "█" * filled + "░" * empty + f" {percentage:.1f}%"
    except (ValueError, TypeError):
        return "░" * length + " 0.0%"


# ============================================================================
# TEXT ESCAPING FUNCTIONS - FIXED VERSIONS
# ============================================================================

def escape_html(text: str) -> str:
    """
    Escape HTML special characters in text to prevent parsing errors.
    
    This function escapes all HTML entities that could cause parsing issues:
    - & → &amp;
    - < → &lt;
    - > → &gt;
    - " → &quot;
    - ' → &#39;
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for Telegram HTML parsing
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Order matters - escape ampersand first!
    result = text
    result = result.replace("&", "&amp;")
    result = result.replace("<", "&lt;")
    result = result.replace(">", "&gt;")
    result = result.replace('"', "&quot;")
    result = result.replace("'", "&#39;")
    
    return result


def escape_markdown(text: str, version: int = 2) -> str:
    """
    Escape Markdown special characters in text to prevent parsing errors.
    
    Args:
        text: Text to escape
        version: 1 for standard Markdown, 2 for MarkdownV2 (default)
    
    Returns:
        Escaped text safe for Telegram Markdown parsing
    """
    if not text or not isinstance(text, str):
        return ""
    
    result = text
    
    if version == 2:
        # Telegram MarkdownV2 - stricter escaping
        escape_chars = [
            ('\\', '\\\\'),      # Must be first!
            ('_', '\\_'),
            ('*', '\\*'),
            ('[', '\\['),
            (']', '\\]'),
            ('(', '\\('),
            (')', '\\)'),
            ('~', '\\~'),
            ('`', '\\`'),
            ('>', '\\>'),
            ('#', '\\#'),
            ('+', '\\+'),
            ('-', '\\-'),
            ('=', '\\='),
            ('|', '\\|'),
            ('{', '\\{'),
            ('}', '\\}'),
            ('.', '\\.'),
            ('!', '\\!')
        ]
    else:
        # Standard Markdown
        escape_chars = [
            ('\\', '\\\\'),
            ('*', '\\*'),
            ('_', '\\_'),
            ('`', '\\`'),
            ('[', '\\['),
            (']', '\\]'),
            ('(', '\\('),
            (')', '\\)'),
            ('~', '\\~'),
            ('>', '\\>'),
            ('#', '\\#'),
            ('+', '\\+'),
            ('-', '\\-'),
            ('=', '\\='),
            ('|', '\\|')
        ]
    
    for char, escaped in escape_chars:
        result = result.replace(char, escaped)
    
    return result


def escape_markdown_v2(text: str) -> str:
    """Alias for escape_markdown with version=2"""
    return escape_markdown(text, version=2)


def escape_markdown_content(text: str) -> str:
    """
    Escape ALL special characters in text for MarkdownV2.
    
    This is the PRIMARY function to use for escaping dynamic content
    like subject names, chapter names, question text, options, etc.
    
    MarkdownV2 special characters that must be escaped:
    _ * [ ] ( ) ~ ` > # + - = | { } . !
    
    Args:
        text: Text to escape (can be None, empty, or any string)
        
    Returns:
        Escaped text safe for Telegram MarkdownV2, or empty string if input is invalid
    """
    if not text or not isinstance(text, str):
        return ""
    
    result = text
    
    # Order matters: escape backslash FIRST
    escape_pairs = [
        ('\\', '\\\\'),      # Backslash - must be first!
        ('_', '\\_'),        # Underscore - common in names
        ('*', '\\*'),        # Asterisk
        ('[', '\\['),        # Left bracket - can start link
        (']', '\\]'),        # Right bracket - can end link
        ('(', '\\('),        # Left paren
        (')', '\\)'),        # Right paren
        ('~', '\\~'),        # Tilde
        ('`', '\\`'),        # Backtick
        ('>', '\\>'),        # Greater than
        ('#', '\\#'),        # Hash
        ('+', '\\+'),        # Plus
        ('-', '\\-'),        # Minus/hyphen
        ('=', '\\='),        # Equals
        ('|', '\\|'),        # Pipe
        ('{', '\\{'),        # Left brace
        ('}', '\\}'),        # Right brace
        ('.', '\\.'),        # Period
        ('!', '\\!')         # Exclamation
    ]
    
    for char, escaped in escape_pairs:
        result = result.replace(char, escaped)
    
    return result


def escape_markdown_dict(data: dict) -> dict:
    """
    Recursively escape all string values in a dictionary for MarkdownV2.
    
    Useful for escaping entire question objects, option dictionaries, etc.
    
    Args:
        data: Dictionary with string values to escape
        
    Returns:
        Dictionary with all string values escaped
        
    Example:
        {
            "question_text": "What is H2O_?",
            "option_a": "Water*Form"
        }
        ->
        {
            "question_text": "What is H2O\\_?",
            "option_a": "Water\\*Form"
        }
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = escape_markdown_content(value)
        elif isinstance(value, dict):
            result[key] = escape_markdown_dict(value)
        elif isinstance(value, list):
            result[key] = [
                escape_markdown_dict(item) if isinstance(item, dict) 
                else escape_markdown_content(item) if isinstance(item, str) 
                else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def safe_text_for_markdown(text: Any) -> str:
    """
    Safely convert any value to a Markdown-escaped string.
    
    This is a convenience function that handles None, non-strings, and
    escapes the content for MarkdownV2.
    
    Args:
        text: Any value (str, int, float, None, etc.)
        
    Returns:
        Escaped string safe for MarkdownV2
    """
    if text is None:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    return escape_markdown_content(text)


def escape_csv_error(error_msg: str) -> str:
    """Escape Markdown special characters in CSV error messages."""
    if not error_msg or not isinstance(error_msg, str):
        return ""
    
    return escape_markdown_v2(error_msg)


def safe_user_text(text: str) -> str:
    """
    Safely escape text that may contain user-provided content.
    
    This is a convenience function for escaping user names, usernames,
    or any text that might come from user input and contain special
    characters that could break Markdown parsing.
    
    Args:
        text: User-provided text to escape
        
    Returns:
        Escaped text safe for Markdown
    """
    return escape_markdown_v2(text)


def format_user_name(first_name: str, username: str = None) -> str:
    """
    Format a user's name safely for display in Markdown messages.
    
    Args:
        first_name: User's first name
        username: Optional username without @
        
    Returns:
        Safely formatted user name string
    """
    safe_first_name = escape_markdown_v2(first_name or 'User')
    
    if username:
        safe_username = escape_markdown_v2(username)
        return f"{safe_first_name} (@{safe_username})"
    
    return safe_first_name


# ============================================================================
# MESSAGE SENDING UTILITIES - IMPROVED VERSIONS
# ============================================================================

def validate_message_text(text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
    """
    Validate text for Telegram message sending.
    
    Returns:
        Dict with validation results
    """
    if not text or not isinstance(text, str):
        return {
            'valid': False,
            'issues': ['Empty text'],
            'safe_text': '',
            'suggestion': 'Provide non-empty text'
        }
    
    issues = []
    parse_mode_lower = parse_mode.lower() if parse_mode else ''
    
    # Check length
    if len(text) > 4096:
        issues.append(f"Text too long ({len(text)} > 4096 characters)")
    
    # Parse mode specific checks
    if parse_mode_lower in ['markdown', 'markdownv2']:
        # Check for unclosed formatting
        formatting_chars = ['*', '_', '`', '~', '[', ']', '(', ')']
        for char in formatting_chars:
            if text.count(char) % 2 != 0:
                issues.append(f"Unbalanced '{char}' character")
    
    elif parse_mode_lower == 'html':
        # Check for basic HTML issues
        if '<' in text and '>' not in text:
            issues.append("Unclosed HTML tag")
        elif '>' in text and '<' not in text:
            issues.append("Unopened HTML tag")
    
    # Generate safe text
    if parse_mode_lower == 'markdownv2':
        safe_text = escape_markdown_v2(text)
    elif parse_mode_lower == 'markdown':
        safe_text = escape_markdown(text, version=1)
    elif parse_mode_lower == 'html':
        safe_text = escape_html(text)
    else:
        safe_text = text
    
    # Truncate if too long
    if len(safe_text) > 4096:
        safe_text = safe_text[:4096]
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'safe_text': safe_text,
        'suggestion': 'Use HTML parse mode for complex formatting' if issues else 'OK'
    }


async def safe_send_message(
    bot,
    chat_id: Union[int, str],
    text: str,
    parse_mode: str = "Markdown",
    max_retries: int = 2,
    **kwargs
) -> Optional[Any]:
    """
    Send a message with proper escaping and error handling.
    
    This function:
    1. Validates the text for formatting issues
    2. Escapes text appropriately for the parse mode
    3. Retries with different parse modes if needed
    4. Falls back to plain text if all else fails
    
    Returns:
        The sent message object, or None if failed
    """
    if not text:
        logger.warning(f"Empty text for chat {chat_id}")
        return None
    
    try:
        chat_id = int(chat_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid chat ID: {chat_id}")
        return None
    
    # Validate text first
    validation = validate_message_text(text, parse_mode)
    
    if not validation['valid']:
        logger.warning(f"Text validation issues for chat {chat_id}: {validation['issues']}")
    
    current_parse_mode = parse_mode
    current_text = validation['safe_text']
    
    for attempt in range(max_retries):
        try:
            return await bot.send_message(
                chat_id=chat_id,
                text=current_text,
                parse_mode=current_parse_mode,
                **kwargs
            )
        
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            
            if "can't parse entities" in error_msg:
                logger.warning(
                    f"Parse error on attempt {attempt + 1} for chat {chat_id}"
                )
                
                if attempt < max_retries - 1:
                    # Try different parse modes
                    if current_parse_mode in ["Markdown", "MarkdownV2"]:
                        # Switch to HTML
                        current_parse_mode = "HTML"
                        current_text = escape_html(text)
                    elif current_parse_mode == "HTML":
                        # Switch to plain text
                        current_parse_mode = None
                        current_text = re.sub(r'[`*_~\[\]()#<>]', '', text)
                    else:
                        # Already plain text, make it safer
                        current_text = re.sub(r'[^\w\s.,!?@#$%^&+=:;"\'\-]', '', text)
                else:
                    # Last resort: plain text, truncated
                    logger.error(f"All parse attempts failed for chat {chat_id}")
                    current_parse_mode = None
                    current_text = re.sub(r'[^\w\s.,!?@#%&+=:;"\'\-]', '', text)[:4000]
                    try:
                        return await bot.send_message(
                            chat_id=chat_id,
                            text=current_text,
                            parse_mode=None,
                            **kwargs
                        )
                    except Exception as final_error:
                        logger.error(f"Final attempt failed for chat {chat_id}: {final_error}")
                        return None
            
            elif "message is too long" in error_msg:
                logger.warning(f"Message too long for chat {chat_id}, truncating")
                current_text = current_text[:4000] + "..."
                continue
            
            elif "chat not found" in error_msg or "bot was blocked" in error_msg:
                logger.warning(f"Cannot send to chat {chat_id}: {e}")
                return None
            
            else:
                logger.error(f"Telegram error for chat {chat_id}: {e}")
                if attempt < max_retries - 1:
                    continue
                return None
        
        except Exception as e:
            logger.error(f"Unexpected error sending to chat {chat_id}: {e}")
            if attempt < max_retries - 1:
                continue
            return None
    
    return None


async def safe_admin_message(
    bot,
    chat_id: Union[int, str],
    text: str,
    parse_mode: str = "Markdown",
    **kwargs
) -> Optional[Any]:
    """Send a message to admin with proper escaping and error handling."""
    result = await safe_send_message(
        bot=bot,
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        **kwargs
    )
    
    if result is None:
        logger.error(f"Failed to send admin message to {chat_id}")
    
    return result


async def notify_admin(
    bot,
    admin_id: Union[int, str],
    title: str,
    message: str,
    emoji: str = "📢",
    parse_mode: str = "Markdown",
    **kwargs
) -> bool:
    """Send a formatted notification to a single admin."""
    try:
        admin_id = int(admin_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid admin ID: {admin_id}")
        return False
    
    # Format the message
    if parse_mode in ["Markdown", "MarkdownV2"]:
        safe_title = escape_markdown(title, version=2 if parse_mode == "MarkdownV2" else 1)
        safe_message = escape_markdown(message, version=2 if parse_mode == "MarkdownV2" else 1)
        formatted_message = f"{emoji} *{safe_title}*\n\n{safe_message}"
    elif parse_mode == "HTML":
        safe_title = escape_html(title)
        safe_message = escape_html(message)
        formatted_message = f"{emoji} <b>{safe_title}</b>\n\n{safe_message}"
    else:
        formatted_message = f"{emoji} {title}\n\n{message}"
    
    # Send the message
    result = await safe_send_message(
        bot=bot,
        chat_id=admin_id,
        text=formatted_message,
        parse_mode=parse_mode,
        **kwargs
    )
    
    return result is not None


async def notify_all_admins(
    bot,
    admin_ids: List[Union[int, str]],
    title: str,
    message: str,
    emoji: str = "📢",
    parse_mode: str = "Markdown",
    **kwargs
) -> Dict[str, int]:
    """
    Send a notification to all admins.
    
    Returns:
        Dict with success and failed counts
    """
    if not admin_ids:
        logger.warning("No admin IDs provided")
        return {'success': 0, 'failed': 0, 'total': 0}
    
    # Prepare message once
    if parse_mode in ["Markdown", "MarkdownV2"]:
        safe_title = escape_markdown(title, version=2 if parse_mode == "MarkdownV2" else 1)
        safe_message = escape_markdown(message, version=2 if parse_mode == "MarkdownV2" else 1)
        formatted_message = f"{emoji} *{safe_title}*\n\n{safe_message}"
    elif parse_mode == "HTML":
        safe_title = escape_html(title)
        safe_message = escape_html(message)
        formatted_message = f"{emoji} <b>{safe_title}</b>\n\n{safe_message}"
    else:
        formatted_message = f"{emoji} {title}\n\n{message}"
    
    results = {'success': 0, 'failed': 0, 'total': len(admin_ids)}
    
    for admin_id in admin_ids:
        try:
            result = await safe_send_message(
                bot=bot,
                chat_id=admin_id,
                text=formatted_message,
                parse_mode=parse_mode,
                **kwargs
            )
            
            if result is not None:
                results['success'] += 1
            else:
                results['failed'] += 1
                
        except Exception as e:
            logger.error(f"Error notifying admin {admin_id}: {e}")
            results['failed'] += 1
    
    logger.info(
        f"Admin notifications: {results['success']}/{results['total']} successful"
    )
    
    return results


# ============================================================================
# ADDITIONAL UTILITIES
# ============================================================================

def get_time_ago(dt: datetime) -> str:
    """Get human readable time ago string"""
    if not isinstance(dt, datetime):
        return "some time ago"
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


def calculate_average(values: List[Union[int, float]]) -> float:
    """Calculate average of a list of numbers"""
    if not values:
        return 0.0
    
    try:
        numeric_values = [float(v) for v in values if v is not None]
        if not numeric_values:
            return 0.0
        
        return sum(numeric_values) / len(numeric_values)
    except (ValueError, TypeError):
        return 0.0


def debug_text_formatting(text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
    """
    Debug text formatting issues.
    
    Returns detailed analysis of potential problems.
    """
    analysis = {
        'text_preview': text[:200] + ('...' if len(text) > 200 else ''),
        'length': len(text),
        'parse_mode': parse_mode,
        'issues': [],
        'suggestions': []
    }
    
    # Check for common issues
    if parse_mode in ["Markdown", "MarkdownV2"]:
        for char in ['*', '_', '`', '~', '[', '(', ')', ']']:
            count = text.count(char)
            if count % 2 != 0:
                analysis['issues'].append(f"Unbalanced '{char}' (count: {count})")
                analysis['suggestions'].append(f"Check for missing '{char}' character")
    
    if len(text) > 4000:
        analysis['issues'].append(f"Text too long ({len(text)} > 4000 chars)")
        analysis['suggestions'].append("Truncate or split the message")
    
    return analysis