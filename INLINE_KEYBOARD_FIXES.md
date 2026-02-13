# Inline Keyboard Fixes - Progress Tracker

## Task
Fix `ValidationError: reply_markup must be InlineKeyboardMarkup, but ReplyKeyboardMarkup was provided` errors by:
- Using `InlineKeyboardMarkup` only with `edit_text()`
- Using `ReplyKeyboardMarkup` only with `answer()`

## Files Fixed

### ✅ app/handlers/start.py
- Already partially fixed - `back_to_menu_callback()` uses `get_main_menu_inline()`

### ✅ app/handlers/quiz.py (3 fixes applied)
- Line ~271: Daily limit reached error - changed `get_main_menu()` to `get_main_menu_inline()`
- Line ~274: Error starting quiz - changed `get_main_menu()` to `get_main_menu_inline()`
- Line ~377: Quiz cancelled message - was already using `get_main_menu_inline()` ✓

### ✅ app/handlers/payment.py (2 fixes applied)
- Line ~85: Error loading payment info - changed `get_main_menu()` to `get_main_menu_inline()`
- Line ~207-211: Error handling in subscribe_callback - already using `get_main_menu_inline()`
- Line ~329: Error loading status - changed `get_main_menu()` to `get_main_menu_inline()`

### ✅ app/handlers/progress.py (1 fix applied)
- Line ~147: Error loading progress - changed `get_main_menu()` to `get_main_menu_inline()`

## Summary
- Files modified: 3 (quiz.py, payment.py, progress.py)
- Total fixes applied: 6
- All `edit_text()` calls now use `InlineKeyboardMarkup`
- All `answer()` calls use appropriate keyboard type

## Key Changes

### quiz.py
```python
# Before:
reply_markup=MainMenuKeyboard.get_main_menu()

# After:
reply_markup=MainMenuKeyboard.get_main_menu_inline()
```

### payment.py
```python
# Before (error handler in command_payment):
reply_markup=MainMenuKeyboard.get_main_menu()

# After:
reply_markup=MainMenuKeyboard.get_main_menu_inline()
```

### progress.py
```python
# Before (error handler in command_progress):
reply_markup=MainMenuKeyboard.get_main_menu()

# After:
reply_markup=MainMenuKeyboard.get_main_menu_inline()
```

## Keyboard Usage Rules (Telegram API)
1. `InlineKeyboardMarkup` - Required for `callback_query.edit_text()`
2. `ReplyKeyboardMarkup` - Used with `message.answer()` for initial commands
3. The `MainMenuKeyboard` class provides both:
   - `get_main_menu()` - Returns `ReplyKeyboardMarkup` (for `answer()`)
   - `get_main_menu_inline()` - Returns `InlineKeyboardMarkup` (for `edit_text()`)

