from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from app.db.base import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.question_repo import QuestionRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.attempt_repo import AttemptRepository
from admin_panel.utils.auth import get_current_admin_user

router = APIRouter()
templates = Jinja2Templates(directory="admin_panel/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show admin dashboard with statistics"""
    try:
        user_repo = UserRepository(db)
        question_repo = QuestionRepository(db)
        payment_repo = PaymentRepository(db)
        attempt_repo = AttemptRepository(db)
        
        # Get user stats
        all_users = await user_repo.get_all_users()
        total_users = len(all_users)
        blocked_users = sum(1 for u in all_users if u.blocked)
        approved_users = sum(1 for u in all_users if u.approved)
        premium_users = sum(1 for u in all_users if u.is_premium)
        
        # Get new users today
        today = datetime.now().date()
        new_users_today = sum(
            1 for u in all_users 
            if u.created_at and u.created_at.date() == today
        )
        
        # Get question stats
        total_questions = await question_repo.get_question_count()
        questions_by_difficulty = {
            'simple': await question_repo.get_question_count(difficulty='simple'),
            'medium': await question_repo.get_question_count(difficulty='medium'),
            'hard': await question_repo.get_question_count(difficulty='hard')
        }
        
        # Get subjects
        subjects = await question_repo.get_subjects()
        
        # Get payment stats
        revenue_data = await payment_repo.get_revenue_stats(days=30)
        total_revenue = revenue_data.get('total_revenue', 0)
        pending_payments = revenue_data.get('pending_count', 0)
        
        # Get recent payments
        from app.db.models import Payment
        query = select(Payment).order_by(desc(Payment.created_at)).limit(5)
        result = await db.execute(query)
        recent_payments = result.scalars().all()
        
        # Get recent activity
        recent_attempts = await attempt_repo.get_recent_attempts(limit=10)
        
        # Calculate growth (simplified)
        last_week_users = total_users  # Simplified - would need proper date comparison
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "admin_user": admin_user,
                "stats": {
                    "total_users": total_users,
                    "blocked_users": blocked_users,
                    "approved_users": approved_users,
                    "premium_users": premium_users,
                    "new_users_today": new_users_today,
                    "total_questions": total_questions,
                    "questions_by_difficulty": questions_by_difficulty,
                    "total_subjects": len(subjects),
                    "total_revenue": total_revenue,
                    "pending_payments": pending_payments,
                    "recent_payments": recent_payments,
                    "recent_attempts": recent_attempts
                },
                "current_date": datetime.now()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dashboard: {str(e)}")


@router.get("/stats", response_class=HTMLResponse)
async def stats_view(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show detailed statistics"""
    try:
        user_repo = UserRepository(db)
        question_repo = QuestionRepository(db)
        attempt_repo = AttemptRepository(db)
        
        all_users = await user_repo.get_all_users()
        
        # User growth by month
        users_by_month = {}
        for user in all_users:
            if user.created_at:
                month_key = user.created_at.strftime("%Y-%m")
                users_by_month[month_key] = users_by_month.get(month_key, 0) + 1
        
        # Activity by day (last 7 days)
        activity_by_day = []
        for i in range(7):
            day = datetime.now().date() - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            count = 0
            for user in all_users:
                # Simplified - would need actual attempt queries
                pass
            activity_by_day.append({
                "date": day,
                "formatted": day.strftime("%b %d"),
                "count": count
            })
        
        # Difficulty distribution
        simple = await question_repo.get_question_count(difficulty='simple')
        medium = await question_repo.get_question_count(difficulty='medium')
        hard = await question_repo.get_question_count(difficulty='hard')
        total = simple + medium + hard
        
        return templates.TemplateResponse(
            "stats.html",
            {
                "request": request,
                "admin_user": admin_user,
                "users_by_month": dict(sorted(users_by_month.items())),
                "activity_by_day": activity_by_day,
                "difficulty_dist": {
                    "simple": simple,
                    "medium": medium,
                    "hard": hard,
                    "total": total
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading stats: {str(e)}")


@router.get("/settings", response_class=HTMLResponse)
async def settings_view(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user)
):
    """Show bot settings"""
    try:
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "admin_user": admin_user
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading settings: {str(e)}")


@router.get("/logs", response_class=HTMLResponse)
async def logs_view(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show activity logs"""
    try:
        from app.db.models import AdminLog
        from app.repositories.admin_log_repo import AdminLogRepository
        
        log_repo = AdminLogRepository(db)
        logs = await log_repo.get_recent_logs(limit=100)
        
        return templates.TemplateResponse(
            "logs.html",
            {
                "request": request,
                "admin_user": admin_user,
                "logs": logs
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading logs: {str(e)}")


@router.get("/admins", response_class=HTMLResponse)
async def admins_view(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user)
):
    """Show admin management"""
    try:
        from app.db.models import TelegramAdmin
        
        # Get all telegram admins
        admins = [
            {"user_id": 123456789, "username": "admin1", "role": "admin", "is_active": True},
            {"user_id": 987654321, "username": "superadmin", "role": "superadmin", "is_active": True}
        ]  # Placeholder - would query from database
        
        return templates.TemplateResponse(
            "admins.html",
            {
                "request": request,
                "admin_user": admin_user,
                "admins": admins
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading admins: {str(e)}")

