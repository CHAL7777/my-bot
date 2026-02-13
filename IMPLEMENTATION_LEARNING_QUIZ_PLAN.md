# Learning-Focused Quiz UX Implementation Plan

## 📋 Project Overview
Transform the existing Telegram quiz bot into a **learning-first** experience that prevents blind clicking and forces explanation engagement.

## 🎯 Required Quiz Flow (STRICT)

### Phase 1: Question & Options
- Send ONE question per message
- Show exactly 4 answer options (A, B, C, D) using `InlineKeyboardButton`
- Single-choice only via inline buttons (NO reply keyboard)
- Clicking option does NOT show correctness immediately

### Phase 2: Answer Selection (Lock Phase)
- When user selects option:
  - Store selected option internally
  - Disable all option buttons (user cannot change answer)
  - Replace options with ONE button: `🧠 Check Answer → Learn Why`
- Do NOT evaluate answer yet
- Handle double-clicks safely

### Phase 3: Check & Reveal (Learning Phase)
- When user clicks `🧠 Check Answer → Learn Why`:
  - Evaluate correctness
  - Edit SAME message (do NOT send new one)
  - Display:
    - ✅ Correct OR ❌ Incorrect
    - The correct option
    - Short, clear explanation (learning-focused)
  - **Explanation MUST be shown before moving forward**

### Phase 4: Auto Progression (No Next Button)
- After showing explanation:
  - Wait 1-2 seconds (`asyncio.sleep`)
  - Automatically load next question
  - **NO "Next" button**
  - **NO manual skipping**

## 🎨 UX Rules (VERY IMPORTANT)
- Zero message spam
- Prefer `edit_message_text` / `edit_reply_markup`
- Buttons must feel intentional & premium
- Force user to see explanation
- Prevent speed-tapping behavior
- Gracefully handle expired callbacks

## 🗄️ Data Storage (SQLite)
Persist each attempt with:
- `user_id`
- `question_id`
- `selected_option`
- `is_correct`
- `timestamp`

Rules:
- One attempt per question
- Ignore duplicate submissions safely

## 📁 Files to Create/Modify

### 1. NEW: `app/handlers/learning_quiz.py`
Main quiz handler with learning-focused UX.

**Functions:**
- `send_question()` - Display question with options
- `select_option()` - Handle initial option selection (lock phase)
- `check_answer()` - Evaluate and show correctness + explanation
- `show_explanation()` - Display learning content
- `next_question()` - Auto-progress to next question

### 2. UPDATE: `app/keyboards/quiz.py`
Add learning-specific keyboard methods.

**New Methods:**
- `get_learning_question_keyboard()` - Question with A, B, C, D options
- `get_locked_answer_keyboard()` - Selected option + "Check Answer" button
- `get_result_keyboard()` - Result with explanation (auto-progress)
- `get_expired_keyboard()` - Handle expired callbacks

### 3. UPDATE: `app/repositories/attempt_repo.py`
Add learning-specific attempt method.

**New Methods:**
- `create_learning_attempt()` - Create attempt for learning quiz

### 4. UPDATE: `app/bot.py`
Register the new learning quiz handler.

## 🔧 Implementation Details

### Callback Data Pattern
```
answer_{question_id}_{option}    → User selects option (A, B, C, D)
check_{question_id}_{option}     → User clicks "Check Answer → Learn Why"
noop_{question_id}_{option}      → Disabled button click
expired                          → Expired callback
```

### State Management
Use FSM with these states:
- `QuizStates.learning_selection` - Selecting answer option
- `QuizStates.learning_check` - Waiting to check answer
- `QuizStates.learning_explanation` - Viewing explanation

### Message Flow
```
1. User sees: Question + 4 options (A, B, C, D)
   ↓ (clicks option)
2. User sees: Question + 4 options (disabled) + "🧠 Check Answer → Learn Why"
   ↓ (clicks "Check Answer")
3. User sees: Result + Correct Answer + Explanation
   ↓ (2 second delay)
4. Auto-progress to next question
```

## ✅ Quality Checklist
- [ ] Use async/await correctly throughout
- [ ] Handle all callback edge cases (expired, duplicate, etc.)
- [ ] Edit same message (no new messages)
- [ ] Force explanation display before progression
- [ ] No "Next" button - automatic progression
- [ ] SQLite persistence for all attempts
- [ ] Webhook-safe (no blocking code)
- [ ] Production-ready error handling
- [ ] Well-commented code

## 🚀 Next Steps
1. Create `app/handlers/learning_quiz.py`
2. Update `app/keyboards/quiz.py` with new keyboard methods
3. Update `app/repositories/attempt_repo.py`
4. Register handler in `app/bot.py`
5. Test the complete flow

