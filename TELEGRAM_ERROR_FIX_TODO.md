# Telegram Error Fix - Implementation TODO

## Phase 1: Core Utilities
- [x] Create comprehensive fix plan
- [ ] Create safe_edit.py utility module
- [ ] Add safe_edit_message function
- [ ] Add MessageEditGuard class
- [ ] Update telegram_utils.py with safe functions

## Phase 2: Quiz Handler Fixes  
- [ ] Fix app/handlers/quiz.py - add duplicate guards
- [ ] Fix select_subject callback
- [ ] Fix select_chapter callback  
- [ ] Fix select_difficulty callback
- [ ] Fix continue_quiz callback
- [ ] Fix finish_quiz function

## Phase 3: Answers Handler Fixes
- [ ] Fix app/handlers/answers.py - handle_answer
- [ ] Add state guard for duplicate prevention
- [ ] Use safe_edit_message for feedback

## Phase 4: Start Handler Fixes
- [ ] Fix app/handlers/start.py - inline_start_quiz_callback
- [ ] Add processing guard
- [ ] Use safe_edit_message

## Phase 5: Bot Instance Management
- [ ] Add instance lock file in bot.py
- [ ] Add signal handlers for graceful shutdown
- [ ] Prevent multiple polling instances

## Phase 6: Testing & Validation
- [ ] Test safe_edit_message function
- [ ] Verify no "message is not modified" errors
- [ ] Test duplicate click prevention
- [ ] Test single instance enforcement

## Files to Modify
1. app/utils/safe_edit.py (NEW)
2. app/utils/telegram_utils.py (UPDATE)
3. app/handlers/quiz.py (UPDATE)
4. app/handlers/answers.py (UPDATE)  
5. app/handlers/start.py (UPDATE)
6. app/bot.py (UPDATE)
7. app/handlers/progress.py (UPDATE)
8. app/handlers/payment.py (UPDATE)

