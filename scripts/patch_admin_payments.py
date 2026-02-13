# This is a patch file for app/handlers/admin_payments.py
# Replace the confirm_approve_payment_callback function with this improved version:

"""
Patch for admin_payments.py - Add strict screenshot validation before payment approval

Location: app/handlers/admin_payments.py
Function: confirm_approve_payment_callback

Replace the existing function with this SECURE version:
"""

SECURE_CONFIRM_APPROVE_PAYMENT_FUNCTION = '''
@router.callback_query(F.data.startswith("confirm_approve_payment_"))
async def confirm_approve_payment_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """
    Confirm and process payment approval with STRICT validation.
    
    Security checks performed:
    1. Payment must exist
    2. Payment must be pending (idempotency)
    3. Screenshot MUST exist (required for approval)
    4. Admin ID must be provided
    """
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[-1])
    
    async for session in get_db():
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)
        
        payment = await payment_repo.get_payment(payment_id)
        
        # VALIDATION 1: Payment exists
        if not payment:
            await safe_update_admin_message(
                callback,
                f"❌ *Payment Not Found*\\n\\n"
                f"Payment #{payment_id} does not exist in the database.",
                parse_mode='Markdown',
                reply_markup=None
            )
            await callback.answer()
            return
        
        # VALIDATION 2: Payment is pending (idempotency check)
        if payment.status != 'pending':
            status_emoji = "✅" if payment.status == 'approved' else "❌"
            await safe_update_admin_message(
                callback,
                f"⚠️ *Payment Already {payment.status.capitalize()}*\\n\\n"
                f"{status_emoji} Payment #{payment_id} has already been "
                f"{payment.status}.\\n"
                f"Cannot re-{payment.status} an already processed payment.\\n\\n"
                f"• Approved by: {payment.approved_by or 'N/A'}\\n"
                f"• Approved at: {payment.approved_at.strftime('%d %b %Y %H:%M') if payment.approved_at else 'N/A'}",
                parse_mode='Markdown',
                reply_markup=None
            )
            await callback.answer()
            return
        
        # VALIDATION 3: Screenshot MUST exist (CRITICAL SECURITY CHECK)
        if not payment.screenshot_file_id:
            await safe_update_admin_message(
                callback,
                (
                    f"🛡️ *SECURITY ALERT: No Screenshot*\\n\\n"
                    f"Payment #{payment_id} has no payment screenshot attached.\\n\\n"
                    f"⚠️ *Approval Blocked:* Cannot approve payment without proof of payment.\\n\\n"
                    f"Please ask the user to upload a clear screenshot of their payment "
                    f"confirmation before proceeding.\\n\\n"
                    f"Required screenshot must show:\\n"
                    f"• Transaction ID / Reference number\\n"
                    f"• Amount paid\\n"
                    f"• Date and time\\n"
                    f"• Payment status (Success/Completed)"
                ),
                parse_mode='Markdown',
                reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id, payment.status)
            )
            await callback.answer()
            return
        
        # All validations passed - proceed with approval
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
                        f"✅ *Payment Approved!*\\n\\n"
                        f"Your payment of ETB{amount:.2f} has been approved.\\n"
                        f"🎫 Subscription activated for {result['subscription_days']} days.\\n\\n"
                        f"Payment ID: #{result['payment_id']}\\n"
                        f"Enjoy learning! 📚"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Failed to notify user: {e}")

            # Update admin message safely, removing inline buttons
            await safe_update_admin_message(
                callback,
                (
                    f"✅ *Payment Approved Successfully*\\n\\n"
                    f"Payment #{payment_id} has been approved.\\n"
                    f"User {result.get('user_id')} has been notified.\\n\\n"
                    f"💎 Premium access granted!"
                ),
                parse_mode='Markdown',
                reply_markup=None
            )

        except Exception as e:
            err_text = str(e)
            await safe_update_admin_message(
                callback,
                f"❌ *Approval Failed*\\n\\nError: {err_text}",
                parse_mode='Markdown',
                reply_markup=AdminPaymentsKeyboard.get_payment_action_keyboard(payment_id)
            )
    
    await callback.answer()
'''

