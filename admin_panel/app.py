from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uvicorn
from typing import Optional

from app.db.base import get_db
from admin_panel.utils.auth import (
    get_current_admin_user,
    create_access_token,
    verify_password,
    get_password_hash
)
from admin_panel.models import AdminUser
from admin_panel.routes import (
    dashboard,
    auth,
    users,
    payments,
    questions,
    subjects,
    leaderboard
)

# Create FastAPI app
app = FastAPI(
    title="Telegram Quiz Bot Admin Panel",
    description="Admin panel for managing Telegram Quiz Bot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="admin_panel/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="admin_panel/templates")

# Include routers
app.include_router(auth.router, prefix="", tags=["authentication"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
app.include_router(leaderboard.router, prefix="/leaderboard", tags=["leaderboard"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to login or dashboard based on authentication"""
    try:
        admin_user = await get_current_admin_user(request)
        return RedirectResponse(url="/dashboard", status_code=302)
    except:
        return RedirectResponse(url="/login", status_code=302)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "admin_panel"}

if __name__ == "__main__":
    port = int(os.environ.get('ADMIN_PORT', 5001))
    host = os.environ.get('ADMIN_HOST', '127.0.0.1')
    uvicorn.run(
        "admin_panel.app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
