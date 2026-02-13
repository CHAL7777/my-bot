from fastapi import APIRouter, Request, Depends, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.base import get_db
from app.repositories.question_repo import QuestionRepository
from admin_panel.utils.auth import get_current_admin_user

router = APIRouter()
templates = Jinja2Templates(directory="admin_panel/templates")


@router.get("/", response_class=HTMLResponse)
async def subjects_list(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show subjects list"""
    try:
        question_repo = QuestionRepository(db)
        subjects = await question_repo.get_subjects(eager_load=True)
        
        # Get question counts for each subject
        subjects_with_counts = []
        for subject in subjects:
            count = await question_repo.get_question_count(subject_id=subject.subject_id)
            subjects_with_counts.append({
                'subject': subject,
                'question_count': count,
                'chapter_count': len(subject.chapters) if hasattr(subject, 'chapters') else 0
            })
        
        return templates.TemplateResponse(
            "subjects.html",
            {
                "request": request,
                "admin_user": admin_user,
                "subjects_with_counts": subjects_with_counts
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading subjects: {str(e)}")


@router.get("/add", response_class=HTMLResponse)
async def add_subject_form(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user)
):
    """Show add subject form"""
    return templates.TemplateResponse(
        "add_subject.html",
        {
            "request": request,
            "admin_user": admin_user
        }
    )


@router.post("/add")
async def add_subject(
    request: Request,
    subject_name: str = Form(...),
    description: str = Form(""),
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Add new subject"""
    try:
        question_repo = QuestionRepository(db)
        
        # Check if subject exists
        existing = await question_repo.get_subject_by_name(subject_name)
        if existing:
            return templates.TemplateResponse(
                "add_subject.html",
                {
                    "request": request,
                    "admin_user": admin_user,
                    "error": f"Subject '{subject_name}' already exists",
                    "form_data": {'subject_name': subject_name, 'description': description}
                }
            )
        
        subject = await question_repo.create_subject(subject_name=subject_name, description=description)
        return RedirectResponse(url="/subjects", status_code=302)
    
    except Exception as e:
        return templates.TemplateResponse(
            "add_subject.html",
            {
                "request": request,
                "admin_user": admin_user,
                "error": f"Error adding subject: {str(e)}",
                "form_data": {'subject_name': subject_name, 'description': description}
            }
        )


@router.get("/{subject_id}", response_class=HTMLResponse)
async def view_subject(
    request: Request,
    subject_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """View subject details with chapters"""
    try:
        question_repo = QuestionRepository(db)
        subject = await question_repo.get_subject(subject_id)
        
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        chapters = await question_repo.get_chapters(subject_id)
        
        # Get chapter question counts
        chapters_with_counts = []
        for chapter in chapters:
            count = await question_repo.get_question_count(subject_id=subject_id, chapter_id=chapter.chapter_id)
            chapters_with_counts.append({
                'chapter': chapter,
                'question_count': count
            })
        
        return templates.TemplateResponse(
            "view_subject.html",
            {
                "request": request,
                "admin_user": admin_user,
                "subject": subject,
                "chapters_with_counts": chapters_with_counts
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading subject: {str(e)}")


@router.post("/{subject_id}/add_chapter")
async def add_chapter(
    request: Request,
    subject_id: int,
    chapter_name: str = Form(...),
    chapter_order: int = Form(0),
    description: str = Form(""),
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Add new chapter to subject"""
    try:
        question_repo = QuestionRepository(db)
        chapter = await question_repo.create_chapter(
            subject_id=subject_id,
            chapter_name=chapter_name,
            chapter_order=chapter_order,
            description=description
        )
        return RedirectResponse(url=f"/subjects/{subject_id}", status_code=302)
    
    except Exception as e:
        return templates.TemplateResponse(
            "view_subject.html",
            {
                "request": request,
                "admin_user": admin_user,
                "error": f"Error adding chapter: {str(e)}"
            }
        )


@router.get("/{subject_id}/toggle")
async def toggle_subject(
    request: Request,
    subject_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle subject active status"""
    try:
        question_repo = QuestionRepository(db)
        subject = await question_repo.get_subject(subject_id)
        
        if subject:
            await question_repo.update_question(
                subject_id,
                is_active=not subject.is_active
            )
        
        return RedirectResponse(url="/subjects", status_code=302)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling subject: {str(e)}")


@router.post("/{subject_id}/edit_name")
async def edit_subject_name(
    request: Request,
    subject_id: int,
    subject_name: str = Form(...),
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Edit subject name"""
    try:
        question_repo = QuestionRepository(db)
        
        # Check if subject exists
        subject = await question_repo.get_subject(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        # Check if new name already exists for another subject
        existing = await question_repo.get_subject_by_name(subject_name)
        if existing and existing.subject_id != subject_id:
            return templates.TemplateResponse(
                "subjects.html",
                {
                    "request": request,
                    "admin_user": admin_user,
                    "error": f"Subject '{subject_name}' already exists",
                    "subjects_with_counts": []
                }
            )
        
        await question_repo.update_subject(subject_id, subject_name=subject_name)
        return RedirectResponse(url="/subjects", status_code=302)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating subject name: {str(e)}")


@router.post("/{subject_id}/edit_description")
async def edit_subject_description(
    request: Request,
    subject_id: int,
    description: str = Form(...),
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Edit subject description"""
    try:
        question_repo = QuestionRepository(db)
        
        # Check if subject exists
        subject = await question_repo.get_subject(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        await question_repo.update_subject(subject_id, description=description)
        return RedirectResponse(url=f"/subjects/{subject_id}", status_code=302)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating subject description: {str(e)}")


@router.get("/{subject_id}/delete")
async def delete_subject(
    request: Request,
    subject_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete subject"""
    try:
        question_repo = QuestionRepository(db)
        # Soft delete - just mark as inactive
        await question_repo.delete_subject(subject_id)
        
        return RedirectResponse(url="/subjects", status_code=302)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting subject: {str(e)}")

