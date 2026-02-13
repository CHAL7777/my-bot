"""
Admin Payments Handler - Telegram Quiz Bot
Manage payments: view pending, approve/reject with notes, view all
"""

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from typing import Optional

from app.keyboards.admin import (
    AdminKeyboard, AdminPaymentsKeyboard
)
from app.utils.constants import EMOJIS
from app.services.payment_service import PaymentService
from app.db.base import get_db
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.repositories.admin_log_repo import AdminLogRepository
from aiogram.exceptions import TelegramBadRequest

router = Router()

# FSM States for payment management
class PaymentStates(StatesGroup):
    """FSM states for payment management operations"""
    waiting_for_reject_reason = State()
    waiting_for_note = State()
    waiting_for_filter = State()


# ============== Utility Functions ==============

async def log_admin_action(admin_id: int, action: str, details: str = None):
    """Log admin action to database"""
    async for session in get_db():
        log_repo = AdminLogRepository(session)
        await log_repo.log_action(admin_id, action, details)


async def get_revenue_stats_text(days: int = 30) -> str:
    """Get revenue statistics as formatted text"""
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        # Get revenue stats
        revenue = await payment_service.get_revenue_analytics(days)
        
        # Get user count
        all_users = await user_repo.get_all_users()
        total_users = len(all_users)
        
        # Get approved payments count
        approved_payments = [p for p in all_users if p.payments]
        
        stats_text = (
            f"{EMOJIS['money']} *Revenue Statistics* ({days} days)\n\n"
            f"💰 *Overview:*\n"
            f"• Total Revenue: ETB{revenue['total_revenue']:.2f}\n"
            f"• Payments: {revenue['payment_count']}\n"
            f"• Avg per Payment: ETB{revenue['avg_revenue_per_payment']:.2f}\n\n"
        )
        
        # Revenue by subscription type
        if 'revenue_by_days' in revenue:
            stats_text += f"📊 *By Subscription:*\n"
            for days_type, data in revenue.get('revenue_by_days', {}).items():
                stats_text += f"• {days_type} days: ETB{data['revenue']:.2f} ({data['count']})\n"
        
        stats_text += f"\n👥 *Conversion:*\n"
        stats_text += f"• Total Users: {total_users}\n"
        stats_text += f"• Payment Count: {revenue['payment_count']}\n"
        
        return stats_text


async def safe_update_admin_message(callback: types.CallbackQuery, text: str,
                                    parse_mode: str = 'Markdown', reply_markup: Optional[types.InlineKeyboardMarkup] = None):
    """Safely update an admin message: prefer edit_text for text messages
    and edit_caption for media (photo) messages. Fall back to sending a
    new message if editing fails. This avoids TelegramBadRequest when the
    original message has no editable text.
    """
    msg = callback.message
    try:
        # If the original message contains a photo, attempt to edit caption first
        if getattr(msg, 'photo', None):
            await msg.edit_caption(text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await msg.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        err = str(e).lower()
        # Handle known 'no text to edit' case by trying the alternate edit
        if 'no text in the message to edit' in err or 'there is no text in the message to edit' in err:
            try:
                if getattr(msg, 'photo', None):
                    await msg.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
                else:
                    await msg.edit_caption(text, parse_mode=parse_mode, reply_markup=reply_markup)
                return
            except Exception:
                # pass through to fallback
                pass
        # Final fallback: send a new message in the same chat so admin still sees confirmation
        try:
            await callback.message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception:
            # If even sending fails, raise so the caller can handle/log it
            raise


# ============== Main Menu Handlers ==============

@router.callback_query(F.data == "admin_payments")
async def admin_payments_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show payment management menu"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['payment']} *Payment Management*\n\n"
        "Choose an option to manage payments:",
        parse_mode='Markdown',
        reply_markup=AdminPaymentsKeyboard.get_payment_management()
    )
    await callback.answer()


# ============== View Pending Payments ==============

@router.callback_query(F.data == "admin_payments_pending")
async def admin_payments_pending_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show pending payments"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        pending_payments = await payment_repo.get_pending_payments(limit=50)
        
        # Fetch user info for each payment
        payments_with_users = []
        for payment in pending_payments:
            user = await user_repo.get_user(payment.user_id)
            # Add user attributes to payment for keyboard
            payment.user_first_name = user.first_name if user else "Unknown"
            payment.user_username = user.username if user else None
            payments_with_users.append(payment)
    
    if not payments_with_users:
        await safe_update_admin_message(
            callback,
            f"✅ *No Pending Payments*\n\nAll payments have been processed.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    # Calculate totals
    total_amount = sum(p.amount for p in payments_with_users)
    
    pending_text = (
        f"{EMOJIS['pending']} *Pending Payments*\n\n"
        f"📊 *Summary:*\n"
        f"• Count: {len(payments_with_users)}\n"
        f"• Total Amount: ETB{total_amount:.2f}\n\n"
    )
    
    await safe_update_admin_message(
        callback,
        pending_text,
        parse_mode='Markdown',
        reply_markup=AdminPaymentsKeyboard.get_pending_payments_keyboard(payments_with_users)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_payments_pending_page_"))
async def admin_payments_pending_page_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle pagination for pending payments"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    page = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        pending_payments = await payment_repo.get_pending_payments(limit=50)
        
        # Fetch user info for each payment
        payments_with_users = []
        for payment in pending_payments:
            user = await user_repo.get_user(payment.user_id)
            payment.user_first_name = user.first_name if user else "Unknown"
            payment.user_username = user.username if user else None
            payments_with_users.append(payment)
    
    await callback.message.edit_text(
        f"{EMOJIS['pending']} *Pending Payments*\n\n"
        f"Select a payment to review:",
        parse_mode='Markdown',
        reply_markup=AdminPaymentsKeyboard.get_pending_payments_keyboard(payments_with_users, page=page)
    )
    await callback.answer()


# ============== View All Payments ==============

@router.callback_query(F.data == "admin_payments_all")
async def admin_payments_all_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show all payments with filters"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJIS['list']} *All Payments*\n\n"
        f"Filter payments by status:",
        parse_mode='Markdown',
        reply_markup=AdminPaymentsKeyboard.get_payment_filter_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_"))
async def admin_payments_filter_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle payment filter selection"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    filter_type = callback.data.split("_")[-1]
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        all_payments = []
        
        if filter_type == 'pending':
            all_payments = await payment_repo.get_pending_payments(limit=100)
        else:
            # Get all payments and filter
            payments = []
            users = await user_repo.get_all_users(limit=500)
            for user in users:
                user_payments = await payment_repo.get_user_payments(user.user_id)
                payments.extend(user_payments)
            
            if filter_type == 'approved':
                all_payments = [p for p in payments if p.status == 'approved']
            elif filter_type == 'rejected':
                all_payments = [p for p in payments if p.status == 'rejected']
            elif filter_type == 'today':
                today = datetime.utcnow().date()
                all_payments = [p for p in payments if p.created_at.date() == today]
            elif filter_type == 'week':
                week_ago = datetime.utcnow() - timedelta(days=7)
                all_payments = [p for p in payments if p.created_at > week_ago]
            elif filter_type == 'month':
                month_ago = datetime.utcnow() - timedelta(days=30)
                all_payments = [p for p in payments if p.created_at > month_ago]
        
        # Fetch user info for each payment
        payments_with_users = []
        for payment in all_payments:
            user = await user_repo.get_user(payment.user_id)
            payment.user_first_name = user.first_name if user else "Unknown"
            payment.user_username = user.username if user else None
            payments_with_users.append(payment)
    
    status_text = filter_type.capitalize()
    
    if not payments_with_users:
        await callback.message.edit_text(
            f"🔍 *No {status_text} Payments*\n\n"
            f"No {filter_type} payments found.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    # Calculate totals
    total_amount = sum(p.amount for p in payments_with_users)
    
    filter_text = (
        f"{EMOJIS['list']} *{status_text} Payments*\n\n"
        f"📊 *Summary:*\n"
        f"• Count: {len(payments_with_users)}\n"
        f"• Total Amount: ETB{total_amount:.2f}\n\n"
    )
    
    await callback.message.edit_text(
        filter_text,
        parse_mode='Markdown',
        reply_markup=AdminPaymentsKeyboard.get_pending_payments_keyboard(payments_with_users)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_payments_stats")
async def admin_payments_stats_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show revenue statistics"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    stats_text = await get_revenue_stats_text(30)
    
    await callback.message.edit_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await callback.answer()


# ============== View Payment Details ==============

@router.callback_query(F.data.startswith("admin_payment_view_"))
async def admin_payment_view_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View a specific payment"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment = await payment_repo.get_payment(payment_id)
        
        if not payment:
            await callback.message.edit_text(
                "❌ Payment not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        user = await user_repo.get_user(payment.user_id)
        if not user:
            await callback.message.edit_text(
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        username = f"@{user.username}" if user.username else f"ID: {payment.user_id}"
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        
        payment_text = (
            f"{EMOJIS['payment']} *Payment #{payment.payment_id}*\n\n"
            f"👤 *User:* {username}\n"
            f"📛 *Name:* {name}\n"
            f"🆔 *User ID:* `{payment.user_id}`\n\n"
            f"💵 *Amount:* ETB{payment.amount:.2f}\n"
            f"📅 *Subscription:* {payment.subscription_days} days\n"
            f"📊 *Status:* {payment.status.capitalize()}\n"
            f"⏰ *Created:* {payment.created_at.strftime('%d %b %Y %H:%M')}\n"
        )
        
        if payment.approved_by:
            approver = await user_repo.get_user(payment.approved_by)
            approver_name = f"@{approver.username}" if approver and approver.username else f"ID: {payment.approved_by}"
            payment_text += f"\n✅ *Approved By:* {approver_name}\n"
            payment_text += f"⏰ *Approved At:* {payment.approved_at.strftime('%d %b %Y %H:%M') if payment.approved_at else 'N/A'}\n"
        
        if payment.rejected_reason:
            payment_text += f"\n❌ *Rejected Reason:*\n{payment.rejected_reason}\n"
        
        if payment.transaction_id:
            payment_text += f"\n🔄 *Transaction ID:* {payment.transaction_id}\n"
        
        if payment.notes:
            payment_text += f"\n📝 *Notes:* {payment.notes}\n"
        
        await safe_update_admin_message(
            callback,
            payment_text,
            parse_mode='Markdown',
            reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id, payment.status)
        )
    
    await callback.answer()


# ============== View Payment Screenshot ==============

@router.callback_query(F.data.startswith("admin_payment_screenshot_"))
async def admin_payment_screenshot_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View payment screenshot"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        payment = await payment_repo.get_payment(payment_id)
        
        if not payment:
            await callback.answer("Payment not found", show_alert=True)
            return
        
        if not payment.screenshot_file_id:
            await callback.answer("No screenshot available", show_alert=True)
            return
        
        try:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=payment.screenshot_file_id,
                caption=f"📸 Screenshot for Payment #{payment_id}",
                reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id, payment.status)
            )
        except Exception as e:
            await callback.answer(f"Error loading screenshot: {str(e)}", show_alert=True)
    
    await callback.answer()


# ============== View Payment User ==============

@router.callback_query(F.data.startswith("admin_payment_user_"))
async def admin_payment_user_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """View user who made the payment"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment = await payment_repo.get_payment(payment_id)
        if not payment:
            await callback.message.edit_text(
                "❌ Payment not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        user = await user_repo.get_user(payment.user_id)
        if not user:
            await callback.message.edit_text(
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        user_text = (
            f"{EMOJIS['user']} *Payment User*\n\n"
            f"🆔 *ID:* `{user.user_id}`\n"
            f"👤 *Username:* @{user.username if user.username else 'N/A'}\n"
            f"📛 *Name:* {user.first_name or ''} {user.last_name or ''}\n"
            f"📅 *Joined:* {user.created_at.strftime('%d %b %Y') if user.created_at else 'N/A'}\n"
            f"🚫 *Blocked:* {'Yes' if user.blocked else 'No'}\n"
        )
        
        await safe_update_admin_message(
            callback,
            user_text,
            parse_mode='Markdown',
            reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id, payment.status)
        )
    
    await callback.answer()


# ============== Approve Payment ==============

@router.callback_query(F.data.startswith("admin_payment_approve_"))
async def admin_payment_approve_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show approve confirmation for payment"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment = await payment_repo.get_payment(payment_id)
        if not payment:
            await callback.message.edit_text(
                "❌ Payment not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        user = await user_repo.get_user(payment.user_id)
        username = f"@{user.username}" if user and user.username else f"ID: {payment.user_id}"
    
    # Safely edit the message: if this callback was triggered from a photo message
    # editing text will fail. Fallback to editing caption or sending a new message.
    approve_text = (
        f"{EMOJIS['approve']} *Approve Payment #{payment_id}*\n\n"
        f"User: {username}\n"
        f"Amount: ETB{payment.amount:.2f}\n"
        f"Subscription: {payment.subscription_days} days\n\n"
        f"⚠️ *This will activate the user's subscription.*\n\n"
        f"Confirm approval?"
    )

    # Use safe helper to edit caption/text or fallback to sending a new message
    await safe_update_admin_message(
        callback,
        approve_text,
        parse_mode='Markdown',
        reply_markup=AdminPaymentsKeyboard.get_approve_confirmation_keyboard(payment_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_approve_payment_"))
async def confirm_approve_payment_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Confirm and process payment approval"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        try:
            result = await payment_service.approve_payment(payment_id, callback.from_user.id)

            # Safe values from service result
            amount = float(result.get('amount') or 0.0)

            # Log action
            await log_admin_action(
                callback.from_user.id,
                "Approve Payment",
                f"Approved payment #{payment_id} for ETB{amount:.2f}"
            )

            # Notify user (best-effort)
            try:
                await callback.bot.send_message(
                    chat_id=result['user_id'],
                    text=(
                        f"✅ *Payment Approved!*\n\n"
                        f"Your payment of ETB{amount:.2f} has been approved.\n"
                        f"🎫 Subscription activated for {result['subscription_days']} days.\n\n"
                        f"Payment ID: #{result['payment_id']}\n"
                        f"Enjoy learning! 📚"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                # Do not fail approval if notification to user cannot be delivered
                print(f"Failed to notify user: {e}")

            # Update admin message safely, removing inline buttons
            await safe_update_admin_message(
                callback,
                (
                    f"✅ *Payment Approved*\n\n"
                    f"Payment #{payment_id} has been approved.\n"
                    f"User {result.get('user_id')} has been notified."
                ),
                parse_mode='Markdown',
                reply_markup=None
            )

        except Exception as e:
            err_text = str(e)
            # Try to present error to admin but keep the action keyboard so they can retry
            await safe_update_admin_message(
                callback,
                f"❌ *Approval Failed*\n\nError: {err_text}",
                parse_mode='Markdown',
                reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id)
            )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_approve_payment")
async def cancel_approve_payment_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Cancel payment approval"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await safe_update_admin_message(
        callback,
        f"◀️ *Approval Cancelled*\n\nThe payment was not approved.",
        parse_mode='Markdown',
        reply_markup=None
    )
    await callback.answer()


# ============== Reject Payment ==============

@router.callback_query(F.data.startswith("admin_payment_reject_"))
async def admin_payment_reject_callback(callback: types.CallbackQuery, state: FSMContext,
                                         is_admin: bool = False):
    """Start payment rejection process"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    await callback.message.edit_text(
        f"❌ *Reject Payment #{payment_id}*\n\n"
        f"Please provide a reason for rejection:\n\n"
        f"Common reasons:\n"
        f"• Screenshot unclear\n"
        f"• Wrong amount paid\n"
        f"• Invalid transaction ID\n"
        f"• Duplicate payment\n\n"
        f"Type the reason below (or /cancel to abort):",
        parse_mode='Markdown'
    )
    
    await state.update_data(payment_id=payment_id)
    await state.set_state(PaymentStates.waiting_for_reject_reason)
    await callback.answer()


@router.message(StateFilter(PaymentStates.waiting_for_reject_reason))
async def handle_reject_reason(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Handle payment rejection reason"""
    if not is_admin:
        return
    
    if message.text == "/cancel":
        await message.answer(
            f"◀️ *Rejection Cancelled*\n\n"
            f"The payment was not rejected.",
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    reason = message.text.strip()
    
    if len(reason) < 5:
        await message.answer(
            "❌ Reason is too short (minimum 5 characters). Please provide a detailed reason:"
        )
        return
    
    data = await state.get_data()
    payment_id = data['payment_id']
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        try:
            result = await payment_service.reject_payment(
                payment_id=payment_id,
                admin_id=message.from_user.id,
                reason=reason
            )
            
            # Log action
            await log_admin_action(
                message.from_user.id,
                "Reject Payment",
                f"Rejected payment #{payment_id}: {reason}"
            )
            
            # Notify user
            try:
                await message.bot.send_message(
                    chat_id=result['user_id'],
                    text=(
                        f"❌ *Payment Rejected*\n\n"
                        f"Your payment has been rejected.\n"
                        f"📝 Reason: {reason}\n\n"
                        f"Payment ID: #{result['payment_id']}\n"
                        f"Amount: ETB{result['amount']:.2f}\n\n"
                        f"Please contact support or upload a valid payment screenshot."
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Failed to notify user: {e}")
            
            await message.answer(
                f"✅ *Payment Rejected*\n\n"
                f"Payment #{payment_id} has been rejected.\n"
                f"User has been notified.\n\n"
                f"*Reason:* {reason}",
                parse_mode='Markdown',
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            
        except Exception as e:
            await message.answer(
                f"❌ *Rejection Failed*\n\n"
                f"Error: {str(e)}",
                parse_mode='Markdown',
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("confirm_reject_payment_"))
async def confirm_reject_payment_callback(callback: types.CallbackQuery, state: FSMContext,
                                            is_admin: bool = False):
    """Handle confirmed rejection with inline button"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # This is handled by the FSM flow
    await callback.answer()


# ============== Add Note to Payment ==============

@router.callback_query(F.data.startswith("admin_payment_note_"))
async def admin_payment_note_callback(callback: types.CallbackQuery, state: FSMContext,
                                       is_admin: bool = False):
    """Start adding note to payment"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    await callback.message.edit_text(
        f"📝 *Add Note to Payment #{payment_id}*\n\n"
        f"Enter the note:\n\n"
        f"Press /skip to leave empty.",
        parse_mode='Markdown'
    )
    
    await state.update_data(payment_id=payment_id)
    await state.set_state(PaymentStates.waiting_for_note)
    await callback.answer()


@router.message(StateFilter(PaymentStates.waiting_for_note), F.text == "/skip")
async def skip_note(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Skip adding note"""
    if not is_admin:
        return
    
    await message.answer(
        f"◀️ *Note Cancelled*\n\n"
        f"No note was added.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    await state.clear()


@router.message(StateFilter(PaymentStates.waiting_for_note))
async def handle_note(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Handle payment note"""
    if not is_admin:
        return
    
    data = await state.get_data()
    payment_id = data['payment_id']
    note = message.text.strip()
    
    async for session in get_db():
        from sqlalchemy import update
        from app.db.models import Payment
        
        await session.execute(
            update(Payment).where(Payment.payment_id == payment_id).values(notes=note)
        )
        await session.commit()
        
        await log_admin_action(
            message.from_user.id,
            "Add Payment Note",
            f"Added note to payment #{payment_id}: {note[:100]}"
        )
    
    await message.answer(
        f"✅ *Note Added*\n\n"
        f"Note has been added to payment #{payment_id}.",
        parse_mode='Markdown',
        reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
    )
    
    await state.clear()


# ============== Approve All Pending ==============

@router.callback_query(F.data == "admin_payments_approve_all")
async def admin_payments_approve_all_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Approve all pending payments"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        pending_payments = await payment_repo.get_pending_payments(limit=100)
        
        if not pending_payments:
            await callback.message.edit_text(
                f"✅ *No Pending Payments*\n\n"
                f"There are no pending payments to approve.",
                parse_mode='Markdown',
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        approved_count = 0
        errors = []
        
        for payment in pending_payments:
            try:
                await payment_service.approve_payment(payment.payment_id, callback.from_user.id)
                approved_count += 1
                
                # Notify user
                try:
                    await callback.bot.send_message(
                        chat_id=payment.user_id,
                        text=(
                            f"✅ *Payment Approved!*\n\n"
                            f"Your payment of ETB{payment.amount:.2f} has been approved.\n"
                            f"🎫 Subscription activated for {payment.subscription_days} days."
                        ),
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass
                    
            except Exception as e:
                errors.append(f"Payment #{payment.payment_id}: {str(e)}")
        
        # Log action
        await log_admin_action(
            callback.from_user.id,
            "Approve All Payments",
            f"Approved {approved_count} payments"
        )
        
        result_text = (
            f"✅ *Bulk Approval Complete*\n\n"
            f"• Approved: {approved_count}\n"
            f"• Failed: {len(errors)}\n"
        )
        
        if errors:
            result_text += f"\n*Errors:*\n"
            for error in errors[:5]:
                result_text += f"• {error}\n"
        
        await callback.message.edit_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
        )
    
    await callback.answer()


# Import inline keyboard button
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ============== INLINE SCREENSHOT REVIEW (NEW - Core Feature) ==============

async def notify_user_payment_approved(bot, user_id: int, payment_id: int,
                                        amount: float, subscription_days: int | None):
    """Send notification to user when payment is approved"""
    # Handle lifetime payments (subscription_days = None)
    sub_text = "Lifetime" if subscription_days is None else f"{subscription_days} days"

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ *Payment Approved!*\n\n"
                f"🎉 Great news! Your payment has been approved.\n\n"
                f"📋 *Payment Details:*\n"
                f"• Payment ID: #{payment_id}\n"
                f"• Amount: {amount:.2f}\n"
                f"• Subscription: {sub_text}\n\n"
                f"🎫 You now have full access to all quiz levels!\n"
                f"Use /quiz to start learning.\n\n"
                f"📚 Good luck with your studies!"
            ),
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Failed to notify user {user_id} about payment approval: {e}")


async def notify_user_payment_rejected(bot, user_id: int, payment_id: int,
                                        amount: float, reason: str):
    """Send notification to user when payment is rejected"""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ *Payment Rejected*\n\n"
                f"Unfortunately, your payment has been rejected.\n\n"
                f"📋 *Payment Details:*\n"
                f"• Payment ID: #{payment_id}\n"
                f"• Amount: ETB{amount:.2f}\n\n"
                f"📝 *Reason:* {reason}\n\n"
                f"🔄 *What to do:*\n"
                f"1. Upload a clear screenshot of your payment\n"
                f"2. Make sure the transaction ID is visible\n"
                f"3. Verify the correct amount was paid\n\n"
                f"💬 Contact @admin if you need assistance."
            ),
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Failed to notify user {user_id} about payment rejection: {e}")


@router.callback_query(F.data.startswith("admin_payment_view_"))
async def admin_payment_view_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """
    View payment details AND show screenshot inline with approve/reject buttons.
    
    This is the MAIN payment review screen - shows screenshot with inline actions.
    """
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment = await payment_repo.get_payment(payment_id)
        
        if not payment:
            await callback.message.edit_text(
                "❌ Payment not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        user = await user_repo.get_user(payment.user_id)
        if not user:
            await callback.message.edit_text(
                "❌ User not found!",
                reply_markup=AdminKeyboard.get_back_to_admin_keyboard()
            )
            await callback.answer()
            return
        
        # Format user info
        username = f"@{user.username}" if user.username else f"ID: {payment.user_id}"
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if not name:
            name = "Unknown"
        
        # Build payment info text
        payment_text = (
            f"💰 *Payment #{payment.payment_id}*\n\n"
            f"👤 *User Details*\n"
            f"• Name: {name}\n"
            f"• Username: {username}\n"
            f"• User ID: `{payment.user_id}`\n\n"
            f"💵 *Payment Details*\n"
            f"• Amount: {payment.amount:.2f}\n"
            f"• Subscription: {payment.subscription_days} days\n"
            f"• Status: ⏳ Pending\n"
            f"• Created: {payment.created_at.strftime('%d %b %Y %H:%M')}\n"
        )
        
        # Check if we have a screenshot
        if payment.screenshot_file_id:
            # Send screenshot with inline keyboard
            try:
                await callback.message.delete()
                await callback.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=payment.screenshot_file_id,
                    caption=payment_text,
                    parse_mode='Markdown',
                    reply_markup=AdminPaymentsKeyboard.get_screenshot_review_inline_keyboard(payment_id)
                )
            except Exception as e:
                # If can't send photo, show text with action buttons
                await callback.message.edit_text(
                    payment_text + f"\n❌ Could not load screenshot: {str(e)}",
                    parse_mode='Markdown',
                    reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id, payment.status)
                )
        else:
            # No screenshot available
            await callback.message.edit_text(
                payment_text + f"\n⚠️ No screenshot available for this payment.",
                parse_mode='Markdown',
                reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id, payment.status)
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("review_approve_"))
async def review_approve_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """
    Approve payment directly from screenshot review.
    
    This is the INLINE approve button handler.
    """
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        try:
            # Attempt to approve payment
            result = await payment_service.approve_payment(payment_id, callback.from_user.id)
            
            # Log action
            await log_admin_action(
                callback.from_user.id,
                "Approve Payment (Inline)",
                f"Approved payment #{payment_id} for ETB{result.get('amount', 0)}"
            )
            
            # Notify user
            await notify_user_payment_approved(
                bot=callback.bot,
                user_id=result['user_id'],
                payment_id=result['payment_id'],
                amount=result['amount'],
                subscription_days=result['subscription_days']
            )
            
            # Update message to show approval and remove inline buttons
            await callback.message.edit_caption(
                (
                    f"✅ *Payment #{payment_id} APPROVED*\n\n"
                    f"User {result.get('user_id')} has been notified.\n"
                    f"Full access granted for {result['subscription_days']} days."
                ),
                parse_mode='Markdown',
                reply_markup=None
            )
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if already processed
            if "already been" in error_msg.lower():
                await callback.message.edit_caption(
                    (
                        f"⚠️ *Payment Already Processed*\n\n"
                        f"This payment has already been {error_msg.split('already been ')[1].split('.')[0]}.\n"
                        f"Please check the pending list for updates."
                    ),
                    parse_mode='Markdown',
                    reply_markup=None
                )
            else:
                await callback.answer(f"Error: {error_msg}", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("review_reject_"))
async def review_reject_callback(callback: types.CallbackQuery, state: FSMContext,
                                  is_admin: bool = False):
    """
    Show rejection options when admin clicks Reject from screenshot review.
    """
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    # Show quick rejection reasons keyboard
    await callback.message.edit_caption(
        (
            f"❌ *Reject Payment #{payment_id}*\n\n"
            f"Select a reason or choose 'Custom' to type your own:"
        ),
        parse_mode='Markdown',
        reply_markup=AdminPaymentsKeyboard.get_reject_with_reason_keyboard(payment_id)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("reject_reason_"))
async def reject_reason_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """
    Handle quick rejection with pre-defined reason.
    """
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Parse: reject_reason_{payment_id}_{reason_code}
    parts = callback.data.split("_")
    payment_id = int(parts[3])
    reason_code = parts[4]
    
    # Map reason codes to full reasons
    reason_map = {
        "unclear_screenshot": "Screenshot is unclear. Please upload a clearer image showing transaction details.",
        "wrong_amount": "Incorrect amount paid. Please verify the payment amount.",
        "no_transaction_id": "Transaction ID not visible. Screenshot must show transaction reference.",
        "duplicate_payment": "Duplicate payment detected. This appears to be a duplicate."
    }
    
    reason = reason_map.get(reason_code, f"Rejected: {reason_code}")
    
    # Process the rejection
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment_service = PaymentService(payment_repo, user_repo)
        
        try:
            result = await payment_service.reject_payment(
                payment_id=payment_id,
                admin_id=callback.from_user.id,
                reason=reason
            )
            
            # Log action
            await log_admin_action(
                callback.from_user.id,
                "Reject Payment (Quick)",
                f"Rejected payment #{payment_id}: {reason}"
            )
            
            # Notify user
            await notify_user_payment_rejected(
                bot=callback.bot,
                user_id=result['user_id'],
                payment_id=result['payment_id'],
                amount=result['amount'],
                reason=reason
            )
            
            # Update message
            await callback.message.edit_caption(
                (
                    f"❌ *Payment #{payment_id} REJECTED*\n\n"
                    f"User has been notified.\n"
                    f"Reason: {reason}"
                ),
                parse_mode='Markdown',
                reply_markup=None
            )
            
        except Exception as e:
            await callback.answer(f"Error: {str(e)}", show_alert=True)
    
    await callback.answer()
