# Referral Test Fix Plan

## Issues Identified

1. **Import Chain Failure**: When `app.handlers.referral` fails to import (due to `asyncpg`), `MainMenuKeyboard` is not available
2. **Missing Direct Import**: Test should import `MainMenuKeyboard` directly from `app.keyboards.menu`
3. **Graceful Degradation**: Test should handle import failures and still verify keyboard structure

## Fix Plan

### Step 1: Update `test_referral_buttons.py`
- Import `MainMenuKeyboard` directly from `app.keyboards.menu`
- Handle import failures gracefully
- Add fallback mock data for testing keyboard structure
- Test keyboard callbacks without database dependencies

### Step 2: Create `app/keyboards/__init__.py` Exports
- Export `MainMenuKeyboard` from `app.keyboards.__init__.py` for easier imports
- This follows Python best practices for package-level exports

## Files to Modify

1. `/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot/test_referral_buttons.py` - Fix import and test logic
2. `/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot/app/keyboards/__init__.py` - Add exports

## Implementation Steps

1. Update test imports to use direct import of `MainMenuKeyboard`
2. Add try/except blocks for all import statements
3. Test keyboard callbacks independently of database
4. Add keyboard structure verification tests
5. Update exports in `app/keyboards/__init__.py`

## Expected Result

After fixes:
- Test 1: Basic imports successful (keyboard imported separately)
- Test 2: Keyboard callback data verified
- Test 3: Handler signatures verified (with graceful handling of missing modules)
- Test 4: Message building verified (with mock data)

