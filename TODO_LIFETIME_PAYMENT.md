# Lifetime Access Payment System Implementation

## Goal: Implement 150 ETB one-time lifetime payment system

### Changes Required

- [ ] 1. Update price in config.py (1500 → 150 ETB)
- [ ] 2. Update payment.py - add duplicate payment prevention
- [ ] 3. Update payment messages to show 150 ETB
- [ ] 4. Update admin notification to mention 150 ETB
- [ ] 5. Test the flow

## Implementation Details

### 1. Config Update (`app/config.py`)
```python
ONE_TIME_PRICE: float = float(os.getenv("ONE_TIME_PRICE", 150))  # 150 ETB
```

### 2. Payment Handler Updates (`app/handlers/payment.py`)
- Add duplicate payment check in `buy_premium_callback`
- Update all price displays to show 150 ETB
- Add "Already has lifetime access" message

### 3. Admin Handler Updates (`app/handlers/admin_payments.py`)
- Update admin notification to show 150 ETB
- Add "Lifetime Payment" label

## Testing Checklist
- [ ] User with approved payment sees "Already have lifetime access"
- [ ] User without payment sees 150 ETB price
- [ ] Admin sees 150 ETB in pending payments
- [ ] Quiz access works after payment approval

