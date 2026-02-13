# TODO: Fix "Select a Subject" Callback Not Handled

## Problem
```
2026-02-03 11:39:52,542 - app.webhook_main - INFO - Processing update 702093051
2026-02-03 11:39:52,573 - aiogram.event - INFO - Update id=702093051 is not handled. Duration 30 ms by bot id=8311608555
```

The `subject_` callback is not being handled when user clicks on a subject after "Start Quiz" is clicked.

## Root Cause Analysis
1. The `select_subject` handler in `quiz.py` had a strict state filter `QuizStates.selecting_subject`
2. The state might not be properly set before the callback is processed
3. The handler filters were too restrictive

## Fix Applied - COMPLETED ✅
- [x] 1. Fixed `inline_start_quiz_callback` in `start.py` - clear state before calling `start_quiz_flow`
- [x] 2. Removed strict state filter from `select_subject` handler in `quiz.py`
- [x] 3. Handler now verifies state INSIDE the function and re-initializes if needed
- [x] 4. Added logging for debugging state transitions

## Files Edited
1. `app/handlers/start.py` - Fixed `inline_start_quiz_callback` to clear state before flow
2. `app/handlers/quiz.py` - Removed `QuizStates.selecting_subject` filter from `select_subject` decorator

## Key Changes

### start.py
```python
# Before: State was set BEFORE calling start_quiz_flow, causing it to skip sending message
await state.set_state(QuizStates.selecting_subject)  
await start_quiz_flow(callback, state, user_id)  # Message never sent!

# After: Clear state, let start_quiz_flow set it and send message
current_state = await state.get_state()
if current_state is not None:
    logger.info(f"[QUIZ] Clearing existing state {current_state} for user {user_id}")
    await state.clear()
await start_quiz_flow(callback, state, user_id)  # Now sends message correctly
```

### quiz.py
```python
# Before: Strict state filter - handler only fires if state is EXACTLY selecting_subject
@router.callback_query(F.data.startswith("subject_"), QuizStates.selecting_subject)
async def select_subject(...):

# After: Removed filter - handler fires for ALL subject_ callbacks
# State is verified INSIDE the function
@router.callback_query(F.data.startswith("subject_"))
async def select_subject(...):
    # Check state inside and re-initialize if needed
    current_state = await state.get_state()
    if current_state != QuizStates.selecting_subject:
        logger.warning(...)
        await start_quiz_flow(callback, state, user_id)  # Re-init
        return
    # ... rest of handler
```

## Why This Fix Works
1. **State is set AFTER sending message**: `start_quiz_flow` now sends the message BEFORE setting the state
2. **Handler always fires**: The `subject_` callback pattern now matches all subject buttons
3. **Graceful recovery**: If state is lost (Redis timeout), the handler re-initializes the flow
4. **Better logging**: Debug logs help identify state issues in production

