# Learning-Focused Quiz Implementation - TODO List

## Phase 1: Keyboard Updates (`app/keyboards/quiz.py`)
- [ ] Add `get_learning_question_keyboard()` - Question with A, B, C, D options
- [ ] Add `get_locked_answer_keyboard()` - Selected option + "Check Answer" button
- [ ] Add `get_result_keyboard()` - Result with explanation (auto-progress)

## Phase 2: Repository Updates (`app/repositories/attempt_repo.py`)
- [ ] Add `create_learning_attempt()` - Create attempt for learning quiz

## Phase 3: Handler Updates (`app/handlers/learning_quiz.py`)
- [ ] Create the learning-focused quiz handler with proper flow
- [ ] Ensure callback patterns are correct: `answer_{id}_X`, `check_{id}_X`
- [ ] Implement auto-progression after explanation

## Phase 4: Registration Updates
- [ ] Update `app/handlers/__init__.py` to export learning_quiz router
- [ ] Update `app/bot.py` to register learning_quiz.router

## Phase 5: Testing
- [ ] Test the complete flow: Question → Selection → Check → Explanation → Auto-next
- [ ] Verify no message spam (same message edited)
- [ ] Verify explanation forced before progression
- [ ] Verify duplicate callback handling

## Key Requirements
✅ Send ONE question per message
✅ Show exactly 4 answer options (A, B, C, D)
✅ Clicking option does NOT show correctness immediately
✅ Disable all buttons after selection
✅ Replace with "🧠 Check Answer → Learn Why" button
✅ Evaluate only when "Check Answer" clicked
✅ Edit SAME message (no new messages)
✅ Show ✅/❌, correct option, and explanation
✅ Wait 1-2 seconds, then auto-progress
✅ NO "Next" button
✅ SQLite persistence

