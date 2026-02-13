from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminLog

class AdminLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_action(self, admin_user_id: int, action: str, details: str = None) -> AdminLog:
        """Log an admin action"""
        log = AdminLog(
            admin_user_id=admin_user_id,
            action=action,
            details=details
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
    
    async def get_logs(self, limit: int = 100, offset: int = 0) -> List[AdminLog]:
        """Get admin logs with pagination"""
        query = select(AdminLog).order_by(
            desc(AdminLog.created_at)
        ).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_logs_by_admin(self, admin_user_id: int, limit: int = 100) -> List[AdminLog]:
        """Get logs for a specific admin"""
        query = select(AdminLog).where(
            AdminLog.admin_user_id == admin_user_id
        ).order_by(desc(AdminLog.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_logs_by_action(self, action: str, limit: int = 100) -> List[AdminLog]:
        """Get logs by action type"""
        query = select(AdminLog).where(
            AdminLog.action == action
        ).order_by(desc(AdminLog.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_logs_by_date_range(self, start_date: datetime, 
                                     end_date: datetime, 
                                     limit: int = 100) -> List[AdminLog]:
        """Get logs within a date range"""
        query = select(AdminLog).where(
            and_(
                AdminLog.created_at >= start_date,
                AdminLog.created_at <= end_date
            )
        ).order_by(desc(AdminLog.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_log_count(self) -> int:
        """Get total log count"""
        query = select(func.count(AdminLog.id))
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_logs_by_target(self, target_type: str, target_id: int) -> List[AdminLog]:
        """Get logs related to a specific target (user, question, payment, etc.)"""
        query = select(AdminLog).where(
            and_(
                AdminLog.action.like(f"%{target_type}%"),
                AdminLog.action.like(f"%{target_id}%")
            )
        ).order_by(desc(AdminLog.created_at))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def clear_old_logs(self, days_to_keep: int = 30) -> int:
        """Delete logs older than specified days, return count deleted"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Delete old logs
        from sqlalchemy import delete
        stmt = delete(AdminLog).where(AdminLog.created_at < cutoff_date)
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        return result.rowcount
    
    async def get_action_summary(self, days: int = 7) -> Dict[str, int]:
        """Get summary of actions by type for the last N days"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            AdminLog.action,
            func.count(AdminLog.id)
        ).where(
            AdminLog.created_at >= start_date
        ).group_by(AdminLog.action)
        
        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

