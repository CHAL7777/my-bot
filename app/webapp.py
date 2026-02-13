"""
FastAPI Web Application for Telegram Bot Webhooks.

This module provides the FastAPI application for handling webhooks
and other HTTP-based interactions with the Telegram Bot.

KEEP-ALIVE SOLUTION:
- Use UptimeRobot (free) to ping your bot every 5 minutes
- Add https://YOUR-RENDER-APP.ondrender.com/ping to UptimeRobot
- This prevents Render free tier from putting your bot to sleep

NOTE: For Render deployment, use app.webhook_main as the main entry point.
This module is kept for backward compatibility and can be used standalone.
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Response
from aiogram import Bot, Router
from aiogram.types import Update

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global reference for webhook handling
_bot: Optional[Bot] = None
_router = Router()

def get_bot() -> Optional[Bot]:
    """Get the bot instance"""
    return _bot

def set_bot(bot: Bot):
    """Set the bot instance (used by webhook_main)"""
    global _bot
    _bot = bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the FastAPI app.
    
    Note: For webhook mode, the bot is initialized by webhook_main.py.
    This lifespan only handles standalone mode when webapp.py is run directly.
    """
    global _bot
    
    # Check if bot was already initialized by webhook_main
    if _bot is not None:
        logger.info("Bot already initialized (webhook_main integration)")
        yield
        return
    
    # Standalone mode - initialize bot ourselves
    if settings.BOT_TOKEN and settings.WEBHOOK_URL:
        try:
            _bot = Bot(token=settings.BOT_TOKEN)
            await _bot.set_webhook(f"{settings.WEBHOOK_URL}/webhook")
            logger.info(f"Webhook set to {settings.WEBHOOK_URL}/webhook")
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")
    elif settings.BOT_TOKEN:
        logger.warning("WEBHOOK_URL not set - running without webhook")
        _bot = Bot(token=settings.BOT_TOKEN)
    
    # Initialize database
    try:
        from app.db.base import init_db
        await init_db()
        logger.info("Database initialized for webapp")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    # Shutdown
    if _bot:
        try:
            if settings.WEBHOOK_URL:
                await _bot.delete_webhook()
                logger.info("Webhook removed")
            await _bot.session.close()
            logger.info("Webapp session closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create the FastAPI app
app = FastAPI(
    title="Telegram Quiz Bot Webhook",
    description="Webhook handler for Telegram Quiz Bot. KEEP-ALIVE: Add /ping to UptimeRobot!",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Dashboard API Routes
# ============================================================================

# Import and include dashboard router
try:
    from app.handlers.admin_dashboard_api import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("Dashboard API router included successfully")
except ImportError as e:
    logger.warning(f"Failed to import dashboard router: {e}")


# ============================================================================
# KEEP-ALIVE ENDPOINTS (ping these to keep bot awake)
# ============================================================================

@app.get("/ping", response_class=Response)
async def ping(request: Request):
    """
    KEEP-ALIVE ENDPOINT - Ping this to prevent bot from sleeping!
    
    Usage: Add https://YOUR-APP.ondrender.com/ping to UptimeRobot
    
    UptimeRobot will ping this every 5 minutes, keeping your bot awake.
    """
    if request.method == "HEAD":
        return Response(status_code=200, content=b"PONG")
    return {"status": "ok", "message": "PONG - Bot is awake!"}


@app.get("/", response_class=Response)
async def root(request: Request):
    """Root endpoint for health check - handles both GET and HEAD"""
    if request.method == "HEAD":
        return Response(status_code=200, content=b"OK")
    return {"status": "ok", "message": "Quiz Bot Webhook is running!"}


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint - handles both GET and HEAD"""
    if request.method == "HEAD":
        return Response(status_code=200, content=b"OK")
    return {"status": "healthy", "service": "quiz_bot_webhook"}


@app.get("/webhook")
async def webhook_info():
    """Webhook info endpoint"""
    return {
        "status": "ok",
        "message": "Telegram Quiz Bot Webhook is active",
        "bot_token_configured": bool(settings.BOT_TOKEN),
        "webhook_url_configured": bool(settings.WEBHOOK_URL),
        "keep_alive": "Ping /ping endpoint every 5 minutes!"
    }


@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming webhook updates from Telegram"""
    bot = get_bot()
    
    try:
        data = await request.json()
        
        if not bot:
            raise HTTPException(status_code=503, detail="Bot not initialized")
        
        # Create Update object from the incoming data
        update = Update(**data)
        
        # Forward to the dispatcher from bot_instance
        from app.bot import bot_instance
        if hasattr(bot_instance, 'dp') and bot_instance.dp:
            await bot_instance.dp.feed_update(bot, update)
        else:
            # For webhook_main integration, use global dp
            from app.webhook_main import dp
            if dp:
                await dp.feed_update(bot, update)
            else:
                raise HTTPException(status_code=503, detail="Dispatcher not available")
        
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 10000))
    host = os.environ.get("WEBAPP_HOST", "0.0.0.0")
    
    uvicorn.run(
        "app.webapp:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
