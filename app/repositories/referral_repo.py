from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_, func, Integer, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Referral, User


class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_referral(self, referrer_id: int, referred_id: int) -> Referral:
        """
        Create a new referral record with idempotency.
        
        IMPORTANT: Uses INSERT ... ON CONFLICT to be idempotent.
        If referral already exists, it returns the existing one without error.
        """
        # Use raw SQL for ON CONFLICT support (more reliable than ORM)
        query = text("""
            INSERT INTO referrals (referrer_id, referred_id, status, created_at)
            VALUES (:referrer_id, :referred_id, 'pending', NOW())
            ON CONFLICT (referrer_id, referred_id) 
            DO UPDATE SET created_at = NOW()
            RETURNING id, referrer_id, referred_id, status, created_at
        """)
        
        result = await self.session.execute(query, {
            "referrer_id": referrer_id,
            "referred_id": referred_id
        })
        row = result.fetchone()
        
        if row:
            # Refresh to get the full object
            referral = await self.get_referral_by_id(row.id)
            if referral:
                return referral
        
        # Fallback: try ORM create if raw SQL didn't return row
        referral = Referral(
            referrer_id=referrer_id,
            referred_id=referred_id,
            status='pending'
        )
        self.session.add(referral)
        await self.session.commit()
        await self.session.refresh(referral)
        return referral

    async def get_referral_by_users(self, referrer_id: int, referred_id: int) -> Optional[Referral]:
        """Get referral between two users"""
        query = select(Referral).where(
            and_(
                Referral.referrer_id == referrer_id,
                Referral.referred_id == referred_id
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def approve_referral(self, referral_id: int) -> Referral:
        """
        Mark referral as approved (referred user was approved by admin).
        
        This is called when admin approves the referred user's payment.
        Changes status from 'pending' to 'approved'.
        """
        stmt = update(Referral).where(Referral.id == referral_id).values(
            status='approved',
            approved_at=datetime.utcnow()
        )
        await self.session.execute(stmt)
        await self.session.commit()

        # Get updated referral
        query = select(Referral).where(Referral.id == referral_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def cancel_referral(self, referral_id: int) -> bool:
        """Cancel a referral"""
        stmt = update(Referral).where(Referral.id == referral_id).values(
            status='cancelled'
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_user_referrals(self, user_id: int, status: str = None) -> List[Referral]:
        """Get all referrals for a user (as referrer)"""
        query = select(Referral).where(Referral.referrer_id == user_id)

        if status:
            query = query.where(Referral.status == status)

        query = query.order_by(Referral.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_referrals_to_user(self, user_id: int, status: str = None) -> List[Referral]:
        """Get all referrals to a user (as referred)"""
        query = select(Referral).where(Referral.referred_id == user_id)

        if status:
            query = query.where(Referral.status == status)

        query = query.order_by(Referral.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_referral_stats_batch(self, user_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Get referral statistics for multiple users in a single optimized query.
        
        This is much more efficient than calling get_referral_stats() for each user
        when building leaderboards or displaying multiple user stats.
        
        Args:
            user_ids: List of user IDs to fetch stats for
            
        Returns:
            Dict mapping user_id -> referral stats dict
        """
        if not user_ids:
            return {}
        
        # Use raw SQL for better performance on batch queries
        # This approach avoids the overhead of multiple ORM queries
        query = text("""
            SELECT 
                referrer_id,
                COUNT(*) as total_sent,
                COUNT(*) FILTER (WHERE status = 'approved') as approved,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
            FROM referrals
            WHERE referrer_id = ANY(:user_ids)
            GROUP BY referrer_id
        """)
        
        result = await self.session.execute(query, {"user_ids": user_ids})
        rows = result.fetchall()
        
        stats_map = {}
        for row in rows:
            user_id = row.referrer_id
            total_sent = row.total_sent or 0
            approved = row.approved or 0
            stats_map[user_id] = {
                'total_sent': total_sent,
                'approved': approved,
                'pending': row.pending or 0,
                'cancelled': row.cancelled or 0,
                'success_rate': round((approved / total_sent * 100) if total_sent > 0 else 0, 2)
            }
        
        # Include users with zero referrals (not in results)
        for user_id in user_ids:
            if user_id not in stats_map:
                stats_map[user_id] = {
                    'total_sent': 0,
                    'approved': 0,
                    'pending': 0,
                    'cancelled': 0,
                    'success_rate': 0
                }
        
        return stats_map

    async def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get referral statistics for a user - OPTIMIZED VERSION.
        
        Performs a single query with conditional aggregation instead of 4 separate queries.
        This reduces database round-trips by ~75%.
        
        Returns:
            Dict with referral statistics
        """
        # OPTIMIZED: Single query with conditional aggregation
        # This runs ONE query instead of FOUR
        query = select(
            func.count(Referral.id).label('total_sent'),
            func.sum(func.cast(Referral.status == 'approved', Integer)).label('approved'),
            func.sum(func.cast(Referral.status == 'pending', Integer)).label('pending'),
            func.sum(func.cast(Referral.status == 'cancelled', Integer)).label('cancelled')
        ).where(Referral.referrer_id == user_id)
        
        result = await self.session.execute(query)
        row = result.one()
        
        total_sent = row.total_sent or 0
        approved = row.approved or 0
        pending = row.pending or 0
        cancelled = row.cancelled or 0
        
        return {
            'total_sent': total_sent,
            'approved': approved,
            'pending': pending,
            'cancelled': cancelled,
            'success_rate': round((approved / total_sent * 100) if total_sent > 0 else 0, 2)
        }

    async def get_top_referrers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top referrers by completed referrals"""
        # Get users with their referral counts
        query = select(
            User.user_id,
            User.username,
            User.first_name,
            User.last_name,
            User.referral_count
        ).where(
            User.referral_count > 0
        ).order_by(
            User.referral_count.desc()
        ).limit(limit)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                'user_id': row.user_id,
                'username': row.username,
                'first_name': row.first_name,
                'last_name': row.last_name,
                'referral_count': row.referral_count,
                'name': f"{row.first_name or ''} {row.last_name or ''}".strip() or row.username or f"User {row.user_id}"
            }
            for row in rows
        ]

    async def get_pending_referrals(self, limit: int = 100) -> List[Referral]:
        """Get all pending referrals"""
        query = select(Referral).where(
            Referral.status == 'pending'
        ).order_by(Referral.created_at.asc()).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending_referrals_with_details(
        self, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get pending referrals with full user details for both referrer and referred users.
        
        This method performs a JOIN query to fetch referral data along with user information
        for both the referrer and the referred user in a single efficient query.
        
        Args:
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of dictionaries containing referral and user details:
            {
                'id': referral_id,
                'referrer_id': user_id,
                'referred_id': user_id,
                'status': 'pending',
                'created_at': datetime,
                'approved_at': datetime or None,
                'reward_claimed': bool,
                'reward_claimed_at': datetime or None,
                'referrer_user': {
                    'user_id': ...,
                    'username': ... or None,
                    'first_name': ... or None,
                    'last_name': ... or None,
                    'is_premium': bool
                },
                'referred_user': {
                    'user_id': ...,
                    'username': ... or None,
                    'first_name': ... or None,
                    'last_name': ... or None,
                    'is_premium': bool
                }
            }
        """
        # Use joinedload to eagerly load both user relationships
        from sqlalchemy.orm import joinedload
        
        query = (
            select(Referral)
            .options(
                joinedload(Referral.referrer_user),
                joinedload(Referral.referred_user)
            )
            .where(Referral.status == 'pending')
            .order_by(Referral.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        referrals = result.unique().scalars().all()
        
        # Transform to dict format with user details
        return [
            {
                'id': referral.id,
                'referrer_id': referral.referrer_id,
                'referred_id': referral.referred_id,
                'status': referral.status,
                'created_at': referral.created_at,
                'approved_at': referral.approved_at,
                'reward_claimed': referral.reward_claimed,
                'reward_claimed_at': referral.reward_claimed_at,
                'referrer_user': {
                    'user_id': referral.referrer_user.user_id,
                    'username': referral.referrer_user.username,
                    'first_name': referral.referrer_user.first_name,
                    'last_name': referral.referrer_user.last_name,
                    'is_premium': referral.referrer_user.is_premium
                } if referral.referrer_user else None,
                'referred_user': {
                    'user_id': referral.referred_user.user_id,
                    'username': referral.referred_user.username,
                    'first_name': referral.referred_user.first_name,
                    'last_name': referral.referred_user.last_name,
                    'is_premium': referral.referred_user.is_premium
                } if referral.referred_user else None
            }
            for referral in referrals
        ]

    async def get_approved_referrals_for_user(self, user_id: int) -> List[Referral]:
        """Get all approved referrals for a user (these earn rewards)"""
        query = select(Referral).where(
            and_(
                Referral.referrer_id == user_id,
                Referral.status == 'approved'
            )
        ).order_by(Referral.approved_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def mark_reward_claimed(self, referral_id: int) -> bool:
        """Mark referral reward as claimed (to prevent double-crediting)"""
        stmt = update(Referral).where(Referral.id == referral_id).values(
            reward_claimed=True,
            reward_claimed_at=datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_referral_by_id(self, referral_id: int) -> Optional[Referral]:
        """Get referral by ID"""
        query = select(Referral).where(Referral.id == referral_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
