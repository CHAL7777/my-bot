# TODO: Interactive Quiz Bot Upgrade

## Phase 1: Message Templates & Service Creation
- [x] Create TODO file and plan
- [x] Create `app/utils/feedback_messages.py` - Message templates for celebrations, encouragement, and end-of-quiz
- [x] Create `app/services/feedback_service.py` - Service for random message selection, streak tracking, progress calculation

## Phase 2: Update Constants
- [x] Update `app/utils/constants.py` - Add new emojis (🎉👏🔥💡🌟⭐🚀💪📚)

## Phase 3: Update Answer Handler
- [x] Update `app/handlers/answers.py`:
  - [x] Add dynamic celebration/encouragement messages
  - [x] Show current score & progress after each question
  - [x] Track and display streaks
  - [x] Add motivational phrases

## Phase 4: Update Quiz Handler
- [x] Update `app/handlers/quiz.py`:
  - [x] Add enhanced quiz start celebration message
  - [x] Enhance finish_quiz with celebratory messages based on performance
  - [x] Add detailed performance feedback

## Phase 5: Update Quiz Keyboard
- [ ] Update `app/keyboards/quiz.py`:
  - [ ] Add progress display (question X of Y)
  - [ ] Add score display in feedback keyboard

## Phase 6: Testing
- [ ] Test quiz flow with new feedback
- [ ] Verify streak tracking works
- [ ] Verify end-of-quiz celebrations match performance

## Implementation Order:
1. [x] Create feedback_messages.py (templates)
2. [x] Create feedback_service.py (logic)
3. [x] Update constants.py (emojis)
4. [x] Update answers.py (main feedback loop)
5. [x] Update quiz.py (start/end enhancements)
6. [ ] Update quiz keyboard (progress display)

## Key Features Being Added:
- ✅ Randomized celebration messages for correct answers
- ✅ Encouraging messages for wrong answers (no shaming!)
- ✅ Streak tracking and display
- ✅ Progress and score after each question
- ✅ Performance-based end-of-quiz celebrations
- ✅ Emojis throughout for visual appeal

