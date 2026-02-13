# Chapter Selection Enhancement - Implementation Plan

## Goal
Enhance the `back_to_chapters` handler to display the same enhanced chapter selection message with question counts as the `select_subject` handler.

## Changes Required

### Phase 1: Helper Function Creation
- [x] 1. Create `_build_chapter_selection_message()` helper function to reduce code duplication
- [x] 2. Function will accept subject_name and chapter_list as parameters
- [x] 3. Returns formatted message string with question counts

### Phase 2: Update `back_to_chapters` Handler
- [x] 1. Modify `back_to_chapters` to fetch fresh chapters from DB with question counts
- [x] 2. Use the new helper function to build consistent enhanced message
- [x] 3. Remove the simple format that doesn't show question counts

### Phase 3: Testing
- [ ] 1. Verify both handlers show enhanced format with question counts
- [ ] 2. Test keyboard navigation between subject/chapter selection
- [ ] 3. Test edge cases (empty chapters, DB errors)

## File Changes
- `app/handlers/quiz.py` - Add helper function and update `back_to_chapters` handler

## Implementation Details

### Helper Function Signature:
```python
def _build_chapter_selection_message(subject_name: str, chapter_list: list) -> str:
    """Build enhanced chapter selection message with question counts."""
```

### Message Format:
```
📚 *{subject_name}* - Chapter Selection

✨ Choose a chapter to start your quiz journey!

📖 *{chapter_name}*
   📊 {total_count} questions available
   🟢 Simple • 🟡 Medium • 🔴 Hard

💡 *Tip:* Start with chapters you want to improve in!

─────────────────────
◀️ Back to Subjects
```

## Status
- [x] Plan approved by user
- [ ] Implementation in progress
- [ ] Testing pending
- [ ] Complete

