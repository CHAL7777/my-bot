#!/usr/bin/env python3
"""
Test script to verify referral parsing logic.
Run this to test if referral code parsing works correctly.
"""

import asyncio
import sys
sys.path.insert(0, '/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot')


# Test the referral code parsing logic directly (same as in referral_service.py)
def parse_referral_code(deep_link: str):
    """
    Parse referral code from Telegram deep link.
    
    Supports formats:
    - /start=REFCODE (Telegram deep link format)
    - /start REFCODE (space-separated format)
    - ref_REFCODE (short format)
    """
    if not deep_link:
        return None
    
    # Handle Telegram deep link format: /start=REFCODE
    if '=' in deep_link:
        parts = deep_link.split('=', 1)
        if len(parts) == 2:
            code = parts[1].strip()
            if code:
                return code
        return None
    
    # Handle short format: ref_REFCODE
    if deep_link.startswith('ref_'):
        return deep_link[4:]
    
    # Handle space-separated format: /start REFCODE
    # Split by space and get the last part
    parts = deep_link.split()
    if len(parts) >= 2:
        # Check if last part looks like a referral code (starts with REF)
        last_part = parts[-1]
        if last_part.startswith('REF') and len(last_part) >= 6:
            return last_part
    
    return None


def test_referral_parsing():
    """Test referral code parsing logic"""
    print("Testing Referral Code Parsing Logic...")
    print("=" * 60)
    
    test_cases = [
        # (input, expected_output, description)
        ("/start=REF123", "REF123", "Standard Telegram deep link"),
        ("/start=ABCDEFGH", "ABCDEFGH", "8-character code"),
        ("/start REF456", "REF456", "Space-separated format"),
        ("/start ref_789XYZ", "789XYZ", "Short format with ref_"),
        ("ref_MYCODE", "MYCODE", "Just ref_ prefix"),
        ("/start", None, "No code provided"),
        ("/start=", None, "Empty code"),
        ("", None, "Empty string"),
        ("/start ref_", None, "Incomplete code"),
        ("/start=CODE1=EXTRA", "CODE1=EXTRA", "Code with equals sign"),
        ("/start=123_456", "123_456", "Code with underscore"),
    ]
    
    passed = 0
    failed = 0
    
    for deep_link, expected, description in test_cases:
        result = parse_referral_code(deep_link)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"  {status}: {description}")
        print(f"         Input: '{deep_link}'")
        print(f"         Expected: '{expected}'")
        print(f"         Got: '{result}'")
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


def test_referral_link_generation():
    """Test referral link generation"""
    print("\nTesting Referral Link Generation...")
    print("=" * 60)
    
    bot_username = "SmartITestExambot"
    
    test_codes = [
        "REF12345",
        "ABCDEFGH",
        "12345678",
    ]
    
    for code in test_codes:
        link = f"https://t.me/{bot_username}?start={code}"
        print(f"  Referral code: {code}")
        print(f"  Generated link: {link}")
        print()
    
    print("=" * 60)


def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("REFERRAL SYSTEM VERIFICATION")
    print("=" * 60)
    print()
    
    # Test 1: Parsing logic
    parsing_ok = test_referral_parsing()
    
    # Test 2: Link generation
    test_referral_link_generation()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if parsing_ok:
        print("✓ All parsing tests passed!")
    else:
        print("✗ Some parsing tests failed!")
    
    print("\nThe referral system works as follows:")
    print("1. User shares their referral link: https://t.me/BotName?start=REFCODE")
    print("2. New user clicks the link and sends /start=REFCODE")
    print("3. The bot parses 'REFCODE' from the message")
    print("4. Bot looks up the user with that referral code")
    print("5. Bot creates a 'pending' referral record")
    print("6. When the referred user gets approved, the referral is 'completed'")
    print()
    print("To test:")
    print("- Share a referral link with someone")
    print("- Have them click and send /start=YOURCODE")
    print("- Check their stats using /referral")
    print("=" * 60)
    
    return 0 if parsing_ok else 1


if __name__ == "__main__":
    exit(main())
