from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AdminLog, TelegramAdmin, User

class AdminRepository:
    @staticmethod
    async def log_action(session: AsyncSession, admin_user_id: int, action: str, details: Optional[str] = None):
        """Insert an admin action log entry."""
        log = AdminLog(
            admin_user_id=admin_user_id,
            action=action,
            details=details
        )
        session.add(log)
        await session.flush()
        return log

    @staticmethod
    async def list_logs(session: AsyncSession, limit: int = 100):
        result = await session.execute(
            AdminLog.__table__.select().order_by(AdminLog.created_at.desc()).limit(limit)
        )
        return result.fetchall()


class TelegramAdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_admin(self, user_id: int) -> Optional[TelegramAdmin]:
        """Get admin by user_id"""
        query = select(TelegramAdmin).where(
            TelegramAdmin.user_id == user_id,
            TelegramAdmin.is_active == True
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_admin(self, user_id: int, username: str = None, 
                          role: str = 'admin', added_by: int = None) -> TelegramAdmin:
        """Create new admin"""
        existing = await self.get_admin(user_id)
        if existing:
            return existing
        
        admin = TelegramAdmin(
            user_id=user_id,
            username=username,
            role=role,
            added_by=added_by
        )
        self.session.add(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin by user_id"""
        stmt = update(TelegramAdmin).where(
            TelegramAdmin.user_id == user_id
        ).values(is_active=False)
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def list_admins(self, role: str = None) -> List[TelegramAdmin]:
        """List all active admins"""
        query = select(TelegramAdmin).where(TelegramAdmin.is_active == True)
        
        if role:
            query = query.where(TelegramAdmin.role == role)
        
        query = query.order_by(TelegramAdmin.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        admin = await self.get_admin(user_id)
        return admin is not None
    
    async def is_superadmin(self, user_id: int) -> bool:
        """Check if user is superadmin"""
        admin = await self.get_admin(user_id)
        return admin is not None and admin.role == 'superadmin'
    
    async def get_admin_role(self, user_id: int) -> Optional[str]:
        """Get admin role"""
        admin = await self.get_admin(user_id)
        return admin.role if admin else None
    
    async def update_admin_role(self, user_id: int, role: str) -> bool:
        """Update admin role"""
        stmt = update(TelegramAdmin).where(
            TelegramAdmin.user_id == user_id
        ).values(role=role)
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Get admin statistics"""
        query = select(TelegramAdmin).where(TelegramAdmin.is_active == True)
        result = await self.session.execute(query)
        admins = result.scalars().all()
        
        total_admins = len(admins)
        superadmins = len([a for a in admins if a.role == 'superadmin'])
        regular_admins = len([a for a in admins if a.role == 'admin'])
        
        return {
            'total_admins': total_admins,
            'superadmins': superadmins,
            'regular_admins': regular_admins
        }
    
    async def can_manage_admins(self, user_id: int) -> bool:
        """Check if admin can manage other admins (superadmin only)"""
        return await self.is_superadmin(user_id)
    
    async def can_approve_payments(self, user_id: int) -> bool:
        """Check if admin can approve payments (admin or superadmin)"""
        return await self.is_admin(user_id)
    
    async def promote_admin(self, user_id: int, role: str) -> bool:
        """Promote or demote an admin to a different role
        
        Args:
            user_id: The admin's user ID
            role: The new role ('admin' or 'superadmin')
        
        Returns:
            True if role was updated, False if admin not found
        """
        if role not in ['admin', 'superadmin']:
            return False
        
        stmt = update(TelegramAdmin).where(
            TelegramAdmin.user_id == user_id
        ).values(role=role)
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_admin_with_adder_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get admin details along with who added them
        
        Args:
            user_id: The admin's user ID
        
        Returns:
            Dict with admin info and adder info, or None if not found
        """
        admin = await self.get_admin(user_id)
        if not admin:
            return None
        
        adder_info = None
        if admin.added_by:
            try:
                adder_user = await self.session.get(User, admin.added_by)
                adder_info = {
                    'user_id': admin.added_by,
                    'username': adder_user.username if adder_user else None,
                    'first_name': adder_user.first_name if adder_user else None
                }
            except Exception:
                # User who added this admin may have been deleted
                adder_info = {
                    'user_id': admin.added_by,
                    'username': None,
                    'first_name': 'Unknown'
                }
        
        return {
            'admin': admin,
            'adder': adder_info
        }
    
    async def get_admin_by_username(self, username: str) -> Optional[TelegramAdmin]:
        """Find an admin by username
        
        Args:
            username: The username to search for (with or without @)
        
        Returns:
            TelegramAdmin if found, None otherwise
        """
        # Remove @ if present
        username = username.lstrip('@')
        
        query = select(TelegramAdmin).where(
            or_(
                TelegramAdmin.username == username,
                TelegramAdmin.username == f"@{username}"
            ),
            TelegramAdmin.is_active == True
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def search_user_by_username(self, username: str) -> Optional[User]:
        """Search for a regular user by username
        
        Args:
            username: The username to search for
        
        Returns:
            User if found, None otherwise
        """
        username = username.lstrip('@')
        
        query = select(User).where(
            or_(
                User.username == username,
                User.username == f"@{username}"
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_admins_with_details(self) -> List[Dict[str, Any]]:
        """Get all admins with full details including who added them
        
        Returns:
            List of admin details dicts
        """
        admins = await self.list_admins()
        result = []
        
        for admin in admins:
            adder_info = None
            if admin.added_by:
                try:
                    adder_user = await self.session.get(User, admin.added_by)
                    adder_info = {
                        'user_id': admin.added_by,
                        'username': adder_user.username if adder_user else None,
                        'first_name': adder_user.first_name if adder_user else None
                    }
                except Exception:
                    # User who added this admin may have been deleted
                    adder_info = {
                        'user_id': admin.added_by,
                        'username': None,
                        'first_name': 'Unknown'
                    }
            
            result.append({
                'id': admin.id,
                'user_id': admin.user_id,
                'username': admin.username,
                'role': admin.role,
                'is_active': admin.is_active,
                'added_by': adder_info,
                'created_at': admin.created_at,
                'updated_at': admin.updated_at
            })
        
        return result

