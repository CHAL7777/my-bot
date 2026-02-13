# Handler Fix Plan

## Root Causes Identified:
1. **Missing `subscriptions` table** - Database errors when handlers try to access it
2. **Deprecated subscription methods** - `NotImplementedError` crashes handlers
3. **User service calling deprecated methods** - `_has_trial_access()` calls failing methods

## Fixes to Implement:

### Phase 1: Database Schema Fixes
- [ ] 1. Add `Subscription` model to `models.py`
- [ ] 2. Create SQL migration script for subscriptions table
- [ ] 3. Run migration to create the table

### Phase 2: Repository Fixes
- [ ] 4. Fix `payment_repo.py` to return `None` instead of raising errors
- [ ] 5. Ensure `create_trial_subscription()` is deprecated gracefully
- [ ] 6. Ensure `get_active_subscription()` returns `None` for lifetime model

### Phase 3: Service Layer Fixes
- [ ] 7. Fix `user_service.py` to remove deprecated trial subscription logic
- [ ] 8. Simplify `_has_trial_access()` to always return `False`

### Phase 4: Testing
- [ ] 9. Verify handlers load without errors
- [ ] 10. Test admin command responds correctly

## Files to Modify:
1. `app/db/models.py` - Add Subscription model
2. `app/repositories/payment_repo.py` - Fix deprecated methods
3. `app/services/user_service.py` - Remove trial logic
4. `scripts/create_subscriptions_table.sql` - New migration script

