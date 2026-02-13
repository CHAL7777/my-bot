#!/usr/bin/env python3
"""
Telegram Webhook Setup Script for Koyeb Deployment

This script sets up the Telegram webhook for your bot.
Run this after deploying to Koyeb and getting your public URL.

Usage:
    python scripts/setup_webhook.py
    python scripts/setup_webhook.py --delete  # To delete webhook
"""

import os
import sys
import argparse
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_bot_token():
    """Get bot token from environment or prompt user."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        token = input("Enter your Bot Token: ").strip()
    return token


def get_webhook_url():
    """Get webhook URL from environment or prompt user."""
    url = os.getenv("WEBHOOK_URL")
    if not url:
        url = input("Enter your Webhook URL (e.g., https://yourbot.koyeb.app): ").strip()
    return url.rstrip("/")


def set_webhook(bot_token: str, webhook_url: str, secret_token: str = None):
    """Set the Telegram webhook."""
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    data = {
        "url": f"{webhook_url}/webhook",
        "max_connections": 100,
        "drop_pending_updates": False
    }
    
    if secret_token:
        data["secret_token"] = secret_token
    
    logger.info(f"Setting webhook to: {data['url']}")
    
    try:
        response = requests.post(api_url, json=data, timeout=30)
        result = response.json()
        
        if result.get("ok"):
            logger.info("✅ Webhook set successfully!")
            logger.info(f"Description: {result.get('description', 'N/A')}")
            return True
        else:
            logger.error(f"❌ Failed to set webhook: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def delete_webhook(bot_token: str):
    """Delete the Telegram webhook."""
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    logger.info("Deleting webhook...")
    
    try:
        response = requests.post(api_url, timeout=30)
        result = response.json()
        
        if result.get("ok"):
            logger.info("✅ Webhook deleted successfully!")
            return True
        else:
            logger.error(f"❌ Failed to delete webhook: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def get_webhook_info(bot_token: str):
    """Get current webhook information."""
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(api_url, timeout=30)
        result = response.json()
        
        if result.get("ok"):
            info = result.get("result", {})
            logger.info("=" * 50)
            logger.info("WEBHOOK INFO:")
            logger.info(f"  URL: {info.get('url', 'Not set')}")
            logger.info(f"  Has Custom Certificate: {info.get('has_custom_certificate', False)}")
            logger.info(f"  Pending Update Count: {info.get('pending_update_count', 0)}")
            logger.info(f"  Max Connections: {info.get('max_connections', 0)}")
            logger.info(f"  Last Error Date: {info.get('last_error_date', 'None')}")
            logger.info(f"  Last Error Message: {info.get('last_error_message', 'None')}")
            
            if info.get('last_synchronization_error_date'):
                logger.info(f"  Sync Error Date: {info['last_synchronization_error_date']}")
            
            logger.info("=" * 50)
            return info
        else:
            logger.error(f"❌ Failed to get webhook info: {result.get('description')}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return None


def generate_secret_token(length: int = 32) -> str:
    """Generate a secret token for webhook verification."""
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def main():
    parser = argparse.ArgumentParser(
        description="Setup Telegram Webhook for Koyeb Deployment"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the current webhook"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show current webhook information"
    )
    parser.add_argument(
        "--generate-token",
        action="store_true",
        help="Generate a secret token for webhook"
    )
    parser.add_argument(
        "--secret",
        type=str,
        default=None,
        help="Custom secret token for webhook"
    )
    
    args = parser.parse_args()
    
    bot_token = get_bot_token()
    
    if not bot_token:
        logger.error("Bot token is required. Set BOT_TOKEN environment variable.")
        sys.exit(1)
    
    if args.generate_token:
        token = generate_secret_token()
        logger.info(f"Generated secret token: {token}")
        logger.info("Use --secret to set it when configuring webhook")
        sys.exit(0)
    
    if args.info:
        get_webhook_info(bot_token)
        sys.exit(0)
    
    if args.delete:
        success = delete_webhook(bot_token)
        sys.exit(0 if success else 1)
    
    webhook_url = get_webhook_url()
    
    if not webhook_url:
        logger.error("Webhook URL is required.")
        sys.exit(1)
    
    success = set_webhook(bot_token, webhook_url, args.secret)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

