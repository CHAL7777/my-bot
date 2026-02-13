# TODO: 25 Questions Per Day Per Chapter + Level + Random Questions on Resume

## Summary
- Implement 25 questions per day limit per (chapter + difficulty) combination
- Ensure questions are random when user cancels exam and comes back (show new questions)

## Tasks

### Phase 1: Database Changes
- [x] 1.1 Add `UserChapterDailyLimit` table to `app/db/models.py`
- [x] 1.2 Create migration script for the new table
- [x] 1.3 Add `DAILY_CHAPTER_QUESTION_LIMIT` setting to `app/config.py`

### Phase 2: Repository Changes
- [x] 2.1 Add `get_chapter_daily_limit()` method to `app/repositories/user_repo.py`
- [x] 2.2 Add `increment_chapter_daily_question_count()` method to `app/repositories/user_repo.py`
- [x] 2.3 Add `get_attempted_question_ids()` method to `app/repositories/question_repo.py`
- [x] 2.4 Add `get_random_questions_excluding()` method to `app/repositories/question_repo.py`

### Phase 3: Service Changes
- [x] 3.1 Update `QuizService.start_quiz()` to check per-chapter-level daily limit (25 questions)
- [x] 3.2 Update `QuizService.start_quiz()` to exclude already answered questions
- [x] 3.3 Update `QuizService.process_answer()` to increment chapter-level counter
- [x] 3.4 Update error handling for chapter-level daily limit reached

### Phase 4: Handler Changes
- [x] 4.1 Error messages handled by quiz service

### Phase 5: Database Migration
- [ ] 5.1 Run migration script: `scripts/chapter_daily_limit_migration.sql`

### Phase 6: Testing
- [ ] 6.1 Test daily limit per chapter + difficulty
- [ ] 6.2 Test that cancelled quiz shows new questions on resume
- [ ] 6.3 Verify existing functionality still works

## Files Modified
1. `app/db/models.py` - Added UserChapterDailyLimit model
2. `app/config.py` - Added DAILY_CHAPTER_QUESTION_LIMIT setting
3. `app/repositories/user_repo.py` - Added chapter-level limit methods
4. `app/repositories/question_repo.py` - Added methods to exclude attempted questions
5. `app/services/quiz_service.py` - Updated quiz service for new limit logic

## New Files Created
1. `scripts/chapter_daily_limit_migration.sql` - Database migration

## Implementation Details

### UserChapterDailyLimit Model
Tracks daily question limits per user per chapter per difficulty level.

### Logic Flow for Random Questions
1. When user starts quiz, get list of already attempted question IDs for this (user, chapter, difficulty) today
2. Pass these IDs to `get_random_questions_excluding()` to exclude from selection
3. This ensures new questions are shown each time user starts/resumes quiz

### Daily Limit Logic
1. Check `UserChapterDailyLimit` for (user, subject, chapter, difficulty, today)
2. If question_count >= 25, raise error with friendly message
3. After each answer, increment question_count by 1

## How to Run Migration
```bash
# Run the SQL migration
psql -U quiz_user -d quiz_bot -f scripts/chapter_daily_limit_migration.sql
```

Or if using the bot's migration system, add the script to the migrations folder.

