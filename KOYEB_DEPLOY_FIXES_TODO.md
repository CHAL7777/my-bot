# Koyeb + Supabase Deployment Fixes - TODO List

## Issue Summary
1. PostgreSQL errors like "unterminated dollar-quoted string"
2. SQLAlchemy async engine SSL keyword errors
3. Koyeb TCP health check failed on port 8000
4. Bot never starts

## Plan
1. Fix `data/schema_postgresql.sql` - Remove DO $$ blocks
2. Create `scripts/init_db.py` - Safe database initialization
3. Fix `app/db/base.py` - Proper asyncpg SSL handling
4. Create `koyeb_start.sh` - Koyeb startup script
5. Update `app/webhook_main.py` - Health checks on port 8000

## Status - ALL COMPLETED ✅
- [x] 1. Fix schema_postgresql.sql - Replace DO $$ blocks
- [x] 2. Create scripts/init_db.py - Database initialization script
- [x] 3. Fix app/db/base.py - SSL handling for asyncpg
- [x] 4. Create koyeb_start.sh - Startup script for Koyeb
- [x] 5. Update app/webhook_main.py - Health checks
- [x] 6. Update Dockerfile - Health check and startup
- [x] 7. Create KOYEB_SUPABASE_DEPLOYMENT_GUIDE.md - Complete deployment guide

## Files Modified/Created
| File | Purpose |
|------|---------|
| `data/schema_postgresql.sql` | Fixed DO $$ block syntax, Supabase compatible |
| `scripts/init_db.py` | NEW - Safe enum/table creation using asyncpg |
| `app/db/base.py` | Fixed SSL handling via URL params (no ssl keyword) |
| `koyeb_start.sh` | NEW - Startup script with pre-flight checks |
| `app/webhook_main.py` | Uses centralized db module, proper health endpoints |
| `Dockerfile` | Health check and koyeb_start.sh entrypoint |
| `KOYEB_SUPABASE_DEPLOYMENT_GUIDE.md` | Complete deployment documentation |

## Quick Start
```bash
# 1. Set environment variables
export BOT_TOKEN=your_token
export DATABASE_URL=postgresql://user:pass@host:5432/db
export WEBHOOK_URL=https://your-app.koyeb.app

# 2. Initialize database
python scripts/init_db.py

# 3. Test locally
bash koyeb_start.sh

# 4. Deploy to Koyeb (Dockerfile based)
# Set environment variables in Koyeb dashboard
# Deploy!
```

