# /contact Command Implementation Plan

## Status: IN PROGRESS

## Implementation Steps

### Step 1: Database Model Updates (`app/db/models.py`)
- [x] Add `ticket_id` field with format "SUP-XXXX"
- [x] Change status enum from (new/read/replied/closed) to (open/replied/closed)
- [x] Update ContactMessage model

### Step 2: Repository Updates (`app/repositories/contact_repo.py`)
- [x] Add `generate_ticket_id()` method
- [x] Add `can_send_contact_request()` for rate limiting check
- [x] Update methods for new status values
- [x] Add rate limit methods

### Step 3: Rate Limiting Middleware (`app/middlewares/rate_limit.py`)
- [x] Add contact-specific rate limit: 1 request per 10 minutes
- [x] Add `CONTACT_RATE_LIMIT_MINUTES` constant
- [x] Update middleware to handle contact command

### Step 4: Handler Updates (`app/handlers/start.py`)
- [x] Replace `/contact` command with exact message format from requirements
- [x] Implement ticket ID generation (SUP-XXXX format)
- [x] Show ticket ID in user confirmation
- [x] Add rate limit warning message

### Step 5: Admin Handler Updates (`app/handlers/admin_messages.py`)
- [x] Update admin notification format
- [x] Include User ID, Username, Full message
- [x] Allow admin to reply directly using ticket ID

### Step 6: Keyboard Updates (`app/keyboards/menu.py`)
- [x] Add `get_cancel_contact_keyboard()` method

### Step 7: Migration Script (`scripts/contact_messages_migration.sql`)
- [x] Update SQL migration for new schema

## Summary of Changes

### 1. Database Model (models.py)
- Added `ticket_id` VARCHAR(20) with UNIQUE constraint
- Changed status from `new/read/replied/closed` to `open/replied/closed`
- Replaced `read_at` with `closed_at` field
- Added index on `ticket_id`

### 2. Repository (contact_repo.py)
- `generate_ticket_id()` - Creates ticket IDs like SUP-1001, SUP-1002
- `get_message_by_ticket_id()` - Find by ticket_id
- `can_send_contact_request()` - Rate limiting check
- `get_open_count()` - Count open tickets
- `get_today_count()` - Today's ticket count

### 3. Rate Limiting (rate_limit.py)
- Added `CONTACT_RATE_LIMIT_MINUTES = 10`
- Added 'contact' rate limit: 1 per 10 minutes
- Custom message for contact rate limit

### 4. User Handler (start.py)
- `/contact` command shows exact message from requirements
- FSM-based contact flow with category selection
- User confirmation shows: "✅ Your support request has been received" with Ticket ID
- Ticket ID format: SUP-XXXX

### 5. Admin Handler (admin_messages.py)
- `/admin_messages` - View pending tickets
- `/reply <ticket_id> <message>` - Reply to ticket
- `/view <ticket_id>` - View full ticket details
- `/close <ticket_id>` - Close ticket
- `/message_stats` - Show statistics

### 6. Keyboards (menu.py)
- `get_cancel_contact_keyboard()` - Cancel/back buttons for contact flow

## Usage

### Users:
1. Send `/contact` or tap Contact button
2. See contact information message
3. Select category
4. Type message
5. Receive confirmation with Ticket ID

### Admins:
1. Receive notification when user submits ticket
2. Use `/reply SUP-1001 <response>` to respond
3. User receives reply directly in their chat

## Database Migration
Run: `scripts/contact_messages_migration.sql`

