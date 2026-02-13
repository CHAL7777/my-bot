# Contact Message Admin View Guide

This document explains how administrators receive and view user contact messages in the Telegram Quiz Bot.

---

## 📊 Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER SENDS CONTACT MESSAGE                       │
│                              /contact or 📞 Contact                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    USER SELECTS CATEGORY (FSM Flow)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │💳 Payment    │  │🐛 Quiz Error │  │🔒 Access     │  │💡 General    │ │
│  │   Issues     │  │              │  │   Problems   │  │   Questions  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      USER TYPES MESSAGE TEXT                             │
│                  (FSM State: waiting_for_message)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SAVE TO DATABASE                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Table: contact_messages                                         │   │
│  │ • ticket_id: SUP-XXXX (e.g., SUP-1001)                          │   │
│  │ • user_id, category, message_text                               │   │
│  │ • status: 'open'                                                │   │
│  │ • created_at: timestamp                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│  SEND CONFIRMATION TO USER    │   │  NOTIFY ALL ADMINS (DM)       │
│  ┌─────────────────────────┐  │   │  ┌─────────────────────────┐  │
│  │ ✅ Your support request │  │   │  │ 📬 New Support Ticket   │  │
│  │    has been received    │  │   │  │                        │  │
│  │ 🎫 Ticket ID: SUP-1001  │  │   │  │ 🎫 Ticket ID: SUP-1001  │  │
│  │ 📁 Category: Payment    │  │   │  │ 📁 Category: Payment    │  │
│  │ ⏰ Response within 24h  │  │   │  │ 👤 User: John (12345)   │  │
│  └─────────────────────────┘  │   │  │ 🆔 User ID: 12345        │  │
└───────────────────────────────┘   │  │ 📧 Username: @johndoe     │  │
                                    │  │ 📝 Message preview...     │  │
                                    │  │ 📋 Quick reply command    │  │
                                    │  └─────────────────────────┘  │
                                    │              │                │
                                    │              ▼                │
                                    │   ┌─────────────────────┐    │
                                    │   │ For each admin in   │    │
                                    │   │ settings.ADMIN_IDS  │    │
                                    │   └─────────────────────┘    │
                                    └──────────────────────────────┘
```

---

## 📨 Admin Notification Message Format

When a user sends a contact message, admins receive a DM with this exact format:

```markdown
📬 *New Support Ticket*

🎫 *Ticket ID:* `SUP-1001`
📁 *Category:* 💳 Payment Issues
👤 *User:* John
🆔 *User ID:* `123456789`
📧 *Username:* @johndoe
⏰ *Time:* 15 Jan 2024 14:30

━━━━━━━━━━━━━━━━━━━━
📝 *Message:*
━━━━━━━━━━━━━━━━━━━━

I made a payment of $25 for lifetime access yesterday but my premium 
status is still not activated. The transaction ID is TXN12345. Can 
you please check?

━━━━━━━━━━━━━━━━━━━━

📋 *Actions:*
• Reply: `/reply SUP-1001 <your reply>`
• View all: /admin_messages
• Close: /close SUP-1001
```

---

## 🖥️ Admin Dashboard Commands

### 1. View All Pending Messages
```bash
/admin_messages
```

**Response:**
```markdown
📬 *Contact Messages*

📊 *Open Tickets:* 5
📋 *Showing:* Last 20 messages

━━━━━━━━━━━━━━━━━━━━

🆕 *SUP-1001* | PAYMENT
👤 John (ID: 123456789)
⏰ 15 Jan 14:30
📝 I made a payment of $25 for lifetime access...

━━━━━━━━━━━━━━━━━━━━

🆕 *SUP-1002* | QUIZ ERROR
👤 Jane (ID: 987654321)
⏰ 15 Jan 14:15
📝 Question #42 has wrong answer option...

━━━━━━━━━━━━━━━━━━━━

💡 *Commands:*
• `/reply <ticket_id> <message>` - Reply to ticket
• `/view <ticket_id>` - View full message
• `/close <ticket_id>` - Close ticket
```

### 2. View Full Message Details
```bash
/view SUP-1001
```

**Response:**
```markdown
📬 *Ticket Details*

🆕 *Status:* OPEN
🎫 *Ticket ID:* `SUP-1001`

━━━━━━━━━━━━━━━━━━━━

👤 *User Information:*
• Name: John Doe
• User ID: `123456789`
• Username: @johndoe

━━━━━━━━━━━━━━━━━━━━

📁 *Category:* Payment Issues
⏰ *Created:* 15 Jan 2024 14:30
💬 *Replied:* Not yet
🔒 *Closed:* Not yet

━━━━━━━━━━━━━━━━━━━━

📝 *Original Message:*
━━━━━━━━━━━━━━━━━━━━

I made a payment of $25 for lifetime access yesterday but my premium 
status is still not activated. The transaction ID is TXN12345. Can 
you please check?

━━━━━━━━━━━━━━━━━━━━

💬 *Admin Reply:*
━━━━━━━━━━━━━━━━━━━━

(No reply yet)

━━━━━━━━━━━━━━━━━━━━

💡 *Quick Actions:*
• Reply: `/reply SUP-1001 <text>`
• Close: `/close SUP-1001`
```

### 3. Reply to User
```bash
/reply SUP-1001 Your payment has been verified and premium activated!
```

**Admin Response:**
```markdown
✅ *Reply Sent*

📤 *To:* John (ID: 123456789)
🎫 *Ticket ID:* `SUP-1001`
📨 *Notification:* ✅ User notified

━━━━━━━━━━━━━━━━━━━━

📝 *Your reply:*
Your payment has been verified and premium activated!
```

**User Response (in their chat):**
```markdown
📬 *Admin Reply - SUP-1001*

━━━━━━━━━━━━━━━━━━━━

Your payment has been verified and premium activated!

━━━━━━━━━━━━━━━━━━━━

👤 *Replied by:* Admin
⏰ *Time:* 15 Jan 2024 14:35

💡 Need more help? Send a new message using /contact
```

### 4. Close Ticket
```bash
/close SUP-1001
```

**Response:**
```markdown
✅ *Ticket Closed*

🎫 *Ticket ID:* `SUP-1001`
👤 *User:* 123456789
📁 *Category:* Payment Issues

This ticket is now closed.
```

### 5. Message Statistics
```bash
/message_stats
```

**Response:**
```markdown
📊 *Contact Message Statistics*

━━━━━━━━━━━━━━━━━━━━

📈 *Overview:*
• Open tickets: *5*
• Messages this week: *12*

━━━━━━━━━━━━━━━━━━━━

📁 *By Category:*
• 💳 Payment: 5
• 🐛 Quiz Errors: 3
• 🔒 Access: 2
• 💡 General: 1
• 💬 Feedback: 1

━━━━━━━━━━━━━━━━━━━━

💡 *Commands:*
• /admin_messages - View messages
• /reply <id> <text> - Reply
```

---

## 📋 Category Types

| Category | Emoji | Use Case |
|----------|-------|----------|
| Payment | 💳 | Subscriptions, payments, refunds |
| Quiz Error | 🐛 | Bugs, incorrect answers |
| Access | 🔒 | Account, login, permissions |
| General | 💡 | How to use features |
| Feedback | 💬 | Suggestions, improvements |

---

## 🔄 Ticket Status Flow

```
    ┌─────────┐
    │  OPEN   │ ← New message received
    └────┬────┘
         │
         │ /reply <id> <text>
         ▼
    ┌─────────┐
    │ REPLIED │ ← Admin sent response
    └────┬────┘
         │
         │ /close <id>
         ▼
    ┌─────────┐
    │ CLOSED  │ ← Ticket resolved
    └─────────┘
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE contact_messages (
    message_id INT PRIMARY KEY AUTO_INCREMENT,
    ticket_id VARCHAR(20) UNIQUE NOT NULL,      -- e.g., SUP-1001
    user_id BIGINT NOT NULL,                     -- Telegram user ID
    category ENUM('payment', 'quiz_error', 'access', 'general', 'feedback') NOT NULL,
    subject VARCHAR(200),                        -- Optional subject
    message_text TEXT NOT NULL,                  -- Full message
    status ENUM('open', 'replied', 'closed') DEFAULT 'open',
    admin_reply TEXT,                            -- Admin's response
    replied_by BIGINT,                           -- Admin who replied
    created_at DATETIME DEFAULT NOW(),
    replied_at DATETIME,
    closed_at DATETIME,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX idx_contact_ticket_id ON contact_messages(ticket_id);
CREATE INDEX idx_contact_user ON contact_messages(user_id, created_at);
CREATE INDEX idx_contact_status ON contact_messages(status, created_at);
```

---

## ⏱️ Rate Limiting

- Users can only send **1 contact message per 10 minutes**
- Prevents spam abuse
- Users see countdown timer if rate-limited

---

## 📱 User Experience Flow

```
1. User taps "📞 Contact" button
   ↓
2. Selects category
   ↓
3. Types message
   ↓
4. Receives confirmation with Ticket ID
   ↓
5. Waits for admin reply (up to 24 hours)
   ↓
6. Receives admin reply directly in chat
```

---

## 🔐 Admin Security

- All admin commands require `is_admin` middleware verification
- Only users in `settings.ADMIN_IDS` can access admin features
- All actions are logged

---

## 🛠️ Configuration

In `app/config.py`:

```python
class Settings:
    # Admin Telegram User IDs
    ADMIN_IDS = [123456789, 987654321]
    
    # Contact rate limit in minutes
    CONTACT_RATE_LIMIT_MINUTES = 10
```

---

## 📊 Summary

| Aspect | Details |
|--------|---------|
| **Notification** | Instant DM to all admins |
| **Ticket ID Format** | SUP-XXXX (e.g., SUP-1001) |
| **Categories** | Payment, Quiz Error, Access, General, Feedback |
| **Admin Commands** | /admin_messages, /view, /reply, /close, /message_stats |
| **User Confirmation** | Yes, with Ticket ID and expected response time |
| **Rate Limiting** | 10 minutes between messages |
| **Storage** | MySQL database (contact_messages table) |

