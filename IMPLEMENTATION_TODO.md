# Payment Approval System Implementation Plan

## Phase 1: Payment Service Enhancements ✅ COMPLETED
- [x] 1.1 Update PaymentService.prevent_duplicate_payments() - check if user is already approved
- [x] 1.2 Update PaymentService.initiate_payment() - prevent approved users from paying again
- [x] 1.3 Update PaymentService.save_payment_screenshot() - better error handling
- [x] 1.4 Add PaymentService.get_payment_eligibility() method

## Phase 2: Payment Repository Improvements ✅ COMPLETED
- [x] 2.1 Add payment_idempotency_check() - prevent duplicate processing
- [x] 2.2 Improve approve_payment() with atomic transactions
- [x] 2.3 Improve reject_payment() with reason validation
- [x] 2.4 Add get_payment_with_user() method for admin review

## Phase 3: Admin Handlers - Inline Screenshot Review ✅ COMPLETED
- [x] 3.1 Rewrite admin_payment_view to sendPhoto with inline keyboard
- [x] 3.2 Add approve/reject buttons directly on screenshot message
- [x] 3.3 Enhance user details display in admin view
- [x] 3.4 Add better notification to users on approval/rejection
- [x] 3.5 Add duplicate approval prevention

## Phase 4: Admin Keyboards ✅ COMPLETED
- [x] 4.1 Update AdminPaymentsKeyboard.get_payment_action_keyboard()
- [x] 4.2 Create inline screenshot review keyboard (get_screenshot_review_inline_keyboard)
- [x] 4.3 Add rejection with quick reasons keyboard (get_reject_with_reason_keyboard)

## Phase 5: User Payment Flow (Existing - Needs Review)
- [x] 5.1 Payment.py already exists - handles user payment flow
- [x] 5.2 SubscriptionMiddleware provides access control

## Phase 6: Access Control Middleware (Existing)
- [x] 6.1 SubscriptionMiddleware checks subscription
- [x] 6.2 User.approved flag already implemented in models

## Phase 7: Quiz Handlers Access Control (Existing)
- [x] 7.1 quiz.py already checks user.approved
- [x] 7.2 Premium difficulty levels blocked for non-subscribed users

## Files Modified:
1. ✅ `app/services/payment_service.py` - Enhanced with one-time payment checks
2. ✅ `app/repositories/payment_repo.py` - Added idempotency and atomic transactions
3. ✅ `app/handlers/admin_payments.py` - Added inline screenshot review handlers
4. ✅ `app/keyboards/admin.py` - Added inline review keyboards

## Testing Checklist:
- [ ] User can't pay twice after approval
- [ ] Admin can view screenshot inline
- [ ] Admin can approve/reject from screenshot message
- [ ] User receives notification on approval
- [ ] User receives notification on rejection with reason
- [ ] Premium difficulty levels blocked for non-approved users
- [ ] Duplicate approval prevented
- [ ] Error messages are clear

## Expected Outcome:
✅ Complete one-time payment model
✅ Admin can review payments with inline screenshot
✅ Consistent access control for premium features
✅ Clear user notifications
✅ Error-safe operations

## Key Features Implemented:

### 1. One-Time Payment Model
- Users can only pay once to unlock all levels
- System checks `user.approved` flag before allowing new payments
- Prevents duplicate payments

### 2. Screenshot-Based Payment
- Users upload payment screenshot via bot
- Screenshot file_id stored for inline display
- Local file path saved for backup

### 3. Admin Review Panel (Inline)
- Admin views payment with screenshot inline using `sendPhoto`
- Approve/Reject buttons directly on the screenshot message
- Quick rejection reasons (unclear screenshot, wrong amount, etc.)
- User details shown alongside screenshot

### 4. Approval Behavior
- Updates payment status to 'approved'
- Marks user as approved = true
- Creates subscription record
- Notifies user of approval

### 5. Rejection Behavior
- Updates payment status to 'rejected'
- Stores rejection reason
- Notifies user with reason and guidance

### 6. Error Safety
- Duplicate approval prevented via idempotency checks
- Missing screenshots handled gracefully
- Clear error messages for users

## Database Schema (Already Exists)
- `users` table with `approved` column
- `payments` table with status, screenshot_file_id, rejected_reason
- `subscriptions` table for tracking access

## Usage:
1. User initiates payment with `/payment`
2. User selects subscription plan
3. User uploads payment screenshot
4. Admin reviews via `/admin_payments` → "Pending Payments"
5. Admin sees screenshot inline with Approve/Reject buttons
6. Admin clicks Approve → user notified and access granted

