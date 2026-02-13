from fastapi import APIRouter, Request, Response, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.db.base import get_db
from admin_panel.utils.auth import (
    authenticate_admin,
    create_access_token,
    get_current_admin_user
)

router = APIRouter()
templates = Jinja2Templates(directory="admin_panel/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle login form submission"""
    # Authenticate user
    admin_user = await authenticate_admin(db, username, password)

    if not admin_user:
        # Return to login page with error
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password"
            }
        )

    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": admin_user.username},
        expires_delta=access_token_expires
    )

    # Set token in cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="admin_token",
        value=access_token,
        httponly=True,
        max_age=30 * 60,  # 30 minutes
        expires=30 * 60,
    )

    return response

@router.post("/logout")
async def logout(response: Response):
    """Handle logout"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="admin_token")
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user)
):
    """Show admin profile page"""
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "admin_user": admin_user
        }
    )
