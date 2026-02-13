# Telegram Parse Error Fix - Implementation Plan

## Problem
```
ERROR - Failed to process update 702090165: Telegram server says - Bad Request: can't parse entities: Can't find end of the entity starting at byte offset 37
```

## Root Cause
Dynamic content (subject names, chapter names, question text, etc.) containing Markdown special characters like `_`, `*`, `[`, `]` is not properly escaped before being inserted into Markdown messages.

## Implementation Steps

### Step 1: Add `escape_markdown_content()` function in helpers.py
- [x] Add comprehensive escaping function for all MarkdownV2 special characters
- [x] Add helper to escape dictionary content (for quiz questions, options, etc.)

### Step 2: Update quiz.py to escape dynamic content
- [x] Escape subject names in `_build_chapter_selection_message()`
- [x] Escape chapter names
- [x] Escape question text and options in quiz messages
- [x] Escape explanations
- [x] Update all message building functions

### Step 3: Update telegram_utils.py to use centralized escaping
- [x] Use `escape_markdown_content()` in safe_answer()
- [x] Update safe_edit_text() and make_safe_text()

### Step 4: Create and run tests
- [ ] Create comprehensive test for parse error fix
- [ ] Verify fix works with problematic content
- [ ] Update existing test file

## Files to Modify
1. `app/utils/helpers.py` - Add escape_markdown_content()
2. `app/handlers/quiz.py` - Use escaping in all message building
3. `app/utils/telegram_utils.py` - Use centralized escaping

## Key Changes

### helpers.py - New function:
```python
def escape_markdown_content(text: str) -> str:
    """Escape ALL special characters for MarkdownV2."""
    # Escapes: _ * [ ] ( ) ~ ` > # + - = | { } . !
    ...
```

### quiz.py - Message building updates:
- Use `escape_markdown_content()` on all dynamic content
- Subject names, chapter names, question text, options, explanations

## Testing
Run: `python test_parse_error_fix.py`

