# Telegram Parse Mode Error Fix Guide

## Problem Analysis

**Error:** `TelegramBadRequest: Bad Request: can't parse entities: Can't find end of the entity starting at byte offset 88`

**Root Cause:** When using `parse_mode='Markdown'` or `parse_mode='HTML'`, Telegram expects special characters to be properly escaped. If your text contains unescaped Markdown special characters like `_ * [ ] ( ) ~ > # + - = | { } . !`, Telegram fails to parse the message.

**Affected Code Locations:**
1. `admin_questions.py` - CSV import validation/result messages
2. `admin_stats.py` - Broadcast preview messages  
3. Various admin handlers sending dynamic content

## Solution: Markdown Escaping

### 1. Helper Functions (Already Available)

The project already has proper escaping functions in `app/utils/helpers.py`:

```python
def escape_markdown(text: str) -> str:
    """Escape Markdown special characters in text"""
    # Escapes: * _ ` [ ] ( ) ~ > # + - = | { } . !
    ...

def escape_csv_error(error_msg: str) -> str:
    """Escape Markdown special characters in CSV error messages"""
    return escape_markdown(error_msg)
```

### 2. Safe Message Sending Utility

Create a new utility for safe message sending:

```python
# app/utils/telegram_utils.py

from aiogram.types import Message, CallbackQuery
from app.utils.helpers import escape_markdown

async def safe_answer(
    obj: Message | CallbackQuery,
    text: str,
    parse_mode: str = "Markdown",
    **kwargs
):
    """
    Safely send a message, escaping Markdown special characters.
    
    Args:
        obj: Message or CallbackQuery object
        text: Text to send (will be escaped if parse_mode is Markdown/MarkdownV2)
        parse_mode: Parse mode ("Markdown", "MarkdownV2", "HTML", or None)
        **kwargs: Additional arguments for answer/edit_text
    """
    if parse_mode in ("Markdown", "MarkdownV2"):
        text = escape_markdown(text)
    
    if hasattr(obj, 'answer'):
        return await obj.answer(text, parse_mode=parse_mode if parse_mode != "None" else None, **kwargs)
    elif hasattr(obj, 'message') and hasattr(obj.message, 'answer'):
        return await obj.message.answer(text, parse_mode=parse_mode if parse_mode != "None" else None, **kwargs)
```

### 3. Before vs After Code Examples

#### BEFORE (Problematic Code):
```python
# admin_questions.py - handle_csv_upload
result_message = (
    f"📊 *Import Results*\n\n"
    f"📈 *Statistics:*\n"
    f"• Total rows: {stats['total_rows']}\n"
    f"• Valid rows: {stats['valid_rows']}\n"
    f"• Imported: {stats['imported']}\n"
    f"• Skipped: {stats['skipped']}\n"
    f"• Duration: {stats['duration']:.2f}s\n\n"
)

if stats['errors']:
    result_message += f"\n\n❌ *Errors ({len(stats['errors'])}):*\n"
    for error in stats['errors'][:3]:
        # ERROR: Not escaping special characters in error messages!
        result_message += f"• {error}\n"  # ← Problem if error contains _ or *

await callback.message.edit_text(
    result_message,
    parse_mode='Markdown',  # ← Fails if text contains unescaped special chars
    reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
)
```

#### AFTER (Fixed Code):
```python
# admin_questions.py - handle_csv_upload
from app.utils.helpers import escape_markdown

result_message = (
    f"📊 *Import Results*\n\n"
    f"📈 *Statistics:*\n"
    f"• Total rows: {stats['total_rows']}\n"
    f"• Valid rows: {stats['valid_rows']}\n"
    f"• Imported: {stats['imported']}\n"
    f"• Skipped: {stats['skipped']}\n"
    f"• Duration: {stats['duration']:.2f}s\n\n"
)

if stats['errors']:
    result_message += f"\n\n❌ *Errors ({len(stats['errors'])}):*\n"
    for error in stats['errors'][:3]:
        # FIX: Always escape dynamic content
        result_message += f"• {escape_markdown(error)}\n"

await callback.message.edit_text(
    result_message,
    parse_mode='Markdown',
    reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
)
```

### 4. Best Practices for CSV/Import Logs

When sending CSV-related or admin messages:

```python
from app.utils.helpers import escape_markdown, escape_csv_error

# For CSV validation errors (contains user data)
error_msg = f"❌ *Validation Failed*\n\n"
for error in errors[:5]:
    error_msg += f"• {escape_csv_error(error)}\n"  # ← Use escape_csv_error

# For dynamic content like question text from CSV
question_text = row['question_text']
escaped_question = escape_markdown(question_text)

# For user-provided text (broadcast messages, etc.)
user_message = callback.data.get('message', '')
escaped_message = escape_markdown(user_message)

# For statistics and logs
stats_text = (
    f"📊 *Import Results*\n"
    f"• Imported: {escape_markdown(str(stats['imported']))}\n"
)

# For filenames and paths (may contain special chars)
filename = document.file_name
safe_filename = escape_markdown(filename)
```

### 5. Parse Mode Selection Guide

| Content Type | Recommended Parse Mode | Reason |
|--------------|----------------------|--------|
| Static UI text | `Markdown` | All static text is already escaped |
| User CSV data | `Markdown` + escape | User content needs escaping |
| Error messages | `Markdown` + escape | May contain special chars |
| Admin broadcasts | `Markdown` + escape | User-provided content |
| HTML-formatted | `HTML` | Use HTML escape if needed |
| Plain text | `None` | Safest option for unknown content |

```python
# When in doubt, use None for plain text
await message.answer(
    "Here's your plain text without formatting",
    parse_mode=None  # ← Safest option
)
```

### 6. Complete Fix for admin_questions.py

Apply escaping to all dynamic content in the CSV import flow:

```python
# Lines around 378-420 in admin_questions.py

# BEFORE: Line 378
await message.answer(
    f"❌ *Validation Failed*\n\n"
    for error in errors[:5]:
        error_msg += f"• {error}\n"  # ← Missing escape
)

# AFTER: Line 378
await message.answer(
    f"❌ *Validation Failed*\n\n"
    for error in errors[:5]:
        error_msg += f"• {escape_csv_error(error)}\n"  # ✓ Fixed
)

# BEFORE: Around line 420
preview_msg = (
    f"✅ *CSV Validated Successfully*\n\n"
    f"📊 *Preview:*\n"
    f"• Valid rows: {valid_rows}\n"
    f"• File: {document.file_name}\n\n"  # ← May contain special chars
)

# AFTER: Around line 420
from app.utils.helpers import escape_markdown

preview_msg = (
    f"✅ *CSV Validated Successfully*\n\n"
    f"📊 *Preview:*\n"
    f"• Valid rows: {valid_rows}\n"
    f"• File: {escape_markdown(document.file_name)}\n\n"  # ✓ Fixed
)
```

### 7. Fix for admin_stats.py (Broadcast Messages)

```python
# BEFORE
await callback.message.edit_text(
    f"📢 *Broadcast Message*\n\n{message_text}",  # ← Unescaped user content
    parse_mode='Markdown'
)

# AFTER
await callback.message.edit_text(
    f"📢 *Broadcast Message*\n\n{escape_markdown(message_text)}",  # ✓ Fixed
    parse_mode='Markdown'
)
```

## Summary

**Key Takeaways:**
1. Always escape dynamic content with `escape_markdown()` when using Markdown parse mode
2. Use `escape_csv_error()` specifically for CSV-related error messages
3. When in doubt about content, use `parse_mode=None` for plain text
4. The error `Can't find end of the entity starting at byte offset X` means there's an unescaped special character at or near that position

**Quick Fix Pattern:**
```python
# For ANY dynamic text in Markdown messages:
text = f"Your message with {dynamic_content}"
escaped = escape_markdown(text)
await message.answer(escaped, parse_mode='Markdown')
