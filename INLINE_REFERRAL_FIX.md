# Inline Keyboard Fix Plan

## Issue: Referral inline keyboard not working same as reply keyboard

### Problem Summary
The inline keyboard buttons have wrong callback_data causing navigation issues:
1. "Back to Menu" in referral keyboard uses `my_referrals` (should go to main menu)
2. "Back to Referrals" uses `my_referrals` (should use `back_to_referrals`)

### Files to Edit

#### 1. `app/keyboards/menu.py`
**`get_referral_keyboard()` method:**
- Change `callback_data="my_referrals"` → `callback_data="back_to_menu"` for "Back to Menu" button

**`get_my_referrals_keyboard()` method:**
- Change `callback_data="back_to_menu"` → `callback_data="back_to_referrals"` for "Back to Menu" button
- This ensures proper back navigation within referral flow

#### 2. `app/handlers/referral.py`
**`back_to_referral_menu_callback()` function:**
- Change `F.data == "back_to_menu"` → `F.data == "back_to_referrals"`
- Update keyboard to use proper callback data

### Expected Behavior After Fix
1. Reply Keyboard "Referrals" → Shows referral info with inline keyboard
2. Inline "Copy Code" → Shows alert with referral code
3. Inline "Copy Link" → Shows alert with referral link  
4. Inline "Top Referrers" → Shows referral leaderboard
5. Inline "Back to Referrals" → Goes back to referral main screen
6. Inline "Back to Menu" → Goes back to main menu

### Callbacks Mapping
| Button Text | Current (Wrong) | Should Be |
|-------------|-----------------|-----------|
| Back to Menu | `my_referrals` | `back_to_menu` |
| Back to Referrals | `my_referrals` | `back_to_referrals` |

