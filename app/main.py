"""
Main entry point for the Telegram Quiz Bot.

This module handles the bot startup, database initialization,
and graceful shutdown.
"""
import asyncio
import signal
import sys
import os
from contextlib import suppress

# When running the script directly (for example `python app/main.py`),
# Python may not include the project root on `sys.path`, causing
# `ModuleNotFoundError: No module named 'app'`. Ensure the project
# root is on `sys.path` so package imports work regardless of CWD.
if __package__ is None:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from app.bot import bot_instance, logger
from app.db.base import init_db
from app.services.db_consistency_fix import verify_and_fix_all_users

async def shutdown(signal, loop):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received exit signal {signal.name}...")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    
    await bot_instance.stop()
    
    loop.stop()
    logger.info("Shutdown complete.")

async def main():
    """Main entry point for the bot."""
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # 🚨 FIX: Run database consistency check on startup
        # This automatically fixes users with is_premium=1 but approved=0
        logger.info("🔧 Running database consistency check...")
        fixed = await verify_and_fix_all_users()
        if fixed > 0:
            logger.info(f"✅ Auto-fixed {fixed} inconsistent users on startup")
        
        # Start the bot
        await bot_instance.start()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Setup signal handlers
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop))
        )
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        loop.close()
        logger.info("Event loop closed")

