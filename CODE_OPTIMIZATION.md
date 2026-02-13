# Code Optimization Tasks - COMPLETED

## ✅ Optimizations Applied

### Task 1: Batch Question Count Query
**File:** `app/repositories/question_repo.py`
- Added `case` import for conditional aggregation
- Added `get_chapter_counts_batch()` method
- Reduces N*4 queries to 1 query for chapter selection
- Uses `func.count(case(...))` pattern for cross-database compatibility

### Task 2: Optimize Chapter Selection
**File:** `app/handlers/quiz.py` - `select_subject()` callback
- Now uses batch query for all chapter counts
- Reduced from 4 queries per chapter to 1 batch query total

### Task 3: Optimize Back to Chapters
**File:** `app/handlers/quiz.py` - `back_to_chapters()` callback  
- Now uses batch query for all chapter counts
- Same optimization as select_subject

## Performance Impact

**Before:** 4*N queries (where N = number of chapters)
**After:** 1 batch query

Example: 10 chapters
- Before: 40 queries
- After: 1 query
- **Reduction: 97.5%**

## Fix Applied
Fixed SQLAlchemy syntax error in batch query:
- Changed `func.sum(func.cast(...))` to `func.count(case(...))`
- This fixes the "'int' object has no attribute '_isnull'" error

## To Apply Changes
Restart your bot to use the optimized code:
```bash
# If running with Python directly
pkill -f "python.*main.py" && python app/main.py

# If using Docker
docker restart <container_name>
```



"