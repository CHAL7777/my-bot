# TODO: Simple Quiz System Implementation

## Requirements:
1. 25 questions per round
2. Simple flow: Subject only (no chapter, no difficulty)
3. Continue with next 25 random questions (excluding previously answered)
4. Store answered question IDs per session
5. Performance optimized for large question sets
6. Motivational feedback (🎉 👏 🔥)

## Files to Modify:

### 1. app/repositories/question_repo.py
- [ ] Add `get_random_questions_optimized()` method
- [ ] Add `get_random_questions_excluding()` method (exclude answered IDs)
- [ ] Add `count_available_questions()` method

### 2. app/services/quiz_service.py
- [ ] Refactor to use subject-only selection
- [ ] Add session tracking with answered_question_ids
- [ ] Add `continue_quiz()` method for next 25 questions
- [ ] Add motivational message generation
- [ ] Add `can_continue()` check

### 3. app/handlers/quiz.py
- [ ] Remove chapter selection handlers
- [ ] Remove difficulty selection handlers
- [ ] Add subject-only selection flow
- [ ] Add `continue_quiz` handler
- [ ] Add `end_quiz` handler
- [ ] Update finish_quiz with motivational feedback

### 4. app/keyboards/quiz.py
- [ ] Add `get_continue_quiz_keyboard()` method
- [ ] Add `get_subject_only_keyboard()` method
- [ ] Simplify question keyboard

### 5. app/config.py (if needed)
- [ ] Update MAX_QUESTIONS_PER_QUIZ to 25
- [ ] Add any new settings

## Implementation Order:
1. question_repo.py - Database layer for random questions
2. quiz_service.py - Business logic
3. quiz_keyboard.py - UI components
4. quiz.py - Handlers

## Success Criteria:
- User selects subject → gets 25 random questions
- Questions don't repeat within session
- After 25 questions → show score + motivational message + Continue/End buttons
- Continue → loads next 25 (excluding answered)
- End → shows final summary and back to menu
- Performance: Fast random selection even with 1000+ questions

