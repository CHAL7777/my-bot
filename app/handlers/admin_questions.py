"""
Admin Questions Handler - Telegram Quiz Bot
Manage questions: upload CSV, add, edit, delete, view, search
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ContentType, BufferedInputFile
from datetime import datetime
import os
import csv
import io

from app.keyboards.admin import (
    AdminKeyboard, AdminQuestionsKeyboard, AdminSubjectsKeyboard
)
from app.keyboards.menu import MainMenuKeyboard
from app.utils.constants import EMOJIS
from app.utils.csv_importer import CSVImporter
from app.utils.validators import InputValidator
from app.utils.helpers import escape_csv_error, escape_markdown
from app.config import settings
from app.db.base import get_db
from app.repositories.question_repo import QuestionRepository
from app.repositories.admin_log_repo import AdminLogRepository
from app.repositories.user_repo import UserRepository

router = Router()

# FSM States for question management
class QuestionStates(StatesGroup):
    """FSM states for question management operations"""
    # CSV Import states
    waiting_for_csv = State()
    waiting_for_csv_confirm = State()
    
    # Add question states
    waiting_for_subject = State()
    waiting_for_chapter = State()
    waiting_for_difficulty = State()
    waiting_for_question_text = State()
    waiting_for_option_a = State()
    waiting_for_option_b = State()
    waiting_for_option_c = State()
    waiting_for_option_d = State()
    waiting_for_correct_option = State()
    waiting_for_explanation = State()
    waiting_for_confirm = State()
    
    # Edit question states
    waiting_for_edit_question_id = State()
    waiting_for_edit_field = State()
    waiting_for_new_value = State()
    
    # Search states
    waiting_for_search_term = State()


# ============== Utility Functions ==============

async def log_admin_action(admin_id: int, action: str, details: str = None):
    """Log admin action to database"""
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        await log_repo.log_action(admin_id, action, details)


async def get_question_stats_text() -> str:
    """Get question statistics as formatted text"""
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        total = await question_repo.get_question_count()
        simple = await question_repo.get_question_count(difficulty='simple')
        medium = await question_repo.get_question_count(difficulty='medium')
        hard = await question_repo.get_question_count(difficulty='hard')
        
        subjects = await question_repo.get_subjects()
        
        stats_text = (
            f"{EMOJIS['question']} *Question Statistics*\n\n"
            f"📊 *Overview:*\n"
            f"• Total Questions: {total}\n"
            f"• Simple: {simple}\n"
            f"• Medium: {medium}\n"
            f"• Hard: {hard}\n\n"
        )
        
        if subjects:
            stats_text += f"📚 *Subjects ({len(subjects)}):*\n"
            for subject in subjects:
                count = await question_repo.get_question_count(subject_id=subject.subject_id)
                stats_text += f"• {subject.subject_name}: {count} questions\n"
        
        return stats_text


# ============== Main Menu Handlers ==============

@router.callback_query(F.data == "admin_questions")
async def admin_questions_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show question management menu"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['question']} *Question Management*\n\n"
        "Choose an option to manage questions:",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_question_management()
    )
    await callback.answer()


# ============== View Questions ==============

@router.callback_query(F.data == "admin_questions_list")
async def admin_questions_list_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show list of all questions"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        questions = await question_repo.search_questions("", limit=100)
    
    if not questions:
        await callback.message.edit_text(
            f"{EMOJIS['warning']} *No Questions Found*\n\n"
            "There are no questions in the database yet.\n"
            "Upload a CSV file or add questions manually.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['list']} *Questions List*\n\n"
        f"Total questions: {len(questions)}\n\n"
        "Select a question to view or edit:",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_questions_list_keyboard(questions)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_questions_list_page_"))
async def admin_questions_list_page_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle pagination for questions list"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    page = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        questions = await question_repo.search_questions("", limit=100)
    
    await callback.message.edit_text(
        f"{EMOJIS['list']} *Questions List*\n\n"
        f"Total questions: {len(questions)}\n\n"
        "Select a question:",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_questions_list_keyboard(questions, page=page)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_questions_stats")
async def admin_questions_stats_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show question statistics"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    stats_text = await get_question_stats_text()
    
    await callback.message.edit_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== View Single Question ==============

@router.callback_query(F.data.startswith("admin_question_view_"))
async def admin_question_view_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View a specific question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    question_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        question = await question_repo.get_question(question_id)
        
        if not question:
            await callback.message.edit_text(
                "❌ Question not found!",
                parse_mode='Markdown',
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        subject = await question_repo.get_subject(question.subject_id)
        chapter = await question_repo.get_chapter(question.chapter_id)
        
        question_text = (
            f"{EMOJIS['question']} *Question #{question.question_id}*\n\n"
            f"*Subject:* {subject.subject_name}\n"
            f"*Chapter:* {chapter.chapter_name}\n"
            f"*Difficulty:* {question.difficulty.capitalize()}\n\n"
            f"{question.question_text}\n\n"
            f"A) {question.option_a}\n"
            f"B) {question.option_b}\n"
            f"C) {question.option_c}\n"
            f"D) {question.option_d}\n\n"
            f"✅ *Correct Answer:* {question.correct_option}\n"
        )
        
        if question.explanation:
            question_text += f"\n📝 *Explanation:*\n{question.explanation}"
        
        await callback.message.edit_text(
            question_text,
            parse_mode='Markdown',
            reply_markup=AdminQuestionsKeyboard.get_question_action_keyboard(question_id)
        )
    
    await callback.answer()


@router.callback_query(F.data == "admin_questions_template")
async def admin_questions_template_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Download CSV template"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    template_content = """subject,chapter,difficulty,question_text,option_a,option_b,option_c,option_d,correct_option,explanation
Mathematics,Addition,simple,What is 2 + 3?,3,4,5,6,B,2 + 3 = 5
Mathematics,Subtraction,simple,What is 10 - 4?,5,6,7,8,B,10 - 4 = 6
Science,Physics,medium,What is the unit of force?,Joule,Watt,Newton,Pascal,C,Force is measured in Newtons
Science,Chemistry,hard,What is the atomic number of Oxygen?,6,7,8,9,C,Oxygen has 8 protons
English,Grammar,simple,Which is a noun?,Run,Beautiful,Book,Quickly,C,Book is a naming word"""
    
    await callback.message.answer_document(
        document=BufferedInputFile(
            template_content.encode('utf-8'),
            filename="question_template.csv"
        ),
        caption=f"{EMOJIS['template']} *CSV Template*\n\n"
               f"Edit this file and upload it through the 'Upload CSV' option.",
        parse_mode='Markdown'
    )
    
    await callback.answer()


# ============== CSV Import ==============

@router.callback_query(F.data == "admin_questions_import")
async def admin_questions_import_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show CSV import options"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['upload']} *CSV Import*\n\n"
        f"Upload a CSV file with questions.\n\n"
        f"📋 *Required Format:*\n"
        f"`subject,chapter,difficulty,question_text,option_a,option_b,option_c,option_d,correct_option,explanation`\n\n"
        f"💡 *Tips:*\n"
        f"• Download the template first\n"
        f"• Validate before importing large files\n"
        f"• Maximum file size: 10MB\n\n"
        f"Choose an option:",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_csv_import_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_questions_csv_upload")
async def admin_questions_csv_upload_callback(callback: types.CallbackQuery, 
                                               state: FSMContext, 
                                               is_admin: bool = False):
    """Start CSV upload process"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await state.set_state(QuestionStates.waiting_for_csv)
    
    await callback.message.edit_text(
        f"{EMOJIS['upload']} *Upload CSV File*\n\n"
        f"Please upload your CSV file now.\n\n"
        f"⚠️ *Important:*\n"
        f"• Only .csv files accepted\n"
        f"• UTF-8 encoding required\n"
        f"• Maximum 10MB file size",
        parse_mode='Markdown'
    )
    await callback.answer()


@router.message(QuestionStates.waiting_for_csv, F.content_type == ContentType.DOCUMENT)
async def handle_csv_upload(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Handle CSV file upload"""
    if not is_admin:
        return
    
    document = message.document
    
    if not document.file_name.endswith('.csv'):
        await message.answer(
            f"❌ Please upload a CSV file (.csv extension)",
            reply_markup=AdminQuestionsKeyboard.get_csv_import_keyboard()
        )
        await state.clear()
        return
    
    # Download file
    file = await message.bot.get_file(document.file_id)
    
    # Create uploads directory
    uploads_dir = os.path.join(settings.DATA_DIR, "questions", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(uploads_dir, f"{timestamp}_{document.file_name}")
    
    await message.bot.download_file(file.file_path, file_path)
    
    # Validate CSV
    importer = CSVImporter()
    is_valid, errors, valid_rows = await importer.validate_file(file_path)
    
    if not is_valid:
        error_msg = f"❌ *Validation Failed*\n\n"
        for error in errors[:5]:
            # Escape Markdown special characters in error messages
            error_msg += f"• {escape_csv_error(error)}\n"
        if len(errors) > 5:
            error_msg += f"... and {len(errors) - 5} more errors"
        
        await message.answer(
            error_msg,
            parse_mode='Markdown',
            reply_markup=AdminQuestionsKeyboard.get_csv_import_keyboard()
        )
        await state.clear()
        return
    
    # Store file path in state
    await state.update_data(csv_file_path=file_path)
    
    # Show preview and ask for confirmation
    preview_msg = (
        f"✅ *CSV Validated Successfully*\n\n"
        f"📊 *Preview:*\n"
        f"• Valid rows: {valid_rows}\n"
        f"• File: {escape_markdown(document.file_name)}\n\n"
        f"Do you want to proceed with the import?"
    )
    
    await message.answer(
        preview_msg,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_confirmation_keyboard("csv_import", 0)
    )


@router.callback_query(F.data.startswith("confirm_csv_import_"), 
                       StateFilter(QuestionStates.waiting_for_csv))
async def confirm_csv_import_callback(callback: types.CallbackQuery, state: FSMContext, 
                                       is_admin: bool = False):
    """Confirm CSV import"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    data = await state.get_data()
    file_path = data.get('csv_file_path')
    
    if not file_path:
        await callback.message.edit_text(
            f"❌ *Session Expired*\n\n"
            f"The CSV file reference was lost. This may happen if:\n"
            f"• The bot was restarted\n"
            f"• The state expired\n"
            f"• You started a different operation\n\n"
            f"Please upload the CSV file again.",
            parse_mode='Markdown',
            reply_markup=AdminQuestionsKeyboard.get_csv_import_keyboard()
        )
        await state.clear()
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['loading']} *Importing Questions...*\n\n"
        f"Please wait while questions are being imported.",
        parse_mode='Markdown'
    )
    
    # Import CSV
    importer = CSVImporter()
    stats = await importer.import_from_file(file_path, callback.from_user.id)
    
    # Prepare result message
    result_message = (
        f"📊 *Import Results*\n\n"
        f"📈 *Statistics:*\n"
        f"• Total rows: {stats['total_rows']}\n"
        f"• Valid rows: {stats['valid_rows']}\n"
        f"• Imported: {stats['imported']}\n"
        f"• Skipped: {stats['skipped']}\n"
        f"• Duration: {stats['duration']:.2f}s\n\n"
    )
    
    if stats['imported'] > 0:
        result_message += f"✅ Successfully imported {stats['imported']} questions!"
    else:
        result_message += f"⚠️ No questions were imported."
    
    if stats['errors']:
        result_message += f"\n\n❌ *Errors ({len(stats['errors'])}):*\n"
        for error in stats['errors'][:3]:
            # Escape Markdown special characters in error messages
            result_message += f"• {escape_csv_error(error)}\n"
        if len(stats['errors']) > 3:
            result_message += f"... and {len(stats['errors']) - 3} more"
    
    # Log action
    await log_admin_action(
        callback.from_user.id,
        "CSV Import",
        f"Imported {stats['imported']} questions, {stats['skipped']} skipped"
    )
    
    await callback.message.edit_text(
        result_message,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_csv_import_0",
                       StateFilter(QuestionStates.waiting_for_csv))
async def cancel_csv_import_callback(callback: types.CallbackQuery, state: FSMContext,
                                      is_admin: bool = False):
    """Cancel CSV import"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    data = await state.get_data()
    file_path = data.get('csv_file_path')
    
    # Delete uploaded file
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    await callback.message.edit_text(
        f"{EMOJIS['back']} *Import Cancelled*\n\n"
        f"The CSV file was not imported.",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_csv_import_keyboard()
    )
    
    await state.clear()
    await callback.answer()


# ============== Search Questions ==============

@router.callback_query(F.data == "admin_questions_search")
async def admin_questions_search_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Start question search"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['search']} *Search Questions*\n\n"
        f"Enter a search term to find questions.\n"
        f"Searches in question text and options.",
        parse_mode='Markdown'
    )
    
    await callback.message.answer(
        "Type your search term:"
    )
    
    await callback.answer()


@router.message(F.text, StateFilter(QuestionStates.waiting_for_search_term))
async def handle_question_search(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Handle question search input"""
    if not is_admin:
        return
    
    search_term = message.text.strip()
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        questions = await question_repo.search_questions(search_term, limit=20)
    
    if not questions:
        await message.answer(
            f"🔍 *No Results*\n\n"
            f"No questions found matching '{search_term}'.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    results_msg = (
        f"🔍 *Search Results*\n\n"
        f"Found {len(questions)} questions matching '{search_term}':\n\n"
    )
    
    await message.answer(
        results_msg,
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_questions_list_keyboard(questions)
    )
    
    await state.clear()


# ============== Delete Question ==============

@router.callback_query(F.data.startswith("admin_question_delete_confirm_"))
async def admin_question_delete_confirm_callback(callback: types.CallbackQuery, 
                                                   is_admin: bool = False):
    """Show delete confirmation for question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    question_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        question = await question_repo.get_question(question_id)
        
        if not question:
            await callback.message.edit_text(
                "❌ Question not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        preview = question.question_text[:50] + "..." if len(question.question_text) > 50 else question.question_text
    
    await callback.message.edit_text(
        f"{EMOJIS['warning']} *Delete Question?*\n\n"
        f"Are you sure you want to delete this question?\n\n"
        f"*Question:* {preview}\n"
        f"*ID:* #{question_id}\n\n"
        f"⚠️ *This action cannot be undone!*",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_delete_confirmation_keyboard(question_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_question_"))
async def confirm_delete_question_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Confirm question deletion"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    question_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        question = await question_repo.get_question(question_id)
        
        if question:
            deleted = await question_repo.delete_question(question_id)
            
            if deleted:
                # Log action
                await log_admin_action(
                    callback.from_user.id,
                    "Delete Question",
                    f"Deleted question #{question_id}"
                )
                
                await callback.message.edit_text(
                    f"✅ *Question Deleted*\n\n"
                    f"Question #{question_id} has been deleted successfully.",
                    parse_mode='Markdown',
                    reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
                )
            else:
                await callback.message.edit_text(
                    f"❌ *Delete Failed*\n\n"
                    f"Could not delete question #{question_id}.",
                    parse_mode='Markdown',
                    reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
                )
        else:
            await callback.message.edit_text(
                "❌ Question not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_question")
async def cancel_delete_question_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Cancel question deletion"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['back']} *Delete Cancelled*\n\n"
        f"The question was not deleted.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== Add Question (FSM) ==============

@router.callback_query(F.data == "admin_questions_add")
async def admin_questions_add_callback(callback: types.CallbackQuery, state: FSMContext,
                                        is_admin: bool = False):
    """Start adding a new question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Get subjects
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subjects = await question_repo.get_subjects()
    
    if not subjects:
        await callback.message.edit_text(
            f"{EMOJIS['warning']} *No Subjects Available*\n\n"
            f"Please add a subject first before creating questions.",
            parse_mode='Markdown',
            reply_markup=AdminSubjectsKeyboard.get_subject_management()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['add']} *Add New Question*\n\n"
        f"Step 1: Select a subject",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_subject_selection_keyboard(subjects)
    )
    
    await state.set_state(QuestionStates.waiting_for_subject)
    await callback.answer()


@router.callback_query(F.data.startswith("select_subject_"), 
                       StateFilter(QuestionStates.waiting_for_subject))
async def select_subject_callback(callback: types.CallbackQuery, state: FSMContext,
                                   is_admin: bool = False):
    """Handle subject selection for new question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subject_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subject = await question_repo.get_subject(subject_id)
        chapters = await question_repo.get_chapters(subject_id)
    
    await state.update_data(
        subject_id=subject_id,
        subject_name=subject.subject_name
    )
    
    if not chapters:
        await callback.message.edit_text(
            f"{EMOJIS['add']} *Add New Question*\n\n"
            f"Subject: *{subject.subject_name}*\n\n"
            f"Step 2: Select difficulty (no chapters available)",
            parse_mode='Markdown',
            reply_markup=AdminQuestionsKeyboard.get_difficulty_keyboard()
        )
        await state.set_state(QuestionStates.waiting_for_difficulty)
    else:
        await callback.message.edit_text(
            f"{EMOJIS['add']} *Add New Question*\n\n"
            f"Subject: *{subject.subject_name}*\n\n"
            f"Step 2: Select a chapter",
            parse_mode='Markdown',
            reply_markup=AdminQuestionsKeyboard.get_chapter_selection_keyboard(chapters)
        )
        await state.set_state(QuestionStates.waiting_for_chapter)
    
    await callback.answer()


@router.callback_query(F.data.startswith("select_chapter_"), 
                       StateFilter(QuestionStates.waiting_for_chapter))
async def select_chapter_callback(callback: types.CallbackQuery, state: FSMContext,
                                   is_admin: bool = False):
    """Handle chapter selection for new question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    chapter_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        chapter = await question_repo.get_chapter(chapter_id)
    
    data = await state.get_data()
    data['chapter_id'] = chapter_id
    data['chapter_name'] = chapter.chapter_name
    await state.update_data(data)
    
    await callback.message.edit_text(
        f"{EMOJIS['add']} *Add New Question*\n\n"
        f"Subject: *{data['subject_name']}*\n"
        f"Chapter: *{chapter.chapter_name}*\n\n"
        f"Step 3: Select difficulty",
        parse_mode='Markdown',
        reply_markup=AdminQuestionsKeyboard.get_difficulty_keyboard()
    )
    
    await state.set_state(QuestionStates.waiting_for_difficulty)
    await callback.answer()


@router.callback_query(F.data.startswith("difficulty_"), 
                       StateFilter(QuestionStates.waiting_for_difficulty))
async def select_difficulty_callback(callback: types.CallbackQuery, state: FSMContext,
                                      is_admin: bool = False):
    """Handle difficulty selection for new question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    difficulty = callback.data.split("_")[-1]
    data = await state.get_data()
    data['difficulty'] = difficulty
    await state.update_data(data)
    
    await callback.message.edit_text(
        f"{EMOJIS['add']} *Add New Question*\n\n"
        f"Subject: *{data['subject_name']}*\n"
        f"Difficulty: *{difficulty.capitalize()}*\n\n"
        f"Step 4: Enter the question text:",
        parse_mode='Markdown'
    )
    
    await state.set_state(QuestionStates.waiting_for_question_text)
    await callback.answer()


@router.message(StateFilter(QuestionStates.waiting_for_question_text))
async def handle_question_text(message: types.Message, state: FSMContext,
                                is_admin: bool = False):
    """Handle question text input"""
    if not is_admin:
        return
    
    if len(message.text) < 10:
        await message.answer(
            "❌ Question text is too short (minimum 10 characters). Please try again:"
        )
        return
    
    data = await state.get_data()
    data['question_text'] = message.text
    await state.update_data(data)
    
    await message.answer(
        f"{EMOJIS['add']} *Add New Question*\n\n"
        f"Question: *{message.text[:50]}...*\n\n"
        f"Step 5: Enter Option A:",
        parse_mode='Markdown'
    )
    
    await state.set_state(QuestionStates.waiting_for_option_a)


@router.message(StateFilter(QuestionStates.waiting_for_option_a))
async def handle_option_a(message: types.Message, state: FSMContext,
                          is_admin: bool = False):
    """Handle option A input"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['option_a'] = message.text
    await state.update_data(data)
    
    await message.answer(
        f"Step 6: Enter Option B:"
    )
    
    await state.set_state(QuestionStates.waiting_for_option_b)


@router.message(StateFilter(QuestionStates.waiting_for_option_b))
async def handle_option_b(message: types.Message, state: FSMContext,
                          is_admin: bool = False):
    """Handle option B input"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['option_b'] = message.text
    await state.update_data(data)
    
    await message.answer(
        f"Step 7: Enter Option C:"
    )
    
    await state.set_state(QuestionStates.waiting_for_option_c)


@router.message(StateFilter(QuestionStates.waiting_for_option_c))
async def handle_option_c(message: types.Message, state: FSMContext,
                          is_admin: bool = False):
    """Handle option C input"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['option_c'] = message.text
    await state.update_data(data)
    
    await message.answer(
        f"Step 8: Enter Option D:"
    )
    
    await state.set_state(QuestionStates.waiting_for_option_d)


@router.message(StateFilter(QuestionStates.waiting_for_option_d))
async def handle_option_d(message: types.Message, state: FSMContext,
                          is_admin: bool = False):
    """Handle option D input"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['option_d'] = message.text
    await state.update_data(data)
    
    keyboard = [
        [
            InlineKeyboardButton(text="A", callback_data="correct_A"),
            InlineKeyboardButton(text="B", callback_data="correct_B"),
            InlineKeyboardButton(text="C", callback_data="correct_C"),
            InlineKeyboardButton(text="D", callback_data="correct_D"),
        ]
    ]
    
    await message.answer(
        f"Step 9: Select the correct answer:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(QuestionStates.waiting_for_correct_option)


@router.callback_query(F.data.startswith("correct_"), 
                       StateFilter(QuestionStates.waiting_for_correct_option))
async def select_correct_option_callback(callback: types.CallbackQuery, state: FSMContext,
                                          is_admin: bool = False):
    """Handle correct option selection"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    correct_option = callback.data.split("_")[-1]
    data = await state.get_data()
    data['correct_option'] = correct_option
    await state.update_data(data)
    
    await callback.message.edit_text(
        f"{EMOJIS['add']} *Add New Question*\n\n"
        f"Step 10 (Optional): Enter an explanation:\n\n"
        f"Press /skip to skip this step.",
        parse_mode='Markdown'
    )
    
    await state.set_state(QuestionStates.waiting_for_explanation)
    await callback.answer()


@router.message(StateFilter(QuestionStates.waiting_for_explanation), F.text == "/skip")
async def skip_explanation(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Skip explanation step"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['explanation'] = ""
    await state.update_data(data)
    
    await show_question_confirmation(message, state)


@router.message(StateFilter(QuestionStates.waiting_for_explanation))
async def handle_explanation(message: types.Message, state: FSMContext,
                              is_admin: bool = False):
    """Handle explanation input"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['explanation'] = message.text
    await state.update_data(data)
    
    await show_question_confirmation(message, state)


async def show_question_confirmation(message: types.Message, state: FSMContext):
    """Show question preview and ask for confirmation"""
    data = await state.get_data()
    
    preview = (
        f"📝 *Question Preview*\n\n"
        f"*Subject:* {data['subject_name']}\n"
        f"*Difficulty:* {data['difficulty'].capitalize()}\n\n"
        f"*Question:* {data['question_text']}\n\n"
        f"A) {data['option_a']}\n"
        f"B) {data['option_b']}\n"
        f"C) {data['option_c']}\n"
        f"D) {data['option_d']}\n\n"
        f"✅ *Correct Answer:* {data['correct_option']}\n"
    )
    
    if data.get('explanation'):
        preview += f"\n📝 *Explanation:*\n{data['explanation']}"
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Confirm & Save", callback_data="confirm_add_question"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_add_question"),
        ]
    ]
    
    await message.answer(
        preview,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == "confirm_add_question")
async def confirm_add_question_callback(callback: types.CallbackQuery, state: FSMContext,
                                         is_admin: bool = False):
    """Confirm and save the new question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    data = await state.get_data()
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        chapter_id = data.get('chapter_id')
        if not chapter_id:
            # Create a default chapter
            chapters = await question_repo.get_chapters(data['subject_id'])
            if chapters:
                chapter_id = chapters[0].chapter_id
            else:
                chapter = await question_repo.create_chapter(
                    subject_id=data['subject_id'],
                    chapter_name="General",
                    chapter_order=1
                )
                chapter_id = chapter.chapter_id
        
        question = await question_repo.create_question(
            subject_id=data['subject_id'],
            chapter_id=chapter_id,
            difficulty=data['difficulty'],
            question_text=data['question_text'],
            option_a=data['option_a'],
            option_b=data['option_b'],
            option_c=data['option_c'],
            option_d=data['option_d'],
            correct_option=data['correct_option'],
            explanation=data.get('explanation', '')
        )
        
        # Log action
        await log_admin_action(
            callback.from_user.id,
            "Add Question",
            f"Added question #{question.question_id} in {data['subject_name']}"
        )
    
    await callback.message.edit_text(
        f"✅ *Question Added Successfully!*\n\n"
        f"Question ID: *#{question.question_id}*\n"
        f"Subject: {data['subject_name']}\n"
        f"Difficulty: {data['difficulty'].capitalize()}",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_add_question")
async def cancel_add_question_callback(callback: types.CallbackQuery, state: FSMContext,
                                        is_admin: bool = False):
    """Cancel adding question"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"❌ *Question Not Saved*\n\n"
        f"The question was not added.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()
    await callback.answer()


# Import inline keyboard button
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

