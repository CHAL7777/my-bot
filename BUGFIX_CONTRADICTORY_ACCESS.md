# 🔧 BUG FIX: Contradictory Access Logic

## Problem Identified

```
User clicks Start Quiz
├── Code: quiz.py → checks `user.approved`
└── Result: user.approved = FALSE → "Access Denied"

User clicks /payment → buy_premium
├── Code: payment_service.py → checks `is_premium OR approved`
└── Result: is_premium = TRUE → "Already has Lifetime Access"

❌ CONTRADICTION: Two different checks, two different results!
```

## Root Cause

**In `quiz.py`:**
```python
if user and not user.approved:  # ← Only checks 'approved'
    return "Access Denied"
```

**In `payment_service.py`:**
```python
is_premium = getattr(user, 'is_premium', False) or getattr(user, 'approved', False)
if is_premium:  # ← Checks BOTH flags (OR condition)
    return "Already has Lifetime Access"
```

The flags `approved` and `is_premium` are out of sync!

---

## ✅ FIXED LOGIC

### Rule: Premium Access = TRUE ONLY IF:
1. User has an APPROVED payment in the `payments` table
2. AND `is_premium = True`
3. AND `approved = True`

### Single Source of Truth Function:

```python
# app/services/access_control_service.py

async def can_access_premium(user_id: int, session) -> Dict[str, Any]:
    """
    SINGLE SOURCE OF TRUTH for premium access.
    
    Premium access = TRUE ONLY IF:
    - User exists
    - AND has an APPROVED payment (status='approved')
    - AND approved_by IS NOT NULL (admin signature)
    - AND approved_at IS NOT NULL (timestamp)
    """
    
    # Step 1: Check user exists
    user = await session.get(User, user_id)
    if not user:
        return {'has_access': False, 'reason': 'NO_USER'}
    
    # Step 2: Check for APPROVED payment (NOT just flags!)
    from sqlalchemy import select, and_
    result = await session.execute(
        select(Payment).where(
            and_(
                Payment.user_id == user_id,
                Payment.status == 'approved',
                Payment.approved_by.isnot(None),  # Admin must exist
                Payment.approved_at.isnot(None)   # Timestamp must exist
            )
        ).order_by(Payment.approved_at.desc()).limit(1)
    )
    approved_payment = result.scalar_one_or_none()
    
    if not approved_payment:
        return {'has_access': False, 'reason': 'NO_APPROVED_PAYMENT'}
    
    # Step 3: Verify screenshot exists
    if not approved_payment.screenshot_file_id:
        return {'has_access': False, 'reason': 'NO_SCREENSHOT'}
    
    # Access granted
    return {'has_access': True, 'payment': approved_payment}
```

---

## 📝 Fixed Code Files

### 1. Fix `app/handlers/quiz.py` - Start Quiz

**BEFORE:**
```python
async def start_quiz_flow(message: types.Message, state: FSMContext, ...):
    user = await user_repo.get_user(user_id)
    if user and not user.approved:  # ❌ WRONG
        await message.answer("❌ Access Denied")
        return
```

**AFTER:**
```python
async def start_quiz_flow(message: types.Message, state: FSMContext, ...):
    async for session in get_db():
        access = await can_access_premium(user_id, session)
        
        if not access['has_access']:
            reason = access['reason']
            
            if reason == 'NO_USER':
                msg = "❌ Please /start first"
            elif reason == 'NO_APPROVED_PAYMENT':
                msg = "❌ Premium Required\n\nUse /payment to unlock premium features"
            elif reason == 'NO_SCREENSHOT':
                msg = "⚠️ Payment verification incomplete\n\nContact admin"
            else:
                msg = "❌ Access Denied"
            
            await message.answer(msg, reply_markup=MainMenuKeyboard.get_main_menu())
            return
```

### 2. Fix `app/handlers/payment.py` - Buy Premium

**BEFORE:**
```python
@router.callback_query(F.data == "buy_premium")
async def buy_premium_callback(callback, state, has_active_subscription):
    if has_active_subscription:  # ❌ FROM MIDDLEWARE (may be stale)
        await callback.message.edit_text("🎉 Already Have Lifetime Access!")
        return
```

**AFTER:**
```python
@router.callback_query(F.data == "buy_premium")
async def buy_premium_callback(callback, state):
    user_id = callback.from_user.id
    
    async for session in get_db():
        # Check ACTUAL approved payment status
        access = await can_access_premium(user_id, session)
        
        if access['has_access']:
            await callback.message.edit_text(
                "🎉 *You Already Have Lifetime Access!*\n\n"
                "Your premium access is active.\n"
                "Use /quiz to start learning!",
                parse_mode='Markdown',
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
            await callback.answer()
            return
    
    # No approved payment - allow payment flow
    await state.set_state(PaymentStates.waiting_for_screenshot)
    await callback.message.edit_text(
        "💎 *One-Time Lifetime Payment*\n\n"
        f"Price: {settings.ONE_TIME_PRICE} birr\n\n"
        "Upload your payment screenshot to proceed.",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_payment_screenshot_keyboard()
    )
```

### 3. Fix `app/services/payment_service.py` - Payment Status Check

**BEFORE:**
```python
async def initiate_payment(self, user_id, subscription_days=None):
    is_premium = getattr(user, 'is_premium', False) or getattr(user, 'approved', False)
    if is_premium:
        raise Exception("✅ Already have lifetime access")
```

**AFTER:**
```python
async def initiate_payment(self, user_id, subscription_days=None):
    user = await self.user_repo.get_user(user_id)
    if not user:
        raise Exception("❌ User not found. Please /start first.")
    
    # Check ACTUAL approved payment
    access = await can_access_premium(user_id, self.payment_repo.session)
    
    if access['has_access']:
        raise Exception(
            "🎉 *You Already Have Lifetime Access!*\n\n"
            "Your account has premium access.\n"
            "Use /quiz to start learning!",
        )
    
    # Check for pending payment
    user_payments = await self.payment_repo.get_user_payments(user_id)
    pending = [p for p in user_payments if p.status == 'pending']
    if pending:
        raise Exception(
            f"⏳ Payment Pending\n\n"
            f"You have a payment (#{pending[0].payment_id}) awaiting review."
        )
```

---

## 🔄 Fixed Logic Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER CLICKS START QUIZ                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ can_access_premium(user_id)   │  ← SINGLE SOURCE
              └───────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
   NO_USER          NO_APPROVED_PAYMENT      HAS_ACCESS
         │                    │                    │
         ▼                    ▼                    ▼
   "Please /start"    "Use /payment"         ✅ ALLOW QUIZ
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Check if PENDING payment     │
              └───────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
   PENDING              NO_PAYMENT            OTHER
         │                    │                    │
         ▼                    ▼                    ▼
   "Awaiting          "Upload screenshot"    "Contact admin"
    approval"              here
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER CLICKS BUY PREMIUM                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ can_access_premium(user_id)   │  ← SAME FUNCTION!
              └───────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
   HAS_ACCESS            NO_ACCESS             ERROR
         │                    │                    │
         ▼                    ▼                    ▼
   "Already             Check if              Handle
    premium!"           PENDING               error
                            │
                            ▼
                   ┌────────────────┐
                   │ PENDING?       │
                   └────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         YES                NO                 ERROR
         │                  │                  │
         ▼                  ▼                  ▼
   "Already          "Upload payment         "Try
    pending!"         screenshot"            again"
```

---

## 📋 SQL Queries for Verification

```sql
-- Check for users with contradictory flags
SELECT 
    user_id, 
    approved, 
    is_premium,
    CASE 
        WHEN approved = TRUE AND is_premium = TRUE THEN 'OK'
        WHEN approved = FALSE AND is_premium = TRUE THEN 'BUG: is_premium TRUE but approved FALSE'
        WHEN approved = TRUE AND is_premium = FALSE THEN 'BUG: approved TRUE but is_premium FALSE'
        ELSE 'OK: Both FALSE'
    END as status
FROM users;

-- Find users who think they have premium but no approved payment
SELECT u.user_id, u.is_premium, u.approved
FROM users u
LEFT JOIN payments p ON u.user_id = p.user_id AND p.status = 'approved'
WHERE u.is_premium = TRUE AND p.payment_id IS NULL;

-- Check actual approved payments
SELECT 
    p.payment_id,
    p.user_id,
    p.status,
    p.approved_by,
    p.approved_at,
    p.screenshot_file_id
FROM payments p
WHERE p.status = 'approved';
```

---

## ✅ Final Checklist

After applying the fix:

- [ ] **Quiz Access Check:** Uses `can_access_premium()` (checks payments table)
- [ ] **Payment Check:** Uses `can_access_premium()` (same function)
- [ ] **No Contradiction:** Both paths agree on access status
- [ ] **Screenshot Required:** Payment approval requires screenshot
- [ ] **Admin Signature:** Approval requires admin_id
- [ ] **Audit Logging:** All access attempts logged

---

## 🚨 Immediate Action Required

**If users are seeing contradictory messages:**

1. Run this SQL to find problematic users:
```sql
SELECT user_id, approved, is_premium 
FROM users 
WHERE approved != is_premium;
```

2. Fix the flags for those users:
```sql
-- If is_premium is TRUE but approved is FALSE
UPDATE users SET approved = TRUE WHERE is_premium = TRUE AND approved = FALSE;

-- If approved is TRUE but is_premium is FALSE  
UPDATE users SET is_premium = TRUE WHERE approved = TRUE AND is_premium = FALSE;
```

3. Ensure new approvals set BOTH flags:
```python
# In approve_payment()
user.is_premium = True    # ← ADD THIS
user.approved = True      # ← KEEP THIS
```

