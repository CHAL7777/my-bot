# TODO: Fix Payment System Issues

## Issue 1: Function Name Mismatch
- `start.py` calls `command_payment` but `payment.py` has `payment_command`
- FIX: Add `command_payment` alias to `payment.py` ✅ DONE

## Issue 2: Database Schema Mismatch
- `subscriptions` table exists but is deprecated
- Missing columns: `is_trial`, `updated_at`
- FIX: Run migration to add missing columns OR drop deprecated table
- Migration script created: `scripts/fix_subscriptions_table.sql`

## Issue 3: User Service Subscription Calls
- `user_service.py` calls `payment_repo.get_active_subscription()` which returns None
- This breaks trial subscription feature
- FIX: Update `user_service.py` to use `User.is_premium` directly ✅ DONE

## Plan
- [x] Add `command_payment` alias in `payment.py`
- [x] Update `user_service.py` to handle deprecated subscription system
- [ ] Run SQL migration to fix `subscriptions` table schema
- [ ] Restart the bot to apply changes

## Status
- [x] Not Started
- [x] In Progress
- [ ] Completed

## How to Run the Migration
```bash
# Connect to MySQL and run the migration
mysql -u root -p quizbot < scripts/fix_subscriptions_table.sql

# Or use docker-compose exec
docker-compose exec db mysql -u root -p quizbot -e "source /scripts/fix_subscriptions_table.sql"
```

