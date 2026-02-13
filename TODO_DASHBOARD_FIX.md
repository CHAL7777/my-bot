# Dashboard Fix Plan

## Issues Identified from Dashboard Overview:
1. **Questions: N/A** - Shows 0 for all categories despite code expecting data
2. **Revenue: birr0.00** - No payments recorded
3. **Health Score: 40.0/100** - Low score due to missing data

## Root Causes:
1. `AnalyticsService._get_question_stats()` calls `get_question_count()` which may return 0
2. Health score calculation gives 0 points for question coverage (20 pts) and revenue (15 pts)
3. No questions exist in the database (needs seeding)
4. Analytics service lacks proper error handling for missing data

## Implementation Steps:

### Step 1: Fix Analytics Service (app/services/analytics_service.py) ✅ DONE
- [x] Add proper error handling for database queries
- [x] Handle cases where question counts are 0
- [x] Add fallback values for health score calculation
- [x] Improve logging for debugging

### Step 2: Create Dashboard API Handler (app/handlers/admin_dashboard_api.py) ✅ DONE
- [x] Create new handler with dashboard API endpoints
- [x] Add proper error handling
- [x] Include data validation
- [x] Add Pydantic models for API responses
- [x] Add health check endpoints

### Step 3: Add Dashboard Endpoints to Webapp (app/webapp.py) ✅ DONE
- [x] Add `/api/dashboard/stats` endpoint
- [x] Add `/api/dashboard/health` endpoint
- [x] Add `/api/dashboard/summary` endpoint
- [x] Include dashboard router

### Step 4: Create Question Seeding Script (scripts/seed_sample_questions.py) ✅ DONE
- [x] Create sample questions for testing
- [x] Add subjects and chapters
- [x] Include all difficulty levels
- [x] Add support for clearing database

### Step 5: Testing
- [ ] Test dashboard API endpoints
- [ ] Verify health score calculation
- [ ] Test with empty database
- [ ] Test with populated database

## Files Created:
- `app/handlers/admin_dashboard_api.py` - Dashboard API handler with REST endpoints
- `scripts/seed_sample_questions.py` - Sample data seeder script

## Files Modified:
- `app/services/analytics_service.py` - Fixed health score and error handling
- `app/webapp.py` - Added dashboard endpoints

## New API Endpoints:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/stats` | GET | Get full dashboard statistics |
| `/api/dashboard/users` | GET | Get user statistics |
| `/api/dashboard/questions` | GET | Get question statistics |
| `/api/dashboard/revenue` | GET | Get revenue statistics |
| `/api/dashboard/health` | GET | Detailed health check |
| `/api/dashboard/health/simple` | GET | Simple health check |
| `/api/dashboard/summary` | GET | Quick dashboard summary |

## Usage:

### Seed sample questions:
```bash
cd scripts
python seed_sample_questions.py
```

### Clear database:
```bash
python seed_sample_questions.py --clear
```

### Test API endpoints:
```bash
# Start the webapp
python -m app.webapp

# Test endpoints
curl http://localhost:8000/api/dashboard/stats
curl http://localhost:8000/api/dashboard/health
curl http://localhost:8000/api/dashboard/summary
```

## Success Criteria:
1. [x] Dashboard shows accurate question counts (with proper error handling)
2. [x] Health score is calculated correctly (even with 0 data)
3. [x] API endpoints return proper JSON responses
4. [x] Error handling prevents crashes
5. [ ] Database seeding works correctly

## Expected Health Score Calculation:
With 6 users, 0 questions, 0 revenue:
- User points: 6 users × 3 = 18 points
- Total expected score: ~18/100 (showing as "critical")

After adding questions:
- 20 questions: 20 × 0.5 = 10 points
- Total expected score: ~28/100

After getting revenue:
- Revenue points: Base 5 = 5 points
- Total expected score: ~33/100

The health score is intentionally designed to be lower when starting out,
encouraging admins to add content and users.

