#!/usr/bin/env python3
"""
Seed initial admins from ADMIN_IDS environment variable.
Run this after the migration to populate initial admin users.
"""

import asyncio
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db.base import async_session
from app.repositories.admin_repo import TelegramAdminRepository
from app.repositories.user_repo import UserRepository


async def seed_initial_admins():
    """Seed initial admins from ADMIN_IDS config"""
    print("Seeding initial admins...")

    admin_ids = settings.ADMIN_IDS
    if not admin_ids:
        print("No ADMIN_IDS configured. Skipping admin seeding.")
        return

    print(f"Found {len(admin_ids)} admin IDs: {admin_ids}")

    async with async_session() as session:
        admin_repo = TelegramAdminRepository(session)
        user_repo = UserRepository(session)

        for admin_id in admin_ids:
            # Check if already exists
            existing = await admin_repo.get_admin(admin_id)
            if existing:
                print(f"Admin {admin_id} already exists, skipping...")
                continue

            # Get user info
            user = await user_repo.get_user(admin_id)
            username = user.username if user else None

            # Create as superadmin
            await admin_repo.create_admin(
                user_id=admin_id,
                username=username,
                role='superadmin',
                added_by=None  # Initial admin, no creator
            )
            print(f"Created superadmin: {admin_id} (@{username})")

    print("Admin seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_initial_admins())
