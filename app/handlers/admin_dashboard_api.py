"""
Admin Dashboard API Handler - Telegram Quiz Bot
Provides dashboard statistics via REST API endpoints.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.db.base import get_db, AsyncSessionLocal
from app.repositories.user_repo import UserRepository
from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ============================================================================
# Pydantic Models for API Responses
# ============================================================================

class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response model"""
    timestamp: str
    period_days: int
    users: Dict[str, Any]
    questions: Dict[str, Any]
    activity: Dict[str, Any]
    revenue: Dict[str, Any]
    health_score: float
    status: str


class UserStatsResponse(BaseModel):
    """User statistics response model"""
    total: int
    active: int
    new: int
    blocked: int
    retention_rate: float


class QuestionStatsResponse(BaseModel):
    """Question statistics response model"""
    total: int
    by_difficulty: Dict[str, int]
    by_subject: Dict[str, int]
    coverage: Dict[str, Any]


class RevenueStatsResponse(BaseModel):
    """Revenue statistics response model"""
    total_revenue: float
    payment_count: int
    avg_revenue_per_payment: float
    daily_trend: list


class HealthResponse(BaseModel):
    """System health response model"""
    status: str
    health_score: float
    checks: Dict[str, Any]
    timestamp: str


# ============================================================================
# Dashboard API Endpoints
# ============================================================================

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    days: int = Query(default=30, description="Number of days for statistics")
) -> DashboardStatsResponse:
    """
    Get comprehensive dashboard statistics.
    
    Returns:
        DashboardStatsResponse with all statistics
    """
    try:
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            question_repo = QuestionRepository(session)
            attempt_repo = AttemptRepository(session)
            payment_repo = PaymentRepository(session)
            
            analytics_service = AnalyticsService(
                user_repo, question_repo, attempt_repo, payment_repo
            )
            
            stats = await analytics_service.get_dashboard_stats(days=days)
            
            # Determine status based on health score
            health_score = stats.get('health_score', 0)
            if health_score > 70:
                status = "healthy"
            elif health_score > 40:
                status = "warning"
            else:
                status = "critical"
            
            return DashboardStatsResponse(
                timestamp=stats.get('timestamp', datetime.now()).isoformat(),
                period_days=stats.get('period_days', days),
                users=stats.get('users', {}),
                questions=stats.get('questions', {}),
                activity=stats.get('activity', {}),
                revenue=stats.get('revenue', {}),
                health_score=health_score,
                status=status
            )
            
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=UserStatsResponse)
async def get_user_stats(
    days: int = Query(default=7, description="Number of days for activity calculation")
) -> UserStatsResponse:
    """Get user statistics"""
    try:
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            
            all_users = await user_repo.get_all_users(limit=10000)
            total_users = len(all_users)
            
            # Get active users
            cutoff_date = datetime.now() - timedelta(days=days)
            active_users = sum(
                1 for u in all_users 
                if u.created_at and u.created_at >= cutoff_date
            )
            
            # Get new users (registered in last N days)
            new_users = active_users
            
            # Get blocked users
            blocked_users = sum(1 for u in all_users if u.blocked)
            
            # Calculate retention rate
            retention_rate = 0
            if total_users > 0:
                retention_rate = (active_users / total_users) * 100
            
            return UserStatsResponse(
                total=total_users,
                active=active_users,
                new=new_users,
                blocked=blocked_users,
                retention_rate=round(retention_rate, 2)
            )
            
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions", response_model=QuestionStatsResponse)
async def get_question_stats() -> QuestionStatsResponse:
    """Get question statistics"""
    try:
        async with AsyncSessionLocal() as session:
            question_repo = QuestionRepository(session)
            
            # Get total count
            total = await question_repo.get_question_count()
            
            # Get counts by difficulty
            simple = await question_repo.get_question_count(difficulty='simple')
            medium = await question_repo.get_question_count(difficulty='medium')
            hard = await question_repo.get_question_count(difficulty='hard')
            
            # Get counts by subject
            subjects = await question_repo.get_subjects()
            by_subject = {}
            for subject in subjects:
                count = await question_repo.get_question_count(subject_id=subject.subject_id)
                by_subject[subject.subject_name] = count
            
            # Calculate coverage
            chapters = []
            for subject in subjects:
                subject_chapters = await question_repo.get_chapters(subject.subject_id)
                chapters.extend(subject_chapters)
            
            covered_chapters = 0
            for chapter in chapters:
                chapter_count = await question_repo.get_question_count(chapter_id=chapter.chapter_id)
                if chapter_count > 0:
                    covered_chapters += 1
            
            coverage_percentage = (covered_chapters / len(chapters) * 100) if chapters else 0
            
            return QuestionStatsResponse(
                total=total,
                by_difficulty={
                    'simple': simple,
                    'medium': medium,
                    'hard': hard
                },
                by_subject=by_subject,
                coverage={
                    'total_chapters': len(chapters),
                    'covered_chapters': covered_chapters,
                    'percentage': round(coverage_percentage, 2)
                }
            )
            
    except Exception as e:
        logger.error(f"Error getting question stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue", response_model=RevenueStatsResponse)
async def get_revenue_stats(
    days: int = Query(default=30, description="Number of days for revenue calculation")
) -> RevenueStatsResponse:
    """Get revenue statistics"""
    try:
        async with AsyncSessionLocal() as session:
            payment_repo = PaymentRepository(session)
            
            stats = await payment_repo.get_revenue_stats(days=days)
            
            return RevenueStatsResponse(
                total_revenue=stats.get('total_revenue', 0),
                payment_count=stats.get('payment_count', 0),
                avg_revenue_per_payment=stats.get('avg_revenue_per_payment', 0),
                daily_trend=stats.get('daily_trend', [])
            )
            
    except Exception as e:
        logger.error(f"Error getting revenue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def detailed_health_check() -> HealthResponse:
    """
    Get detailed system health information.
    
    Returns:
        HealthResponse with status, health score, and individual checks
    """
    checks = {}
    overall_status = "healthy"
    health_score = 100
    
    try:
        async with AsyncSessionLocal() as session:
            # Check database connection
            try:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                checks['database'] = {
                    'status': 'healthy',
                    'response_time_ms': 10
                }
            except Exception as e:
                checks['database'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_score -= 30
                overall_status = "critical"
            
            # Check question count
            try:
                question_repo = QuestionRepository(session)
                question_count = await question_repo.get_question_count()
                if question_count > 0:
                    checks['questions'] = {
                        'status': 'healthy',
                        'count': question_count
                    }
                else:
                    checks['questions'] = {
                        'status': 'warning',
                        'count': 0,
                        'message': 'No questions in database'
                    }
                    health_score -= 10
                    if overall_status != "critical":
                        overall_status = "warning"
            except Exception as e:
                checks['questions'] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_score -= 15
            
            # Check user count
            try:
                user_repo = UserRepository(session)
                all_users = await user_repo.get_all_users(limit=10000)
                user_count = len(all_users)
                if user_count > 0:
                    checks['users'] = {
                        'status': 'healthy',
                        'count': user_count
                    }
                else:
                    checks['users'] = {
                        'status': 'warning',
                        'count': 0,
                        'message': 'No users registered'
                    }
                    health_score -= 5
            except Exception as e:
                checks['users'] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_score -= 10
            
            # Check revenue (optional - not critical)
            try:
                payment_repo = PaymentRepository(session)
                revenue_stats = await payment_repo.get_revenue_stats(days=30)
                checks['revenue'] = {
                    'status': 'healthy' if revenue_stats['total_revenue'] > 0 else 'warning',
                    'total': revenue_stats['total_revenue'],
                    'payment_count': revenue_stats['payment_count']
                }
                if revenue_stats['total_revenue'] == 0:
                    health_score -= 5
                    if overall_status == "healthy":
                        overall_status = "warning"
            except Exception as e:
                checks['revenue'] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_score -= 5
    
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        overall_status = "critical"
        health_score = 0
        checks['overall'] = {'status': 'error', 'error': str(e)}
    
    # Ensure health score doesn't go below 0
    health_score = max(0, health_score)
    
    return HealthResponse(
        status=overall_status,
        health_score=health_score,
        checks=checks,
        timestamp=datetime.now().isoformat()
    )


@router.get("/health/simple")
async def simple_health_check() -> Dict[str, Any]:
    """
    Simple health check endpoint (for load balancers/UptimeRobot).
    
    Returns minimal response for basic health verification.
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return {"status": "healthy", "service": "quiz_bot_dashboard"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ============================================================================
# Summary Endpoint
# ============================================================================

@router.get("/summary")
async def get_dashboard_summary() -> Dict[str, Any]:
    """
    Get a quick summary of the dashboard for display purposes.
    
    Returns simplified statistics for quick overview.
    """
    try:
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            question_repo = QuestionRepository(session)
            payment_repo = PaymentRepository(session)
            
            # Get user count
            all_users = await user_repo.get_all_users(limit=10000)
            total_users = len(all_users)
            active_users = sum(1 for u in all_users if not u.blocked)
            
            # Get question count
            total_questions = await question_repo.get_question_count()
            
            # Get revenue
            revenue_stats = await payment_repo.get_revenue_stats(days=30)
            
            # Calculate health score (simplified)
            health_score = 0
            if total_users > 0:
                health_score += 30  # Users exist
            if total_questions > 0:
                health_score += 30  # Questions exist
            if revenue_stats['total_revenue'] > 0:
                health_score += 20  # Revenue exists
            if active_users > 0:
                health_score += 20  # Active users
            
            return {
                'summary': {
                    'users': {
                        'total': total_users,
                        'active': active_users
                    },
                    'questions': {
                        'total': total_questions
                    },
                    'revenue': {
                        'total_30_days': revenue_stats['total_revenue'],
                        'payment_count': revenue_stats['payment_count']
                    },
                    'health_score': health_score,
                    'status': 'healthy' if health_score > 70 else 'warning' if health_score > 40 else 'critical'
                },
                'generated_at': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

