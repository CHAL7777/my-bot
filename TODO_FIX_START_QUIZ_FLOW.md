# TODO: Fix start_quiz_flow() argument mismatch

## Problem (FIXED)
Error: `start_quiz_flow() takes 3 positional arguments but 4 were given`

## Root Cause (FIXED)
- Function `start_quiz_flow()` in `quiz.py` was defined with 3 parameters
- Callers in `answers.py`, `start.py` were passing 4 arguments including `safe_sender`
- Callers in `start_fixed.py` were passing `access_result` instead of `user_id`

## Files Edited
1. ✅ `app/handlers/quiz.py` - Updated function signature to accept optional parameters
2. ✅ `app/handlers/answers.py` - Fixed `start_quiz_flow` call at line 555
3. ✅ `app/handlers/start.py` - Fixed all `start_quiz_flow` calls
4. ✅ `app/handlers/start_fixed.py` - Fixed all `start_quiz_flow` calls

## Fix Applied (COMPLETED)
Updated `start_quiz_flow()` to accept:
- `update`: types.Update or Message
- `state`: FSMContext
- `user_id`: int
- `safe_sender`: Optional[PlainTextMessageSender] = None (auto-created if not provided)
- `quick_mode`: Optional[bool] = False

All callers now use consistent signature:
- `await start_quiz_flow(message, state, user_id)` 
- or `await start_quiz_flow(callback, state, user_id, quick_mode=True)`

## Note: New Issue
After fixing the argument mismatch, a new issue appeared:
- "Update is not handled" for `subject_` callbacks

This is a separate routing issue unrelated to the argument fix and needs further investigation.

