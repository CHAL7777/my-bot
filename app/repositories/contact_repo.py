from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContactMessage


class ContactMessageRepository:
    """Repository for managing user-to-admin contact messages (Support Tickets)"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_ticket_id(self) -> str:
        """Generate a unique ticket ID in format SUP-XXXX"""
        # Get the next available message_id
        query = select(func.max(ContactMessage.message_id))
        result = await self.session.execute(query)
        max_id = result.scalar() or 0
        
        # Generate new ticket ID (start from 1001)
        new_id = max_id + 1 if max_id >= 1000 else 1001
        return f"SUP-{new_id}"

    async def create_message(
        self,
        user_id: int,
        category: str,
        message_text: str,
        subject: Optional[str] = None
    ) -> ContactMessage:
        """Create a new contact message from a user"""
        ticket_id = await self.generate_ticket_id()
        
        message = ContactMessage(
            ticket_id=ticket_id,
            user_id=user_id,
            category=category,
            subject=subject,
            message_text=message_text,
            status='open'
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_message(self, message_id: int) -> Optional[ContactMessage]:
        """Get a specific message by ID"""
        query = select(ContactMessage).where(
            ContactMessage.message_id == message_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_message_by_ticket_id(self, ticket_id: str) -> Optional[ContactMessage]:
        """Get a specific message by ticket ID"""
        query = select(ContactMessage).where(
            ContactMessage.ticket_id == ticket_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_messages(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[ContactMessage]:
        """Get all messages from a specific user"""
        query = select(ContactMessage).where(
            ContactMessage.user_id == user_id
        ).order_by(desc(ContactMessage.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_messages_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ContactMessage]:
        """Get messages by status (open, replied, closed)"""
        query = select(ContactMessage).where(
            ContactMessage.status == status
        ).order_by(desc(ContactMessage.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_open_messages(self, limit: int = 100) -> List[ContactMessage]:
        """Get all open messages (for admin dashboard)"""
        return await self.get_messages_by_status('open', limit)

    async def get_pending_messages(self, limit: int = 100) -> List[ContactMessage]:
        """Get messages that need admin attention (open status)"""
        return await self.get_messages_by_status('open', limit)

    async def can_send_contact_request(self, user_id: int) -> Tuple[bool, Optional[datetime]]:
        """
        Check if user can send a contact request (rate limiting).
        
        Returns:
            Tuple of (can_send: bool, next_allowed_at: Optional[datetime])
        """
        # Get the last message from this user using ORM query
        query = (
            select(ContactMessage)
            .where(ContactMessage.user_id == user_id)
            .order_by(desc(ContactMessage.created_at))
            .limit(1)
        )
        
        result = await self.session.execute(query)
        last_message = result.scalar_one_or_none()

        if not last_message:
            # No previous messages, user can send
            return True, None

        # Use Python datetime for comparison (simpler than raw SQL with timezones)
        last_time = last_message.created_at
        
        # Calculate time difference using Python datetime
        # Convert to local datetime if needed
        now = datetime.utcnow()
        
        # If last_time is timezone-aware, make now timezone-aware too
        if last_time.tzinfo is not None:
            now = now.replace(tzinfo=last_time.tzinfo)
        
        time_diff = now - last_time
        
        # 10 minutes = 600 seconds
        if time_diff.total_seconds() >= 600:
            return True, None
        
        # Calculate next allowed time
        next_allowed = last_time + timedelta(minutes=10)
        return False, next_allowed

    async def mark_as_replied(
        self,
        message_id: int,
        admin_user_id: int,
        reply_text: str
    ) -> Optional[ContactMessage]:
        """Mark a message as replied and add admin's reply"""
        message = await self.get_message(message_id)
        if message:
            message.status = 'replied'
            message.admin_reply = reply_text
            message.replied_by = admin_user_id
            message.replied_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(message)
        return message

    async def mark_as_closed(self, message_id: int) -> Optional[ContactMessage]:
        """Close a message (no more replies needed)"""
        message = await self.get_message(message_id)
        if message:
            message.status = 'closed'
            message.closed_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(message)
        return message

    async def get_open_count(self) -> int:
        """Get count of open (unreplied) tickets"""
        query = select(func.count(ContactMessage.message_id)).where(
            ContactMessage.status == 'open'
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_message_count_by_category(self) -> dict:
        """Get message count grouped by category"""
        query = select(
            ContactMessage.category,
            func.count(ContactMessage.message_id)
        ).group_by(ContactMessage.category)

        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def get_recent_messages(self, days: int = 7, limit: int = 100) -> List[ContactMessage]:
        """Get messages from the last N days"""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(ContactMessage).where(
            ContactMessage.created_at >= cutoff_date
        ).order_by(desc(ContactMessage.created_at)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_message(self, message_id: int) -> bool:
        """Delete a message (admin only)"""
        message = await self.get_message(message_id)
        if message:
            await self.session.delete(message)
            await self.session.commit()
            return True
        return False

    async def get_today_count(self, user_id: int) -> int:
        """Get count of messages from user today"""
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        query = select(func.count(ContactMessage.message_id)).where(
            and_(
                ContactMessage.user_id == user_id,
                ContactMessage.created_at >= today,
                ContactMessage.created_at < tomorrow
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

