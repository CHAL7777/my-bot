from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.admin_repo import TelegramAdminRepository
from app.config import settings

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ):
        # Get user ID
        user_id = event.from_user.id
        
        # Initialize admin flags as False
        is_admin = False
        is_superadmin = False
        
        # Check if user is admin (from settings.ADMIN_IDS - hardcoded superadmins)
        if user_id in settings.ADMIN_IDS:
            is_admin = True
            is_superadmin = True
        else:
            # Also check dynamic admin table (TelegramAdmin)
            async for session in get_db():
                admin_repo = TelegramAdminRepository(session)
                
                # Check if user is a superadmin in the dynamic table
                if await admin_repo.is_superadmin(user_id):
                    is_admin = True
                    is_superadmin = True
                # Check if user is a regular admin in the dynamic table
                elif await admin_repo.is_admin(user_id):
                    is_admin = True
                    is_superadmin = False
        
        data['is_admin'] = is_admin
        data['is_superadmin'] = is_superadmin
        
        # Get database session
        async for session in get_db():
            user_repo = UserRepository(session)
            
            # Check if user exists and is not blocked
            user = await user_repo.get_user(user_id)
            
            if user and user.blocked:
                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "🚫 Your account has been blocked. Please contact admin.",
                        show_alert=True
                    )
                else:
                    await event.answer(
                        "🚫 Your account has been blocked. Please contact admin.",
                        reply_markup=None
                    )
                return
            
            data['user'] = user
            data['user_repo'] = user_repo
            
            # Call handler
            return await handler(event, data)
