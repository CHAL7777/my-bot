# Referral System - How to Share Your Link

## For Users

### Get Your Referral Link
1. Open your Telegram and search for @SmartITestExambot
2. Start the bot by sending `/start`
3. Send the `/referral` command
4. You'll receive your unique referral link and code

### Share Your Link
Your referral link format:
```
https://t.me/SmartITestExambot?start=ref_YOUR_CODE
```

Example: `https://t.me/SmartITestExambot?start=ref_ABC12345`

### Reward System
- Refer **5 friends** who complete registration
- Earn **lifetime premium access**!

---

## For Bot Admin - Configuration Check

### Verify BOT_USERNAME Setting
Your `.env` file should have:
```env
BOT_USERNAME=SmartITestExambot
```

### Check Current Setting
Run this command to verify:
```bash
grep BOT_USERNAME .env
```

If not set, add it:
```bash
echo "BOT_USERNAME=SmartITestExambot" >> .env
```

Then restart the bot:
```bash
./restart_bot.sh
```

---

## Referral Link Testing

Test your referral system:
1. Copy your referral link
2. Open in a new Telegram chat or browser
3. Click "Start" button
4. The bot should welcome the new user and credit the referrer

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Referral link not working | Verify `BOT_USERNAME` in .env is set to `SmartITestExambot` |
| No referral code generated | User needs to send `/referral` command first |
| Referrals not counted | Check database migration was run (`scripts/referral_admin_migration.sql`) |

---

## Quick Share Text

Use this template to share on WhatsApp, Facebook, etc.:

```
📚 Join me on SmartITestExambot!

Take quizzes, track your progress, and compete on leaderboards.

Use my referral link:
https://t.me/SmartITestExambot?start=ref_[YOUR_CODE]

#SmartITest #QuizBot #ExamPrep
```

