from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.repositories.leaderboard_repo import LeaderboardRepository
from admin_panel.utils.auth import get_current_admin_user

router = APIRouter()
templates = Jinja2Templates(directory="admin_panel/templates")

@router.get("/", response_class=HTMLResponse)
async def leaderboard_view(
    request: Request,
    period: str = "overall",
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show leaderboard for selected period"""
    try:
        leaderboard_repo = LeaderboardRepository(db)

        # Get leaderboard data
        leaderboard = await leaderboard_repo.get_leaderboard(period)

        # Get leaderboard statistics
        stats = await leaderboard_repo.get_leaderboard_stats()

        return templates.TemplateResponse(
            "leaderboard.html",
            {
                "request": request,
                "admin_user": admin_user,
                "leaderboard": leaderboard,
                "period": period,
                "stats": stats
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading leaderboard: {str(e)}")

@router.post("/reset/{period}")
async def reset_leaderboard(
    period: str,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset leaderboard for a period"""
    try:
        # Check if admin has permission (only superadmin can reset)
        if admin_user.get('role') != 'superadmin':
            raise HTTPException(status_code=403, detail="Only superadmin can reset leaderboard")

        leaderboard_repo = LeaderboardRepository(db)

        # Clear leaderboard for the period
        # Note: This would require modifying LeaderboardRepository
        # For now, just redirect
        return RedirectResponse(url=f"/leaderboard?period={period}", status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting leaderboard: {str(e)}")

@router.get("/stats")
async def get_leaderboard_stats(
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get leaderboard statistics (API endpoint)"""
    try:
        leaderboard_repo = LeaderboardRepository(db)
        stats = await leaderboard_repo.get_leaderboard_stats()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")
