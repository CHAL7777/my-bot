"""
Webhook entry point for Telegram Quiz Bot.

This module provides a unified FastAPI + aiogram webhook setup for deployment
on Koyeb, Render, or any platform supporting FastAPI.

Start command:
    uvicorn app.webhook_main:app --host 0.0.0.0 --port $PORT

Environment variables required:
    - BOT_TOKEN: Telegram bot token
    - WEBHOOK_URL: Full URL where the bot is hosted
    - DATABASE_URL: PostgreSQL connection string (postgresql+asyncpg://...)
    - PORT: Port for the HTTP server
"""
import asyncio
import logging
import os
import re
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Ensure project root is in path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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

# ============== DNS Validation Helper ==============

def validate_webhook_url(webhook_url: str) -> tuple[bool, str]:
    """
    Validate webhook URL format and DNS resolution.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not webhook_url:
        return False, "WEBHOOK_URL is empty or not set"
    
    # Remove trailing slashes and /webhook path if present
    clean_url = webhook_url.strip().rstrip('/')
    
    # Validate URL format
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP address
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(clean_url):
        return False, f"Invalid URL format: {webhook_url}"
    
    # Extract hostname for DNS check
    try:
        parsed = urlparse(clean_url)
        hostname = parsed.hostname
        
        if not hostname:
            return False, f"Could not extract hostname from: {webhook_url}"
        
        logger.info(f"Validating DNS for hostname: {hostname}")
        
        # Try to resolve the hostname
        socket.gethostbyname(hostname)
        logger.info(f"✓ DNS resolution successful for {hostname}")
        
        return True, ""
        
    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname: {hostname} - {e}"
    except Exception as e:
        return False, f"Unexpected error validating URL: {e}"


def build_webhook_url(base_url: str, webhook_path: str) -> str:
    """
    Build the complete webhook URL.
    
    Args:
        base_url: Base URL from configuration
        webhook_path: Webhook path (e.g., /webhook)
    
    Returns:
        Complete webhook URL
    """
    # Clean the base URL
    clean_base = base_url.strip().rstrip('/')
    
    # Clean the path and ensure it starts with /
    clean_path = webhook_path.strip()
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    
    # Remove any duplicate path segments
    clean_base = clean_base.rstrip('/')
    
    return f"{clean_base}{clean_path}"


# ============== Configuration ==============
from app.config import settings

BOT_TOKEN = settings.BOT_TOKEN
WEBHOOK_URL = settings.WEBHOOK_URL.rstrip("/") if settings.WEBHOOK_URL else ""
WEBHOOK_PATH = settings.WEBHOOK_PATH
PORT = settings.WEBHOOK_PORT
# Use COMPLETE_WEBHOOK_URL to avoid duplicate paths
COMPLETE_WEBHOOK_URL = settings.COMPLETE_WEBHOOK_URL

# ============== Database Setup ==============
# Use the centralized database module from app.db.base
from app.db.base import db, get_db, init_db, close_db

# ============== Bot Setup ==============
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None
scheduler = None

def _setup_middlewares(dp: Dispatcher):
    """Setup all middlewares for the bot"""
    from app.middlewares.auth import AuthMiddleware
    from app.middlewares.subscription import SubscriptionMiddleware
    from app.middlewares.rate_limit import RateLimitMiddleware
    
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

async def setup_handlers(dp: Dispatcher):
    """Import and setup all handlers"""
    from app.handlers import (
        start, quiz, quiz_high_quality, answers, progress,
        leaderboard, payment, admin,
        admin_questions, admin_users, admin_subjects,
        admin_payments, admin_stats, admin_logs,
        admin_messages, referral, admin_manage,
        admin_referrals  # Add admin_referrals handler
    )

    dp.include_router(start.router)
    dp.include_router(quiz.router)
    dp.include_router(quiz_high_quality.router)
    dp.include_router(answers.router)
    dp.include_router(progress.router)
    dp.include_router(leaderboard.router)
    dp.include_router(payment.router)
    dp.include_router(referral.router)
    dp.include_router(admin.router)
    dp.include_router(admin_questions.router)
    dp.include_router(admin_users.router)
    dp.include_router(admin_subjects.router)
    dp.include_router(admin_payments.router)
    dp.include_router(admin_stats.router)
    dp.include_router(admin_logs.router)
    dp.include_router(admin_messages.router)
    dp.include_router(admin_manage.router)
    dp.include_router(admin_referrals.router)  # Register admin_referrals router
    
    logger.info("All handlers registered successfully")

async def init_storage():
    """Initialize FSM storage: try Redis if configured, else MemoryStorage."""
    from app.config import settings
    
    if not settings.REDIS_URL:
        logger.info("No REDIS_URL configured; using MemoryStorage for FSM")
        return MemoryStorage()

    try:
        import redis.asyncio as aioredis
        from aiogram.fsm.storage.redis import RedisStorage
    except Exception as e:
        logger.warning("Redis libraries not available (%s). Falling back to MemoryStorage", e)
        return MemoryStorage()

    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        logger.info("Connected to Redis; using RedisStorage for FSM")
        return RedisStorage(redis=redis_client)
    except Exception as e:
        logger.warning("Could not connect to Redis (%s). Falling back to MemoryStorage", e)
        try:
            await redis_client.close()
            await redis_client.wait_closed()
        except Exception:
            pass
        return MemoryStorage()

async def setup_scheduler(bot: Bot):
    """Setup and start all scheduled tasks"""
    from app.scheduler.reminders import ReminderScheduler
    from app.scheduler.expiry_check import ExpiryChecker
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = AsyncIOScheduler()
    reminder_scheduler = ReminderScheduler(bot)
    expiry_checker = ExpiryChecker(bot)
    
    scheduler.add_job(reminder_scheduler.send_daily_reminders, CronTrigger(hour=9, minute=0), id='daily_reminders')
    scheduler.add_job(expiry_checker.check_subscription_expiry, CronTrigger(hour=0, minute=0), id='subscription_expiry_check')
    scheduler.add_job(reminder_scheduler.send_weekly_leaderboard, CronTrigger(day_of_week='sun', hour=20, minute=0), id='weekly_leaderboard')
    scheduler.add_job(expiry_checker.cleanup_old_data, CronTrigger(day=1, hour=2, minute=0), id='data_cleanup')
    
    scheduler.start()
    logger.info("Scheduler started successfully")
    return scheduler

# ============== Lifespan Context Manager ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global bot, dp, scheduler
    
    logger.info("=" * 60)
    logger.info("🚀 STARTING TELEGRAM QUIZ BOT - WEBHOOK MODE")
    logger.info("=" * 60)
    
    try:
        # Validate configuration
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN environment variable is required!")
            raise RuntimeError("BOT_TOKEN not set")
        logger.info("✅ BOT_TOKEN configured")

        if not WEBHOOK_URL:
            logger.warning("⚠️ WEBHOOK_URL not set")
        else:
            logger.info(f"✅ WEBHOOK_URL configured: {WEBHOOK_URL}")

        # Initialize database using centralized module
        logger.info("🔧 Initializing database...")
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Create bot instance
        logger.info("🤖 Creating bot instance...")
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        logger.info("✅ Bot instance created")
        
        # Initialize storage and dispatcher
        logger.info("📦 Initializing FSM storage and dispatcher...")
        storage = await init_storage()
        dp = Dispatcher(storage=storage)
        logger.info("✅ Dispatcher initialized")
        
        # Setup middlewares
        logger.info("🔐 Setting up middlewares...")
        _setup_middlewares(dp)
        logger.info("✅ Middlewares configured")
        
        # Setup handlers
        logger.info("📋 Registering handlers...")
        await setup_handlers(dp)
        logger.info("✅ All handlers registered")
        
        # Setup scheduler
        logger.info("⏰ Starting scheduler...")
        scheduler = await setup_scheduler(bot)
        logger.info("✅ Scheduler started")
        
        # Set webhook
        if COMPLETE_WEBHOOK_URL:
            # Use COMPLETE_WEBHOOK_URL which avoids duplicate paths
            webhook_url = COMPLETE_WEBHOOK_URL
            
            logger.info(f"🔗 Built webhook URL: {webhook_url}")
            
            # Validate webhook URL before attempting to set it
            logger.info("🔍 Validating webhook URL...")
            is_valid, error_msg = validate_webhook_url(webhook_url)
            
            if not is_valid:
                logger.error(f"❌ Webhook URL validation failed: {error_msg}")
                logger.error("⚠️  Cannot set webhook. Please check:")
                logger.error("   1. WEBHOOK_URL environment variable is correctly set")
                logger.error("   2. The domain name is publicly accessible")
                logger.error("   3. DNS is properly configured for your domain")
                logger.error("   4. The server is running and accessible via HTTPS")
                
                # Continue without webhook rather than crashing
                logger.warning("⚠️  Starting bot without webhook (polling mode required)")
            else:
                try:
                    logger.info(f"🔗 Setting webhook to: {webhook_url}")
                    await bot.set_webhook(webhook_url)
                    logger.info("✅ Webhook registered successfully!")
                except Exception as webhook_error:
                    logger.error(f"❌ Failed to set webhook: {webhook_error}")
                    logger.error("⚠️  Starting bot without webhook (polling mode required)")
        else:
            logger.warning("⚠️ WEBHOOK_URL not set - running without webhook")
        
        logger.info("=" * 60)
        logger.info("✅ BOT STARTUP COMPLETE - READY TO RECEIVE UPDATES")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 SHUTTING DOWN BOT...")
    logger.info("=" * 60)
    
    try:
        if scheduler:
            scheduler.shutdown()
            logger.info("✅ Scheduler stopped")
        
        if bot:
            try:
                await bot.delete_webhook()
                logger.info("✅ Webhook removed")
            except Exception as e:
                logger.error(f"⚠️ Failed to remove webhook: {e}")
            await bot.session.close()
            logger.info("✅ Bot session closed")
        
        if dp and hasattr(dp, 'storage'):
            await dp.storage.close()
            logger.info("✅ Storage closed")
        
        # Close database connections
        await close_db()
        logger.info("✅ Database connections closed")
            
    except Exception as e:
        logger.error(f"⚠️ Error during shutdown: {e}")
    
    logger.info("=" * 60)
    logger.info("✅ SHUTDOWN COMPLETE")
    logger.info("=" * 60)

# ============== FastAPI App ==============
app = FastAPI(
    title="Telegram Quiz Bot Webhook",
    description="Webhook handler for Telegram Quiz Bot",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/ping", response_class=Response)
async def ping(request: Request):
    """Health check endpoint - Koyeb TCP health check compatible"""
    return Response(status_code=200, content=b"PONG", media_type="text/plain")

@app.head("/ping", response_class=Response)
async def ping_head(request: Request):
    """HEAD request handler for /ping"""
    return Response(status_code=200, content=b"", media_type="text/plain")

@app.get("/", response_class=JSONResponse)
async def root(request: Request):
    """Root endpoint for health check"""
    return {
        "status": "ok", 
        "message": "Quiz Bot Webhook is running!",
        "webhook_url": f"{WEBHOOK_URL}/webhook" if WEBHOOK_URL else "not configured"
    }

@app.head("/", response_class=Response)
async def root_head(request: Request):
    """HEAD request handler for /"""
    return Response(status_code=200, content=b"", media_type="text/plain")

@app.get("/health", response_class=JSONResponse)
async def health_check(request: Request):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "quiz_bot_webhook",
        "bot_configured": bool(BOT_TOKEN),
        "webhook_configured": bool(WEBHOOK_URL)
    }

@app.head("/health", response_class=Response)
async def health_check_head(request: Request):
    """HEAD request handler for /health"""
    return Response(status_code=200, content=b"", media_type="text/plain")

@app.get("/webhook/dns", response_class=JSONResponse)
async def webhook_dns_check():
    """
    Webhook DNS validation check endpoint.
    Use this to verify your webhook URL is properly configured.
    """
    if not COMPLETE_WEBHOOK_URL:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "WEBHOOK_URL not configured",
                "recommendation": "Set the WEBHOOK_URL environment variable"
            }
        )
    
    webhook_url = COMPLETE_WEBHOOK_URL
    is_valid, error_msg = validate_webhook_url(webhook_url)
    
    if is_valid:
        return {
            "status": "success",
            "webhook_url": webhook_url,
            "dns_valid": True,
            "message": "Webhook URL is valid and DNS resolution works"
        }
    else:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "webhook_url": webhook_url,
                "dns_valid": False,
                "error": error_msg,
                "recommendations": [
                    "Verify WEBHOOK_URL environment variable is correct",
                    "Ensure your domain DNS is properly configured",
                    "Check that your server is publicly accessible via HTTPS",
                    "Verify the domain is not behind a firewall blocking Telegram"
                ]
            }
        )

@app.get("/webhook", response_class=JSONResponse)
async def webhook_info():
    """Webhook info endpoint"""
    return {
        "status": "ok",
        "message": "Telegram Quiz Bot Webhook is active",
        "webhook_path": WEBHOOK_PATH,
        "bot_token_configured": bool(BOT_TOKEN),
        "webhook_url_configured": bool(WEBHOOK_URL)
    }

@app.head("/webhook", response_class=Response)
async def webhook_head(request: Request):
    """HEAD request handler for /webhook"""
    return Response(status_code=200, content=b"", media_type="text/plain")

@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming webhook updates from Telegram"""
    global bot, dp
    
    try:
        if not bot:
            logger.error("Bot not initialized")
            raise HTTPException(status_code=503, detail="Bot not initialized")
        
        if not dp:
            logger.error("Dispatcher not initialized")
            raise HTTPException(status_code=503, detail="Dispatcher not available")
        
        try:
            data = await request.json()
        except Exception as json_error:
            logger.error(f"Failed to parse request JSON: {json_error}")
            return {"ok": False, "error": "Invalid JSON"}
        
        if not data:
            logger.warning("Empty update received")
            return {"ok": True}
        
        update_id = data.get('update_id', 'unknown')
        logger.info(f"Processing update {update_id}")
        
        try:
            update = Update(**data)
        except Exception as parse_error:
            logger.error(f"Failed to parse update {update_id}: {parse_error}")
            return {"ok": True}
        
        try:
            await dp.feed_update(bot, update)
        except Exception as process_error:
            logger.error(f"Failed to process update {update_id}: {process_error}")
            return {"ok": True}
        
        return {"ok": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/db/health", response_class=JSONResponse)
async def db_health():
    """Database health check using centralized database module"""
    try:
        # Use the centralized database session
        async_session = db.async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )

@app.head("/db/health", response_class=Response)
async def db_health_head(request: Request):
    """HEAD request handler for /db/health"""
    return Response(status_code=200, content=b"", media_type="text/plain")

# ============================================================================
# Run with uvicorn
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.webhook_main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info"
    )

