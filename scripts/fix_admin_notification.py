#!/usr/bin/env python3
"""
Script to fix the notify_admins_about_contact function in start.py
This fixes the issue where admin notifications weren't being sent.
"""

import re

# Read the file
with open('/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot/app/handlers/start.py', 'r') as f:
    content = f.read()

# The old function to replace
old_function = '''async def notify_admins_about_contact(
    bot,
    ticket_id: str,
    message_id: int,
    user_id: int,
    user_name: str,
    username: str,
    category: str,
    message_text: str
):
    """Notify all admins about a new contact message with safe Markdown formatting"""
    from datetime import datetime

    # Category display names
    category_display = {
        'payment': 'Payment Issues',
        'quiz_error': 'Quiz Errors',
        'access': 'Access Problems',
        'general': 'General Questions',
        'feedback': 'Feedback'
    }

    # Truncate message if too long
    display_text = message_text[:500] + "..." if len(message_text) > 500 else message_text

    # Build notification
    title = f"New Support Ticket: {ticket_id}"
    user_info = f"User: {user_name} (@{username}) ID: {user_id}"
    details = (
        f"Category: {category_display.get(category, category)}\\n"
        f"Time: {datetime.now().strftime('%d %b %Y %H:%M')}\\n\\n"
        f"Message:\\n\\n"
        f"{display_text}\\n\\n"
        f"Actions:\\n"
        f"- Reply: /reply {ticket_id} <your reply>\\n"
        f"- View all: /admin_messages\\n"
        f"- Close: /close {ticket_id}"
    )

    admin_message = f"{title}\\n\\n{user_info}\\n\\n{details}"

    # Send to all admin users
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")'''

# The new function
new_function = '''async def notify_admins_about_contact(
    bot,
    ticket_id: str,
    message_id: int,
    user_id: int,
    user_name: str,
    username: str,
    category: str,
    message_text: str
):
    """Notify all admins about a new contact message - using database + env fallback"""
    from datetime import datetime
    from app.repositories.admin_repo import TelegramAdminRepository

    # Category display names
    category_display = {
        'payment': 'Payment Issues',
        'quiz_error': 'Quiz Errors',
        'access': 'Access Problems',
        'general': 'General Questions',
        'feedback': 'Feedback'
    }

    # Truncate message if too long
    display_text = message_text[:500] + "..." if len(message_text) > 500 else message_text

    # Build notification message
    notification_text = (
        f"🆕 *New Support Ticket: {ticket_id}*\\n\\n"
        f"👤 *User Info:*\\n"
        f"• Name: {user_name}\\n"
        f"• Username: @{username or 'N/A'}\\n"
        f"• User ID: \\`{user_id}\\`\\n\\n"
        f"📁 *Category:* {category_display.get(category, category)}\\n"
        f"⏰ *Time:* {datetime.now().strftime('%d %b %Y %H:%M')}\\n\\n"
        f"━━━━━━━━━━━━━━━━━━━━\\n\\n"
        f"📝 *Message:*\\n{display_text}\\n\\n"
        f"━━━━━━━━━━━━━━━━━━━━\\n\\n"
        f"💡 *Quick Actions:*\\n"
        f"• Reply: \\`/reply {ticket_id} <your reply>\\`\\n"
        f"• View all: \\`/admin_messages\\`\\n"
        f"• Close: \\`/close {ticket_id}\\`"
    )

    # Collect admin IDs from multiple sources
    admin_ids_to_notify = set()

    # 1. First, try to get admins from database (most reliable)
    try:
        async for session in get_db():
            admin_repo = TelegramAdminRepository(session)
            db_admins = await admin_repo.get_active_admins()
            for admin in db_admins:
                if admin.user_id:
                    admin_ids_to_notify.add(admin.user_id)
    except Exception as e:
        print(f"Error fetching admins from database: {e}")

    # 2. Also check settings.ADMIN_IDS (env var fallback)
    try:
        if hasattr(settings, 'ADMIN_IDS') and settings.ADMIN_IDS:
            for admin_id in settings.ADMIN_IDS:
                admin_ids_to_notify.add(admin_id)
    except Exception as e:
        print(f"Error reading ADMIN_IDS from settings: {e}")

    # Send notification to all collected admin IDs
    notified_count = 0
    for admin_id in admin_ids_to_notify:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=notification_text,
                parse_mode='Markdown'
            )
            notified_count += 1
            print(f"✅ Notified admin {admin_id} about ticket {ticket_id}")
        except Exception as e:
            print(f"❌ Failed to notify admin {admin_id}: {e}")

    if notified_count == 0:
        print(f"⚠️ No admins were notified about ticket {ticket_id}! Check ADMIN_IDS env var or database.")
    else:
        print(f"✅ Notified {notified_count} admins about ticket {ticket_id}")'''

# Replace the function
if old_function in content:
    content = content.replace(old_function, new_function)
    with open('/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot/app/handlers/start.py', 'w') as f:
        f.write(content)
    print("✅ Successfully updated notify_admins_about_contact function!")
else:
    print("❌ Could not find the function to replace. The file may have already been updated or format is different.")
    print("Searching for partial match...")
    
    # Try to find partial match
    if "notify_admins_about_contact" in content:
        print("Found function name in file, but content doesn't match exactly.")
        print("Please manually update the function in app/handlers/start.py")
    else:
        print("Function not found in file at all!")
