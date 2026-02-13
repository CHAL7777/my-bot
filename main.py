import os
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Update, WebAppInfo
)
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession

# Database imports
from app.db.base import get_db, init_db, close_db
from app.repositories.user_repo import UserRepository
from app.repositories.question_repo import QuestionRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.repositories.referral_repo import ReferralRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

QUIZ_SESSIONS: Dict[int, dict] = {}

def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Start Quiz")],
            [KeyboardButton(text="Leaderboard")],
            [KeyboardButton(text="Subscription")],
            [KeyboardButton(text="My Profile")],
        ],
        resize_keyboard=True
    )

def get_difficulty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Simple", callback_data="difficulty_simple"),
                InlineKeyboardButton(text="Medium", callback_data="difficulty_medium"),
                InlineKeyboardButton(text="Hard", callback_data="difficulty_hard")
            ],
            [
                InlineKeyboardButton(text="Back", callback_data="back_to_menu")
            ]
        ]
    )

def get_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Pay 150 Birr", callback_data="pay_now")
            ],
            [
                InlineKeyboardButton(text="Instructions", callback_data="payment_instructions")
            ],
            [
                InlineKeyboardButton(text="Back", callback_data="back_to_menu")
            ]
        ]
    )

def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Today", callback_data="lb_daily"),
                InlineKeyboardButton(text="This Week", callback_data="lb_weekly")
            ],
            [
                InlineKeyboardButton(text="This Month", callback_data="lb_monthly"),
                InlineKeyboardButton(text="All Time", callback_data="lb_overall")
            ],
            [
                InlineKeyboardButton(text="Back", callback_data="back_to_menu")
            ]
        ]
    )

async def get_subjects_keyboard() -> InlineKeyboardMarkup:
    async for session in get_db():
        question_repo = QuestionRepository(session)
        subjects = await question_repo.get_subjects()
        keyboard = []
        for subject in subjects:
            keyboard.append([
                InlineKeyboardButton(
                    text=subject.subject_name,
                    callback_data=f"subject_{subject.subject_id}"
                )
            ])
        keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_to_difficulty")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_chapters_keyboard(subject_id: int) -> InlineKeyboardMarkup:
    async for session in get_db():
        question_repo = QuestionRepository(session)
        chapters = await question_repo.get_chapters(subject_id)
        keyboard = []
        for chapter in chapters:
            keyboard.append([
                InlineKeyboardButton(
                    text=chapter.chapter_name,
                    callback_data=f"chapter_{chapter['chapter_id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_to_subjects")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    async for session in get_db():
        user_repo = UserRepository(session)
        await user_repo.create_user(user_id, username, first_name, last_name)
    
    welcome_text = (
        "Welcome to Quiz Bot!\n\n"
        "Test your knowledge with quizzes on various subjects!\n\n"
        "Click 'Start Quiz' to begin\n"
        "Check the leaderboard\n"
        "Upgrade to premium\n\n"
        "Let's get started!"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

@router.message(F.text == "Start Quiz")
async def start_quiz(message: Message):
    user_id = message.from_user.id

    async for session in get_db():
        user_repo = UserRepository(session)
        user = await user_repo.get_user(user_id)

        if not user or not user.approved:
            await message.answer(
                "Access Denied\n\n"
                "You need to subscribe to access quizzes.\n"
                "Click 'Subscription' to upgrade.",
                reply_markup=get_main_menu()
            )
            return
    
    await message.answer(
        "Select Difficulty\n\n"
        "Choose your difficulty level:",
        reply_markup=get_difficulty_keyboard()
    )

@router.message(Command("quiz"))
async def cmd_quiz(message: Message):
    """Handle /quiz command - same as Start Quiz button"""
    user_id = message.from_user.id

    async for session in get_db():
        user_repo = UserRepository(session)
        user = await user_repo.get_user(user_id)

        if not user or not user.approved:
            await message.answer(
                "Access Denied\n\n"
                "You need to subscribe to access quizzes.\n"
                "Click 'Subscription' to upgrade.",
                reply_markup=get_main_menu()
            )
            return
    
    await message.answer(
        "Select Difficulty\n\n"
        "Choose your difficulty level:",
        reply_markup=get_difficulty_keyboard()
    )

@router.message(F.text == "Leaderboard")
async def show_leaderboard(message: Message):
    await message.answer(
        "Leaderboard\n\n"
        "Select a time period:",
        reply_markup=get_leaderboard_keyboard()
    )

@router.message(F.text == "Subscription")
async def show_subscription(message: Message):
    user_id = message.from_user.id

    async for session in get_db():
        user_repo = UserRepository(session)
        user = await user_repo.get_user(user_id)

        if user and user.is_premium:
            await message.answer(
                "Premium Active\n\n"
                "You have lifetime access to all quizzes!\n\n"
                "Thank you for your support!",
                reply_markup=get_main_menu()
            )
        else:
            await message.answer(
                "Subscription Plans\n\n"
                "One-time payment for lifetime access: 150 Birr\n\n"
                "What would you like to do?",
                reply_markup=get_payment_keyboard()
            )

@router.message(F.text == "My Profile")
async def show_profile(message: Message):
    user_id = message.from_user.id

    async for session in get_db():
        user_repo = UserRepository(session)
        attempt_repo = AttemptRepository(session)
        referral_repo = ReferralRepository(session)

        user = await user_repo.get_user(user_id)

        if user:
            # Get user stats from attempt repository
            stats = await attempt_repo.get_user_stats(user_id, days=None)

            # Get referral count
            referral_stats = await referral_repo.get_referral_stats(user_id)
            referral_count = referral_stats['completed']

            profile_text = (
                f"Your Profile\n\n"
                f"Name: {user.first_name or 'N/A'}\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"Status: {'Premium' if user.is_premium else 'Free'}\n\n"
                f"Quiz Stats\n"
                f"Total Attempts: {stats['total_attempts'] or 0}\n"
                f"Correct Answers: {stats['correct_attempts'] or 0}\n"
                f"Accuracy: {stats['accuracy']:.1f}%\n\n"
                f"Referrals: {referral_count}"
            )

            if user.is_premium:
                await message.answer(profile_text, reply_markup=get_main_menu())
            else:
                # Generate referral code if not exists
                if not user.referral_code:
                    # For now, we'll use a simple implementation
                    import random
                    import string
                    referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    await user_repo.update_user(user_id, referral_code=referral_code)
                else:
                    referral_code = user.referral_code

                profile_text += f"\n\nYour Referral Code: {referral_code}"
                await message.answer(profile_text, reply_markup=get_main_menu())

@router.callback_query(F.data == "pay_now")
async def pay_now(callback: CallbackQuery):
    await callback.message.answer(
        "Payment Instructions\n\n"
        "1. Send 150 Birr to our payment account\n"
        "2. Take a screenshot of the payment\n"
        "3. Send the screenshot here\n\n"
        "After admin approval, you'll get lifetime access!\n\n"
        "Contact @admin for questions."
    )
    await callback.answer()

@router.callback_query(F.data == "payment_instructions")
async def payment_instructions(callback: CallbackQuery):
    await callback.message.answer(
        "Payment Instructions\n\n"
        "1. Transfer 150 Birr to our account\n"
        "2. Screenshot the payment confirmation\n"
        "3. Send the screenshot to this chat\n"
        "4. Wait for admin approval (usually within 24h)\n\n"
        "Once approved, you'll have lifetime access!"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("lb_"))
async def show_leaderboard_period(callback: CallbackQuery):
    period = callback.data.replace("lb_", "")
    period_map = {
        'daily': 'Today',
        'weekly': 'This Week',
        'monthly': 'This Month',
        'overall': 'All Time'
    }

    async for session in get_db():
        leaderboard_repo = LeaderboardRepository(session)
        entries = await leaderboard_repo.get_leaderboard(period)

        if not entries:
            await callback.message.answer(
                f"{period_map.get(period, 'Leaderboard')}\n\n"
                "No entries yet. Be the first!"
            )
        else:
            text = f"{period_map.get(period, 'Leaderboard')}\n\n"
            for entry in entries:
                name = entry['username'] or entry['first_name'] or f"User {entry['user_id']}"
                text += f"{entry['rank']}. {name} - {entry['score']} pts ({entry['accuracy']:.0f}%)\n"

            await callback.message.answer(text)

    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.answer(
        "Main Menu\n\n"
        "Choose an option:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("difficulty_"))
async def select_difficulty(callback: CallbackQuery):
    difficulty = callback.data.replace("difficulty_", "")
    await callback.message.answer(
        "Select Subject\n\n"
        "Choose a subject:",
        reply_markup=get_subjects_keyboard()
    )
    QUIZ_SESSIONS[callback.from_user.id] = {'difficulty': difficulty}
    await callback.answer()

@router.callback_query(F.data == "back_to_difficulty")
async def back_to_difficulty(callback: CallbackQuery):
    await callback.message.answer(
        "Select Difficulty\n\n"
        "Choose your difficulty level:",
        reply_markup=get_difficulty_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("subject_"))
async def select_subject(callback: CallbackQuery):
    subject_id = int(callback.data.replace("subject_", ""))
    user_id = callback.from_user.id

    if user_id in QUIZ_SESSIONS:
        QUIZ_SESSIONS[user_id]['subject_id'] = subject_id

    chapters_keyboard = await get_chapters_keyboard(subject_id)
    await callback.message.answer(
        "Select Chapter\n\n"
        "Choose a chapter:",
        reply_markup=chapters_keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_subjects")
async def back_to_subjects(callback: CallbackQuery):
    await callback.message.answer(
        "Select Subject\n\n"
        "Choose a subject:",
        reply_markup=get_subjects_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("chapter_"))
async def select_chapter(callback: CallbackQuery):
    chapter_id = int(callback.data.replace("chapter_", ""))
    user_id = callback.from_user.id

    if user_id not in QUIZ_SESSIONS:
        await callback.message.answer("Please start a new quiz.")
        await callback.answer()
        return

    session = QUIZ_SESSIONS[user_id]
    subject_id = session.get('subject_id')
    difficulty = session.get('difficulty', 'simple')

    async for db_session in get_db():
        question_repo = QuestionRepository(db_session)
        questions = await question_repo.get_random_questions(subject_id, chapter_id, difficulty, limit=10)

        if not questions:
            await callback.message.answer(
                "No Questions Available\n\n"
                "There are no questions for this selection yet.\n"
                "Please try a different chapter."
            )
            await callback.answer()
            return

        quiz_id = str(uuid4())
        session['quiz_id'] = quiz_id
        session['questions'] = questions
        session['current_index'] = 0
        session['score'] = 0
        session['chapter_id'] = chapter_id

        first_question = questions[0]
        question_text = (
            f"Quiz Started!\n\n"
            f"Question 1/{len(questions)}\n\n"
            f"{first_question['question_text']}\n\n"
            f"A. {first_question['option_a']}\n"
            f"B. {first_question['option_b']}\n"
            f"C. {first_question['option_c']}\n"
            f"D. {first_question['option_d']}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="A", callback_data=f"answer_A_{quiz_id}"),
                    InlineKeyboardButton(text="B", callback_data=f"answer_B_{quiz_id}"),
                    InlineKeyboardButton(text="C", callback_data=f"answer_C_{quiz_id}"),
                    InlineKeyboardButton(text="D", callback_data=f"answer_D_{quiz_id}")
                ]
            ]
        )

        await callback.message.answer(question_text, reply_markup=keyboard)
        await callback.answer()

@router.callback_query(F.data.startswith("answer_"))
async def answer_question(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in QUIZ_SESSIONS:
        await callback.message.answer("Please start a new quiz.")
        await callback.answer()
        return
    
    session = QUIZ_SESSIONS[user_id]
    quiz_id = session.get('quiz_id')
    
    if not quiz_id or callback.data.split("_")[2] != quiz_id:
        await callback.answer("Invalid quiz session!", show_alert=True)
        return
    
    parts = callback.data.split("_")
    selected_option = parts[1]
    
    questions = session.get('questions', [])
    current_index = session.get('current_index', 0)
    
    if current_index >= len(questions):
        await callback.message.answer("Quiz completed!")
        await callback.answer()
        return
    
    question = questions[current_index]
    is_correct = selected_option == question['correct_option']
    
    if is_correct:
        points = {'simple': 1, 'medium': 2, 'hard': 3}.get(session.get('difficulty', 'simple'), 1)
        session['score'] += points
    
    async for db_session in get_db():
        attempt_repo = AttemptRepository(db_session)
        await attempt_repo.create_attempt(user_id, question['question_id'], selected_option, is_correct)
    
    current_index += 1
    session['current_index'] = current_index
    
    if current_index >= len(questions):
        score = session.get('score', 0)
        total = len(questions)
        accuracy = (score / total) * 100 if total > 0 else 0
        
        result_text = (
            f"Quiz Complete!\n\n"
            f"Score: {score}/{total}\n"
            f"Accuracy: {accuracy:.0f}%\n\n"
        )
        
        if accuracy >= 80:
            result_text += "Excellent! You're doing great!"
        elif accuracy >= 60:
            result_text += "Good job! Keep practicing!"
        else:
            result_text += "Keep learning and try again!"
        
        await callback.message.answer(result_text, reply_markup=get_main_menu())
        del QUIZ_SESSIONS[user_id]
    else:
        next_question = questions[current_index]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="A", callback_data=f"answer_A_{quiz_id}"),
                    InlineKeyboardButton(text="B", callback_data=f"answer_B_{quiz_id}"),
                    InlineKeyboardButton(text="C", callback_data=f"answer_C_{quiz_id}"),
                    InlineKeyboardButton(text="D", callback_data=f"answer_D_{quiz_id}")
                ]
            ]
        )
        
        question_text = (
            f"Question {current_index + 1}/{len(questions)}\n\n"
            f"{next_question['question_text']}\n\n"
            f"A. {next_question['option_a']}\n"
            f"B. {next_question['option_b']}\n"
            f"C. {next_question['option_c']}\n"
            f"D. {next_question['option_d']}"
        )
        
        await callback.message.answer(question_text, reply_markup=keyboard)
    
    await callback.answer()

@router.message(F.content_type == "photo")
async def handle_payment_screenshot(message: Message):
    user_id = message.from_user.id
    photo = message.photo[-1]
    file_id = photo.file_id

    async for session in get_db():
        payment_repo = PaymentRepository(session)
        await payment_repo.create_payment(
            user_id=user_id,
            amount=150.0,
            screenshot_file_id=file_id,
            notes="Payment screenshot submitted"
        )
    
    await message.answer(
        "Payment Received!\n\n"
        "Your payment screenshot has been submitted for review.\n"
        "You'll get a notification once approved (usually within 24h)."
    )

@router.message(F.text == "/admin")
async def admin_command(message: Message):
    await message.answer(
        "Admin Panel\n\n"
        "Use /pending to see pending payments\n"
        "Use /approve <payment_id> to approve\n"
        "Use /reject <payment_id> to reject"
    )

@router.message(F.text.startswith("/approve "))
async def approve_payment_command(message: Message):
    try:
        payment_id = int(message.text.split()[1])
        async for session in get_db():
            payment_repo = PaymentRepository(session)
            await payment_repo.approve_payment(payment_id, admin_id=1)
        await message.answer(f"Payment {payment_id} approved!")
    except (ValueError, IndexError):
        await message.answer("Usage: /approve <payment_id>")
    except Exception as e:
        await message.answer(f"Error approving payment: {str(e)}")

@router.message(F.text.startswith("/reject "))
async def reject_payment_command(message: Message):
    try:
        payment_id = int(message.text.split()[1])
        async for session in get_db():
            payment_repo = PaymentRepository(session)
            await payment_repo.reject_payment(payment_id, admin_id=1, reason="Rejected via admin command")
        await message.answer(f"Payment {payment_id} rejected!")
    except (ValueError, IndexError):
        await message.answer("Usage: /reject <payment_id>")
    except Exception as e:
        await message.answer(f"Error rejecting payment: {str(e)}")

@router.message(F.text == "/pending")
async def show_pending_payments(message: Message):
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        payments = await payment_repo.get_pending_payments()

        if not payments:
            await message.answer("No pending payments.")
            return

        text = "Pending Payments\n\n"
        for p in payments:
            name = p.username or p.first_name or str(p.user_id)
            text += f"ID: {p.payment_id} | {name} | {p.amount} Birr\n"

        await message.answer(text)

@router.message(F.text == "/stats")
async def show_stats(message: Message):
    user_id = message.from_user.id

    async for session in get_db():
        attempt_repo = AttemptRepository(session)
        stats = await attempt_repo.get_user_stats(user_id)

        text = (
            f"Your Stats\n\n"
            f"Total Attempts: {stats['total_attempts'] or 0}\n"
            f"Correct: {stats['correct_attempts'] or 0}\n"
            f"Accuracy: {stats['accuracy']:.1f}%"
        )

        await message.answer(text)

@router.message(F.text == "/referral")
async def show_referral(message: Message):
    user_id = message.from_user.id

    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)

        user = await user_repo.get_user(user_id)

        if not user:
            await message.answer("Please /start first.")
            return

        # Generate referral code if not exists
        if not user.referral_code:
            import random
            import string
            referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            await user_repo.update_user(user_id, referral_code=referral_code)
        else:
            referral_code = user.referral_code

        referral_stats = await referral_repo.get_referral_stats(user_id)
        referral_count = referral_stats['completed']

        text = (
            f"Referral Program\n\n"
            f"Your code: {referral_code}\n"
            f"Referrals: {referral_count}\n\n"
            "Share your code with friends!\n"
            "When they subscribe, you get rewards!"
        )

        await message.answer(text)

@router.message()
async def echo_handler(message: Message):
    await message.answer(
        "I don't understand that command.\n"
        "Use the menu buttons or try /start",
        reply_markup=get_main_menu()
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    if BOT_TOKEN and WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL + "/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
    await init_db()
    logger.info("Database initialized")
    yield
    if BOT_TOKEN:
        await bot.delete_webhook()
        logger.info("Webhook deleted")
    await close_db()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Quiz Bot is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}

@app.on_event("shutdown")
async def shutdown():
    if BOT_TOKEN:
        await bot.session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
