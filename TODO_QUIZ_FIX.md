# Quiz Fix Plan

## Issues Identified

### 1. `app/handlers/quiz.py` - Incomplete `practice_weak_area` function
- **Issue**: Function ends mid-sentence at `await callback.answer("Invalid request",`
- **Fix**: Complete the function implementation

### 2. `app/handlers/quiz.py` - Type mismatch in `finish_quiz`
- **Issue**: `datetime.now() - start_time` but `start_time` is `time.time()` (epoch float)
- **Fix**: Use `time.time() - start_time` for consistent float calculation

## Files to Edit
1. `app/handlers/quiz.py`

## Implementation Steps
- [ ] 1. Fix `finish_quiz` time calculation (change datetime to time.time())
- [ ] 2. Complete `practice_weak_area` function
- [ ] 3. Verify syntax is correct

## Success Criteria
- [ ] No syntax errors in quiz.py
- [ ] Time tracking works correctly
- [ ] All quiz handlers function properly

