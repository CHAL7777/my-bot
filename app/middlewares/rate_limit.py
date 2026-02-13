from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import asyncio

from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.config import settings

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.user_limits = defaultdict(list)
        self.lock = asyncio.Lock()

        # Rate limits configuration - Increased for better user experience
        # Format: (max_requests, time_window_seconds)
        # Note: Contact uses database-based rate limiting in contact_repo.py
        # instead of in-memory rate limiting (more reliable, persists across restarts)
        self.rate_limits = {
            'message': (20, 60),     # 20 messages per minute (was 5)
            'callback': (30, 60),    # 30 callbacks per minute (was 10)
            'quiz_start': (5, 120),  # 5 quiz starts per 2 minutes (was 3 per 5 min)
            'payment': (5, 3600),    # 5 payments per hour (was 2 per day)
            # Contact removed from middleware - uses database rate limiting in contact_repo.py
        }
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ):
        user_id = event.from_user.id

        # Determine event type
        if isinstance(event, Message):
            event_type = 'message'

            # Check for specific commands
            text = event.text or ""
            if text.startswith('/quiz'):
                event_type = 'quiz_start'
            elif text.startswith('/payment'):
                event_type = 'payment'
            # Note: /contact commands use database rate limiting (contact_repo.py)
            # instead of middleware rate limiting

        elif isinstance(event, CallbackQuery):
            event_type = 'callback'

            # Check for specific callback actions
            callback_data = event.data or ""
            if callback_data.startswith('difficulty_'):
                event_type = 'quiz_start'
            # Note: contact_ callbacks use database rate limiting (contact_repo.py)

        # Check rate limit
        if not await self._check_rate_limit(user_id, event_type):
            await event.answer(
                "⏳ Too many requests. Please wait a moment.",
                show_alert=True
            )
            return

        # Call handler
        return await handler(event, data)
    
    async def _check_rate_limit(self, user_id: int, event_type: str) -> bool:
        """Check if user is within rate limits"""
        async with self.lock:
            now = datetime.now()
            
            # Get limits for this event type
            max_requests, time_window = self.rate_limits.get(event_type, (10, 60))
            
            # Clean old requests
            user_requests = self.user_limits[(user_id, event_type)]
            user_requests = [req for req in user_requests if now - req < timedelta(seconds=time_window)]
            self.user_limits[(user_id, event_type)] = user_requests
            
            # Check limit
            if len(user_requests) >= max_requests:
                return False
            
            # Add current request
            user_requests.append(now)
            return True
    
    async def check_daily_quiz_limit(self, user_id: int) -> bool:
        """Check daily quiz limit from database"""
        async for session in get_db():
            user_repo = UserRepository(session)
            
            try:
                daily_limit = await user_repo.get_daily_limit(user_id)
                
                if daily_limit.quiz_count >= settings.DAILY_QUIZ_LIMIT:
                    return False
                
                return True
                
            except Exception:
                # If there's an error, allow the request
                return True
    
    async def reset_limits(self):
        """Reset all rate limits (call this periodically)"""
        async with self.lock:
            now = datetime.now()
            
            # Remove entries older than 1 hour
            for key in list(self.user_limits.keys()):
                self.user_limits[key] = [
                    req for req in self.user_limits[key]
                    if now - req < timedelta(hours=1)
                ]
                
                # Remove empty lists
                if not self.user_limits[key]:
                    del self.user_limits[key]