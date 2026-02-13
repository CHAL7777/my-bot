# TODO: Inline Referral Keyboard Fix

## Problem
- Error: "MESSAGE_TOO_LONG" when sending referral keyboard
- The Telegram share URL exceeds Telegram's 2048 character limit
- Update ID not being handled

## Solution
1. Shorten the share text in referral keyboard
2. Use URL-shortened referral link
3. Add error handling for unhandled updates
4. Add try-except wrapper for message sending

## Files to Modify
1. `app/keyboards/menu.py` - Fix get_referral_keyboard() to use shorter text
2. `app/webhook_main.py` - Add error handling for unhandled updates
3. `app/handlers/referral.py` - Add error handling

## Steps
- [ ] 1. Shorten referral share text
- [ ] 2. Add URL shortening support
- [ ] 3. Add error handling in webhook_main.py
- [ ] 4. Test the fix

