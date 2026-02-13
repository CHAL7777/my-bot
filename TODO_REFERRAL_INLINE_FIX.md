# TODO: Fix Inline Keyboard Referral Consistency

## Issues Found:
1. `get_referral_keyboard` back button goes to main menu instead of referrals
2. Inline keyboard doesn't have "Copy Link" button (only has "Copy Code")
3. Handler for `back_to_referrals` callback missing

## Plan:

### Step 1: Update `app/keyboards/menu.py`
- [ ] Update `get_referral_keyboard()`:
  - Add "Copy Link" button with callback `copy_referral_link`
  - Change "Back to Menu" callback from `back_to_menu` to `my_referrals`

### Step 2: Update `app/handlers/referral.py`
- [ ] Add handler `back_to_referrals_callback()` for `my_referrals` callback

### Step 3: Run verification test
- [ ] Run `python test_referral_buttons.py` to verify fixes

## Expected Changes:

### Before (get_referral_keyboard):
```python
keyboard = [
    [Share on Telegram button],
    [Copy Code button],  # Only copy code
    [Leaderboard button],
    [Back to Menu - callback: back_to_menu]  # Wrong navigation
]
```

### After (get_referral_keyboard):
```python
keyboard = [
    [Share on Telegram button],
    [Copy Code button],
    [Copy Link button],  # NEW: Copy link button
    [Leaderboard button],
    [Back to Referrals - callback: my_referrals]  # FIXED: Stay in referral flow
]
```

