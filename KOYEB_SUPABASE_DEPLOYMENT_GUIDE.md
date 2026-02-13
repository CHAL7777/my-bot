# Koyeb + Supabase Deployment Guide for Telegram Quiz Bot

This guide provides complete instructions for deploying the Telegram Quiz Bot on Koyeb using Supabase (PostgreSQL).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supabase Setup](#supabase-setup)
3. [Environment Variables](#environment-variables)
4. [Local Testing](#local-testing)
5. [Koyeb Deployment](#koyeb-deployment)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, ensure you have:

- **Python 3.12+** installed locally
- **Git** installed
- **Supabase Account** (free tier works)
- **Koyeb Account** (free tier works)
- **Telegram Bot Token** from @BotFather

---

## Supabase Setup

### 1. Create a Supabase Project

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click "New Project"
3. Fill in the details:
   - **Name**: `telegram-quiz-bot` (or your preference)
   - **Database Password**: Generate a strong password and save it
4. Wait for the project to be created (2-3 minutes)

### 2. Get Database Connection String

1. Go to **Settings** → **Database**
2. Look for "Connection string" section
3. Copy the **URI** (should look like `postgresql://user:password@host:5432/postgres`)
4. **Important**: You'll need this for the `DATABASE_URL` environment variable

### 3. Configure Network (Optional but Recommended)

For production, restrict connections:

1. In Supabase Dashboard → **Settings** → **Database**
2. Under "Connection allow list", add Koyeb's IP ranges
   - Or disable the allow list for development (less secure)

---

## Environment Variables

Create a `.env` file in the project root with these variables:

```bash
# ============== REQUIRED ==============

# Telegram Bot Token (get from @BotFather)
BOT_TOKEN=your_bot_token_here

# Supabase Database URL
# Format: postgresql://user:password@host:5432/dbname
DATABASE_URL=postgresql://user:password@host:5432/postgres

# Full URL where your bot will be hosted
# Koyeb will give you: https://your-app-name.koyeb.app
WEBHOOK_URL=https://your-app-name.koyeb.app

# ============== OPTIONAL ==============

# Webhook path (default: /webhook)
WEBHOOK_PATH=/webhook

# Port (Koyeb uses 8000 by default)
PORT=8000

# Admin IDs (comma-separated Telegram user IDs)
ADMIN_IDS=123456789,987654321

# Bot username (for referral links)
BOT_USERNAME=YourBotUsername

# Currency settings
CURRENCY=ETB
SUBSCRIPTION_PRICE_30_DAYS=500

# Feature flags
ENABLE_TRIAL=false
DAILY_QUIZ_LIMIT=20

# Logging
LOG_LEVEL=info
```

---

## Local Testing

Before deploying to Koyeb, test locally:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# This creates all enum types and tables
python scripts/init_db.py
```

You should see:
```
🗄️  DATABASE INITIALIZATION FOR KOYEB + SUPABASE
===============================================
✓ Connected to PostgreSQL!
✓ All enum types created!
✓ Tables created
✓ Indexes created
✓ Triggers created
✅ DATABASE INITIALIZATION COMPLETE!
```

### 3. Test the Application

```bash
# Run the startup script
bash koyeb_start.sh
```

Expected output:
```
🚀 Telegram Quiz Bot - Koyeb Deployment
===============================================
[INFO] Pre-flight checks passed!
[INFO] Database initialized successfully!
[INFO] Starting Telegram Quiz Bot in webhook mode...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✅ BOT STARTUP COMPLETE - READY TO RECEIVE UPDATES
```

### 4. Verify Health Endpoints

Open a new terminal and test:

```bash
# Test ping endpoint
curl http://localhost:8000/ping
# Expected: PONG

# Test health endpoint
curl http://localhost:8000/health
# Expected: {"status":"healthy", ...}

# Test database health
curl http://localhost:8000/db/health
# Expected: {"status":"healthy", "database":"connected"}
```

---

## Koyeb Deployment

### 1. Push Code to GitHub

Ensure your code is in a GitHub repository:

```bash
git add .
git commit -m "Prepare for Koyeb deployment"
git push origin main
```

### 2. Create Koyeb App

1. Go to [Koyeb Dashboard](https://app.koyeb.com)
2. Click **"Create App"**
3. Select your GitHub repository
4. Configure the build settings:
   - **Builder**: Dockerfile
   - **Dockerfile Location**: `/Dockerfile`

### 3. Configure Environment Variables

In Koyeb dashboard, go to **Settings** → **Environment Variables** and add:

| Variable | Value | Secret? |
|----------|-------|---------|
| `BOT_TOKEN` | Your Telegram bot token | ✅ Yes |
| `DATABASE_URL` | `postgresql://...` | ✅ Yes |
| `WEBHOOK_URL` | `https://your-app.koyeb.app` | ❌ No |
| `PORT` | `8000` | ❌ No |
| `WEBHOOK_PATH` | `/webhook` | ❌ No |
| `BOT_USERNAME` | Your bot username | ❌ No |
| `ADMIN_IDS` | `123456789,...` | ❌ No |
| `CURRENCY` | `ETB` (or your currency) | ❌ No |
| `LOG_LEVEL` | `info` | ❌ No |

### 4. Configure Health Check

Koyeb will automatically use the `/ping` endpoint if configured:

1. Go to **Settings** → **Health Check**
2. **Health check path**: `/ping`
3. **Port**: `8000`

### 5. Deploy

Click **"Deploy"** and wait for the build to complete.

### 6. Verify Deployment

Once deployed, check:

1. **Logs**: Go to **Logs** tab to see startup logs
2. **Health**: Visit `https://your-app.koyeb.app/ping`
3. **Database**: Visit `https://your-app.koyeb.app/db/health`

Expected healthy response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### 7. Set Telegram Webhook

After deployment, set the webhook:

```bash
curl -F "url=https://your-app.koyeb.app/webhook" https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

Replace `<YOUR_BOT_TOKEN>` with your actual bot token.

---

## Troubleshooting

### Issue: "unterminated dollar-quoted string" or "syntax error at or near EXCEPTION"

**Cause**: The original schema used `DO $$` blocks which Supabase doesn't support well.

**Solution**: Use the updated `scripts/init_db.py` which creates enums safely:

```bash
python scripts/init_db.py
```

### Issue: "Invalid argument(s) 'ssl' sent to create_engine()"

**Cause**: SQLAlchemy was trying to pass `ssl=True` as a keyword argument.

**Solution**: The updated `app/db/base.py` now handles SSL via URL parameters:

```python
# SSL is now handled via the URL parameter
DATABASE_URL = f"postgresql+asyncpg://.../?sslmode=require"
```

### Issue: TCP health check failed on port 8000

**Cause**: The application wasn't binding to the correct port or interface.

**Solution**: The `koyeb_start.sh` script now:
- Binds to `0.0.0.0` (all interfaces)
- Uses port from `$PORT` environment variable (default: 8000)
- Includes proper health check endpoints

### Issue: Bot never starts / Service unhealthy

**Checklist**:

1. Verify all required environment variables are set:
   ```bash
   echo $BOT_TOKEN
   echo $DATABASE_URL
   echo $WEBHOOK_URL
   ```

2. Check database connection:
   ```bash
   python scripts/init_db.py
   ```

3. Check application logs in Koyeb dashboard

4. Verify the `/ping` endpoint responds:
   ```bash
   curl https://your-app.koyeb.app/ping
   ```

### Issue: "current transaction is aborted" errors

**Cause**: A previous query failed and the transaction was left in an aborted state.

**Solution**: The updated code now properly handles exceptions:

```python
async with session() as session:
    try:
        # Your query here
        await session.execute(...)
    except Exception:
        await session.rollback()
        raise
```

### Issue: Database connection timeout

**Cause**: Supabase might be blocking connections or the connection pool is exhausted.

**Solutions**:
1. Check Supabase network settings
2. Reduce `DB_POOL_SIZE` in environment
3. Add `connect_timeout` to connection string

---

## File Changes Summary

The following files were modified/created for Koyeb + Supabase compatibility:

| File | Changes |
|------|---------|
| `data/schema_postgresql.sql` | Fixed DO $$ block syntax |
| `scripts/init_db.py` | **NEW** - Safe enum/table creation |
| `app/db/base.py` | Fixed SSL handling for asyncpg |
| `koyeb_start.sh` | **NEW** - Startup script for Koyeb |
| `Dockerfile` | Updated health check and entrypoint |

---

## Quick Reference

### Commands

```bash
# Initialize database
python scripts/init_db.py

# Test locally
bash koyeb_start.sh

# Check health (local)
curl http://localhost:8000/health
curl http://localhost:8000/db/health

# Check health (production)
curl https://your-app.koyeb.app/health
curl https://your-app.koyeb.app/db/health

# Set webhook (production)
curl -F "url=https://your-app.koyeb.app/webhook" https://api.telegram.org/bot<TOKEN>/setWebhook
```

### Environment Variables Quick Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ Yes | Telegram bot token |
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string |
| `WEBHOOK_URL` | ✅ Yes | Full URL of your Koyeb app |
| `PORT` | No | Port (default: 8000) |
| `WEBHOOK_PATH` | No | Webhook path (default: /webhook) |
| `BOT_USERNAME` | No | Bot username for referral links |
| `ADMIN_IDS` | No | Comma-separated admin IDs |
| `CURRENCY` | No | Currency code (default: ETB) |
| `LOG_LEVEL` | No | Logging level (default: info) |

---

## Support

If you encounter issues not covered here:

1. Check Koyeb logs in the dashboard
2. Test locally with `bash koyeb_start.sh`
3. Verify database connection with `python scripts/init_db.py`
4. Check [Koyeb Documentation](https://www.koyeb.com/docs)
5. Check [Supabase Documentation](https://supabase.com/docs)

