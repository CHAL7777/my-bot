#!/usr/bin/env python3
"""
Test script to verify the parse error fix.

This script tests that Markdown formatting is properly stripped from messages
to prevent "can't parse entities" errors when the bot uses HTML parse mode.
"""

import sys
sys.path.insert(0, '/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot')

from app.utils.plain_sender import PlainTextMessageSender, _strip_markdown


def test_strip_markdown():
    """Test the Markdown stripping function."""
    print("Testing _strip_markdown function...")
    
    test_cases = [
        # (input, expected_output)
        ("Hello *world*", "Hello world"),
        ("**bold text**", "bold text"),
        ("_italic text_", "italic text"),
        ("__italic text__", "italic text"),
        ("`code`", ""),
        ("~~strikethrough~~", ""),
        ("*bold* and **also bold**", "bold and also bold"),
        ("Normal text with *bold* in between", "Normal text with bold in between"),
        ("***bold and italic***", "bold and italic"),
        ("No formatting here", "No formatting here"),
        ("*leading asterisk", "leading asterisk"),
        ("trailing asterisk*", "trailing asterisk"),
        ("_leading underscore", "leading underscore"),
        ("trailing underscore_", "trailing underscore"),
    ]
    
    all_passed = True
    for input_text, expected in test_cases:
        result = _strip_markdown(input_text)
        if result != expected:
            print(f"  FAIL: '{input_text}' -> '{result}' (expected '{expected}')")
            all_passed = False
        else:
            print(f"  PASS: '{input_text}' -> '{result}'")
    
    return all_passed


def test_clean_text():
    """Test the clean_text method."""
    print("\nTesting clean_text method...")
    
    test_cases = [
        # (input, expected_output)
        ("Hello *world*", "Hello world"),
        ("**bold**", "bold"),
        ("User's `code`", "User's 'code'"),
        ("Price ~discount~", "Price -discount-"),
        ("<script>alert('xss')</script>", "<script>alert('xss')</script>"),
        ("*bold* and _italic_", "bold and italic"),
    ]
    
    all_passed = True
    for input_text, expected in test_cases:
        result = PlainTextMessageSender.clean_text(input_text)
        if result != expected:
            print(f"  FAIL: '{input_text}' -> '{result}' (expected '{expected}')")
            all_passed = False
        else:
            print(f"  PASS: '{input_text}' -> '{result}'")
    
    return all_passed


def test_real_world_examples():
    """Test with real-world message examples from the bot."""
    print("\nTesting with real-world examples...")
    
    # Examples from feedback_messages.py that could cause parse errors
    real_world_examples = [
        (
            "🌱🔍 *LEARNING JOURNEY!*",
            "LEARNING JOURNEY!"
        ),
        (
            "This is *just the beginning*! Learning takes time and *you're on your way*!",
            "This is just the beginning! Learning takes time and you're on your way!"
        ),
        (
            "🏆 *YOUR RESULTS:*",
            "YOUR RESULTS:"
        ),
        (
            "✅ *{correct}/{total}* questions correct",
            " questions correct"  # Placeholders remain, but formatting is stripped
        ),
        (
            "📈 *Accuracy:* *{accuracy:.0f}%*",
            "Accuracy:  %"  # Placeholders remain, but formatting is stripped
        ),
    ]
    
    all_passed = True
    for input_text, expected_partial in real_world_examples:
        result = PlainTextMessageSender.clean_text(input_text)
        # Check that Markdown is stripped (result should not contain * or _ for formatting)
        if '*' in result or ('_' in result and ' ' not in result):
            print(f"  FAIL: Markdown not stripped from: '{result}'")
            all_passed = False
        else:
            print(f"  PASS: '{input_text}' -> '{result}'")
    
    return all_passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("Parse Error Fix - Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("strip_markdown", test_strip_markdown()))
    results.append(("clean_text", test_clean_text()))
    results.append(("real_world_examples", test_real_world_examples()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed! The parse error fix is working correctly.")
    else:
        print("Some tests failed! Please review the failures above.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

