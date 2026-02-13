from fastapi import APIRouter, Request, Depends, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
from typing import Optional

from app.db.base import get_db
from app.repositories.question_repo import QuestionRepository
from admin_panel.utils.auth import get_current_admin_user
from admin_panel.utils.csv_handler import validate_and_process_csv

router = APIRouter()
templates = Jinja2Templates(directory="admin_panel/templates")

@router.get("/", response_class=HTMLResponse)
async def questions_list(
    request: Request,
    page: int = 1,
    subject_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show questions list with filtering"""
    try:
        question_repo = QuestionRepository(db)

        # Get subjects and chapters for filters
        subjects = await question_repo.get_subjects()
        chapters = []
        if subject_id:
            chapters = await question_repo.get_chapters(subject_id)

        # Get questions count
        total_questions = await question_repo.get_question_count(
            subject_id=subject_id,
            chapter_id=chapter_id,
            difficulty=difficulty
        )

        # For now, get all questions (pagination can be added later)
        # This is simplified - in production you'd want proper pagination
        questions = []  # Placeholder - would need a method to get questions with filters

        return templates.TemplateResponse(
            "questions.html",
            {
                "request": request,
                "admin_user": admin_user,
                "questions": questions,
                "subjects": subjects,
                "chapters": chapters,
                "subject_id": subject_id,
                "chapter_id": chapter_id,
                "difficulty": difficulty,
                "total_questions": total_questions
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading questions: {str(e)}")

@router.get("/add", response_class=HTMLResponse)
async def add_question_form(
    request: Request,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Show add question form"""
    try:
        question_repo = QuestionRepository(db)
        subjects = await question_repo.get_subjects()

        return templates.TemplateResponse(
            "add_question.html",
            {
                "request": request,
                "admin_user": admin_user,
                "subjects": subjects
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading form: {str(e)}")

@router.post("/add")
async def add_question(
    request: Request,
    subject_id: int = Form(...),
    chapter_id: int = Form(...),
    difficulty: str = Form(...),
    question_text: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct_option: str = Form(...),
    explanation: str = Form(""),
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Add new question"""
    try:
        question_repo = QuestionRepository(db)

        question_data = {
            'subject_id': subject_id,
            'chapter_id': chapter_id,
            'difficulty': difficulty,
            'question_text': question_text,
            'option_a': option_a,
            'option_b': option_b,
            'option_c': option_c,
            'option_d': option_d,
            'correct_option': correct_option,
            'explanation': explanation
        }

        question = await question_repo.create_question(question_data)
        return RedirectResponse(url="/questions", status_code=302)

    except Exception as e:
        # Return to form with error
        question_repo = QuestionRepository(db)
        subjects = await question_repo.get_subjects()

        return templates.TemplateResponse(
            "add_question.html",
            {
                "request": request,
                "admin_user": admin_user,
                "subjects": subjects,
                "error": f"Error adding question: {str(e)}",
                "form_data": {
                    'subject_id': subject_id,
                    'chapter_id': chapter_id,
                    'difficulty': difficulty,
                    'question_text': question_text,
                    'option_a': option_a,
                    'option_b': option_b,
                    'option_c': option_c,
                    'option_d': option_d,
                    'correct_option': correct_option,
                    'explanation': explanation
                }
            }
        )

@router.post("/upload-csv")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload and process CSV file with questions"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file")

        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')

        # Process CSV
        question_repo = QuestionRepository(db)
        results = await validate_and_process_csv(csv_content, question_repo)

        return templates.TemplateResponse(
            "csv_upload_result.html",
            {
                "request": request,
                "admin_user": admin_user,
                "results": results
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@router.get("/chapters/{subject_id}")
async def get_chapters_for_subject(
    subject_id: int,
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chapters for a subject (AJAX endpoint)"""
    try:
        question_repo = QuestionRepository(db)
        chapters = await question_repo.get_chapters(subject_id)

        return {"chapters": [{"id": c.chapter_id, "name": c.chapter_name} for c in chapters]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading chapters: {str(e)}")
