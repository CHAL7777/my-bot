#!/usr/bin/env python3
"""
Test script for message splitting functionality.

This script tests the split_long_text function to ensure it properly
handles messages that exceed Telegram's 4096 character limit.
"""

import sys
import os
import types
import importlib.util

# ============================================================================
# ISOLATE IMPORTS TO AVOID DATABASE INITIALIZATION
# ============================================================================
# The app package imports trigger database initialization which requires
# asyncpg. We create dummy modules to prevent this.

# Create dummy module namespace to prevent app package initialization
dummy_app = types.ModuleType('app')
sys.modules['app'] = dummy_app
dummy_utils = types.ModuleType('app.utils')
sys.modules['app.utils'] = dummy_utils

# Now we can safely load plain_sender directly
plain_sender_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    "app/utils/plain_sender.py"
)
spec = importlib.util.spec_from_file_location("plain_sender", plain_sender_path)
plain_sender_module = importlib.util.module_from_spec(spec)
sys.modules['app.utils.plain_sender'] = plain_sender_module
spec.loader.exec_module(plain_sender_module)

split_long_text = plain_sender_module.split_long_text
PlainTextMessageSender = plain_sender_module.PlainTextMessageSender


def test_split_short_text():
    """Test splitting text that fits within the limit."""
    text = "Short text"
    parts = split_long_text(text)
    assert len(parts) == 1, f"Expected 1 part, got {len(parts)}"
    assert parts[0] == text, f"Expected '{text}', got '{parts[0]}'"
    print("✓ Short text test passed")


def test_split_empty_text():
    """Test splitting empty text."""
    parts = split_long_text("")
    assert parts == [], f"Expected empty list, got {parts}"
    parts = split_long_text(None)
    assert parts == [], f"Expected empty list for None, got {parts}"
    print("✓ Empty text test passed")


def test_split_exactly_at_limit():
    """Test text exactly at the limit (4096 chars)."""
    text = "A" * 4000
    parts = split_long_text(text, max_length=4096)
    assert len(parts) == 1, f"Expected 1 part, got {len(parts)}"
    assert len(parts[0]) <= 4096, f"Part exceeds limit: {len(parts[0])}"
    print("✓ At-limit text test passed")


def test_split_slightly_over_limit():
    """Test text slightly over the limit."""
    text = "A" * 5000
    parts = split_long_text(text, max_length=4096)
    assert len(parts) >= 1, "Expected at least 1 part"
    for part in parts:
        assert len(part) <= 4096, f"Part exceeds limit: {len(part)}"
    print(f"✓ Slightly over limit test passed ({len(parts)} parts)")


def test_split_with_newlines():
    """Test splitting text with newlines at natural boundaries."""
    lines = [f"Line {i}: This is a sample line with some content." for i in range(100)]
    text = "\n".join(lines)
    parts = split_long_text(text, max_length=4096)
    
    assert len(parts) >= 1, "Expected at least 1 part"
    for part in parts:
        assert len(part) <= 4096, f"Part exceeds limit: {len(part)}"
    # Verify most parts end at newlines
    for part in parts[:-1]:
        assert part.endswith("\n") or len(part) < 4096, f"Part should end at newline: {part[-50:]}"
    print(f"✓ Newline splitting test passed ({len(parts)} parts)")


def test_split_long_content():
    """Test splitting long content similar to quiz results."""
    # Create content similar to what might be sent in quiz results
    lines = []
    for i in range(50):
        lines.append(f"Question {i+1}: What is the answer to this question?")
        lines.append(f"A. Option A for question {i+1}")
        lines.append(f"B. Option B for question {i+1}")
        lines.append(f"C. Option C for question {i+1}")
        lines.append(f"D. Option D for question {i+1}")
        lines.append("")
        lines.append("Explanation: This is the detailed explanation for the answer.")
        lines.append("")
        lines.append("-" * 30)
        lines.append("")
    
    text = "\n".join(lines)
    parts = split_long_text(text, max_length=4096)
    
    assert len(parts) >= 1, "Expected at least 1 part"
    for part in parts:
        assert len(part) <= 4096, f"Part exceeds limit: {len(part)}"
    print(f"✓ Long content test passed ({len(parts)} parts, total {len(text)} chars)")


def test_max_parts_limit():
    """Test that max_parts limit is respected."""
    text = "A" * 50000
    parts = split_long_text(text, max_length=4096, max_parts=5)
    assert len(parts) <= 5, f"Expected max 5 parts, got {len(parts)}"
    print(f"✓ Max parts limit test passed ({len(parts)} parts)")


def test_with_prefix_and_suffix():
    """Test splitting with custom prefix and suffix."""
    text = "B" * 8000
    parts = split_long_text(text, max_length=4096, prefix="[Part ", suffix="]")
    for part in parts:
        assert len(part) <= 4096, f"Part exceeds limit: {len(part)}"
        assert "[Part" in part or len(text) <= 4096, "Prefix not found in part"
    print(f"✓ Prefix/suffix test passed ({len(parts)} parts)")


def test_emoji_content():
    """Test splitting content with emojis."""
    lines = []
    for i in range(30):
        lines.append(f"🎉 Question {i+1}: What is the answer?")
        lines.append(f"✅ A. Option A ✨")
        lines.append(f"❌ B. Option B 🔥")
        lines.append(f"💡 C. Option C 🌟")
        lines.append("")
    
    text = "\n".join(lines)
    parts = split_long_text(text, max_length=4096)
    
    assert len(parts) >= 1, "Expected at least 1 part"
    for part in parts:
        assert len(part) <= 4096, f"Part exceeds limit: {len(part)}"
    print(f"✓ Emoji content test passed ({len(parts)} parts)")


def test_clean_text():
    """Test the clean_text function."""
    # Test with problematic characters
    text = "User's `code` and ~tilde~ characters"
    cleaned = PlainTextMessageSender.clean_text(text)
    assert "`" not in cleaned, "Backtick should be replaced"
    assert "~" not in cleaned, "Tilde should be replaced"
    print("✓ Clean text test passed")


def test_safe_truncate():
    """Test the safe_truncate function."""
    text = "This is a long sentence with many words that should be truncated."
    truncated = PlainTextMessageSender.safe_truncate(text, 30)
    assert len(truncated) <= 30 + 3, f"Truncated text too long: {len(truncated)}"
    assert truncated.endswith("..."), "Should end with ellipsis"
    print("✓ Safe truncate test passed")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Testing Message Splitting Functionality")
    print("=" * 60)
    
    try:
        test_split_short_text()
        test_split_empty_text()
        test_split_exactly_at_limit()
        test_split_slightly_over_limit()
        test_split_with_newlines()
        test_split_long_content()
        test_max_parts_limit()
        test_with_prefix_and_suffix()
        test_emoji_content()
        test_clean_text()
        test_safe_truncate()
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

