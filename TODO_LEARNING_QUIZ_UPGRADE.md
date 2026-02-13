# Learning Quiz Implementation - TODO

## Task
Upgrade existing `/quiz` command to implement learning-focused quiz with "Check & Reveal" pattern.

## Requirements
1. **QUESTION PHASE**: Send question with exactly 4 options (A, B, C, D) using InlineKeyboardButton
2. **LOCK PHASE (ANTI-SPAM)**: When user selects option, store selection, disable all buttons, show single "🧠 Check Answer → Learn Why" button
3. **REVEAL PHASE (MANDATORY LEARNING)**: Show ✅/❌, user's answer, correct answer, explanation
4. **AUTO-PROGRESSION**: Wait 1-2 seconds using asyncio.sleep, automatically load next question

## Files to Modify

### 1. `app/keyboards/quiz.py`
- [ ] Add `get_locked_option_keyboard()` - Shows selected option with "🧠 Check Answer → Learn Why"
- [ ] Add `get_reveal_result_keyboard()` - Shows result with disabled options

### 2. `app/handlers/quiz_fixed.py`
- [ ] Rewrite with 4-phase pattern
- [ ] Implement FSM states for quiz flow
- [ ] Handle answer selection (Phase 1 → 2)
- [ ] Handle "Check Answer" click (Phase 2 → 3)
- [ ] Implement auto-progression (Phase 3 → 4 → 1)
- [ ] Handle edge cases (expired callbacks, message not modified)

## Implementation Steps

### Step 1: Keyboard Methods
```python
def get_locked_option_keyboard(question_id: int, selected_option: str) -> InlineKeyboardMarkup:
    """Show selected option + 🧠 Check Answer → Learn Why button"""
    # Selected option gets ✓ marker
    # Unselected options disabled
    # Bottom button: 🧠 Check Answer → Learn Why

def get_reveal_result_keyboard(question_number: int, total_questions: int, 
                               is_correct: bool, selected_option: str, 
                               correct_option: str) -> InlineKeyboardMarkup:
    """Show result with explanation - single button for auto-progression"""
```

### Step 2: FSM States
```python
class QuizStates(StatesGroup):
    waiting_for_answer = State()  # Phase 1: User sees question
    locked_for_check = State()    # Phase 2: User selected, waiting for check
    viewing_explanation = State() # Phase 3: User seeing explanation
```

### Step 3: Quiz Flow
1. User sees question → `waiting_for_answer`
2. User clicks option → save selection, switch to `locked_for_check`
3. User clicks "🧠 Check Answer" → evaluate, show explanation → `viewing_explanation`
4. asyncio.sleep(1.5) → auto-next question → `waiting_for_answer`

## Edge Cases to Handle
- [ ] "message is not modified" errors (use safe_edit)
- [ ] Expired callbacks (quiz moved on)
- [ ] Double-clicks (ignore safely)
- [ ] Quiz completion (show results)

## Testing Checklist
- [ ] User can select only one option
- [ ] Selected option is locked (can't change)
- [ ] "🧠 Check Answer" button appears after selection
- [ ] Explanation is shown clearly
- [ ] User MUST see Correct/Incorrect
- [ ] Auto-progression happens after 1-2 seconds
- [ ] No "Next" button after explanation
- [ ] Quiz results shown at end

