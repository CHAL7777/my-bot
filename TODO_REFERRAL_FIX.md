# TODO: Telegram Quiz Bot - Referral System Complete Fix

## ✅ IMPLEMENTATION COMPLETE

All code changes have been implemented. Run the migration script to apply database changes.

---

## Summary of Changes

### Files Modified:

1. **`app/db/models.py`** - Added `referral_balance` column, updated Referral model status to 'approved'
2. **`app/repositories/referral_repo.py`** - Added idempotent create_referral, approve_referral, mark_reward_claimed methods
3. **`app/services/referral_service.py`** - Complete rewrite with new methods
4. **`app/handlers/start_fixed.py`** - Updated to use capture_referral_on_start()
5. **`app/handlers/referral.py`** - Updated to show referral balance and use 'approved' status
6. **`scripts/referral_reward_migration.sql`** - SQL migration script created

### Key Features Implemented:

- ✅ Self-referral prevention
- ✅ Duplicate referral prevention  
- ✅ Referral counting ONLY after payment approval
- ✅ 20 Birr reward credited to referrer
- ✅ Notification sent to referrer
- ✅ Idempotent operations (prevents double-counting)

---

## Deployment Steps

### 1. Run Database Migration

```bash
# Connect to your PostgreSQL/Supabase database and run:
psql -d your_database -f scripts/referral_reward_migration.sql
```

Or if using Supabase SQL Editor, copy and run the contents of:
`scripts/referral_reward_migration.sql`

### 2. Restart the Bot

```bash
# If running via systemd
sudo systemctl restart telegram-quiz-bot

# Or if using docker-compose
docker-compose restart bot
```

### 3. Verify Migration

Run the verification queries from the migration script to confirm:
- `referral_balance` column exists
- Status values are 'pending', 'approved', 'cancelled'

---

## New Referral Flow

```
1. User A shares link → User B clicks /start=REFCODE
2. → Check: Not self-referral? 
3. → Check: User B not already referred?
4. → Save referral as 'pending'
5. User B pays and submits screenshot
6. Admin approves payment
7. → Mark referral as 'approved'
8. → Credit 20 Birr to referrer
9. → Send notification to referrer
```

---

## API Reference

### New Methods in ReferralService:

- `capture_referral_on_start(referrer_id, referred_id)` - Creates pending referral
- `approve_referral_and_credit_reward(referred_id, bot)` - Called on payment approval
- `credit_referral_reward(referrer_id, amount)` - Credits 20 Birr
- `notify_referrer_about_reward(bot, referrer_id, amount, referred_user_id)` - Sends notification

### New Methods in ReferralRepository:

- `create_referral(referrer_id, referred_id)` - Idempotent insert
- `approve_referral(referral_id)` - Updates status to approved
- `mark_reward_claimed(referral_id)` - Marks reward as claimed

---

## Testing Checklist

```bash
# Test cases:
# 1. /start with valid referral code → Referral created as pending
# 2. /start with own referral code → Self-referral prevented
# 3. /start twice with referral code → Already exists, skipped
# 4. Admin approves payment → Referral approved, reward credited
# 5. Admin approves same payment twice → Idempotent, no double credit
# 6. Referrer checks /referrals → Shows updated balance
```

