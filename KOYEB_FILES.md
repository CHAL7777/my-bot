# Koyeb Deployment Files Summary

This document lists all the files created/modified for Koyeb deployment.

## Created Files

### 1. `koyeb.json`
Koyeb declarative configuration file for CLI deployment.

### 2. `Procfile`
Heroku-style process file for Buildpack deployment.

### 3. `buildpack.toml`
Buildpack configuration for Python detection.

### 4. `KOYEB_DEPLOYMENT.md`
Comprehensive deployment guide with:
- Step-by-step instructions
- Environment variable reference
- Troubleshooting section
- Quick deploy commands

### 5. `KOYEB_CHECKLIST.md`
Pre and post-deployment checklist for verification.

### 6. `.env.example`
Template for environment variables (rename to `.env`).

### 7. `scripts/setup_webhook.py`
Script to set up Telegram webhook after deployment.

### 8. `scripts/deployment_check.py`
Script to verify deployment health and connectivity.

## Modified Files

### 1. `start.sh`
Enhanced startup script with:
- Multi-platform detection (Koyeb, Render, Fly.io, Docker)
- Automatic webhook setup
- Better logging and error handling
- Platform-specific optimizations

## Quick Start

### Option 1: Docker (Recommended)

1. Push code to GitHub
2. Create service in Koyeb Dashboard
3. Select Dockerfile build method
4. Add environment variables
5. Deploy

### Option 2: Buildpacks

1. Push code to GitHub
2. Create service in Koyeb Dashboard
3. Select Buildpack method
4. Add environment variables
5. Deploy

### Option 3: Koyeb CLI

```bash
koyeb apps:create telegram-quiz-bot
koyeb services:create \
  --app telegram-quiz-bot \
  --name web \
  --git github.com/yourusername/telegram-quiz-bot \
  --branch main \
  --dockerfile-path Dockerfile \
  --run-command "bash start.sh" \
  --port 10000 \
  --env "BOT_TOKEN=your_token" \
  --env "WEBHOOK_URL=https://yourbot.koyeb.app"
```

## Environment Variables Required

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram Bot Token (required) |
| `WEBHOOK_URL` | Public HTTPS URL (required) |
| `PORT` | Port (default: 10000) |
| `ADMIN_IDS` | Comma-separated admin IDs |

## Post-Deployment Steps

1. Get your Koyeb URL: `https://your-app.koyeb.app`
2. Run webhook setup:
   ```bash
   python scripts/setup_webhook.py
   ```
3. Verify deployment:
   ```bash
   python scripts/deployment_check.py
   ```
4. Test bot in Telegram

## Files Structure

```
telegram-quiz-bot/
├── koyeb.json                    # Koyeb CLI config
├── Procfile                      # Buildpack entry point
├── buildpack.toml                # Buildpack config
├── KOYEB_DEPLOYMENT.md           # Full deployment guide
├── KOYEB_CHECKLIST.md            # Deployment checklist
├── .env.example                  # Environment template
├── start.sh                      # Enhanced startup script
└── scripts/
    ├── setup_webhook.py          # Webhook setup utility
    └── deployment_check.py       # Health check utility
```

## Support

- Koyeb Docs: https://koyeb.com/docs
- Telegram Bot API: https://core.telegram.org/bots/api
- Project Issues: GitHub Issues

