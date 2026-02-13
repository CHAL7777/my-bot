#!/usr/bin/env python3
"""
Standalone test script to verify webhook URL validation functions.
"""

import sys
import os
import re
import socket
from urllib.parse import urlparse

# ============== Copy of validation functions from webhook_main.py ==============

def validate_webhook_url(webhook_url: str) -> tuple[bool, str]:
    """Validate webhook URL format and DNS resolution."""
    if not webhook_url:
        return False, "WEBHOOK_URL is empty or not set"
    
    clean_url = webhook_url.strip().rstrip('/')
    
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(clean_url):
        return False, f"Invalid URL format: {webhook_url}"
    
    try:
        parsed = urlparse(clean_url)
        hostname = parsed.hostname
        
        if not hostname:
            return False, f"Could not extract hostname from: {webhook_url}"
        
        print(f"  Validating DNS for hostname: {hostname}")
        socket.gethostbyname(hostname)
        print(f"  DNS resolution successful for {hostname}")
        
        return True, ""
        
    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname: {hostname} - {e}"
    except Exception as e:
        return False, f"Unexpected error validating URL: {e}"


def build_webhook_url(base_url: str, webhook_path: str) -> str:
    """Build the complete webhook URL."""
    clean_base = base_url.strip().rstrip('/')
    clean_path = webhook_path.strip()
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    clean_base = clean_base.rstrip('/')
    return f"{clean_base}{clean_path}"


def test_build_webhook_url():
    """Test building webhook URLs."""
    print("Testing build_webhook_url()...")
    
    tests = [
        ("https://example.com", "/webhook", "https://example.com/webhook"),
        ("https://example.com/", "/webhook", "https://example.com/webhook"),
        ("https://example.com", "/webhook/", "https://example.com/webhook"),
        ("https://example.com", "webhook", "https://example.com/webhook"),
        ("http://localhost:8000", "/webhook", "http://localhost:8000/webhook"),
    ]
    
    all_passed = True
    for base, path, expected in tests:
        result = build_webhook_url(base, path)
        status = "OK" if result == expected else "FAIL"
        print(f"  {status} build_webhook_url('{base}', '{path}') = '{result}'")
        if result != expected:
            print(f"     Expected: '{expected}'")
            all_passed = False
    
    return all_passed


def test_validate_webhook_url():
    """Test webhook URL validation."""
    print("\nTesting validate_webhook_url()...")
    
    # Test URL format validation only (DNS requires network)
    print("\n  Testing URL format validation only:")
    
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    valid_formats = [
        "https://example.com/webhook",
        "https://mybot.koyeb.app/webhook",
        "http://localhost:8000/webhook",
        "https://api.telegram.org/webhook",
        "http://127.0.0.1:8000/webhook",
    ]
    
    all_passed = True
    for url in valid_formats:
        clean_url = url.strip().rstrip('/')
        is_valid = bool(url_pattern.match(clean_url))
        status = "OK" if is_valid else "FAIL"
        print(f"  {status} Format valid: '{url}'")
        if not is_valid:
            all_passed = False
    
    print("\n  Testing invalid formats:")
    invalid_formats = [
        "",
        "not-a-url",
        "ftp://example.com/webhook",
    ]
    
    for url in invalid_formats:
        clean_url = url.strip().rstrip('/')
        is_valid = bool(clean_url and url_pattern.match(clean_url))
        status = "OK" if not is_valid else "FAIL"
        print(f"  {status} Correctly rejected: '{url}'")
        if is_valid:
            all_passed = False
    
    return all_passed


def main():
    print("=" * 60)
    print("Webhook URL Validation Tests (Standalone)")
    print("=" * 60)
    
    passed1 = test_build_webhook_url()
    passed2 = test_validate_webhook_url()
    
    print("\n" + "=" * 60)
    if passed1 and passed2:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 60)
    
    print("\nTo diagnose webhook issues in production:")
    print("1. Check WEBHOOK_URL environment variable is correctly set")
    print("2. Verify DNS is configured for your domain")
    print("3. Ensure your server is accessible via HTTPS")
    print("4. Visit /webhook/dns endpoint when running the bot")


if __name__ == "__main__":
    main()

