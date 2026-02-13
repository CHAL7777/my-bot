# Render Deployment Guide for Telegram Quiz Bot

## Overview

This guide explains how to deploy the Telegram Quiz Bot on Render's free tier using webhook architecture.

## Architecture Changes

The bot has been converted from polling to webhook mode:

- **Old**: `app/main.py` - Used `dp.start_polling(self.bot)` 
- **New**: `app/webhook_main.py` - Uses FastAPI with `/webhook` endpoint

## Environment Variables (Render Dashboard)

Set the following environment variables in your Render service:

| Variable | Value | Required |
|----------|-------|----------|
| `BOT_TOKEN` | Your Telegram bot token | Yes |
| `WEBHOOK_URL` | Your Render app URL (e.g., `https://your-app.onrender.com`) | Yes |
| `PORT` | Render provides this automatically | Auto |

### Example .env file for local testing:

```env
BOT_TOKEN=your_telegram_bot_token_here
WEBHOOK_URL=http://localhost:10000
PORT=10000
```

Note: The database path is set automatically in `start.sh` to use `/opt/render/project/src/data/quizbot.db` for Render deployments.

## Start Command

Render will use this command to start your bot:

```bash
uvicorn app.webhook_main:app --host 0.0.0.0 --port $PORT
```

Or use the provided start script:

```bash
bash start.sh
```

## Deployment Steps

### 1. Push to GitHub

Ensure all changes are committed and pushed:

```bash
git add .
git commit -m "Convert to webhook architecture for Render deployment"
git push origin main
```

### 2. Create Render Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: telegram-quiz-bot
   - **Region**: Choose closest to your users
   - **Branch**: main
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash start.sh`

### 3. Set Environment Variables

In the Render service settings, add:
- `BOT_TOKEN`: Your Telegram bot token
- `WEBHOOK_URL`: Your Render service URL (get this after first deployment)

### 4. Deploy

Click "Create Web Service". Render will build and deploy your bot.

### 5. Configure Webhook

After deployment:
1. Copy your Render service URL (e.g., `https://telegram-quiz-bot.onrender.com`)
2. Set `WEBHOOK_URL` environment variable to this URL
3. Redeploy or use the /webhook_info endpoint to trigger webhook setup

## Local Testing

To test locally:

```bash
# Export environment variables
export BOT_TOKEN="your_token"
export WEBHOOK_URL="http://localhost:10000"
export PORT=10000

# Run the bot
uvicorn app.webhook_main:app --host 0.0.0.0 --port $PORT

# Or use start.sh
bash start.sh
```

Then test the endpoints:
- Health check: `http://localhost:10000/health`
- Webhook info: `http://localhost:10000/webhook`

## Telegram BotFather Setup

After deployment, set the webhook using BotFather:

1. Open Telegram and talk to [@BotFather](https://t.me/BotFather)
2. Use command: `/setwebhook`
3. Send: `https://your-render-app.onrender.com/webhook`

Or use the API directly:

```bash
curl -F "url=https://your-render-app.onrender.com/webhook" https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root info |
| `/health` | GET | Health check for Render |
| `/webhook` | GET | Webhook info |
| `/webhook` | POST | Telegram webhook handler |
| `/db/health` | GET | Database health check |

## Troubleshooting

### Bot not responding
1. Check logs in Render dashboard
2. Verify `WEBHOOK_URL` is set correctly
3. Ensure webhook is set via BotFather or API

### Database issues
1. Check `/db/health` endpoint
2. Verify `/data` directory exists
3. Check logs for SQLAlchemy errors

### Webhook not set
1. Check `BOT_TOKEN` is correct
2. Verify `WEBHOOK_URL` ends without trailing slash
3. Check Render logs for startup errors

## Files Modified

- `app/webhook_main.py` - New unified webhook entry point
- `app/webapp.py` - Refactored for integration
- `app/bot.py` - Added webhook methods
- `app/config.py` - Added webhook settings
- `app/db/base.py` - Added data directory creation
- `start.sh` - Updated for webhook mode

## Rollback

To revert to polling mode, use the old entry point:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Or set environment variable `USE_WEBHOOK=false` and modify `app/main.py` accordingly.

