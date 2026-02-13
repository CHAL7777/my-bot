# Admin Panel Fix Plan

## Current State Analysis

### Existing Routes (in `/admin_panel/routes/`):
- ✅ `auth.py` - Authentication routes
- ✅ `users.py` - User management routes
- ✅ `questions.py` - Question management routes
- ✅ `leaderboard.py` - Leaderboard routes

### Missing Routes (referenced in `app.py` but not existing):
- ❌ `dashboard.py` - Dashboard statistics
- ❌ `payments.py` - Payment management
- ❌ `subjects.py` - Subject/Chapter management

### Existing Templates (in `/admin_panel/templates/`):
- ✅ `base.html` - Base template with navigation
- ✅ `dashboard.html` - Dashboard page
- ✅ `index.html` - Index page
- ✅ `leaderboard.html` - Leaderboard page
- ✅ `questions.html` - Questions management
- ✅ `subjects.html` - Subjects management

### Missing Templates (referenced in routes but not existing):
- ❌ `login.html` - Login page (referenced in auth.py)
- ❌ `users.html` - Users list (referenced in users.py)
- ❌ `profile.html` - Admin profile (referenced in auth.py)

## Issues Found

1. **Import Error**: `admin_panel/app.py` tries to import `dashboard`, `payments`, `subjects` routes that don't exist
2. **Missing Templates**: Routes reference templates that don't exist (`login.html`, `users.html`, `profile.html`)
3. **Route Dependencies**: `users.py` references `users.html` which doesn't exist

## Fix Plan

### Phase 1: Create Missing Route Files

1. **Create `admin_panel/routes/dashboard.py`**
   - Dashboard home page with statistics
   - Overview of users, questions, payments, subscriptions

2. **Create `admin_panel/routes/payments.py`**
   - List all payments
   - Approve/Reject payments
   - View payment details

3. **Create `admin_panel/routes/subjects.py`**
   - List subjects and chapters
   - Add/Edit/Delete subjects
   - Add/Edit/Delete chapters

### Phase 2: Create Missing Templates

1. **Create `admin_panel/templates/login.html`**
   - Login form with username/password
   - Error handling

2. **Create `admin_panel/templates/users.html`**
   - Users list with pagination
   - Search functionality
   - Actions: Approve, Reject, Block, Unblock

3. **Create `admin_panel/templates/profile.html`**
   - Admin profile information
   - Change password

### Phase 3: Fix Route References

1. **Fix `admin_panel/routes/users.py`**
   - Update to use existing templates or create needed ones

## Implementation Order

1. Create dashboard.py route
2. Create payments.py route  
3. Create subjects.py route
4. Create login.html template
5. Create users.html template
6. Create profile.html template
7. Test admin panel startup

