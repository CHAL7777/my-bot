# Fix Quiz Buttons - TODO List

## Issues Identified:
1. "View Details" button uses `learn_details_{quiz_session_id}` callback - NO HANDLER
2. "Try Again" button uses `learn_retry` callback - NO HANDLER  
3. "Weak Areas" button shows wrong navigation (main menu instead of quiz results)
4. "Recommendations" button shows wrong navigation (main menu instead of quiz results)

## Fix Plan:

### Step 1: Add missing handler for `learn_details_{quiz_session_id}`
- [ ] Add handler in `app/handlers/quiz.py` that handles `learn_details_` prefix
- [ ] Should reuse existing `_display_question_for_review` function
- [ ] Use proper quiz results keyboard

### Step 2: Add missing handler for `learn_retry`
- [ ] Add handler in `app/handlers/quiz.py` for `learn_retry` callback
- [ ] Should restore quiz settings from state and restart

### Step 3: Fix `show_weak_areas` handler
- [ ] Change from `MainMenuKeyboard.get_main_menu_inline()` to `QuizKeyboard.get_quiz_results_keyboard()`
- [ ] Add quiz_session_id parameter to return to quiz results

### Step 4: Fix `get_recommendations` handler
- [ ] Change from `MainMenuKeyboard.get_main_menu_inline()` to `QuizKeyboard.get_quiz_results_keyboard()`
- [ ] Add quiz_session_id parameter to return to quiz results

### Step 5: Fix `try_again` handler
- [ ] Update to properly restore subject_id, chapter_id, difficulty from state
- [ ] Use MainMenuKeyboard.get_difficulty_keyboard() for difficulty selection
- [ ] Add navigation back to quiz results

## Files to Modify:
- `app/handlers/quiz.py` - Add missing handlers and fix existing ones

## Testing:
- [ ] Test "View Details" button shows question review
- [ ] Test "Try Again" button restarts quiz with same settings
- [ ] Test "Weak Areas" shows weak areas and navigates back to results
- [ ] Test "Recommendations" shows recommendations and navigates back to results

