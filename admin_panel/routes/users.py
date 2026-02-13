from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional

from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from admin_panel.utils.auth import get_current_admin_user

router = APIRouter()
templates = Jinja2Templates(directory="admin_panel/templates")

@router.get("/", response_class=HTMLResponse)
async def users_list(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show users list with pagination and search"""
    try:
        user_repo = UserRepository(db)
        per_page = 20
        offset = (page - 1) * per_page

        # Get users
        if search:
            users = await user_repo.search_users(search)
            total_users = len(users)
            users = users[offset:offset + per_page]
        else:
            users = await user_repo.get_all_users(skip=offset, limit=per_page)
            # Get total count (simplified)
            all_users = await user_repo.get_all_users()
            total_users = len(all_users)

        total_pages = (total_users + per_page - 1) // per_page

        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "admin_user": admin_user,
                "users": users,
                "page": page,
                "total_pages": total_pages,
                "search": search,
                "total_users": total_users
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading users: {str(e)}")

@router.post("/{user_id}/approve")
async def approve_user(
    user_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve a user"""
    try:
        user_repo = UserRepository(db)
        success = await user_repo.update_user(user_id, approved=True)

        if success:
            return RedirectResponse(url="/users", status_code=302)
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving user: {str(e)}")

@router.post("/{user_id}/reject")
async def reject_user(
    user_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject a user (set approved=False)"""
    try:
        user_repo = UserRepository(db)
        success = await user_repo.update_user(user_id, approved=False)

        if success:
            return RedirectResponse(url="/users", status_code=302)
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rejecting user: {str(e)}")

@router.post("/{user_id}/block")
async def block_user(
    user_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Block a user"""
    try:
        user_repo = UserRepository(db)
        success = await user_repo.block_user(user_id)

        if success:
            return RedirectResponse(url="/users", status_code=302)
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error blocking user: {str(e)}")

@router.post("/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Unblock a user"""
    try:
        user_repo = UserRepository(db)
        success = await user_repo.unblock_user(user_id)

        if success:
            return RedirectResponse(url="/users", status_code=302)
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error unblocking user: {str(e)}")

@router.get("/{user_id}/details", response_class=HTMLResponse)
async def user_details(
    user_id: int,
    request: Request,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show detailed user information"""
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_user(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user statistics
        user_stats = await user_repo.get_user_statistics(user_id)

        # Get recent attempts
        recent_attempts = await user_repo.get_user_attempts(user_id, limit=10)

        return templates.TemplateResponse(
            "user_details.html",
            {
                "request": request,
                "admin_user": admin_user,
                "user": user,
                "stats": user_stats,
                "recent_attempts": recent_attempts
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading user details: {str(e)}")
