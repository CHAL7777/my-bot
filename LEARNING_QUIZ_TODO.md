# Learning Quiz Implementation Plan

## Objective
Upgrade existing quiz.py into a learning-first quiz experience without adding new handlers or changing routing structure.

## Current State Analysis

### Files to Modify:
1. `app/handlers/answers.py` - Add check handler, modify answer handler
2. `app/handlers/quiz.py` - Add auto-progress function
3. `app/keyboards/quiz.py` - Add new keyboard methods

### Existing Callbacks to Reuse:
- `answer_{question_id}_{option}` - For option selection
- `continue_quiz` - For continuation

### New Callbacks to Add (in same files):
- `check_{question_id}_{option}` - For "Check Answer → Learn Why"

## Implementation Steps

### Step 1: Add FSM State for Lock Phase
Add `selected_option` field to existing state management

### Step 2: Modify Question Sending (continue_quiz in quiz.py)
- Keep same message format
- Add `question_start_time` for timing

### Step 3: Add Option Selection Lock Handler (answers.py)
- Parse `answer_{question_id}_{option}`
- Store selected option in FSM
- Replace buttons with "Check Answer → Learn Why"

### Step 4: Add Check Answer Handler (answers.py)
- Parse `check_{question_id}_{option}`
- Evaluate correctness
- Show result + correct answer + explanation
- Edit same message

### Step 5: Add Auto-Progress Function (quiz.py)
- asyncio.sleep(1-2 seconds)
- Load next question
- No manual button needed

### Step 6: Add New Keyboard Methods (keyboards/quiz.py)
- `get_locked_keyboard()` - For lock phase
- `get_result_keyboard()` - For reveal phase

## Flow Diagram

```
User Sees Question (4 buttons A,B,C,D)
       ↓
User Clicks Option (answer_{qid}_{opt})
       ↓
LOCK PHASE:
- Store option in FSM
- Replace 4 buttons with 1:
  "Check Answer → Learn Why"
       ↓
User Clicks Check Button (check_{qid}_{opt})
       ↓
REVEAL PHASE:
- Show ✅/❌
- Show correct answer
- Show explanation
       ↓
AUTO-PROGRESS (1-2 sec delay):
- Load next question
- No manual action needed
```

## Key Rules
1. ❌ No speed-tapping through questions
2. ❌ No skipping explanations
3. ❌ No changing answers
4. ✅ Mandatory explanation
5. ✅ User sees correct/incorrect
6. ✅ Edit same message (no new messages)

## Files Modified
- [ ] app/handlers/answers.py
- [ ] app/handlers/quiz.py
- [ ] app/keyboards/quiz.py

