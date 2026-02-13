#!/usr/bin/env python3
"""
Verify referral system configuration for @SmartITestExambot
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_config():
    print("🔍 Checking Referral System Configuration...")
    print("=" * 50)
    
    # Check BOT_USERNAME
    try:
        from app.config import settings
        bot_username = getattr(settings, 'BOT_USERNAME', None)
        
        if bot_username and bot_username != 'YourBotName':
            print(f"✅ BOT_USERNAME: {bot_username}")
        else:
            print("❌ BOT_USERNAME not set or default value!")
            print("   Add to .env: BOT_USERNAME=SmartITestExambot")
    except Exception as e:
        print(f"❌ Error loading config: {e}")
    
    # Check REFERRAL_REWARD_THRESHOLD
    try:
        threshold = getattr(settings, 'REFERRAL_REWARD_THRESHOLD', None)
        print(f"✅ REFERRAL_REWARD_THRESHOLD: {threshold}")
    except:
        print("⚠️  Could not check REFERRAL_REWARD_THRESHOLD")
    
    # Check if referral files exist
    print("\n📁 Checking referral files...")
    files_to_check = [
        "app/handlers/referral.py",
        "app/services/referral_service.py", 
        "app/repositories/referral_repo.py",
        "scripts/referral_admin_migration.sql"
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - NOT FOUND")
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    print(f"   Bot URL: https://t.me/SmartITestExambot")
    print(f"   Referral Link Format: https://t.me/SmartITestExambot?start=ref_CODE")
    print(f"   User Command: /referral")
    print("\n🚀 Your referral link is ready to share!")

if __name__ == "__main__":
    check_config()

