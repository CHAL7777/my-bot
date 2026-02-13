#!/usr/bin/env python3
"""
Script to check pending contact messages in the database.
Usage: python scripts/check_pending_messages.py
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import get_db
from app.repositories.contact_repo import ContactMessageRepository


async def check_pending_messages():
    """Check and display pending contact messages."""
    print("=" * 60)
    print("PENDING CONTACT MESSAGES CHECK")
    print("=" * 60)
    
    async for session in get_db():
        repo = ContactMessageRepository(session)
        
        # Get open/pending messages
        pending_messages = await repo.get_pending_messages()
        print(f"\n📬 Found {len(pending_messages)} pending messages:")
        print("-" * 60)
        
        if pending_messages:
            for msg in pending_messages:
                print(f"  Ticket ID: {msg.ticket_id}")
                print(f"  User ID: {msg.user_id}")
                print(f"  Category: {msg.category}")
                print(f"  Subject: {msg.subject}")
                print(f"  Message: {msg.message_text[:100]}..." if len(msg.message_text) > 100 else f"  Message: {msg.message_text}")
                print(f"  Status: {msg.status}")
                print(f"  Created: {msg.created_at}")
                print("-" * 40)
        else:
            print("  No pending messages found! ✅")
        
        # Get counts by category
        print("\n📊 Messages by Category:")
        category_counts = await repo.get_message_count_by_category()
        for category, count in category_counts.items():
            print(f"  {category}: {count}")
        
        # Get open count
        open_count = await repo.get_open_count()
        print(f"\n📈 Total Open Tickets: {open_count}")
        
        print("\n" + "=" * 60)
        print("CHECK COMPLETE")
        print("=" * 60)
        
        return


if __name__ == "__main__":
    asyncio.run(check_pending_messages())

