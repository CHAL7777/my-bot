# Koyeb Deployment Guide for Telegram Quiz Bot

## Overview

This guide provides step-by-step instructions to deploy your Telegram Quiz Bot on Koyeb using Docker and Buildpacks.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
   - [Option 1: Docker (Recommended)](#option-1-docker-recommended)
   - [Option 2: Buildpacks](#option-2-buildpacks)
3. [Configuration](#configuration)
4. [Environment Variables](#environment-variables)
5. [Webhook Setup](#webhook-setup)
6. [Database Considerations](#database-considerations)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying to Koyeb, ensure you have:

- A Koyeb account (sign up at [koyeb.com](https://www.koyeb.com))
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- A domain name with SSL certificate (optional but recommended)
- Git installed locally
- Your project pushed to a Git repository (GitHub, GitLab, etc.)

---

## Deployment Options

### Option 1: Docker (Recommended)

Koyeb has excellent Docker support. Your existing Dockerfile is already configured for Koyeb deployment.

#### Steps:

1. **Push your code to GitHub/GitLab**

```bash
git add .
git commit -m "Prepare for Koyeb deployment"
git push origin main
```

2. **Create a new Service on Koyeb**

   - Log in to [Koyeb Dashboard](https://app.koyeb.com)
   - Click "Create Service"
   - Select your Git provider and repository
   - Choose the branch (usually `main`)

3. **Configure the Service**

   - **Build method**: Dockerfile
   - **Dockerfile path**: `Dockerfile` (default)
   - **Run command**: `bash start.sh` (or leave empty, Dockerfile has CMD)
   - **Port**: `10000`

4. **Add Environment Variables**

   Navigate to the "Variables" section and add:

   ```
   BOT_TOKEN=your_bot_token_here
   WEBHOOK_URL=https://your-domain.com
   PORT=10000
   DB_TYPE=sqlite
   DATA_DIR=/data
   SQLITE_DB_PATH=/data/quizbot.db
   ```

5. **Deploy**

   Click "Deploy" and wait for the build to complete.

---

### Option 2: Buildpacks

Koyeb also supports Buildpacks for Python applications.

#### Steps:

1. **Create buildpack.toml**

   A `buildpack.toml` file is already included in your project.

2. **Create Procfile**

   A `Procfile` is already included:
   ```
   web: bash start.sh
   ```

3. **Deploy on Koyeb**

   - Select "Buildpack" as the build method
   - Koyeb will automatically detect Python buildpack
   - Configure the same environment variables as above

---

## Configuration

### koyeb.json

We've created a `koyeb.json` file for declarative deployment. You can use the Koyeb CLI to deploy:

```bash
# Install Koyeb CLI
curl -fsSL https://get.koyeb.com/cli | sh

# Login
koyeb login

# Deploy
koyeb apps:create telegram-quiz-bot
koyeb services:create \
  --app telegram-quiz-bot \
  --name web \
  --git github.com/your-username/telegram-quiz-bot \
  --branch main \
  --dockerfile-path Dockerfile \
  --run-command "bash start.sh" \
  --port 10000 \
  --env BOT_TOKEN=your_token \
  --env WEBHOOK_URL=https://your-domain.com
```

---

## Environment Variables

Configure these environment variables in Koyeb:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Your Telegram Bot Token from @BotFather |
| `WEBHOOK_URL` | Yes | - | Your public URL (e.g., https://yourbot.koyeb.app) |
| `PORT` | No | 10000 | Port for the web server (Koyeb uses 10000) |
| `DB_TYPE` | No | sqlite | Database type (sqlite, mysql, mariadb) |
| `DATA_DIR` | No | /data | Directory for persistent data |
| `SQLITE_DB_PATH` | No | /data/quizbot.db | SQLite database file path |
| `REDIS_URL` | No | - | Redis connection string for session storage |
| `ADMIN_IDS` | No | - | Comma-separated admin Telegram IDs |
| `ENABLE_TRIAL` | No | false | Enable trial period for new users |
| `SUBSCRIPTION_PRICE_30_DAYS` | No | 500 | 30-day subscription price (ETB) |
| `SUBSCRIPTION_PRICE_90_DAYS` | No | 1200 | 90-day subscription price (ETB) |
| `ONE_TIME_PRICE` | No | 150 | Lifetime subscription price (ETB) |
| `DAILY_QUIZ_LIMIT` | No | 20 | Max quizzes per day per user |
| `MAX_QUESTIONS_PER_QUIZ` | No | 10 | Questions per quiz session |
| `DAILY_QUESTION_LIMIT` | No | 500 | Max questions per day |

---

## Webhook Setup

### Getting Your Koyeb URL

After deploying, Koyeb will assign a URL like:
```
https://telegram-quiz-bot-yourusername.koyeb.app
```

### Setting Telegram Webhook

You need to set up the webhook for your Telegram bot. Run:

```bash
curl -F "url=https://YOUR-KOYEB-URL/webhook" https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook
```

Or add this to your deployment script:

```bash
# In your start.sh or deployment script
if [ -n "$WEBHOOK_URL" ]; then
    curl -s -F "url=$WEBHOOK_URL/webhook" "https://api.telegram.org/bot$BOT_TOKEN/setWebhook"
    echo "Webhook set to $WEBHOOK_URL/webhook"
fi
```

### Verify Webhook

```bash
curl https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo
```

---

## Database Considerations

### SQLite (Default)

Your bot uses SQLite by default, stored in `/data`. Koyeb provides ephemeral filesystem, but `/data` is persisted across restarts.

**Pros:**
- No additional setup required
- Works out of the box

**Cons:**
- Not suitable for high traffic
- No connection pooling

### PostgreSQL (Recommended for Production)

For better reliability, use PostgreSQL:

1. **Create PostgreSQL Database**

   You can use:
   - Koyeb's managed PostgreSQL
   - Supabase
   - Railway
   - Neon

2. **Set Environment Variables**

   ```
   DB_TYPE=mysql  # or mariadb
   DB_HOST=your-db-host.com
   DB_PORT=5432
   DB_NAME=your_db_name
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

3. **Update requirements.txt**

   Ensure you have the PostgreSQL driver:
   ```
   asyncpg>=0.29.0
   ```

---

## Troubleshooting

### Bot Not Responding

1. **Check Logs**

   Go to Koyeb Dashboard → Your Service → Logs

2. **Common Issues**

   - **Webhook not set**: Run the curl command to set webhook
   - **Wrong PORT**: Ensure PORT=10000
   - **Missing BOT_TOKEN**: Check environment variables

3. **Test Endpoint**

   ```bash
   curl https://your-koyeb-url/ping
   ```

   Should return `{"status":"ok"}` or similar.

### Database Issues

- Ensure `DATA_DIR=/data` is set
- Check that `/data` directory is writable
- Verify database migrations run on startup

### Memory Issues

If your bot is crashing with memory errors:

1. Add swap space in `start.sh`:
   ```bash
   dd if=/dev/zero of=/tmp/swap bs=1M count=512
   chmod 600 /tmp/swap
   mkswap /tmp/swap
   swapon /tmp/swap
   ```

2. Reduce `DB_POOL_SIZE` in environment variables

### SSL/HTTPS Issues

Koyeb automatically provides SSL for your subdomain. If using custom domain:

1. Add domain in Koyeb settings
2. Update DNS records
3. Let SSL certificate provision (may take a few hours)

---

## Health Check Endpoint

Your bot includes a health check endpoint at `/ping`:

```bash
curl https://your-koyeb-url/ping
```

This is used by Koyeb's health check system.

---

## Scaling

### Vertical Scaling

Increase instance size in Koyeb Dashboard:
- **Development**: 1 GB RAM
- **Production**: 2+ GB RAM

### Horizontal Scaling

Koyeb supports auto-scaling. Configure in service settings:
- Min instances: 1
- Max instances: 3
- CPU target: 70%
- Memory target: 80%

**Note**: For Telegram bots, horizontal scaling requires Redis for state management. Set `REDIS_URL` environment variable.

---

## Security Best Practices

1. **Never commit `.env` files**
2. **Use Koyeb Secrets** for sensitive variables
3. **Rotate BOT_TOKEN** periodically
4. **Enable 2FA** on Telegram account
5. **Use HTTPS** (automatic on Koyeb)

---

## Monitoring

### Koyeb Dashboard

Monitor:
- Request count
- Response time
- Error rate
- Memory usage
- CPU usage

### Telegram Bot Stats

Use @BotFather → /mybots → Select Bot → Bot Settings → Analytics

---

## Rollback

To rollback to a previous version:

1. Go to Koyeb Dashboard
2. Navigate to your Service
3. Click "Deployments"
4. Select a previous deployment
5. Click "Rollback"

---

## Support

- **Koyeb Docs**: https://koyeb.com/docs
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Aiogram Docs**: https://docs.aiogram.dev

---

## Quick Deploy Command

```bash
# One-liner deployment using Koyeb CLI
koyeb services:create \
  --app telegram-quiz-bot \
  --name bot \
  --git github.com/yourusername/telegram-quiz-bot \
  --branch main \
  --dockerfile-path Dockerfile \
  --run-command "bash start.sh" \
  --port 10000 \
  --env "BOT_TOKEN=YOUR_BOT_TOKEN" \
  --env "WEBHOOK_URL=https://yourbot.koyeb.app" \
  --env "DB_TYPE=sqlite" \
  --env "DATA_DIR=/data" \
  --env "ONE_TIME_PRICE=150" \
  --env "DAILY_QUIZ_LIMIT=20"
```

---

**Happy Deploying! 🚀**

