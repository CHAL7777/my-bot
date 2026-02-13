from app.handlers.start import router as start_router
from app.handlers.quiz_fixed import router as quiz_router
from app.handlers.quiz_high_quality import router as quiz_hq_router
from app.handlers.answers import router as answers_router
from app.handlers.progress import router as progress_router
from app.handlers.leaderboard import router as leaderboard_router
from app.handlers.payment import router as payment_router
from app.handlers.admin import router as admin_router
from app.handlers.admin_questions import router as admin_questions_router
from app.handlers.admin_users import router as admin_users_router
from app.handlers.admin_subjects import router as admin_subjects_router
from app.handlers.admin_payments import router as admin_payments_router
from app.handlers.admin_stats import router as admin_stats_router
from app.handlers.admin_logs import router as admin_logs_router
from app.handlers.admin_messages import router as admin_messages_router
from app.handlers.admin_manage import router as admin_manage_router
from app.handlers.admin_referrals import router as admin_referrals_router
from app.handlers.referral import router as referral_router

__all__ = [
    'start_router',
    'quiz_router',
    'quiz_hq_router',
    'answers_router',
    'progress_router',
    'leaderboard_router',
    'payment_router',
    'admin_router',
    'admin_questions_router',
    'admin_users_router',
    'admin_subjects_router',
    'admin_payments_router',
    'admin_stats_router',
    'admin_logs_router',
    'admin_messages_router',
    'admin_manage_router',
    'admin_referrals_router',
    'referral_router'
]
