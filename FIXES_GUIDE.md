# Telegram Quiz Bot - Comprehensive Fix Guide

This document provides complete solutions for all identified issues in the Telegram Quiz Bot.

## Table of Contents
1. [Issue Summary](#issue-summary)
2. [Database Migration](#database-migration)
3. [Keyboard Type Fixes](#keyboard-type-fixes)
4. [Handler Signature Fixes](#handler-signature-fixes)
5. [Complete Code References](#complete-code-references)
6. [Testing Instructions](#testing-instructions)

---

## Issue Summary

### Issue 1: Missing Database Columns
**Error**: `ProgrammingError: (MySQL/ MariaDB) Unknown column 'xxx' in 'field list'`

**Affected columns**:
- `subscriptions.updated_at`
- `quiz_attempts.quiz_session_id`
- `user_progress.created_at`
- `user_progress.updated_at`
- `payments.subscription_days`
- `payments.transaction_id`
- `payments.notes`

**Solution**: Run the safe migration script that checks column existence before adding.

### Issue 2: ReplyKeyboardMarkup vs InlineKeyboardMarkup
**Error**: `TelegramAPIError: Wrong keyword passed... reply_markup must be of type InlineKeyboardMarkup`

**Cause**: Using `edit_text()` with `ReplyKeyboardMarkup` instead of `InlineKeyboardMarkup`.

**Solution**: Use `MainMenuKeyboard.get_main_menu_inline()` for callback handlers using `edit_text()`.

### Issue 3: Missing Handler Arguments
**Error**: `TypeError: missing required argument 'has_active_subscription'`

**Cause**: Handlers called from button presses don't receive middleware-injected parameters.

**Solution**: Add `has_active_subscription: bool = False` parameter to all relevant handlers.

---

## Database Migration

### Option 1: Python Script (Recommended)
```bash
# Preview changes (dry-run)
python scripts/run_migration.py --dry-run

# Apply changes
python scripts/run_migration.py

# Verify schema only
python scripts/run_migration.py --verify
```

### Option 2: Direct SQL Execution
```bash
# Connect to MariaDB and run the SQL file
mysql -u root -p telegram_quiz_bot < scripts/sql_migration_safe.sql
```

### Option 3: Manual SQL Commands
```sql
-- Add missing columns to subscriptions
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Add missing columns to user_progress
ALTER TABLE user_progress 
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Add missing columns to quiz_attempts
ALTER TABLE quiz_attempts 
ADD COLUMN IF NOT EXISTS quiz_session_id VARCHAR(50);

-- Add missing columns to payments
ALTER TABLE payments 
ADD COLUMN IF NOT EXISTS subscription_days INT NOT NULL DEFAULT 30,
ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS notes TEXT;
```

---

## Keyboard Type Fixes

### Before (Broken):
```python
# WRONG - Using ReplyKeyboardMarkup with edit_text()
@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_callback(callback: types.CallbackQuery, is_admin: bool = False):
    await callback.message.edit_text(
        "🏠 Main Menu",
        reply_markup=MainMenuKeyboard.get_main_menu(is_admin)  # Returns ReplyKeyboardMarkup!
    )
```

### After (Fixed):
```python
# CORRECT - Using InlineKeyboardMarkup with edit_text()
@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_callback(callback: types.CallbackQuery, is_admin: bool = False):
    await callback.message.edit_text(
        "🏠 Main Menu",
        reply_markup=MainMenuKeyboard.get_main_menu_inline(is_admin)  # Returns InlineKeyboardMarkup!
    )
```

### Keyboard Method Reference

| Method | Returns | Use Case |
|--------|---------|----------|
| `get_main_menu()` | `ReplyKeyboardMarkup` | Initial `/start` command, regular messages |
| `get_main_menu_inline()` | `InlineKeyboardMarkup` | Callback queries with `edit_text()` |
| `get_payment_options_keyboard()` | `InlineKeyboardMarkup` | Payment options (callback queries) |
| `get_progress_options_keyboard()` | `InlineKeyboardMarkup` | Progress options (callback queries) |
| `get_leaderboard_keyboard()` | `InlineKeyboardMarkup` | Leaderboard options (callback queries) |

---

## Handler Signature Fixes

### Before (Broken):
```python
# Handler missing has_active_subscription parameter
@router.message(lambda message: message.text and "Start Quiz" in message.text)
async def start_quiz_button_handler(message: Message, state: FSMContext):
    from app.handlers.quiz import start_quiz_flow
    await start_quiz_flow(message, state)  # Missing subscription check!
```

### After (Fixed):
```python
# Handler with has_active_subscription parameter
@router.message(lambda message: message.text and "Start Quiz" in message.text)
async def start_quiz_button_handler(message: Message, state: FSMContext,
                                    has_active_subscription: bool = False):
    from app.handlers.quiz import start_quiz_flow
    await start_quiz_flow(message, state, has_active_subscription)  # Properly passed!
```

### Affected Handlers Summary

| File | Handler | Fix Applied |
|------|---------|-------------|
| `start.py` | `payment_button_handler` | Added `has_active_subscription` |
| `start.py` | `progress_button_handler` | Added `has_active_subscription` |
| `start.py` | `start_quiz_button_handler` | Added `has_active_subscription` |
| `quiz.py` | `command_quiz` | Added `has_active_subscription` |
| `quiz.py` | `start_quiz_flow` | Added `has_active_subscription` |
| `quiz.py` | `select_difficulty` | Added `has_active_subscription` |
| `quiz.py` | `try_again_quiz` | Added `has_active_subscription` |
| `progress.py` | `command_progress` | Added `has_active_subscription` |
| `progress.py` | `progress_overview_callback` | Added `has_active_subscription` |
| `progress.py` | `daily_progress_callback` | Added `has_active_subscription` |
| `progress.py` | `weak_areas_callback` | Added `has_active_subscription` |
| `progress.py` | `learning_recommendations_callback` | Added `has_active_subscription` |
| `progress.py` | `learning_path_callback` | Added `has_active_subscription` |
| `answers.py` | `handle_answer` | Added `has_active_subscription` |
| `answers.py` | `retry_same_quiz` | Added `has_active_subscription` |
| `answers.py` | `choose_different_chapter` | Added `has_active_subscription` |
| `answers.py` | `try_higher_difficulty` | Added `has_active_subscription` |

---

## Complete Code References

### Updated Files

1. **`scripts/sql_migration_safe.sql`** - Safe SQL migration script
2. **`scripts/run_migration.py`** - Python migration runner with safety checks
3. **`app/handlers/start.py`** - Fixed keyboard usage and handler signatures
4. **`app/handlers/quiz.py`** - Fixed handler signatures for quiz flow
5. **`app/handlers/answers.py`** - Fixed handler signatures for answer processing
6. **`app/handlers/progress.py`** - Fixed handler signatures for progress views

### Unchanged Files (Already Correct)

- `app/db/models.py` - Models already have all required columns defined
- `app/keyboards/menu.py` - Already provides both keyboard types
- `app/keyboards/quiz.py` - Already provides InlineKeyboardMarkup only

---

## Known Issues Resolved

### Issue: CommandStart got unexpected keyword argument 'deep'
**Error**: `CommandStart.__init__() got an unexpected keyword argument 'deep'`

**Cause**: `CommandStart(deep=True)` is not a valid parameter in Aiogram 3.x.

**Fix**: Changed `@router.message(CommandStart(deep=True))` to `@router.message(CommandStart())` in `app/handlers/start.py`.

---

## Testing Instructions

### 1. Database Migration Test
```bash
# Check current schema
python scripts/run_migration.py --verify

# Apply migrations
python scripts/run_migration.py

# Verify again
python scripts/run_migration.py --verify
```

### 2. Bot Startup Test
```bash
# Start the bot
python -m app.main

# Check for startup errors
# Look for: "Bot started" message
```

### 3. Command Tests
Send these commands to your bot:

| Command | Expected Behavior |
|---------|-------------------|
| `/start` | Should show ReplyKeyboard with menu options |
| `/quiz` | Should start quiz flow (check subscription) |
| `/progress` | Should show progress with subscription status |
| `/payment` | Should show payment options |
| Click "Start Quiz" button | Should start quiz flow properly |
| Click "Back to Menu" | Should use InlineKeyboard and work |

### 4. Error Checking
Monitor logs for these errors:
- `TelegramAPIError` - Keyboard type issue (FIXED)
- `TypeError: missing required argument` - Handler signature issue (FIXED)
- `ProgrammingError: Unknown column` - Database schema issue (RUN MIGRATION)

---

## Compatibility Notes

### Python 3.14
- All code uses Python 3.10+ syntax (no changes needed)
- Type hints are compatible

### Aiogram
- All handlers use proper Aiogram patterns
- Callback queries properly handled with `await callback.answer()`
- State management using FSMContext

### SQLAlchemy Async
- All database operations use async sessions
- Connection pooling configured properly
- `expire_on_commit=False` for performance

### MariaDB
- Column definitions use MariaDB-compatible syntax
- `IF NOT EXISTS` checks prevent duplicate errors
- Index creation uses conditional syntax

---

## Rollback Instructions

If issues occur, rollback with:

```sql
-- Remove added columns (run in MariaDB)
ALTER TABLE subscriptions DROP COLUMN IF EXISTS updated_at;
ALTER TABLE subscriptions DROP COLUMN IF EXISTS created_at;
ALTER TABLE user_progress DROP COLUMN IF EXISTS created_at;
ALTER TABLE user_progress DROP COLUMN IF EXISTS updated_at;
ALTER TABLE quiz_attempts DROP COLUMN IF EXISTS quiz_session_id;
ALTER TABLE payments DROP COLUMN IF EXISTS subscription_days;
ALTER TABLE payments DROP COLUMN IF EXISTS transaction_id;
ALTER TABLE payments DROP COLUMN IF EXISTS notes;
```

Then restore from your backup if needed.

---

## Support

For issues not covered here:
1. Check the bot logs in `app/bot.log`
2. Verify database schema with `--verify` flag
3. Test handlers individually using the Command Tests above

