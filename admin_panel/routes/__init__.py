# Admin Panel Routes
from admin_panel.routes.dashboard import router as dashboard_router
from admin_panel.routes.auth import router as auth_router
from admin_panel.routes.users import router as users_router
from admin_panel.routes.payments import router as payments_router
from admin_panel.routes.questions import router as questions_router
from admin_panel.routes.subjects import router as subjects_router
from admin_panel.routes.leaderboard import router as leaderboard_router

__all__ = [
    'dashboard_router',
    'auth_router',
    'users_router',
    'payments_router',
    'questions_router',
    'subjects_router',
    'leaderboard_router',
]

