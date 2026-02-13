# Production Bot Fixes - Implementation Guide

This document describes the fixes applied to make the Telegram quiz bot production-ready.

## Summary of Changes

### 1. Subscription Middleware (`app/middlewares/subscription.py`)

**Problem**: The middleware was blocking ALL users including those who hadn't completed the payment flow.

**Solution**:
- Added `ALLOWED_COMMANDS` list: `/start`, `/help`, `/about`, `/contact`, `/payment`, `/approve`, `/admin`, `/cancel`
- Added `NAVIGATION_CALLBACKS` for non-quiz navigation
- Added `is_command_allowed()` function to check commands
- Added `is_navigation_callback()` function to check callbacks
- Improved `ACCESS_DENIED_MESSAGE` with clear instructions:
  - Explains how to get approved
  - Provides step-by-step payment flow
  - Includes contact information for help
- Added `get_handler_name()` function for proper logging
- Added `auto_approve_if_payment_completed()` function for streamlining approval

**Key Changes**:
```python
# Before: Only basic commands allowed
if message_text.startswith('/start') or message_text.startswith('/help'):

# After: Comprehensive command checking
if is_command_allowed(message_text):
    # Allow command without approval check
```

### 2. Safe Admin Notifications (`app/utils/helpers.py`)

**Problem**: Admin notifications with special characters caused "can't parse entities" errors.

**Solution**:
- Added `escape_markdown()` function (already existed, now properly used)
- Added `safe_admin_message()` function with:
  - Automatic Markdown escaping
  - Fallback to plain text on parse errors
  - Comprehensive error handling
- Added `notify_admin()` for single admin notifications
- Added `notify_all_admins()` for bulk notifications

**Key Changes**:
```python
# Before: Direct send (prone to parse errors)
await bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')

# After: Safe sending with escaping and fallback
await safe_admin_message(
    bot=bot,
    chat_id=admin_id,
    text=message,
    parse_mode='Markdown'
)
```

### 3. UX Improvements

**Problem**: Users didn't understand why they were denied access.

**Solution**:
- Updated `ACCESS_DENIED_MESSAGE` to include:
  - Clear explanation of why access is restricted
  - Step-by-step guide to getting approved
  - Expected processing time
  - How to contact admins for help

### 4. Handler Name Logging

**Problem**: Handler names showed as "unknown" in logs.

**Solution**:
- Added `get_handler_name()` function that:
  - Uses Python's inspect module to unwrap decorated functions
  - Falls back gracefully if inspection fails
  - Returns class name for aiogram handlers

## Best Practices Applied

### 1. Always Respond to User Commands
```python
# Middleware ensures /start always responds
if is_command_allowed(message_text):
    return await handler(event, data)
```

### 2. Provide Clear Error Messages
```python
ACCESS_DENIED_MESSAGE = (
    "❌ *Access Restricted*\n\n"
    "📚 To take quizzes, you need an approved account.\n\n"
    "💰 *How to Get Approved:*\n\n"
    "1️⃣ Use /payment to get payment instructions\n"
    "2️⃣ Complete your payment\n"
    "3️⃣ Send your payment screenshot to this chat\n"
    "4️⃣ Wait for admin to verify and approve you\n\n"
    "⏳ *Processing Time:*\n"
    "Admins typically review within 24 hours.\n\n"
    "💡 *Need Help?* Use /contact to message admins."
)
```

### 3. Safe Message Sending
```python
async def safe_admin_message(bot, chat_id, text, parse_mode="Markdown", **kwargs):
    """Send message with proper escaping and error handling."""
    try:
        # Escape Markdown characters
        if parse_mode in ("Markdown", "MarkdownV2"):
            text = escape_markdown(text)
        
        # Try sending with Markdown
        return await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, **kwargs)
    except TelegramBadRequest:
        # Fallback to plain text
        return await bot.send_message(chat_id=chat_id, text=text, parse_mode=None, **kwargs)
```

### 4. Fail Securely
```python
except Exception as e:
    logger.error(f"Middleware error: {e}")
    # Deny access on error rather than allowing it
    data['can_access_quiz'] = False
```

## Files Modified

1. **`app/middlewares/subscription.py`**
   - Added helper functions for command/callback checking
   - Updated ACCESS_DENIED_MESSAGE with clear instructions
   - Improved handler name logging
   - Added auto-approve function

2. **`app/utils/helpers.py`**
   - Added `safe_admin_message()` function
   - Added `notify_admin()` function
   - Added `notify_all_admins()` function
   - Enhanced error handling

## Deployment Instructions

### 1. Backup Existing Files
```bash
cp app/middlewares/subscription.py app/middlewares/subscription.py.bak
cp app/utils/helpers.py app/utils/helpers.py.bak
```

### 2. Apply Changes
The files have been updated. No additional steps needed.

### 3. Restart the Bot
```bash
# If using systemctl
sudo systemctl restart telegram-quiz-bot

# If using docker
docker restart telegram-quiz-bot

# If using python directly
pkill -f "python.*main.py"
python main.py &
```

### 4. Verify the Fixes

Test these scenarios:
1. ✅ New user can run `/start`
2. ✅ New user can run `/payment`
3. ✅ New user can run `/help` and `/about`
4. ✅ Unapproved user sees clear instructions when trying quiz
5. ✅ Admin notifications don't crash with special characters
6. ✅ Logs show correct handler names

## Monitoring

After deployment, check the logs for:
```bash
tail -f logs/bot.log | grep "[AUTH]"
```

You should see:
- `[AUTH] User X | Handler: command_start | RESULT: COMMAND_ALLOWED` for allowed commands
- `[AUTH] User X | Handler: select_difficulty | RESULT: NOT_APPROVED` for denied quiz access

## Rollback Plan

If issues occur, rollback:
```bash
cp app/middlewares/subscription.py.bak app/middlewares/subscription.py
cp app/utils/helpers.py.bak app/utils/helpers.py
restart_bot
```

## Additional Recommendations

### 1. Add Health Check Endpoint
For webhook deployment, add to `app/webapp.py`:
```python
@app.get("/health")
async def health_check():
    return {"status": "ok", "bot": "running"}
```

### 2. Monitor Error Rates
Set up alerts for:
- High rate of "can't parse entities" errors
- High rate of middleware errors
- Users repeatedly denied access

### 3. Regular Database Maintenance
```sql
-- Check for users with inconsistent states
SELECT * FROM users WHERE is_premium = 1 AND approved = 0;

-- Check for blocked users trying to access
SELECT * FROM users WHERE blocked = 1;
```

## Support

For issues or questions, check:
1. `logs/bot.log` for detailed error messages
2. `app/middlewares/subscription.py` for authorization logic
3. `app/utils/helpers.py` for notification utilities

