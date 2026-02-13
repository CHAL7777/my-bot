# Escape Fix Plan for quiz.py

## Status: ✅ Approved

### Already Fixed (import already present in code):
- ✅ Import `escape_markdown_content` is already at line 18
- ✅ `get_recommendations` (~line 1147) already has escaping
- ✅ `start_recommended_quiz` (~line 1244) already has escaping
- ✅ `practice_weak_area` (~line 1341) already has escaping

### Needs Fixing:
1. [ ] `select_difficulty` (~line 710): Add escaping for `subject_name` and `chapter_name`

## Implementation Steps:
1. Edit `select_difficulty` function to add escaping for subject_name and chapter_name

