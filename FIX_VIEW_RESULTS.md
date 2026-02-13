# Fix Plan: View Results Not Working After Quiz Completion

## Issue Analysis
The "View Results" functionality is broken because:
1. **Duplicate handlers**: `view_results` callback is handled in multiple places
2. **Circular calls**: `view_quiz_results` handler calls `finish_quiz` which tries to re-display results
3. **State cleared prematurely**: FSM state is cleared before results can be viewed

## Files to Edit
1. `app/handlers/answers.py` - Fix `view_quiz_results` handler
2. `app/handlers/quiz.py` - Ensure `finish_quiz` saves quiz_session_id for later retrieval
3. `app/repositories/attempt_repo.py` - Verify `get_quiz_session_attempts` works correctly

## Fix Steps

### Step 1: Fix `view_quiz_results` in `answers.py`
- Remove the circular call to `finish_quiz`
- Create a dedicated handler that retrieves quiz details from database
- Show results without clearing state (state should already be cleared by finish_quiz)

### Step 2: Ensure `finish_quiz` saves quiz_session_id for later retrieval
- Store quiz_session_id in user data for later reference
- Use AttemptRepository to fetch quiz session attempts

### Step 3: Verify `quiz_details_` handler works
- Ensure it can retrieve quiz session details after state is cleared

## Execution Order
1. Edit `app/handlers/answers.py` - Fix view_quiz_results handler
2. Edit `app/handlers/quiz.py` - Ensure finish_quiz saves quiz_session_id properly
3. Test the fix

