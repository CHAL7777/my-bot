import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.middlewares.auth import AuthMiddleware
from app.middlewares.subscription import SubscriptionMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class QuizBot:
    def __init__(self):
        self.bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = None
        self._webhook_url: Optional[str] = None
        
    def _setup_middlewares(self):
        """Setup all middlewares for the bot"""
        self.dp.message.middleware(AuthMiddleware())
        self.dp.callback_query.middleware(AuthMiddleware())
        self.dp.message.middleware(SubscriptionMiddleware())
        self.dp.callback_query.middleware(SubscriptionMiddleware())
        self.dp.message.middleware(RateLimitMiddleware())
        self.dp.callback_query.middleware(RateLimitMiddleware())
        logger.info("Middlewares configured: Auth -> Subscription -> RateLimit")
    
    async def setup_handlers(self):
        """Import and setup all handlers in correct order."""
        from app.handlers import (
            start, quiz, quiz_high_quality, answers, progress,
            leaderboard, payment, admin,
            admin_questions, admin_users, admin_subjects,
            admin_payments, admin_stats, admin_logs,
            admin_messages, referral, admin_manage, admin_referrals
        )

        # Log handler registration order
        logger.info("=" * 50)
        logger.info("REGISTERING HANDLERS IN ORDER:")
        logger.info("  1. start.router")
        logger.info("  2. answers.router (BEFORE quiz - critical)")
        logger.info("  3. quiz.router")
        logger.info("  4. quiz_high_quality.router")
        logger.info("  5. progress.router")
        logger.info("  6. leaderboard.router")
        logger.info("  7. payment.router")
        logger.info("  8. referral.router")
        logger.info("  9. admin.router + sub-routers")
        logger.info("=" * 50)
        
        # Register handlers in order (CRITICAL: answers before quiz)
        self.dp.include_router(start.router)
        self.dp.include_router(answers.router)
        self.dp.include_router(quiz.router)
        self.dp.include_router(quiz_high_quality.router)
        self.dp.include_router(progress.router)
        self.dp.include_router(leaderboard.router)
        self.dp.include_router(payment.router)
        self.dp.include_router(referral.router)
        self.dp.include_router(admin.router)
        self.dp.include_router(admin_users.router)
        self.dp.include_router(admin_questions.router)
        self.dp.include_router(admin_subjects.router)
        self.dp.include_router(admin_payments.router)
        self.dp.include_router(admin_stats.router)
        self.dp.include_router(admin_logs.router)
        self.dp.include_router(admin_messages.router)
        self.dp.include_router(admin_manage.router)
        self.dp.include_router(admin_referrals.router)
        
        logger.info("All handlers registered successfully")

    async def _init_storage(self):
        """Initialize FSM storage: Redis if configured, else MemoryStorage."""
        if not settings.REDIS_URL:
            logger.info("No REDIS_URL; using MemoryStorage for FSM")
            return MemoryStorage()

        try:
            import redis.asyncio as aioredis
            from aiogram.fsm.storage.redis import RedisStorage
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}). Using MemoryStorage")
            return MemoryStorage()

        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            await redis_client.ping()
            logger.info(f"Connected to Redis; using RedisStorage")
            return RedisStorage(redis=redis_client)
        except Exception as e:
            logger.warning(f"Could not connect to Redis ({e}). Using MemoryStorage")
            return MemoryStorage()
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Quiz Bot...")
        storage = await self._init_storage()
        self.dp = Dispatcher(storage=storage)
        self._setup_middlewares()
        await self.setup_handlers()
        
        from app.scheduler import setup_scheduler
        scheduler = setup_scheduler(self.bot)
        scheduler.start()
        
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("Stopping Quiz Bot...")
        try:
            if self.dp and getattr(self.dp, "storage", None):
                await self.dp.storage.close()
        except Exception:
            pass
        await self.bot.session.close()

    async def setup_webhook(self, webhook_url: str) -> bool:
        """Set up webhook for the bot."""
        try:
            logger.info(f"Setting up webhook: {webhook_url}")
            await self.bot.set_webhook(webhook_url)
            self._webhook_url = webhook_url
            logger.info("Webhook set successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """Delete the current webhook."""
        try:
            logger.info("Deleting webhook...")
            await self.bot.delete_webhook()
            self._webhook_url = None
            logger.info("Webhook deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False

    def get_webhook_url(self) -> Optional[str]:
        """Get the current webhook URL."""
        return self._webhook_url

# Singleton instance
bot_instance = QuizBot()
