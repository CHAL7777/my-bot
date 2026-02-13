# TODO: back_to_chapters Function Update

## Plan Status: Approved

## Steps to Complete:
- [x] 1. Read and understand the current `back_to_chapters` function
- [x] 2. Read `MainMenuKeyboard` to understand keyboard format requirements
- [x] 3. Create implementation plan
- [ ] 4. Implement the enhanced `back_to_chapters` function
- [ ] 5. Test the changes

## Implementation Details:
**File:** `app/handlers/quiz.py`

**Old Function (~15 lines):**
- Simply gets chapters from state
- Shows basic message without question counts

**New Function (~80 lines):**
- Gets `subject_id` from state data
- Validates `subject_id` exists
- Fetches fresh chapters from database with question counts
- Uses `_build_chapter_selection_message()` helper
- Creates simple chapter list for keyboard
- Updates state with fresh chapter data

