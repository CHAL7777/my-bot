# Telegram Quiz Bot - Koyeb Deployment Checklist

## Pre-Deployment Checklist

- [ ] **Git Repository**
  - [ ] Code pushed to GitHub/GitLab
  - [ ] `.env` file NOT committed (add to `.gitignore`)
  - [ ] Sensitive files excluded

- [ ] **Telegram Bot**
  - [ ] Bot created via @BotFather
  - [ ] Bot Token saved securely
  - [ ] Bot username noted (needed for referral links)
  - [ ] Bot description and commands set

- [ ] **Environment Variables**
  - [ ] BOT_TOKEN ready
  - [ ] ADMIN_IDS (comma-separated Telegram user IDs)
  - [ ] Payment prices configured (if using payments)

## Koyeb Account Setup

- [ ] Koyeb account created
- [ ] Payment method added (if using paid plan)
- [ ] Domain configured (optional)

## Deployment Steps

### Option 1: Docker (Recommended)

1. [ ] Select repository in Koyeb
2. [ ] Choose Dockerfile build method
3. [ ] Set run command: `bash start.sh`
4. [ ] Set port: `10000`
5. [ ] Add environment variables
6. [ ] Click Deploy
7. [ ] Wait for build to complete
8. [ ] Get assigned URL
9. [ ] Run webhook setup script
10. [ ] Test bot in Telegram

### Option 2: Buildpacks

1. [ ] Select repository in Koyeb
2. [ ] Choose Buildpack build method
3. [ ] Koyeb auto-detects Python
4. [ ] Set run command: `web: bash start.sh`
5. [ ] Add environment variables
6. [ ] Click Deploy
7. [ ] Follow same steps 7-10 above

## Post-Deployment Checklist

- [ ] Health check endpoint responding (`/ping`)
- [ ] Webhook set successfully
- [ ] Bot responds to /start command
- [ ] Database initialized
- [ ] Admin commands working
- [ ] Payment flow tested (if applicable)

## Testing Checklist

- [ ] Basic commands
  - [ ] `/start` - Bot responds
  - [ ] `/help` - Help message shows
  - [ ] `/stats` - User stats display

- [ ] Quiz functionality
  - [ ] Difficulty selection works
  - [ ] Subject selection works
  - [ ] Chapter selection works
  - [ ] Questions display correctly
  - [ ] Answer submission works
  - [ ] Score calculation correct
  - [ ] Results display properly

- [ ] Leaderboard
  - [ ] Daily leaderboard shows
  - [ ] Weekly leaderboard shows
  - [ ] Monthly leaderboard shows
  - [ ] All-time leaderboard shows

- [ ] Subscription/Payment (if enabled)
  - [ ] Payment instructions display
  - [ ] Screenshot upload works
  - [ ] Admin approval works
  - [ ] Premium access granted

- [ ] Admin features
  - [ ] Admin panel accessible
  - [ ] User management works
  - [ ] Question management works
  - [ ] Payment approval works

## Monitoring Setup

- [ ] Koyeb logs accessible
- [ ] Error alerts configured (optional)
- [ ] Bot logs checked for issues

## Backup & Recovery

- [ ] Database backup strategy planned
- [ ] Know how to rollback deployment
- [ ] Have deployment checklist documented

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Bot not responding | Check logs in Koyeb Dashboard |
| Webhook not setting | Verify URL is HTTPS and accessible |
| Database errors | Check DATA_DIR environment variable |
| Memory issues | Increase instance size or reduce pool size |
| Slow responses | Enable Redis for session storage |

## Quick Commands

### Set Webhook
```bash
python scripts/setup_webhook.py
```

### Check Deployment
```bash
python scripts/deployment_check.py
```

### View Logs
```bash
# In Koyeb Dashboard -> Logs tab
```

### Rollback
```bash
# In Koyeb Dashboard -> Deployments -> Select previous version
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram Bot Token |
| `WEBHOOK_URL` | Yes | - | Public HTTPS URL |
| `PORT` | No | 10000 | Web server port |
| `DB_TYPE` | No | sqlite | Database type |
| `DATA_DIR` | No | /data | Persistent data directory |
| `ADMIN_IDS` | No | - | Admin Telegram IDs |

## Security Checklist

- [ ] BOT_TOKEN stored securely
- [ ] No hardcoded secrets in code
- [ ] HTTPS enabled (automatic on Koyeb)
- [ ] Admin IDs properly configured
- [ ] Rate limiting enabled

## Performance Checklist

- [ ] Database queries optimized
- [ ] Connection pooling configured
- [ ] Memory usage monitored
- [ ] Response times acceptable

## Next Steps

1. [ ] Set up monitoring/alerting
2. [ ] Create backup strategy
3. [ ] Document admin procedures
4. [ ] Plan scaling strategy
5. [ ] Set up analytics

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Version Deployed:** _______________
**Notes:** _______________

