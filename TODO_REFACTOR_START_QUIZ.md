# TODO: Refactor start_quiz to share logic between inline and normal handlers

## Issues Identified:
1. `start_quiz_flow` uses direct SQL queries instead of `can_access_premium()` single source of truth
2. Keyboard type mismatch - uses ReplyKeyboard when called from inline callbacks
3. No unified message handling for Message vs CallbackQuery.message
4. Duplicate access checks causing contradictions

## Plan:
- [x] 1. Create `start_quiz_logic()` in `quiz.py` - shared function with:
  - [x] Detects if it's Message or CallbackQuery and responds appropriately
  - [x] Uses `can_access_premium()` for consistent access checking
  - [x] Uses correct keyboard type (ReplyKeyboard for Message, InlineKeyboard for callback)
  
- [x] 2. Refactor `start_quiz_flow` to call `start_quiz_logic()` and handle message sending
- [x] 3. Update `start_quiz_button_handler` in `start.py` to use shared logic
- [x] 4. Update `inline_start_quiz_callback` in `start.py` to use shared logic
- [x] 5. Update `try_again_quiz` in `quiz.py` to use new signature

## Files Modified:
- `app/handlers/quiz.py` - Core logic changes
- `app/handlers/start.py` - Handler updates

## Summary of Changes:

### `app/handlers/quiz.py`:
1. Added imports for `Message`, `CallbackQuery` and `can_access_premium`
2. Created `start_quiz_logic()` function - the SINGLE SOURCE OF TRUTH for quiz access:
   - Accepts either `Message` or `CallbackQuery` as input
   - Uses `can_access_premium()` from `access_control_service.py` for consistent access checking
   - Returns a dict with `allowed`, `access_denied_message`, `use_inline_keyboard`, `error`
3. Created helper functions `_send_quiz_access_denied()` and `_send_quiz_subjects()`:
   - Automatically use `edit_text()` for callbacks and `answer()` for messages
   - Use correct keyboard type based on context
4. Refactored `start_quiz_flow()` to:
   - Accept either `Message` or `CallbackQuery`
   - Call `start_quiz_logic()` for access checking
   - Delegate message sending to helper functions

### `app/handlers/start.py`:
1. Updated `start_quiz_button_handler()`:
   - Removed `has_active_subscription` parameter (not needed anymore)
   - Now passes `Message` directly to `start_quiz_flow()`
2. Updated `inline_start_quiz_callback()`:
   - Removed `has_active_subscription` parameter
   - Removed duplicate access check (now handled in shared logic)
   - Now passes `CallbackQuery` directly to `start_quiz_flow()`
   - Access check and appropriate response is handled by shared logic

### Architecture (New Flow):
```
Message (Start Quiz button)
        ↓
start_quiz_flow(message, state)
        ↓
start_quiz_logic() 
        ↓
can_access_premium() → allowed?
        ↓
_send_quiz_subjects() → answer() with InlineKeyboard
```

```
CallbackQuery (Start Quiz inline button)
        ↓
start_quiz_flow(callback, state)
        ↓
start_quiz_logic()
        ↓
can_access_premium() → allowed?
        ↓
_send_quiz_subjects() → edit_text() with InlineKeyboard
```

Both handlers now use IDENTICAL logic with the only difference being the message delivery method.

