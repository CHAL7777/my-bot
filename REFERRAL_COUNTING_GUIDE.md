# How Referrals Are Counted

## ⚠️ IMPORTANT: Referrals Count After Payment Approval!

**Referrals are NOW counted ONLY after the referred user:**
1. Joins via referral link ✅
2. **Makes a payment** 💰
3. **Gets approved by admin** ✅

---

## 📊 Referral Counting Flow (NEW)

```
User A shares link: https://t.me/SmartITestExambot?start=ref_REFXYZ123
        ↓
User B clicks link and sends /start
        ↓
Bot detects referral code (ref_REFXYZ123)
        ↓
Bot creates Referral record (status='PENDING')
        ↓
--- User B is in PENDING status (not counted yet) ---
        ↓
User B makes payment and uploads screenshot
        ↓
Admin reviews and APPROVES the payment
        ↓
Bot marks referral as "COMPLETED" ✅
        ↓
User A's referral_count is incremented by 1
        ↓
Check if User A qualifies for reward (5 completed referrals)
```

## 🔢 What Gets Counted (UPDATED)

| Status | Description | Counted? |
|--------|-------------|----------|
| `pending` | Referred user joined but hasn't paid/approved yet | ❌ NO |
| `completed` | Referred user paid AND got approved | ✅ YES |
| `cancelled` | Referral was cancelled/invalid | ❌ NO |

## 📈 Statistics Displayed (`/referral` command)

```python
{
    'total_sent': 10,      # All referral links ever shared
    'completed': 7,        # ✅ Paid & Approved (counts toward reward)
    'pending': 2,          # Joined but not paid yet
    'cancelled': 1,        # Invalid/cancelled
    'success_rate': 70.0   # completed / completed * 100 (only counted ones)
}
```

> **Note:** Success rate is now calculated only from completed referrals, not total_sent.

## 🎁 Reward System

**Threshold:** `REFERRAL_REWARD_THRESHOLD = 5` (configurable)

When a user reaches **5 completed referrals**:
1. Bot checks if user is already premium
2. If not premium → grants `is_premium = True`
3. User gets **lifetime premium access**

## 💡 Key Points

1. **Immediate Completion:** Referrals are marked completed immediately when the new user joins (not after they take a quiz)

2. **No Self-Referral:** Users cannot refer themselves (same user_id check)

3. **Unique Referrals:** Each user can only be referred once (unique constraint on referrer_id + referred_id)

4. **Two Counters:**
   - `referrals` table: Tracks individual referral records
   - `User.referral_count`: Cached count for fast leaderboard queries

## 🔧 Database Tables Involved

### `users` table
```sql
referral_code VARCHAR(20)    -- User's unique code (e.g., "REFZYG782M2")
referral_count INT DEFAULT 0 -- Cached count of completed referrals
```

### `referrals` table
```sql
id INT PRIMARY KEY
referrer_id BIGINT           -- Who referred
referred_id BIGINT           -- Who joined
status ENUM('pending', 'completed', 'cancelled')
created_at DATETIME
completed_at DATETIME
reward_claimed BOOLEAN
```

## 📋 Example Scenario (UPDATED)

```
Day 1: User A sends /referral → gets code "REFZYG782M2"
Day 2: User B clicks https://t.me/SmartITestExambot?start=ref_REFXYZ123
       → Referral record created (status=pending)
       → User A's count = 0 (not counted yet!)
Day 3: User B uploads payment screenshot
Day 4: Admin approves User B's payment
       → Referral marked as completed ✅
       → User A.referral_count = 1 (NOW COUNTED!)
Day 5-8: User C, D, E, F join via referral and get approved
       → User A.referral_count = 5
       → User A automatically gets premium! 🎉
```

> **Key Difference:** Referrals are NOT counted immediately when someone joins.
> They are counted ONLY after the referred user pays AND gets approved.

## ⚠️ Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Count not increasing | Referral not processed | Check `/start` handler calls `process_referral()` |
| Shows wrong count | Cached count outdated | Run `scripts/fix_user_states.py` |
| Link shows "YourBotName" | `BOT_USERNAME` not set | Set in `.env` or restart bot |
| User can't get referral code | User not registered | User must start bot first |

## 🔍 View Referral Stats

**For Users:**
```
Send: /referral
```

**For Admins (Admin Panel):**
- Navigate to Users section
- View referral_count column
- Check referrals table for details

