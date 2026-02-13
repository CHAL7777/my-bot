# Quiz Buttons Fix Plan

## Issues Identified:
1. **Markdown Parsing Error**: "can't parse entities: Can't find end of the entity" - caused by unescaped special characters in subject names, chapter names, question text
2. **"Weak Areas" button** - Uses wrong keyboard (MainMenuKeyboard instead of QuizKeyboard)
3. **"Recommendations" button** - Uses wrong keyboard (MainMenuKeyboard instead of QuizKeyboard)
4. **"Try Again" button** - Handler exists but doesn't restore quiz settings properly

## Root Cause Analysis:
- Dynamic content like subject names, chapter names, and question text contain special characters (underscores, asterisks, parentheses, etc.)
- Telegram Markdown interprets these as formatting, causing "can't parse entities" errors
- Need to use `escape_markdown_content()` for all dynamic content

## Files to Fix:
1. `app/handlers/quiz.py` - Fix escaping in `show_weak_areas`, `get_recommendations`, `finish_quiz`, `try_again_quiz`
2. `app/handlers/progress.py` - Fix escaping and keyboard usage in `weak_areas_callback`
3. `app/keyboards/quiz.py` - Add proper back navigation to quiz results

## Implementation Steps:

### Step 1: Fix show_weak_areas in quiz.py
- Add `escape_markdown_content()` for subject names, chapter names, difficulty
- Change keyboard from `MainMenuKeyboard.get_main_menu_inline()` to `QuizKeyboard.get_weak_areas_keyboard()`

### Step 2: Fix get_recommendations in quiz.py
- Add `escape_markdown_content()` for all text
- Add proper back navigation to quiz results

### Step 3: Fix finish_quiz in quiz.py
- Add `escape_markdown_content()` for all dynamic content
- Ensure keyboard provides proper back navigation

### Step 4: Fix try_again_quiz in quiz.py
- Add proper difficulty selection after clearing state
- Use `MainMenuKeyboard.get_difficulty_keyboard()` with stored subject_id, chapter_id

### Step 5: Fix weak_areas_callback in progress.py
- Add `escape_markdown_content()` for all text
- Use `QuizKeyboard.get_weak_areas_keyboard()` for proper navigation

## Testing:
- [ ] Test "Start Quiz" button starts quiz flow
- [ ] Test "Weak Areas" shows weak areas with proper escaping
- [ ] Test "Recommendations" shows recommendations with proper escaping
- [ ] Test "Try Again" button works correctly
- [ ] Verify no Markdown parsing errors

