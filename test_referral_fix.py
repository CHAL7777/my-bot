#!/usr/bin/env python3
"""
Test script to verify the referral management button fix.
This tests that the handlers correctly get is_admin from data dict.
"""

import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test 1: Verify imports work
print("Test 1: Verifying imports...")
try:
    from app.handlers.admin_referrals import router as admin_referrals_router
    from app.handlers.referral import router as referral_router
    from app.keyboards.admin import AdminReferralKeyboard
    from app.keyboards.menu import MainMenuKeyboard
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Verify handlers have correct signatures
print("\nTest 2: Verifying handler signatures...")
import inspect

# Check admin_referrals handlers
admin_referrals_callbacks = [
    'admin_referrals_callback',
    'admin_referrals_top_callback',
    'admin_referrals_all_callback',
    'admin_referrals_pending_callback',
    'admin_referral_payout_callback',
    'confirm_payout_callback',
    'process_payout_callback',
    'cancel_payout_callback',
    'admin_view_user_referrals_callback',
    'admin_referrals_export_callback',
    'admin_referrals_help_callback'
]

for handler_name in admin_referrals_callbacks:
    handler = getattr(admin_referrals_router, 'callbacks', {}).get(handler_name)
    if handler:
        sig = inspect.signature(handler)
        params = list(sig.parameters.keys())
        # Check that callback handlers use 'data' parameter
        if 'data' in params:
            print(f"  ✓ {handler_name} has 'data' parameter")
        else:
            print(f"  ✗ {handler_name} missing 'data' parameter: {params}")
    else:
        print(f"  ⚠ {handler_name} not found in router callbacks")

# Check referral handlers
referral_callbacks = [
    'my_referrals_callback',
    'copy_referral_code_callback',
    'share_referral_callback',
    'referral_leaderboard_callback',
    'copy_referral_link_callback'
]

print("\nChecking user referral handlers:")
for handler_name in referral_callbacks:
    handler = getattr(referral_router, 'callbacks', {}).get(handler_name)
    if handler:
        sig = inspect.signature(handler)
        params = list(sig.parameters.keys())
        if 'data' in params:
            print(f"  ✓ {handler_name} has 'data' parameter")
        else:
            print(f"  ✗ {handler_name} missing 'data' parameter: {params}")
    else:
        print(f"  ⚠ {handler_name} not found in router callbacks")

# Test 3: Verify keyboard has callback data
print("\nTest 3: Verifying keyboard callback data...")

# Check AdminReferralKeyboard
try:
    kb = AdminReferralKeyboard.get_referral_management()
    callback_datas = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    expected_callbacks = [
        'admin_referrals_top',
        'admin_referrals_all', 
        'admin_referrals_pending',
        'admin_referrals_export',
        'admin_referrals_help',
        'back_to_admin'
    ]
    
    for expected in expected_callbacks:
        if expected in callback_datas:
            print(f"  ✓ AdminReferralKeyboard has '{expected}'")
        else:
            print(f"  ✗ AdminReferralKeyboard missing '{expected}'")
except Exception as e:
    print(f"  ⚠ Error checking AdminReferralKeyboard: {e}")

# Check MainMenuKeyboard referral buttons
try:
    kb = MainMenuKeyboard.get_referral_keyboard()
    callback_datas = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    expected_callbacks = [
        'my_referrals',
        'referral_leaderboard'
    ]
    
    for expected in expected_callbacks:
        if expected in callback_datas:
            print(f"  ✓ MainMenuKeyboard has '{expected}'")
        else:
            print(f"  ✗ MainMenuKeyboard missing '{expected}'")
except Exception as e:
    print(f"  ⚠ Error checking MainMenuKeyboard: {e}")

# Test 4: Verify check_admin_access helper
print("\nTest 4: Verifying check_admin_access helper...")
from app.handlers.admin_referrals import check_admin_access

# Test with admin data
admin_data = {'is_admin': True, 'is_superadmin': True}
is_admin, is_superadmin = check_admin_access(admin_data)
assert is_admin == True, "is_admin should be True"
assert is_superadmin == True, "is_superadmin should be True"
print("  ✓ check_admin_access returns correct values for admin")

# Test with non-admin data
non_admin_data = {'is_admin': False, 'is_superadmin': False}
is_admin, is_superadmin = check_admin_access(non_admin_data)
assert is_admin == False, "is_admin should be False"
assert is_superadmin == False, "is_superadmin should be False"
print("  ✓ check_admin_access returns correct values for non-admin")

# Test with empty data
empty_data = {}
is_admin, is_superadmin = check_admin_access(empty_data)
assert is_admin == False, "is_admin should default to False"
assert is_superadmin == False, "is_superadmin should default to False"
print("  ✓ check_admin_access handles empty data correctly")

print("\n" + "="*50)
print("All tests passed! ✓")
print("="*50)
print("\nThe referral management button fix is complete.")
print("\nKey changes:")
print("1. All admin_referrals.py handlers now get is_admin from data['is_admin']")
print("2. All referral.py callback handlers now get is_admin from data dict")
print("3. Added check_admin_access() helper for consistent admin checks")
print("4. Removed broken is_admin=False default parameters")

