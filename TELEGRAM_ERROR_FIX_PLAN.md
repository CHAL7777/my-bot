# Telegram Bot Error Fix Plan

## Error Analysis

### Error 1: TelegramBadRequest
```
TelegramBadRequest: Bad Request: message is not modified:
specified new message content and reply markup are exactly the same
as a current content and reply markup of the message
```

**Root Cause:**
- When calling `callback.message.edit_text()` with identical content and reply_markup as the current message
- Common in callback handlers that may be triggered multiple times with the same state
- No validation before attempting to edit

### Error 2: TelegramConflictError  
```
TelegramConflictError: Conflict: terminated by other getUpdates request
```

**Root Cause:**
- Multiple bot instances running with the same token
- Webhook and polling both active simultaneously
- Improper shutdown leaving orphaned connections

---

## Solution Overview

### Part 1: Safe Message Editing Utility
Create a robust utility that:
1. Compares current message content with new content
2. Only calls `edit_text()` if content actually differs
3. Handles reply_markup comparison
4. Provides detailed logging

### Part 2: Handler Fixes
Update all callback handlers to:
1. Use safe edit utility
2. Add state-based guards to prevent duplicate processing
3. Implement proper callback.answer() calls

### Part 3: Conflict Prevention
1. Single instance enforcement
2. Proper shutdown handling
3. Connection cleanup

---

## Implementation Steps

### Step 1: Create Safe Edit Utility
**File:** `app/utils/safe_edit.py`

```python
"""
Safe message editing utilities for aiogram v3.
Prevents 'message is not modified' errors.
"""

from typing import Optional
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)

async def safe_edit_message(
    message: Message,
    new_text: str,
    new_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown"
) -> bool:
    """
    Safely edit a message, only if content actually changed.
    
    Args:
        message: The message to edit
        new_text: New text content
        new_markup: New inline keyboard (optional)
        parse_mode: Parse mode for the text
        
    Returns:
        True if message was edited, False if no changes needed
    """
    # Check if content is actually different
    current_text = message.text or message.caption or ""
    
    # Normalize text for comparison
    if parse_mode in ("Markdown", "MarkdownV2"):
        current_text = current_text.strip()
        new_text = new_text.strip()
    
    # Check if text changed
    text_changed = current_text != new_text
    
    # Check if markup changed
    current_markup = message.reply_markup
    markup_changed = current_markup != new_markup
    
    # If nothing changed, log and return False
    if not text_changed and not markup_changed:
        logger.debug(
            f"No changes detected for message {message.message_id}, "
            f"skipping edit"
        )
        return False
    
    # If only markup changed, can just edit markup
    if not text_changed and markup_changed:
        try:
            await message.edit_reply_markup(reply_markup=new_markup)
            logger.debug(f"Updated markup for message {message.message_id}")
            return True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.debug(f"Markup actually same for message {message.message_id}")
                return False
            raise
    
    # Full edit needed
    try:
        await message.edit_text(
            text=new_text,
            reply_markup=new_markup,
            parse_mode=parse_mode
        )
        logger.debug(f"Edited message {message.message_id}")
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(f"Message {message.message_id} already has same content")
            return False
        raise


class MessageEditGuard:
    """
    Context manager to prevent duplicate edit attempts.
    
    Usage:
        async with MessageEditGuard(state, "editing_question"):
            await callback.message.edit_text(...)
    """
    
    def __init__(self, state: FSMContext, guard_key: str):
        self.state = state
        self.guard_key = f"editing_{guard_key}"
    
    async def __aenter__(self):
        # Check if already editing
        data = await self.state.get_data()
        if data.get(self.guard_key):
            raise EditInProgressError("Edit already in progress")
        await self.state.update_data({self.guard_key: True})
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Clear guard
        data = await self.state.get_data()
        await self.state.update_data({self.guard_key: False})
        if exc_type:
            raise exc_val


class EditInProgressError(Exception):
    """Raised when an edit is already in progress"""
    pass
```

### Step 2: Update Telegram Utils
**File:** `app/utils/telegram_utils.py`

Add safe editing functions that integrate with the existing utilities.

### Step 3: Fix Quiz Handlers
**File:** `app/handlers/quiz.py`

Key fixes:
1. Add guard checks before edit_text
2. Use safe edit utility
3. Prevent duplicate callback processing

### Step 4: Fix Answers Handler  
**File:** `app/handlers/answers.py`

Key fixes:
1. Add state-based duplicate prevention
2. Use safe edit utility for answer feedback

### Step 5: Fix Start Handler
**File:** `app/handlers/start.py`

Key fixes:
1. Fix `inline_start_quiz_callback` to use safe editing
2. Add duplicate prevention

### Step 6: Bot Instance Management
**File:** `app/bot.py`

Add:
1. Instance lock file
2. Proper signal handling
3. Graceful shutdown

---

## Code Examples

### Before (Problematic):
```python
@router.callback_query(F.data == "start_quiz")
async def inline_start_quiz_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Loading...",
        reply_markup=some_markup
    )
    # Problem: May be called multiple times
```

### After (Fixed):
```python
@router.callback_query(F.data == "start_quiz")
async def inline_start_quiz_callback(callback: types.CallbackQuery, state: FSMContext):
    # Guard against duplicate calls
    data = await state.get_data()
    if data.get('processing_start_quiz'):
        await callback.answer("Already processing...", show_alert=False)
        return
    
    await state.update_data({'processing_start_quiz': True})
    
    try:
        from app.utils.safe_edit import safe_edit_message
        await safe_edit_message(
            callback.message,
            "Loading...",
            reply_markup=some_markup
        )
        
        # ... rest of handler
        
    finally:
        await state.update_data({'processing_start_quiz': False})
```

---

## Testing Checklist

- [ ] No "message is not modified" errors in logs
- [ ] No "Conflict: terminated by other getUpdates" errors
- [ ] Callback handlers respond correctly
- [ ] Multiple rapid clicks don't cause errors
- [ ] Bot restarts cleanly
- [ ] Single instance enforcement works

---

## Best Practices

1. **Always compare before editing**: Use safe_edit utility
2. **Guard against duplicates**: Use state flags for in-progress operations
3. **Proper callback answering**: Always call `await callback.answer()`
4. **Single instance**: Ensure only one bot process runs
5. **Graceful shutdown**: Handle SIGTERM/SIGINT properly

