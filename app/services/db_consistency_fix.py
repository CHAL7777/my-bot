"""
Database Consistency Fix - Run on Bot Startup

This module automatically fixes inconsistent user states when the bot starts.
It ensures all users with is_premium=1 have approved=1.
"""

import asyncio
import logging
from sqlalchemy import text
from app.db.base import get_db

logger = logging.getLogger(__name__)


async def fix_inconsistent_user_states():
    """
    Automatically fix all users with is_premium=1 but approved=0.
    """
    logger.info("Checking for inconsistent user states...")
    
    try:
        session = get_db()
        async with session() as db_session:
            query = text("""
                SELECT user_id, username, approved, is_premium 
                FROM users 
                WHERE is_premium = 1 AND approved = 0
            """)
            result = await db_session.execute(query)
            inconsistent_users = result.fetchall()
            
            if inconsistent_users:
                logger.warning(f"Found {len(inconsistent_users)} users with inconsistent states")
                
                fix_query = text("""
                    UPDATE users SET approved = 1 
                    WHERE is_premium = 1 AND approved = 0
                """)
                await db_session.execute(fix_query)
                await db_session.commit()
                
                logger.info(f"Fixed {len(inconsistent_users)} inconsistent user states")
                return True
            else:
                logger.info("No inconsistent user states found")
                return False
                
    except Exception as e:
        logger.error(f"Error fixing user states: {e}")
        return False


async def verify_and_fix_all_users():
    """Comprehensive check and fix for all users."""
    logger.info("Verifying all user states...")
    
    try:
        session = get_db()
        async with session() as db_session:
            query = text("SELECT user_id, approved, is_premium FROM users")
            result = await db_session.execute(query)
            all_users = result.fetchall()
            
            fixed_count = 0
            
            for user_id, approved, is_premium in all_users:
                if is_premium and not approved:
                    update_query = text(
                        "UPDATE users SET approved = 1 WHERE user_id = :user_id"
                    )
                    await db_session.execute(update_query, {"user_id": user_id})
                    logger.info(f"Fixed user {user_id}: approved=1")
                    fixed_count += 1
            
            if fixed_count > 0:
                await db_session.commit()
                logger.info(f"Fixed {fixed_count} users total")
            else:
                logger.info("All users are consistent")
            
            return fixed_count
            
    except Exception as e:
        logger.error(f"Error verifying users: {e}")
        return 0


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    print("Running database consistency fix...")
    
    result = asyncio.run(verify_and_fix_all_users())
    
    if result > 0:
        print(f"Fixed {result} inconsistent users")
    else:
        print("All users are consistent")
    
    sys.exit(0)
