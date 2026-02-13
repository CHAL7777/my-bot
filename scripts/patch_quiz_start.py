# PATCH FILE: app/handlers/quiz.py
# Fix: Replace the start_quiz_flow function to use can_access_premium()

# Find this function (around line 47-81) and replace it with:

async def start_quiz_flow(message: types.Message, state: FSMContext,
                         has_active_subscription: bool = False):
    """
    Start the quiz selection flow.
    
    Uses single source of truth for access check via can_access_premium().
    FIXED: Now uses the same access check as payment flow to avoid contradictions.
    """
    user_id = message.from_user.id
    
    async for session in get_db():
        # Use single source of truth for access check
        from app.services.access_control_service import can_access_premium
        
        access_result = await can_access_premium(
            user_id=user_id,
            session=session,
            log_attempt=True,
            resource="start_quiz",
            action="access"
        )
        
        if not access_result['allowed']:
            # Determine appropriate message based on reason
            reason = access_result['reason_code']
            
            if reason == 'NO_USER':
                msg = (
                    "❌ *Account Not Found*\n\n"
                    "Please start a conversation with the bot first using /start."
                )
            elif reason == 'NO_PAYMENT':
                msg = (
                    "💳 *Premium Access Required*\n\n"
                    "This feature requires premium access.\n"
                    "Use /payment to unlock all features!"
                )
            elif reason == 'PAYMENT_PENDING':
                msg = (
                    "⏳ *Payment Under Review*\n\n"
                    "Your payment is pending admin approval.\n"
                    "Please wait for approval before accessing quizzes.\n\n"
                    "This usually takes 1-24 hours."
                )
            elif reason == 'PAYMENT_REJECTED':
                msg = (
                    "❌ *Payment Was Rejected*\n\n"
                    "Your previous payment was rejected.\n"
                    "Please contact admin or upload a new payment screenshot."
                )
            elif reason == 'NO_SCREENSHOT':
                msg = (
                    "⚠️ *Payment Verification Incomplete*\n\n"
                    "Your payment is missing required documentation.\n"
                    "Please contact admin to resolve this issue."
                )
            else:
                msg = (
                    "❌ *Access Denied*\n\n"
                    "Your account is not approved for premium features.\n"
                    "Please wait for approval or contact the administrator."
                )
            
            await message.answer(
                msg,
                parse_mode='Markdown',
                reply_markup=MainMenuKeyboard.get_main_menu()
            )
            return
        
        # Continue with quiz flow if access granted
        question_repo = QuestionRepository(session)
        
        # Get available subjects
        subjects = await question_repo.get_subjects()
        
        if not subjects:
            await message.answer(
                "📭 No subjects available yet.\n"
                "Please check back later or contact admin to add subjects.",
                reply_markup=MainMenuKeyboard.get_main_menu()
            )
            return
        
        # Format subjects for display
        subject_list = [
            {'subject_id': s.subject_id, 'subject_name': s.subject_name}
            for s in subjects
        ]
        
        await state.set_state(QuizStates.selecting_subject)
        await state.update_data({
            'subjects': subject_list,
            'user_id': message.from_user.id,
            'has_active_subscription': True  # User has access, so set to True
        })
        
        await message.answer(
            "📚 *Select a Subject*\n\n"
            "Choose the subject you want to practice:",
            parse_mode='Markdown',
            reply_markup=MainMenuKeyboard.get_subjects_keyboard(subject_list)
        )

# ============================================================
# ALTERNATIVE: Quick fix by changing the original check
# Just change ONE LINE in the original function:
# ============================================================

# ORIGINAL (line 63):
#     if user and not user.approved:

# CHANGE TO:
#     from app.services.access_control_service import can_access_premium
#     access = await can_access_premium(user_id, session)
#     if not access['allowed']:

# ============================================================

