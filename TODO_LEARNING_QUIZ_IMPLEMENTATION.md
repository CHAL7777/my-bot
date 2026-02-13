# TODO: Learning Quiz Implementation - 4 Phase Pattern

## Implementation Steps

### Step 1: Update Keyboard Methods (`app/keyboards/quiz.py`)
- [x] 1.1 Add `get_reveal_result_keyboard()` - Shows result with explanation, single button for auto-progression
- [x] 1.2 Enhance `get_locked_option_keyboard()` - Ensure proper callback data format (already exists)
- [x] 1.3 Add helper function to format options with markers (✅/❌) (already exists in get_marked_result_keyboard)

### Step 2: Update Quiz Handler FSM (`app/handlers/quiz.py`)
- [x] 2.1 Add new FSM states:
  - `waiting_for_answer` - Phase 1: User sees question
  - `locked_for_check` - Phase 2: User selected, waiting for check
  - `viewing_explanation` - Phase 3: User seeing explanation

### Step 3: Create Learning Quiz Handlers (`app/handlers/learning_quiz_handlers.py`)
- [x] 3.1 Add `handle_answer_select` - Phase 1→2: Lock selection, show "🧠 Check Answer"
- [x] 3.2 Add `handle_check_answer` - Phase 2→3: Evaluate, show explanation
- [x] 3.3 Add `_auto_next_question` - Phase 3→4→1: Auto-progression with asyncio.sleep(1.5)
- [x] 3.4 Add `handle_auto_next` - Manual fallback for auto-progress
- [x] 3.5 Add `handle_locked_noop` - Handle disabled button clicks
- [x] 3.6 Add `handle_explanation_noop` - Handle disabled button clicks during explanation
- [x] 3.7 Add `cancel_quiz_learning` - Cancel quiz during learning flow

### Step 4: Register New Handlers
- [x] 4.1 Add `learning_quiz_router` to `app/handlers/__init__.py`
- [x] 4.2 Register router in `app/bot.py` setup_handlers()

### Step 5: Edge Cases Handled
- [x] 5.1 "message is not modified" errors - Handled with try/except
- [x] 5.2 Expired callbacks - Check state before processing
- [x] 5.3 Double-clicks - Guard with answered_questions check
- [x] 5.4 Quiz completion - Calls finish_quiz when all questions answered

## Quiz Flow (4 Phases)

```
Phase 1 (waiting_for_answer):
  User sees question with 4 options (A, B, C, D)
  User clicks an option

Phase 2 (locked_for_check):
  Selected option is locked (✓ marker)
  Other options disabled
  "🧠 Check Answer → Learn Why" button appears
  User clicks the button

Phase 3 (viewing_explanation):
  Shows ✅/❌ for correct/incorrect
  Shows user's answer and correct answer
  Shows explanation (if available)
  Shows score update
  Auto-progress after 1.5 seconds

Phase 4 (auto-progress):
  Loads next question
  Returns to Phase 1
```

## File Changes Summary

### `app/keyboards/quiz.py`
- Added `get_reveal_result_keyboard()` method for Phase 3 display

### `app/handlers/quiz.py`
- Added FSM states: `waiting_for_answer`, `locked_for_check`, `viewing_explanation`

### `app/handlers/learning_quiz_handlers.py` (NEW FILE)
- Complete learning quiz flow implementation
- Auto-progression with 1.5 second delay
- Proper state management

### `app/handlers/__init__.py`
- Added import for `learning_quiz_handlers.router`

### `app/bot.py`
- Added `learning_quiz_handlers.router` to handler registration

## Testing Checklist
- [ ] User can select only one option
- [ ] Selected option is locked (can't change)
- [ ] "🧠 Check Answer" button appears after selection
- [ ] Explanation is shown clearly
- [ ] User MUST see Correct/Incorrect
- [ ] Auto-progression happens after 1-2 seconds
- [ ] No "Next" button after explanation (auto-progress)
- [ ] Quiz results shown at end

