"""
Payment Handler - Redesigned for Safe Payment Handling

This handler manages payment operations with:
- Safe attribute access (handles missing columns gracefully)
- Proper error handling for all edge cases
- Clear user-friendly error messages

Payment Flow:
1. User initiates payment with /payment
2. User selects "One-time Lifetime" button (buy_premium)
3. User uploads payment screenshot
4. Admin reviews and approves/rejects the payment
5. User is notified of the result
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ContentType
from datetime import datetime
import os

from app.keyboards.menu import MainMenuKeyboard
from app.services.payment_service import PaymentService
from app.db.base import get_db
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.config import settings
from app.utils.constants import EMOJIS
from app.utils.helpers import format_currency

router = Router()

class PaymentStates(StatesGroup):
    """FSM states for payment flow"""
    waiting_for_screenshot = State()
    waiting_for_subscription_choice = State()
    waiting_for_payment_confirmation = State()

# ============== Main Payment Command ==============

@router.message(Command("payment"))
async def payment_command(message: types.Message, state: FSMContext,
                          has_active_subscription: bool = False):
    """
    Handle /payment command - show payment options and status.
    
    This is the main entry point for payment-related operations.
    Displays payment methods and instructions.
    
    Note: has_active_subscription is injected by SubscriptionMiddleware.
    """
    user_id = message.from_user.id
    
    # Build payment message with CBE and Telebirr details
    payment_msg = (
        "💳 *Payment Options*\n\n"
        
        "🎯 *One-Time Lifetime Access:*\n"
        f"• Price: *{settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}* (One-time payment)\n"
        "• Duration: Lifetime\n"
        "• Includes all premium features (Simple, Medium, Hard)\n\n"
        
        "🏦 *Payment Methods:*\n\n"
        
        "🏦 *Commercial Bank of Ethiopia (CBE)*\n"
        "• Account Number: `1000583115467`\n"
        "• Account Name: Chala Gobena\n\n"
        
        "📱 *Telebirr*\n"
        "• Number: `0974745704`\n\n"
        
        "📸 *Payment Instructions:*\n"
        f"1. Send *{settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}* using one of the methods above\n"
        "2. Take a clear screenshot of your payment confirmation\n"
        "3. Upload the screenshot here\n\n"
        
        "✅ *What happens next:*\n"
        "• Admin will manually verify your payment\n"
        "• You'll receive a confirmation message\n"
        "• Premium access will be unlocked after approval\n\n"
        
        "💡 *Tip:* Make sure your screenshot shows the transaction ID and amount clearly."
    )
    
    await message.answer(
        payment_msg,
        reply_markup=MainMenuKeyboard.get_payment_options_keyboard(),
        parse_mode='Markdown'
    )

# ============== Buy Premium (One-time Lifetime) ==============

@router.callback_query(F.data == "buy_premium")
async def buy_premium_callback(callback: types.CallbackQuery, state: FSMContext,
                               has_active_subscription: bool = False):
    """
    Handle buy_premium callback - one-time lifetime payment.
    
    Shows payment instructions and starts the payment screenshot upload flow.
    Checks if user already has premium access to prevent duplicate payments.
    """
    user_id = callback.from_user.id
    
    # Check if user already has premium - prevent duplicate payments
    if has_active_subscription:
        await callback.message.edit_text(
            "🎉 *You Already Have Lifetime Access!*\n\n"
            "You already have premium access with lifetime validity.\n"
            "Enjoy all premium features without any additional payment!\n\n"
            "💡 Need any help? Use /help to see available commands.",
            parse_mode='Markdown',
            reply_markup=MainMenuKeyboard.get_main_menu_inline()
        )
        await callback.answer()
        return
    
    # Show payment details for one-time lifetime purchase
    payment_msg = (
        "💎 *One-Time Lifetime Payment*\n\n"
        "🎯 *What you'll get:*\n"
        "• Lifetime premium access\n"
        "• All difficulty levels (Simple, Medium, Hard)\n"
        "• Priority support\n"
        "• All future features included\n\n"
        
        f"💰 *Payment Details:*\n"
        f"• Price: *{settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}*\n"
        "• Type: One-time payment (no monthly fees)\n"
        "• Duration: Lifetime\n\n"
        
        "🏦 *Payment Methods:*\n\n"
        
        "🏦 *Commercial Bank of Ethiopia (CBE)*\n"
        "• Account Number: `1000583115467`\n"
        "• Account Name: Chala Gobena\n\n"
        
        "📱 *Telebirr*\n"
        "• Number: `0974745704`\n\n"
        
        "📸 *After Payment:*\n"
        "1. Take a clear screenshot of your payment confirmation\n"
        "2. Upload the screenshot here\n"
        "3. Admin will verify and activate your premium\n\n"
        
        "⏱️ *Processing Time:* 1-24 hours\n\n"
        
        f"💡 *Your User ID:* `{user_id}` (include in payment note if possible)"
    )
    
    # Set state to waiting for screenshot
    await state.set_state(PaymentStates.waiting_for_screenshot)
    await state.update_data({
        'subscription_type': 'lifetime',
        'subscription_days': None  # Lifetime = None
    })
    
    await callback.message.edit_text(
        payment_msg,
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_payment_screenshot_keyboard()
    )
    await callback.answer()


# ============== Screenshot Upload Handler ==============

@router.message(PaymentStates.waiting_for_screenshot, F.content_type == ContentType.PHOTO)
async def handle_payment_screenshot(message: types.Message, state: FSMContext):
    """
    Handle payment screenshot upload.
    
    This is the critical step where users submit their payment proof.
    The screenshot is saved locally and a payment record is created.
    """
    user_id = message.from_user.id
    
    # Get the highest resolution photo
    photo = message.photo[-1]
    
    # Create screenshots directory if it doesn't exist
    screenshots_dir = os.path.join(settings.DATA_DIR, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    
    try:
        # Download the photo
        file = await message.bot.get_file(photo.file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(screenshots_dir, f"{user_id}_{timestamp}.jpg")
        
        await message.bot.download_file(file.file_path, file_path)
        
        async for session in get_db():
            payment_repo = PaymentRepository(session)
            user_repo = UserRepository(session)
            
            payment_service = PaymentService(payment_repo, user_repo)
            
            # Save payment record
            result = await payment_service.save_payment_screenshot(
                user_id=user_id,
                file_id=photo.file_id,
                file_path=file_path,
                subscription_days=None  # Lifetime access
            )
            
            payment_id = result['payment_id']
            
            # Prepare confirmation message
            confirmation_msg = (
                "✅ *Screenshot Received!*\n\n"
                f"📋 *Payment Details:*\n"
                f"• Payment ID: #{payment_id}\n"
                f"• Amount: {settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}\n"
                "• Type: Lifetime Premium\n"
                "• Status: ⏳ Pending approval\n\n"
                
                "⏱️ *What happens next:*\n"
                "1. Admin reviews your screenshot (1-24 hours)\n"
                "2. You receive approval notification\n"
                "3. Premium access activated automatically\n\n"
                
                "📞 *Need faster approval?*\n"
                f"Contact admin with your Payment ID: #{payment_id}\n\n"
                
                "💡 Keep this Payment ID for reference!"
            )
            
            await message.answer(
                confirmation_msg,
                reply_markup=MainMenuKeyboard.get_main_menu(),
                parse_mode='Markdown'
            )
            
            # Clear state
            await state.clear()
            
            # Notify admins about new payment
            await notify_admins_about_payment(message.bot, payment_id, user_id)
            
    except Exception as e:
        await message.answer(
            f"❌ Error processing screenshot: {str(e)}\n\n"
            "Please try again or contact support.",
            reply_markup=MainMenuKeyboard.get_main_menu()
        )
        await state.clear()

async def notify_admins_about_payment(bot, payment_id: int, user_id: int):
    """Notify all admins about new payment with formatted message"""
    username = f"User {user_id}"
    try:
        async for session in get_db():
            user_repo = UserRepository(session)
            user = await user_repo.get_user(user_id)
            if user:
                username = user.first_name or user.username or f"User {user_id}"
    except:
        pass
    
    # Format: 💰 Payment Alert
    admin_message = (
        f"💰 *Payment Alert*\n\n"
        f"New payment submitted by *{username}*\n"
        f"Amount: *{settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}*\n"
        f"Status: *Pending*\n\n"
        f"📋 Payment ID: `#{payment_id}`\n"
        f"👤 User ID: `{user_id}`\n"
        f"⏰ Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
        f"Use /admin_payments to review."
    )
    
    # Send to all admin users
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")

@router.message(PaymentStates.waiting_for_screenshot)
async def handle_wrong_content_type(message: types.Message):
    """Handle wrong content type when waiting for screenshot"""
    await message.answer(
        "❌ Please send a screenshot photo.\n\n"
        "Take a clear screenshot of your payment confirmation and send it here.\n"
        "Make sure the transaction ID and amount are visible.",
        reply_markup=MainMenuKeyboard.get_main_menu()
    )


# ============== Upload Screenshot Callback ==============

@router.callback_query(F.data == "upload_screenshot")
async def upload_screenshot_callback(callback: types.CallbackQuery, state: FSMContext):
    """Prompt user to upload payment screenshot"""
    await state.set_state(PaymentStates.waiting_for_screenshot)
    
    await callback.message.edit_text(
        "📸 *Upload Payment Screenshot*\n\n"
        "Please upload a clear screenshot of your payment confirmation.\n\n"
        "✅ *What should be visible:*\n"
        "• Transaction ID / Reference number\n"
        f"• Amount: {settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}\n"
        "• Date and time\n"
        "• Payment status (Success/Completed)\n\n"
        "❌ *What to avoid:*\n"
        "• Blurry images\n"
        "• Cropped screenshots\n"
        "• Missing transaction details\n\n"
        "📎 *Tap the attachment icon (📎) to upload your screenshot.*",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_cancel_payment_keyboard()
    )
    await callback.answer()


# ============== Cancel Payment ==============

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Cancel payment process"""
    await state.clear()
    
    await callback.message.edit_text(
        "❌ *Payment Process Cancelled*\n\n"
        "No worries! You can start the payment process anytime by:\n"
        "• Tapping '💰 One-time Lifetime Access' button\n"
        "• Using /payment command\n\n"
        "💡 Need help? Contact admin for assistance.",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_main_menu_inline()
    )
    await callback.answer()


# ============== Payment History ==============

@router.callback_query(F.data == "view_payment_history")
async def view_payment_history_callback(callback: types.CallbackQuery):
    """View complete payment history"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        
        try:
            payments = await payment_repo.get_user_payments(user_id)
            
            if not payments:
                history_msg = (
                    "📋 *Payment History*\n\n"
                    "No payment history found.\n"
                    "Make your first payment to unlock premium features!"
                )
            else:
                history_msg = (
                    f"📋 *Payment History*\n\n"
                    f"Total payments: {len(payments)}\n\n"
                )
                
                for payment in payments[:10]:
                    status_emoji = {
                        'approved': '✅',
                        'pending': '⏳',
                        'rejected': '❌'
                    }.get(payment.status, '❓')
                    
                    # Safe access to subscription_days
                    sub_days = getattr(payment, 'subscription_days', None)
                    sub_text = f"{sub_days} days" if sub_days else "Lifetime"
                    
                    history_msg += (
                        f"{status_emoji} *Payment #{payment.payment_id}*\n"
                        f"• Amount: {settings.CURRENCY_SYMBOL}{payment.amount:.2f}\n"
                        f"• Access: {sub_text}\n"
                        f"• Status: {payment.status.capitalize()}\n"
                        f"• Date: {payment.created_at.strftime('%d %b %Y %H:%M')}\n"
                    )
                    
                    if payment.approved_at:
                        history_msg += f"• Approved: {payment.approved_at.strftime('%d %b %Y %H:%M')}\n"
                    
                    if payment.rejected_reason:
                        history_msg += f"• Reason: {payment.rejected_reason}\n"
                    
                    history_msg += "\n"
            
            await callback.message.edit_text(
                history_msg,
                reply_markup=MainMenuKeyboard.get_payment_options_keyboard()
            )
            
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Error loading payment history: {str(e)}",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


# ============== Payment Status ==============

@router.callback_query(F.data == "payment_status")
async def payment_status_callback(callback: types.CallbackQuery):
    """Check detailed payment status"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        try:
            status = await payment_service.get_payment_status(user_id)
            
            status_msg = (
                f"📊 *Payment Status*\n\n"
                f"👤 User: {callback.from_user.first_name or 'Student'}\n"
                f"🆔 User ID: {user_id}\n\n"
            )
            
            # Check premium status
            is_premium = status.get('is_premium', False)
            
            if is_premium:
                subscription = status.get('subscription')
                if subscription:
                    start_date = subscription.get('start_date')
                    status_msg += (
                        "✅ *Premium Active (Lifetime)*\n"
                        f"• Start: {start_date.strftime('%d %b %Y') if start_date else 'N/A'}\n"
                        "• Access: All features\n"
                        "• Status: Active\n\n"
                    )
            else:
                status_msg += (
                    "❌ *No Premium Access*\n"
                    "• Access level: Simple quizzes only\n"
                    "• Premium features: Locked 🔒\n\n"
                )
            
            # Pending payments
            pending_count = status.get('pending_payments', 0)
            if pending_count > 0:
                status_msg += (
                    f"⏳ *Pending Payments:* {pending_count}\n"
                    "Waiting for admin review. Usually processed within 24 hours.\n\n"
                )
            
            status_msg += (
                "💡 *Need Help?*\n"
                "Contact admin if payment pending > 24 hours."
            )
            
            await callback.message.edit_text(
                status_msg,
                reply_markup=MainMenuKeyboard.get_payment_options_keyboard()
            )
            
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Error loading status: {str(e)}",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()


# ============== Payment Instructions ==============

@router.callback_query(F.data == "payment_instructions")
async def payment_instructions_callback(callback: types.CallbackQuery):
    """Show detailed payment instructions"""
    instructions_msg = (
        "📋 *Payment Instructions*\n\n"
        
        f"💵 *Amount:* {settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL} (One-time payment)\n\n"
        
        "💳 *Payment Methods:*\n"
        "• Commercial Bank of Ethiopia (CBE)\n"
        "• Telebirr\n\n"
        
        "📸 *Screenshot Requirements:*\n"
        "• Clear and readable\n"
        "• Shows transaction ID\n"
        f"• Shows amount: {settings.ONE_TIME_PRICE} {settings.CURRENCY_SYMBOL}\n"
        "• Shows date and time\n"
        "• Shows 'Success' or 'Completed' status\n\n"
        
        "⏱️ *Processing Time:*\n"
        "• usually within 1-24 hours\n"
        "• Faster during business hours\n\n"
        
        "💡 *Include your User ID in payment note:*\n"
        f"`{callback.from_user.id}`"
    )
    
    await callback.message.edit_text(
        instructions_msg,
        reply_markup=MainMenuKeyboard.get_payment_options_keyboard()
    )
    await callback.answer()


# ============== Contact Support ==============

@router.callback_query(F.data == "contact_support")
async def contact_support_callback(callback: types.CallbackQuery):
    """Show support contact information"""
    support_msg = (
        "📞 *Support & Contact*\n\n"
        
        "🆘 *Payment Issues:*\n"
        "• Payment not showing: Wait 5 minutes\n"
        "• Screenshot rejected: Check clarity\n"
        "• Premium access not activated: Contact admin\n\n"
        
        "📧 *Contact Methods:*\n"
        "• Telegram: @quizbot_admin\n"
        "• Email: support@quizbot.com\n\n"
        
        "📋 *When contacting support:*\n"
        f"1. Provide your User ID: {callback.from_user.id}\n"
        "2. Mention Payment ID if applicable\n"
        "3. Describe issue clearly"
    )
    
    await callback.message.edit_text(
        support_msg,
        reply_markup=MainMenuKeyboard.get_payment_options_keyboard()
    )
    await callback.answer()

