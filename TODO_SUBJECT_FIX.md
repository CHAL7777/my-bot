# TODO: Fix Admin Panel Subject Management

## Issues Identified:
1. **Delete Subject** - Uses `update_question(subject_id)` which is wrong (expects question_id)
2. **Edit Name/Description** - No endpoints exist for these operations
3. **Repository** - Missing `update_subject` and `delete_subject` methods
4. **Template** - Edit modals don't have proper forms to submit changes

## Plan:
- [x] 1. Add `update_subject()` and `delete_subject()` methods to `question_repo.py`
- [x] 2. Add endpoints in `admin_panel/routes/subjects.py`:
  - [x] `POST /{subject_id}/edit_name` - Update subject name
  - [x] `POST /{subject_id}/edit_description` - Update subject description
  - [x] Fix `delete_subject` to use the new method
- [x] 3. Update `subjects.html` to add proper forms inside the modals
- [x] 4. Improve main menu keyboard with 2-column grid layout

## Changes Made:

### 1. app/repositories/question_repo.py
- Added `update_subject(subject_id, **kwargs)` - Updates subject fields
- Added `delete_subject(subject_id)` - Soft deletes subject (marks as inactive)

### 2. admin_panel/routes/subjects.py
- Added `POST /{subject_id}/edit_name` endpoint - Updates subject name with validation
- Added `POST /{subject_id}/edit_description` endpoint - Updates subject description
- Fixed `delete_subject` to use `question_repo.delete_subject()` instead of incorrect `update_question()`

### 3. admin_panel/templates/subjects.html
- Fixed Edit Name modal with proper `<form method="POST" action="...">` and input field with `name="subject_name"`
- Fixed Edit Description modal with proper `<form method="POST" action="...">` and textarea with `name="description"`
- Fixed Delete modal with proper `<a href="...">` link to the delete endpoint

### 4. app/keyboards/menu.py
- Updated `get_main_menu()` - Changed from single-column to 2-column grid layout
- Updated `get_main_menu_inline()` - Changed from single-column to 2-column grid layout with organized groupings
- Added new `get_main_menu_compact()` - 3-column compact layout for more options

### Menu Layout (2-column):
```
┌─────────────────┬─────────────────┐
│  🎯 Start Quiz  │  🎁 Referrals   │
├─────────────────┼─────────────────┤
│  📊 My Progress │  🏆 Leaderboard │
├─────────────────┼─────────────────┤
│  💳 Subscription│  💬 Contact     │
├─────────────────┼─────────────────┤
│  ❓ Help        │  📊 Weak Areas  │
└─────────────────┴─────────────────┘
```

