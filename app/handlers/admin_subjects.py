"""
Admin Subjects Handler - Telegram Quiz Bot
Manage subjects: add, edit, delete, view
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.admin import (
    AdminKeyboard, AdminSubjectsKeyboard
)
from app.utils.constants import EMOJIS
from app.db.base import get_db
from app.repositories.question_repo import QuestionRepository
from app.repositories.admin_log_repo import AdminLogRepository

router = Router()

# FSM States for subject management
class SubjectStates(StatesGroup):
    """FSM states for subject management operations"""
    waiting_for_subject_name = State()
    waiting_for_subject_description = State()
    waiting_for_confirm = State()
    waiting_for_edit_name = State()
    waiting_for_edit_description = State()
    waiting_for_chapter_name = State()
    waiting_for_chapter_description = State()


# ============== Utility Functions ==============

async def log_admin_action(admin_id: int, action: str, details: str = None):
    """Log admin action to database"""
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        await log_repo.log_action(admin_id, action, details)


# ============== Main Menu Handlers ==============

@router.callback_query(F.data == "admin_subjects")
async def admin_subjects_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show subject management menu"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['subject']} *Subject Management*\n\n"
        "Choose an option to manage subjects:",
        parse_mode='Markdown',
        reply_markup=AdminSubjectsKeyboard.get_subject_management()
    )
    await callback.answer()


# ============== View Subjects ==============

@router.callback_query(F.data == "admin_subjects_list")
async def admin_subjects_list_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show list of all subjects with question counts"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subjects = []
    subject_counts = {}
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        # Use new method that prevents DetachedInstanceError
        subjects, subject_counts = await question_repo.get_subjects_with_counts()
    
    if not subjects:
        await callback.message.edit_text(
            f"{EMOJIS['warning']} *No Subjects Found*\n\n"
            "There are no subjects in the database yet.\n"
            "Add a subject to get started.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    # Build text with counts - using pre-computed counts to avoid DetachedInstanceError
    subjects_text = (
        f"{EMOJIS['list']} *Subjects List*\n\n"
        f"Total subjects: {len(subjects)}\n\n"
    )
    
    for subject in subjects:
        q_count = subject_counts.get(subject.subject_id, 0)
        subjects_text += f"📚 *{subject.subject_name}*\n"
        subjects_text += f"   • Questions: {q_count}\n\n"
    
    # Use the new keyboard method that accepts pre-computed counts
    # This prevents DetachedInstanceError by NOT accessing subject.questions
    await callback.message.edit_text(
        subjects_text,
        parse_mode='Markdown',
        reply_markup=AdminSubjectsKeyboard.get_subjects_list_keyboard(
            subjects, 
            subject_counts
        )
    )
    await callback.answer()


@router.callback_query(F.data == "admin_subjects_stats")
async def admin_subjects_stats_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show subject statistics"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subjects = await question_repo.get_subjects()
        
        total_questions = 0
        total_chapters = 0
        
        stats_text = (
            f"{EMOJIS['stats']} *Subject Statistics*\n\n"
            f"📊 *Overview:*\n"
            f"• Total Subjects: {len(subjects)}\n\n"
        )
        
        for subject in subjects:
            q_count = await question_repo.get_question_count(subject_id=subject.subject_id)
            chapters = await question_repo.get_chapters(subject.subject_id)
            
            total_questions += q_count
            total_chapters += len(chapters)
            
            stats_text += (
                f"📚 *{subject.subject_name}*\n"
                f"   • Questions: {q_count}\n"
                f"   • Chapters: {len(chapters)}\n"
                f"   • Status: {'🟢 Active' if subject.is_active else '🔴 Inactive'}\n\n"
            )
        
        stats_text += f"*Totals:* {total_questions} questions, {total_chapters} chapters"
    
    await callback.message.edit_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== View Single Subject ==============

@router.callback_query(F.data.startswith("admin_subject_view_"))
async def admin_subject_view_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View a specific subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subject_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        subject = await question_repo.get_subject(subject_id)
        if not subject:
            await callback.message.edit_text(
                "❌ Subject not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        chapters = await question_repo.get_chapters(subject_id)
        q_count = await question_repo.get_question_count(subject_id=subject_id)
        
        subject_text = (
            f"{EMOJIS['subject']} *Subject: {subject.subject_name}*\n\n"
        )
        
        if subject.description:
            subject_text += f"📝 *Description:*\n{subject.description}\n\n"
        
        subject_text += (
            f"📊 *Statistics:*\n"
            f"• Questions: {q_count}\n"
            f"• Chapters: {len(chapters)}\n"
            f"• Status: {'🟢 Active' if subject.is_active else '🔴 Inactive'}\n"
            f"• Created: {subject.created_at.strftime('%d %b %Y') if subject.created_at else 'N/A'}\n\n"
        )
        
        if chapters:
            subject_text += f"📑 *Chapters:*\n"
            for chapter in chapters:
                c_q_count = await question_repo.get_question_count(chapter_id=chapter.chapter_id)
                subject_text += f"• {chapter.chapter_name} ({c_q_count} questions)\n"
        else:
            subject_text += f"📑 *No chapters yet.*"
        
        await callback.message.edit_text(
            subject_text,
            parse_mode='Markdown',
            reply_markup=AdminSubjectsKeyboard.get_subject_action_keyboard(subject_id)
        )
    
    await callback.answer()


# ============== Add Subject ==============

@router.callback_query(F.data == "admin_subjects_add")
async def admin_subjects_add_callback(callback: types.CallbackQuery, state: FSMContext,
                                       is_admin: bool = False):
    """Start adding a new subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['add']} *Add New Subject*\n\n"
        f"Step 1: Enter the subject name:",
        parse_mode='Markdown'
    )
    
    await state.set_state(SubjectStates.waiting_for_subject_name)
    await callback.answer()


@router.message(StateFilter(SubjectStates.waiting_for_subject_name))
async def handle_subject_name(message: types.Message, state: FSMContext,
                               is_admin: bool = False):
    """Handle subject name input"""
    if not is_admin:
        return
    
    subject_name = message.text.strip()
    
    if len(subject_name) < 2:
        await message.answer(
            "❌ Subject name is too short (minimum 2 characters). Please try again:"
        )
        return
    
    # Check if subject already exists
    async for session in get_db():
        question_repo = QuestionRepository(session)
        existing = await question_repo.get_subject_by_name(subject_name)
    
    if existing:
        await message.answer(
            f"❌ Subject '{subject_name}' already exists!",
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    await state.update_data(subject_name=subject_name)
    
    await message.answer(
        f"{EMOJIS['add']} *Add New Subject*\n\n"
        f"Subject: *{subject_name}*\n\n"
        f"Step 2 (Optional): Enter a description:\n\n"
        f"Press /skip to skip this step.",
        parse_mode='Markdown'
    )
    
    await state.set_state(SubjectStates.waiting_for_subject_description)


@router.message(StateFilter(SubjectStates.waiting_for_subject_description), F.text == "/skip")
async def skip_subject_description(message: types.Message, state: FSMContext,
                                    is_admin: bool = False):
    """Skip description step"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['description'] = ""
    await state.update_data(data)
    
    await show_subject_confirmation(message, state)


@router.message(StateFilter(SubjectStates.waiting_for_subject_description))
async def handle_subject_description(message: types.Message, state: FSMContext,
                                      is_admin: bool = False):
    """Handle description input"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['description'] = message.text
    await state.update_data(data)
    
    await show_subject_confirmation(message, state)


async def show_subject_confirmation(message: types.Message, state: FSMContext):
    """Show subject preview and ask for confirmation"""
    data = await state.get_data()
    
    preview = (
        f"📝 *Subject Preview*\n\n"
        f"*Name:* {data['subject_name']}\n"
    )
    
    if data.get('description'):
        preview += f"\n📝 *Description:*\n{data['description']}"
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Confirm & Save", callback_data="confirm_add_subject"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_add_subject"),
        ]
    ]
    
    await message.answer(
        preview,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == "confirm_add_subject")
async def confirm_add_subject_callback(callback: types.CallbackQuery, state: FSMContext,
                                        is_admin: bool = False):
    """Confirm and save the new subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    data = await state.get_data()
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        subject = await question_repo.create_subject(
            subject_name=data['subject_name'],
            description=data.get('description', '')
        )
        
        # Log action
        await log_admin_action(
            callback.from_user.id,
            "Add Subject",
            f"Added subject: {data['subject_name']}"
        )
    
    await callback.message.edit_text(
        f"✅ *Subject Added Successfully!*\n\n"
        f"Subject: *{data['subject_name']}*\n"
        f"ID: #{subject.subject_id}",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_add_subject")
async def cancel_add_subject_callback(callback: types.CallbackQuery, state: FSMContext,
                                       is_admin: bool = False):
    """Cancel adding subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"❌ *Subject Not Saved*\n\n"
        f"The subject was not added.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()
    await callback.answer()


# ============== Edit Subject ==============

@router.callback_query(F.data == "admin_subjects_edit")
async def admin_subjects_edit_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show subjects to edit"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subjects = await question_repo.get_subjects()
    
    if not subjects:
        await callback.message.edit_text(
            f"{EMOJIS['warning']} *No Subjects Found*\n\n"
            "Add a subject first to edit it.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    edit_text = (
        f"{EMOJIS['edit']} *Edit Subject*\n\n"
        f"Select a subject to edit:"
    )
    
    keyboard = []
    for subject in subjects:
        keyboard.append([
            InlineKeyboardButton(
                text=f"Edit {subject.subject_name}",
                callback_data=f"edit_subject_{subject.subject_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Back", callback_data="admin_subjects")
    ])
    
    await callback.message.edit_text(
        edit_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_subject_"))
async def edit_subject_callback(callback: types.CallbackQuery, state: FSMContext,
                                 is_admin: bool = False):
    """Show edit options for a subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subject_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subject = await question_repo.get_subject(subject_id)
        
        if not subject:
            await callback.message.edit_text(
                "❌ Subject not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        await state.update_data(subject_id=subject_id, subject_name=subject.subject_name)
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Edit Name",
                callback_data="edit_subject_name"
            ),
            InlineKeyboardButton(
                text="📝 Edit Description",
                callback_data="edit_subject_description"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Back",
                callback_data="admin_subjects_edit"
            )
        ]
    ]
    
    await callback.message.edit_text(
        f"{EMOJIS['edit']} *Edit Subject: {subject.subject_name}*\n\n"
        f"Choose what to edit:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "edit_subject_name")
async def edit_subject_name_callback(callback: types.CallbackQuery, state: FSMContext,
                                      is_admin: bool = False):
    """Start editing subject name"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"{EMOJIS['edit']} *Edit Subject Name*\n\n"
        f"Current name: *{data['subject_name']}*\n\n"
        f"Enter the new name:",
        parse_mode='Markdown'
    )
    
    await state.set_state(SubjectStates.waiting_for_edit_name)
    await callback.answer()


@router.message(StateFilter(SubjectStates.waiting_for_edit_name))
async def handle_edit_subject_name(message: types.Message, state: FSMContext,
                                    is_admin: bool = False):
    """Handle edited subject name"""
    if not is_admin:
        return
    
    new_name = message.text.strip()
    
    if len(new_name) < 2:
        await message.answer(
            "❌ Name is too short (minimum 2 characters). Please try again:"
        )
        return
    
    data = await state.get_data()
    subject_id = data['subject_id']
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        # Check if new name already exists
        existing = await question_repo.get_subject_by_name(new_name)
        if existing and existing.subject_id != subject_id:
            await message.answer(
                f"❌ Subject '{new_name}' already exists!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await state.clear()
            return
        
        # Update subject
        from sqlalchemy import update
        from app.db.models import Subject
        
        await session.execute(
            update(Subject).where(Subject.subject_id == subject_id).values(subject_name=new_name)
        )
        await session.commit()
        
        # Log action
        await log_admin_action(
            message.from_user.id,
            "Edit Subject",
            f"Changed subject name from '{data['subject_name']}' to '{new_name}'"
        )
    
    await message.answer(
        f"✅ *Subject Updated*\n\n"
        f"New name: *{new_name}*",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()


@router.callback_query(F.data == "edit_subject_description")
async def edit_subject_description_callback(callback: types.CallbackQuery, state: FSMContext,
                                             is_admin: bool = False):
    """Start editing subject description"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['edit']} *Edit Description*\n\n"
        f"Enter the new description:\n\n"
        f"Press /clear to remove the description.",
        parse_mode='Markdown'
    )
    
    await state.set_state(SubjectStates.waiting_for_edit_description)
    await callback.answer()


@router.message(StateFilter(SubjectStates.waiting_for_edit_description), F.text == "/clear")
async def clear_subject_description(message: types.Message, state: FSMContext,
                                     is_admin: bool = False):
    """Clear subject description"""
    if not is_admin:
        return
    
    data = await state.get_data()
    subject_id = data['subject_id']
    
    async for session in get_db():
        from sqlalchemy import update
        from app.db.models import Subject
        
        await session.execute(
            update(Subject).where(Subject.subject_id == subject_id).values(description=None)
        )
        await session.commit()
        
        await log_admin_action(
            message.from_user.id,
            "Edit Subject",
            f"Cleared description for subject {data['subject_name']}"
        )
    
    await message.answer(
        f"✅ *Description Cleared*\n\n"
        f"The description has been removed.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()


@router.message(StateFilter(SubjectStates.waiting_for_edit_description))
async def handle_edit_subject_description(message: types.Message, state: FSMContext,
                                            is_admin: bool = False):
    """Handle edited description"""
    if not is_admin:
        return
    
    new_description = message.text
    data = await state.get_data()
    subject_id = data['subject_id']
    
    async for session in get_db():
        from sqlalchemy import update
        from app.db.models import Subject
        
        await session.execute(
            update(Subject).where(Subject.subject_id == subject_id).values(description=new_description)
        )
        await session.commit()
        
        await log_admin_action(
            message.from_user.id,
            "Edit Subject",
            f"Updated description for subject {data['subject_name']}"
        )
    
    await message.answer(
        f"✅ *Description Updated*",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()


# ============== Delete Subject ==============

@router.callback_query(F.data == "admin_subjects_delete")
async def admin_subjects_delete_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show subjects to delete"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subjects = await question_repo.get_subjects()
    
    if not subjects:
        await callback.message.edit_text(
            f"{EMOJIS['warning']} *No Subjects Found*\n\n"
            "Add a subject first.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    delete_text = (
        f"{EMOJIS['warning']} *Delete Subject*\n\n"
        f"⚠️ *Warning:* Deleting a subject will also delete all its chapters and questions!\n\n"
        f"Select a subject to delete:"
    )
    
    keyboard = []
    for subject in subjects:
        q_count = await question_repo.get_question_count(subject_id=subject.subject_id)
        keyboard.append([
            InlineKeyboardButton(
                text=f"Delete {subject.subject_name} ({q_count} questions)",
                callback_data=f"delete_subject_confirm_{subject.subject_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Back", callback_data="admin_subjects")
    ])
    
    await callback.message.edit_text(
        delete_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_subject_confirm_"))
async def delete_subject_confirm_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show delete confirmation for subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subject_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subject = await question_repo.get_subject(subject_id)
        
        if not subject:
            await callback.message.edit_text(
                "❌ Subject not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        q_count = await question_repo.get_question_count(subject_id=subject_id)
        chapters = await question_repo.get_chapters(subject_id)
    
    await callback.message.edit_text(
        f"{EMOJIS['danger']} *Delete Subject: {subject.subject_name}*\n\n"
        f"⚠️ *This will delete:*\n"
        f"• Subject: {subject.subject_name}\n"
        f"• Chapters: {len(chapters)}\n"
        f"• Questions: {q_count}\n\n"
        f"⚠️ *This action cannot be undone!*",
        parse_mode='Markdown',
        reply_markup=AdminSubjectsKeyboard.get_delete_subject_confirmation_keyboard(subject_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_subject_"))
async def confirm_delete_subject_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Confirm subject deletion"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subject_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subject = await question_repo.get_subject(subject_id)
        
        if subject:
            # Delete is handled by CASCADE when subject is deleted
            # We just need to delete the subject itself
            from sqlalchemy import delete
            from app.db.models import Subject
            
            await session.execute(delete(Subject).where(Subject.subject_id == subject_id))
            await session.commit()
            
            # Log action
            await log_admin_action(
                callback.from_user.id,
                "Delete Subject",
                f"Deleted subject: {subject.subject_name}"
            )
            
            await callback.message.edit_text(
                f"✅ *Subject Deleted*\n\n"
                f"Subject '{subject.subject_name}' and all its chapters/questions have been deleted.",
                parse_mode='Markdown',
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ Subject not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_subject")
async def cancel_delete_subject_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Cancel subject deletion"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['back']} *Delete Cancelled*\n\n"
        f"The subject was not deleted.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== Add Chapter to Subject ==============

@router.callback_query(F.data.startswith("admin_subject_add_chapter_"))
async def admin_subject_add_chapter_callback(callback: types.CallbackQuery, state: FSMContext,
                                              is_admin: bool = False):
    """Start adding a chapter to a subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subject_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subject = await question_repo.get_subject(subject_id)
        
        if not subject:
            await callback.message.edit_text(
                "❌ Subject not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        await state.update_data(subject_id=subject_id, subject_name=subject.subject_name)
    
    await callback.message.edit_text(
        f"{EMOJIS['add']} *Add Chapter*\n\n"
        f"Subject: *{subject.subject_name}*\n\n"
        f"Step 1: Enter the chapter name:",
        parse_mode='Markdown'
    )
    
    await state.set_state(SubjectStates.waiting_for_chapter_name)
    await callback.answer()


@router.message(StateFilter(SubjectStates.waiting_for_chapter_name))
async def handle_chapter_name(message: types.Message, state: FSMContext,
                               is_admin: bool = False):
    """Handle chapter name input"""
    if not is_admin:
        return
    
    chapter_name = message.text.strip()
    
    if len(chapter_name) < 2:
        await message.answer(
            "❌ Chapter name is too short (minimum 2 characters). Please try again:"
        )
        return
    
    data = await state.get_data()
    data['chapter_name'] = chapter_name
    await state.update_data(data)
    
    await message.answer(
        f"{EMOJIS['add']} *Add Chapter*\n\n"
        f"Chapter: *{chapter_name}*\n\n"
        f"Step 2 (Optional): Enter a description:\n\n"
        f"Press /skip to skip this step.",
        parse_mode='Markdown'
    )
    
    await state.set_state(SubjectStates.waiting_for_chapter_description)


@router.message(StateFilter(SubjectStates.waiting_for_chapter_description), F.text == "/skip")
async def skip_chapter_description(message: types.Message, state: FSMContext,
                                    is_admin: bool = False):
    """Skip chapter description step"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['description'] = ""
    await state.update_data(data)
    
    await save_chapter(message, state)


@router.message(StateFilter(SubjectStates.waiting_for_chapter_description))
async def handle_chapter_description(message: types.Message, state: FSMContext,
                                       is_admin: bool = False):
    """Handle chapter description input"""
    if not is_admin:
        return
    
    data = await state.get_data()
    data['description'] = message.text
    await state.update_data(data)
    
    await save_chapter(message, state)


async def save_chapter(message: types.Message, state: FSMContext):
    """Save the new chapter"""
    data = await state.get_data()
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        # Get chapters to determine order
        existing_chapters = await question_repo.get_chapters(data['subject_id'])
        next_order = len(existing_chapters) + 1
        
        chapter = await question_repo.create_chapter(
            subject_id=data['subject_id'],
            chapter_name=data['chapter_name'],
            chapter_order=next_order,
            description=data.get('description', '')
        )
        
        # Log action
        await log_admin_action(
            message.from_user.id,
            "Add Chapter",
            f"Added chapter '{data['chapter_name']}' to subject '{data['subject_name']}'"
        )
    
    await message.answer(
        f"✅ *Chapter Added Successfully!*\n\n"
        f"Chapter: *{data['chapter_name']}*\n"
        f"Subject: {data['subject_name']}\n"
        f"Order: #{next_order}",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()


@router.callback_query(F.data.startswith("admin_subject_chapters_"))
async def admin_subject_chapters_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View chapters of a subject"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    subject_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        question_repo = QuestionRepository(session)
        
        subject = await question_repo.get_subject(subject_id)
        if not subject:
            await callback.message.edit_text(
                "❌ Subject not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        chapters = await question_repo.get_chapters(subject_id)
        
        if not chapters:
            await callback.message.edit_text(
                f"{EMOJIS['warning']} *No Chapters*\n\n"
                f"Subject '{subject.subject_name}' has no chapters yet.",
                parse_mode='Markdown',
                reply_markup=AdminSubjectsKeyboard.get_subject_action_keyboard(subject_id)
            )
            await callback.answer()
            return
        
        chapters_text = (
            f"{EMOJIS['list']} *Chapters in {subject.subject_name}*\n\n"
        )
        
        for chapter in chapters:
            q_count = await question_repo.get_question_count(chapter_id=chapter.chapter_id)
            chapters_text += (
                f"📑 *{chapter.chapter_name}*\n"
                f"   • Questions: {q_count}\n"
                f"   • Order: {chapter.chapter_order}\n\n"
            )
        
        await callback.message.edit_text(
            chapters_text,
            parse_mode='Markdown',
            reply_markup=AdminSubjectsKeyboard.get_subject_action_keyboard(subject_id)
        )
    
    await callback.answer()


# Import inline keyboard button
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

