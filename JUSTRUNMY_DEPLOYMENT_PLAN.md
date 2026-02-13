# JustRunMy.App Deployment Plan for Telegram Quiz Bot

## Current State Analysis

### Files Analyzed:
1. **app/webhook_main.py** - Main webhook entry point (already webhook-ready)
2. **app/config.py** - Configuration with SQLite paths (already configured)
3. **app/bot.py** - Bot instance with handlers
4. **app/db/base.py** - Database initialization
5. **start.sh** - Startup script (needs modification)
6. **requirements.txt** - Dependencies already include aiogram, fastapi, uvicorn, aiosqlite

### Issues Found:
1. **start.sh** uses Render-specific paths (`/opt/render/project/src/data`) instead of `/data`
2. **webhook_main.py** needs minor improvements for JustRunMy.App
3. **Missing proper /data directory creation** in startup

---

## Implementation Plan

### Phase 1: Update startup script (start.sh)
- [ ] Change `DATA_DIR` from `/opt/render/project/src/data` to `/data`
- [ ] Remove Render-specific paths
- [ ] Ensure `/data` directory exists before startup
- [ ] Keep all existing functionality

### Phase 2: Improve webhook_main.py
- [ ] Add explicit `/data` directory creation in lifespan startup
- [ ] Add proper HEAD request handling (ignore 405)
- [ ] Add detailed startup logging
- [ ] Ensure webhook URL format matches JustRunMy.App requirements
- [ ] Add graceful error handling for webhook retries

### Phase 3: Create JustRunMy.App specific start script
- [ ] Create `start_justrunmy.sh` optimized for JustRunMy.App
- [ ] Remove unnecessary Render-specific logic
- [ ] Add platform detection

### Phase 4: Create deployment documentation
- [ ] Create `JUSTRUNMY_DEPLOYMENT.md` with step-by-step guide
- [ ] Document required environment variables
- [ ] Document webhook setup steps

---

## Environment Variables Required for JustRunMy.App:

```bash
# Required
BOT_TOKEN=your_telegram_bot_token

# Optional (auto-detected from platform)
PORT=10000  # JustRunMy.App provides this

# Recommended
WEBHOOK_URL=https://your-app.justrunmy.app
DATABASE_URL=sqlite+aiosqlite:////data/quizbot.db
SQLITE_DB_PATH=/data/quizbot.db
DB_TYPE=sqlite
```

---

## Webhook URL Format:
```
https://<your-app>.justrunmy.app/webhook
```

---

## Health Check Endpoints (Already Implemented):
- ✅ `GET /ping` → Returns 200 OK
- ✅ `GET /health` → Returns health status
- ✅ `GET /` → Root endpoint
- ✅ `HEAD /ping` → Returns 200 (for platform health checks)

---

## Files to Modify:
1. `start.sh` - Update paths
2. `app/webhook_main.py` - Add /data directory creation, improve logging
3. Create `start_justrunmy.sh` - New startup script for JustRunMy.App
4. Create `JUSTRUNMY_DEPLOYMENT.md` - Documentation

---

## Testing Checklist:
- [ ] Bot starts via `uvicorn app.webhook_main:app --host 0.0.0.0 --port $PORT`
- [ ] SQLite database created at `/data/quizbot.db`
- [ ] Webhook registered successfully on startup
- [ ] Health check endpoints return 200
- [ ] Telegram can send webhook updates
- [ ] Graceful shutdown works

