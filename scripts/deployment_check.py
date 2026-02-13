#!/usr/bin/env python3
"""
Deployment Verification Script

Run this script to verify your Koyeb deployment is working correctly.
"""

import os
import sys
import json
import requests
import subprocess


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(name, status, details=""):
    icon = "✅" if status else "❌"
    print(f"{icon} {name}: {details or ('OK' if status else 'FAILED')}")
    return status


def check_environment():
    """Check required environment variables."""
    print_header("Environment Variables")
    
    required = ["BOT_TOKEN"]
    optional = [
        "WEBHOOK_URL", "PORT", "DB_TYPE", "DATA_DIR",
        "SQLITE_DB_PATH", "REDIS_URL", "ADMIN_IDS"
    ]
    
    all_ok = True
    
    for var in required:
        value = os.getenv(var, "")
        all_ok &= print_status(var, bool(value), f"set to: {value[:10]}..." if value else "NOT SET")
    
    for var in optional:
        value = os.getenv(var, "")
        print_status(var, bool(value), value if value else "not set (using default)")
    
    return all_ok


def check_bot_token():
    """Verify bot token is valid."""
    print_header("Bot Token Verification")
    
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        return print_status("BOT_TOKEN", False, "Not set")
    
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10
        )
        data = response.json()
        
        if data.get("ok"):
            bot_info = data.get("result", {})
            print_status("Bot Name", True, f"@{bot_info.get('username', 'N/A')}")
            print_status("Bot ID", True, str(bot_info.get("id", "N/A")))
            print_status("Supports Inline", True, str(bot_info.get("supports_inline_queries", False)))
            return True
        else:
            return print_status("API Response", False, data.get("description", "Unknown error"))
            
    except Exception as e:
        return print_status("API Request", False, str(e))


def check_webhook():
    """Check current webhook status."""
    print_header("Webhook Status")
    
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        return print_status("BOT_TOKEN", False, "Not set")
    
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getWebhookInfo",
            timeout=10
        )
        data = response.json()
        
        if data.get("ok"):
            info = data.get("result", {})
            url = info.get("url", "")
            expected_url = os.getenv("WEBHOOK_URL", "").rstrip("/")
            
            if url:
                print_status("Webhook URL", True, url)
                
                if expected_url and url.startswith(expected_url):
                    print_status("URL Match", True, "Matches expected URL")
                elif expected_url:
                    print_status("URL Match", False, f"Expected {expected_url}")
                
                print_status("Pending Updates", info.get("pending_update_count", 0) == 0)
                print_status("Max Connections", True, str(info.get("max_connections", 0)))
                
                if info.get("last_error_date"):
                    print_status("Last Error", False, f"{info.get('last_error_message', 'Unknown')}")
                else:
                    print_status("Last Error", True, "None")
                
                return True
            else:
                return print_status("Webhook URL", False, "Not set")
        else:
            return print_status("API Response", False, data.get("description", "Unknown error"))
            
    except Exception as e:
        return print_status("API Request", False, str(e))


def check_health_endpoint():
    """Check if health endpoint is accessible."""
    print_header("Health Endpoint")
    
    port = os.getenv("PORT", 10000)
    webhook_url = os.getenv("WEBHOOK_URL", "")
    
    if not webhook_url:
        return print_status("WEBHOOK_URL", False, "Not set")
    
    try:
        response = requests.get(
            f"{webhook_url}/ping",
            timeout=10
        )
        
        if response.status_code == 200:
            print_status("Health Check", True, f"Status: {response.status_code}")
            try:
                data = response.json()
                print_status("Response", True, json.dumps(data))
            except:
                print_status("Response", True, response.text[:100])
            return True
        else:
            return print_status("Health Check", False, f"Status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        return print_status("Health Check", False, str(e)[:50])


def check_webhook_endpoint():
    """Check if webhook endpoint is accessible."""
    print_header("Webhook Endpoint")
    
    webhook_url = os.getenv("WEBHOOK_URL", "")
    
    if not webhook_url:
        return print_status("WEBHOOK_URL", False, "Not set")
    
    try:
        # Send a test POST request (should return 400 or 401 for invalid update)
        response = requests.post(
            f"{webhook_url}/webhook",
            json={"update_id": 0},
            timeout=10
        )
        
        # 400 means endpoint is accessible (bad request because update is invalid)
        if response.status_code in [400, 401, 403]:
            print_status("Webhook Endpoint", True, f"Status: {response.status_code} (accessible)")
            return True
        else:
            print_status("Webhook Endpoint", True, f"Status: {response.status_code}")
            return True
            
    except requests.exceptions.RequestException as e:
        return print_status("Webhook Endpoint", False, str(e)[:50])


def check_database():
    """Check database connection."""
    print_header("Database")
    
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    if db_type == "sqlite":
        db_path = os.getenv("SQLITE_DB_PATH", "/data/quizbot.db")
        
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print_status("SQLite Database", True, f"Size: {size:,} bytes")
            return True
        else:
            return print_status("SQLite Database", False, f"File not found: {db_path}")
    else:
        return print_status("Database Type", True, db_type)


def run_tests():
    """Run pytest tests if available."""
    print_header("Tests")
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print_status("Pytest", True, "Available")
            
            # Run tests
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            if result.returncode == 0:
                print_status("Tests", True, "All passed")
                return True
            else:
                print_status("Tests", False, "Some failed")
                return False
        else:
            return print_status("Pytest", False, "Not installed")
            
    except FileNotFoundError:
        return print_status("Pytest", False, "Not installed")
    except Exception as e:
        return print_status("Tests", False, str(e)[:50])


def main():
    print("\n" + "#" * 60)
    print("#" + " " * 18 + "Koyeb Deployment Check" + " " * 19 + "#")
    print("#" * 60)
    
    results = []
    
    results.append(("Environment", check_environment()))
    results.append(("Bot Token", check_bot_token()))
    results.append(("Webhook", check_webhook()))
    results.append(("Health Endpoint", check_health_endpoint()))
    results.append(("Webhook Endpoint", check_webhook_endpoint()))
    results.append(("Database", check_database()))
    
    # Optional: Run tests
    if "--run-tests" in sys.argv:
        results.append(("Tests", run_tests()))
    
    print_header("Summary")
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        icon = "✅" if passed else "❌"
        print(f"{icon} {name}: {status}")
        all_passed &= passed
    
    print("\n" + "-" * 60)
    if all_passed:
        print("🎉 All checks passed! Your deployment is ready!")
    else:
        print("⚠️  Some checks failed. Please review the output above.")
    print("-" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

