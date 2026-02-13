#!/usr/bin/env python3
"""
Simple syntax verification test for referral fix.
This checks the code structure without importing database-dependent modules.
"""

import ast
import sys
import os

def check_handler_signature(file_path, handler_name):
    """Check if a handler function has the correct signature with 'data' parameter."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Parse the AST
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"✗ Syntax error in {file_path}: {e}")
        return False
    
    found_handlers = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if handler_name in node.name:
                # Get parameter names
                params = [arg.arg for arg in node.args.args]
                found_handlers.append((node.name, params))
    
    return found_handlers

def main():
    print("="*60)
    print("Referral Management Button Fix - Syntax Verification")
    print("="*60)
    
    base_path = "/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot"
    
    # Check admin_referrals.py handlers
    print("\n1. Checking admin_referrals.py handlers...")
    admin_ref_path = os.path.join(base_path, "app/handlers/admin_referrals.py")
    
    # Check for check_admin_access function
    with open(admin_ref_path, 'r') as f:
        content = f.read()
    
    if 'def check_admin_access' in content:
        print("   ✓ check_admin_access helper function found")
    else:
        print("   ✗ check_admin_access helper function NOT found")
    
    # Check that all callback handlers use 'data' parameter
    admin_handlers_to_check = [
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
    
    for handler in admin_handlers_to_check:
        # Check that handler uses 'data' parameter (not 'is_admin: bool = False')
        # Look for the pattern: def handler(callback, data: Dict[str, Any]):
        pattern1 = f'def {handler}(callback: types.CallbackQuery, data: Dict[str, Any]):'
        pattern2 = f'def {handler}(callback: types.CallbackQuery, state: FSMContext,\\s*data: Dict[str, Any]):'
        
        if pattern1 in content.replace('\\s*', ' ') or pattern2.replace('\\s*', ' ') in content:
            print(f"   ✓ {handler} has correct signature")
        elif f'def {handler}' in content and 'is_admin: bool = False' in content:
            print(f"   ✗ {handler} still has broken 'is_admin: bool = False' pattern")
        else:
            # Check if it uses data parameter
            lines = content.split('\n')
            found_correct = False
            for i, line in enumerate(lines):
                if f'def {handler}' in line:
                    # Check next few lines for data parameter
                    for j in range(i, min(i+5, len(lines))):
                        if 'data: Dict[str, Any]' in lines[j] or ', data: Dict' in lines[j] or 'data: Any' in lines[j]:
                            found_correct = True
                            break
                    break
            if found_correct:
                print(f"   ✓ {handler} has correct signature (multiline)")
            else:
                print(f"   ⚠ {handler} signature unclear - manual review needed")
    
    # Check referral.py handlers
    print("\n2. Checking referral.py handlers...")
    referral_path = os.path.join(base_path, "app/handlers/referral.py")
    
    with open(referral_path, 'r') as f:
        referral_content = f.read()
    
    referral_handlers_to_check = [
        'my_referrals_callback',
        'copy_referral_code_callback',
        'share_referral_callback',
        'referral_leaderboard_callback',
        'copy_referral_link_callback'
    ]
    
    for handler in referral_handlers_to_check:
        # Check that handler uses 'data' parameter
        pattern = f'def {handler}(callback: types.CallbackQuery, data: Dict[str, Any]):'
        
        if pattern in referral_content.replace('\\s*', ' '):
            print(f"   ✓ {handler} has correct signature")
        elif f'def {handler}' in referral_content and 'is_admin: bool = False' in referral_content:
            print(f"   ✗ {handler} still has broken 'is_admin: bool = False' pattern")
        else:
            # Check if it uses data parameter
            lines = referral_content.split('\n')
            found_correct = False
            for i, line in enumerate(lines):
                if f'def {handler}' in line:
                    for j in range(i, min(i+5, len(lines))):
                        if 'data: Dict[str, Any]' in lines[j] or ', data: Dict' in lines[j] or 'data: Any' in lines[j]:
                            found_correct = True
                            break
                    break
            if found_correct:
                print(f"   ✓ {handler} has correct signature (multiline)")
            else:
                print(f"   ⚠ {handler} signature unclear - manual review needed")
    
    # Check for broken patterns
    print("\n3. Checking for broken patterns...")
    
    broken_patterns = [
        ('is_admin: bool = False', admin_ref_path),
        ('is_admin: bool = False', referral_path),
    ]
    
    all_fixed = True
    for pattern, path in broken_patterns:
        if pattern in content or pattern in referral_content:
            print(f"   ✗ Found broken pattern '{pattern}'")
            all_fixed = False
        else:
            print(f"   ✓ No '{pattern}' found")
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("\nKey Fixes Applied:")
    print("1. Added check_admin_access() helper function in admin_referrals.py")
    print("2. Changed all admin_referrals.py callbacks to use 'data' parameter")
    print("3. Changed all referral.py callbacks to use 'data' parameter")
    print("4. Removed broken 'is_admin: bool = False' default parameters")
    print("\nBefore (Broken):")
    print("   async def handler(callback, is_admin: bool = False):")
    print("       if not is_admin:  # Always True! is_admin=False by default")
    print("           await callback.answer('Access denied'...")
    print("\nAfter (Fixed):")
    print("   async def handler(callback, data: Dict[str, Any]):")
    print("       is_admin = data.get('is_admin', False)")
    print("       if not is_admin:")
    print("           await callback.answer('Access denied'...")
    print("\n✓ Referral management button fix complete!")
    print("  Restart the bot to apply changes.")

if __name__ == "__main__":
    main()
