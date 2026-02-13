# Fix Admin Management Flow - TODO

## Problem
When super admin clicks "Add by User ID" or "Add by Username" button, the bot asks for input but doesn't handle the subsequent message containing the user ID/username.

## Solution
Implement FSM (Finite State Machine) to manage the admin creation flow.

## Tasks

### Phase 1: FSM States and Message Handlers
- [x] 1. Import FSM and States in admin_manage.py
- [x] 2. Create AdminManagementStates state group
- [x] 3. Add message handler for user ID input (waiting_for_admin_user_id)
- [x] 4. Add message handler for username input (waiting_for_admin_username)
- [x] 5. Add message handler for role selection (waiting_for_admin_role)

### Phase 2: Update Callback Handlers
- [x] 6. Update add_admin_by_userid_callback to set FSM state
- [x] 7. Update add_admin_by_username_callback to set FSM state
- [x] 8. Add state clearing on success/cancellation

### Phase 3: Add Cancel Handler
- [x] 9. Add handler to cancel admin creation flow

### Phase 4: Repository Updates
- [x] 10. Add get_user_by_username method to UserRepository

### Phase 5: Testing
- [ ] 11. Test the complete flow

## Files Modified
- app/handlers/admin_manage.py
- app/repositories/user_repo.py


