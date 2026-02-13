# TODO: Referral System & Multi-Admin Support Implementation

## Database & Models
- [x] 1. Create migration script (`scripts/referral_admin_migration.sql`)
- [x] 2. Update `app/db/models.py` - Add referral fields to User, create Referral and TelegramAdmin models

## Repository Layer
- [x] 3. Create `app/repositories/referral_repo.py`
- [x] 4. Update `app/repositories/admin_repo.py` - Add TelegramAdminRepository

## Service Layer
- [x] 5. Create `app/services/referral_service.py`
- [x] 6. Create `app/services/admin_service.py`

## Middleware
- [x] 7. Update `app/middlewares/auth.py` - Check database for admin permissions

## Handlers
- [x] 8. Update `app/handlers/start.py` - Handle referral links in /start
- [x] 9. Create `app/handlers/referral.py` - Referral command handler
- [x] 10. Create `app/handlers/admin_manage.py` - Admin management UI handlers
- [x] 11. Update `app/handlers/admin.py` - Add admin management comments

## Keyboards
- [x] 12. Update `app/keyboards/admin.py` - Add AdminManageKeyboard

## Configuration & Utilities
- [x] 13. Update `app/config.py` - Add referral configuration
- [x] 14. Create `scripts/seed_initial_admins.py` - Admin seeding script

## Integration
- [x] 15. Update `app/bot.py` - Register new handlers

## Testing
- [ ] 16. Run database migration
- [ ] 17. Seed initial admins
- [ ] 18. Test referral system
- [ ] 19. Test admin management

---

## Implementation Summary

### Referral System
- Each user gets a unique referral code (`REFXXXXXXXX`)
- Referral links: `https://t.me/BotName?start=ref_CODE`
- When new user joins with referral:
  - Referral record created
  - Referrer's count increased
  - Reward granted after N referrals (configurable)

### Multi-Admin Support
- Database-backed admin management (`telegram_admins` table)
- Two roles: `superadmin` and `admin`
- Superadmin can add/remove admins
- Admin can approve payments, manage users/questions

### New Commands
- `/referral` - View referral stats and link
- `/add_admin <user_id> [role]` - Add new admin (superadmin only)
- `/remove_admin <user_id>` - Remove admin (superadmin only)
- `/list_admins` - List all admins
- `/admin_help` - Show admin help

### Migration Steps
1. Run: `mysql quiz_bot < scripts/referral_admin_migration.sql`
2. Run: `python scripts/seed_initial_admins.py`
3. Restart the bot



