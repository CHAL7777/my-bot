# Implementation Plan: Referral System & Multi-Admin Support

## 📋 Overview
This document outlines the implementation plan for:
1. **Referral System** - Allow users to invite friends and earn rewards
2. **Multiple Admin Support** - Database-backed admin management with roles

---

## 🔄 PHASE 1: Database Changes

### 1.1 Update User Model
**File:** `app/db/models.py`

Add new fields to the `User` class:
```python
# Add to User class
referral_code = Column(String(20), unique=True, nullable=True)
referred_by = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
referral_count = Column(Integer, default=0)  # Number of successful referrals

# Add relationship for referred users
referred_users = relationship("User", back_populates="referrer", foreign_keys="[User.referred_by]")
referrer = relationship("User", back_populates="referred_users", foreign_keys="[User.referred_by]")
```

### 1.2 Create Referral Model
**File:** `app/db/models.py`

```python
class Referral(Base):
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    referred_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    status = Column(Enum('pending', 'completed', 'cancelled', name='referral_status'), default='pending')
    reward_claimed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    referrer_user = relationship("User", foreign_keys="[Referral.referrer_id]")
    referred_user = relationship("User", foreign_keys="[Referral.referred_id]")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('referrer_id', 'referred_id', name='unique_referral'),
    )
```

### 1.3 Create TelegramAdmins Model
**File:** `app/db/models.py`

```python
class TelegramAdmin(Base):
    __tablename__ = "telegram_admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    role = Column(Enum('superadmin', 'admin', name='telegram_admin_role'), default='admin')
    is_active = Column(Boolean, default=True)
    added_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_telegram_admin_user_id', 'user_id'),
        Index('idx_telegram_admin_role', 'role'),
    )
```

### 1.4 Create Migration Script
**File:** `scripts/referral_admin_migration.sql`

```sql
-- Add referral fields to users table
ALTER TABLE users ADD COLUMN referral_code VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN referred_by BIGINT NULL;
ALTER TABLE users ADD COLUMN referral_count INT DEFAULT 0;

-- Create referrals table
CREATE TABLE IF NOT EXISTS referrals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    referred_id BIGINT NOT NULL,
    status ENUM('pending', 'completed', 'cancelled') DEFAULT 'pending',
    reward_claimed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_referral (referrer_id, referred_id),
    INDEX idx_referrer (referrer_id),
    INDEX idx_referred (referred_id),
    INDEX idx_status (status)
);

-- Create telegram_admins table
CREATE TABLE IF NOT EXISTS telegram_admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    role ENUM('superadmin', 'admin') DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    added_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_admin_user_id (user_id),
    INDEX idx_admin_role (role)
);
```

---

## 🔧 PHASE 2: Repository Layer

### 2.1 Create Referral Repository
**File:** `app/repositories/referral_repo.py`

```python
class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_referral(self, referrer_id: int, referred_id: int) -> Referral:
        """Create a new referral record"""
    
    async def get_referral_by_users(self, referrer_id: int, referred_id: int) -> Optional[Referral]:
        """Get referral between two users"""
    
    async def complete_referral(self, referral_id: int) -> Referral:
        """Mark referral as completed"""
    
    async def get_user_referrals(self, user_id: int, status: str = None) -> List[Referral]:
        """Get all referrals for a user"""
    
    async def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """Get referral statistics for a user"""
```

### 2.2 Update Admin Repository
**File:** `app/repositories/admin_repo.py`

```python
class TelegramAdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_admin(self, user_id: int) -> Optional[TelegramAdmin]:
        """Get admin by user_id"""
    
    async def create_admin(self, user_id: int, username: str = None, 
                          role: str = 'admin', added_by: int = None) -> TelegramAdmin:
        """Create new admin"""
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin by user_id"""
    
    async def list_admins(self, role: str = None) -> List[TelegramAdmin]:
        """List all admins"""
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
    
    async def is_superadmin(self, user_id: int) -> bool:
        """Check if user is superadmin"""
    
    async def get_admin_role(self, user_id: int) -> Optional[str]:
        """Get admin role"""
```

---

## 🧠 PHASE 3: Service Layer

### 3.1 Create Referral Service
**File:** `app/services/referral_service.py`

```python
class ReferralService:
    def __init__(self, referral_repo: ReferralRepository, 
                 user_repo: UserRepository):
        self.referral_repo = referral_repo
        self.user_repo = user_repo
    
    async def generate_referral_code(self, user_id: int) -> str:
        """Generate unique referral code for user"""
    
    async def get_referral_code(self, user_id: int) -> str:
        """Get user's referral code (create if not exists)"""
    
    async def process_referral(self, referrer_id: int, referred_id: int) -> Dict[str, Any]:
        """Process a referral when new user joins"""
    
    async def get_referral_link(self, user_id: int) -> str:
        """Generate referral link for user"""
    
    async def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's referral statistics"""
    
    async def check_and_grant_reward(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Check if user qualifies for referral reward"""
```

### 3.2 Update Admin Service
**File:** `app/services/admin_service.py`

```python
class AdminService:
    def __init__(self, admin_repo: TelegramAdminRepository):
        self.admin_repo = admin_repo
    
    async def add_admin(self, user_id: int, username: str = None, 
                       role: str = 'admin', added_by: int = None) -> TelegramAdmin:
        """Add new admin"""
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin"""
    
    async def list_admins(self, role: str = None) -> List[Dict[str, Any]]:
        """List all admins with details"""
    
    async def can_manage_admins(self, admin_id: int) -> bool:
        """Check if admin can manage other admins"""
    
    async def can_approve_payments(self, admin_id: int) -> bool:
        """Check if admin can approve payments"""
```

---

## 👑 PHASE 4: Middleware Updates

### 4.1 Update Auth Middleware
**File:** `app/middlewares/auth.py`

Update to check database for admin permissions:

```python
class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        
        # Check if user is admin (from database)
        from app.repositories.admin_repo import TelegramAdminRepository
        from app.db.base import get_db
        
        async for session in get_db():
            admin_repo = TelegramAdminRepository(session)
            is_admin = await admin_repo.is_admin(user_id)
            is_superadmin = await admin_repo.is_superadmin(user_id)
            
            data['is_admin'] = is_admin
            data['is_superadmin'] = is_superadmin
            
            if is_admin:
                role = await admin_repo.get_admin_role(user_id)
                data['admin_role'] = role
```

---

## 🔗 PHASE 5: Handler Updates

### 5.1 Update Start Handler
**File:** `app/handlers/start.py`

Modify `command_start` to handle referral links:

```python
@router.message(CommandStart(deep_link=None))
async def command_start(message: Message, state: FSMContext, 
                       is_admin: bool = False, deep_link: str = None):
    """
    Handle /start command with optional referral code.
    
    Format: /start or /start ref_CODE
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Parse referral code from deep_link
    referral_code = None
    if deep_link and deep_link.startswith('ref_'):
        referral_code = deep_link[4:]  # Remove 'ref_' prefix
    
    async for session in get_db():
        user_repo = UserRepository(session)
        referral_repo = ReferralRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        # Process referral if code provided
        if referral_code:
            referrer_user = await user_repo.get_user_by_referral_code(referral_code)
            if referrer_user and referrer_user.user_id != user_id:
                # Process the referral
                result = await referral_service.process_referral(
                    referrer_user.user_id, user_id
                )
        
        # Register user (existing logic)
        # ...
```

### 5.2 Create Referral Handler
**File:** `app/handlers/referral.py`

```python
from aiogram import Router, types, F
from aiogram.filters import Command

router = Router()

@router.message(Command("referral"))
@router.message(Command("referrals"))
async def referral_command(message: types.Message, is_admin: bool = False):
    """Show user's referral stats"""
    user_id = message.from_user.id
    
    async for session in get_db():
        referral_repo = ReferralRepository(session)
        user_repo = UserRepository(session)
        referral_service = ReferralService(referral_repo, user_repo)
        
        # Get or create referral code
        referral_code = await referral_service.get_referral_code(user_id)
        referral_link = await referral_service.get_referral_link(user_id)
        stats = await referral_service.get_referral_stats(user_id)
    
    # Send stats message
    # ...

@router.callback_query(F.data == "my_referrals")
async def my_referrals_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Handle my referrals inline callback"""
    # Similar to referral_command
```

### 5.3 Update Admin Handler
**File:** `app/handlers/admin.py`

Add admin management commands:

```python
from aiogram import Router, types, F
from aiogram.filters import Command

router = Router()

@router.message(Command("add_admin"))
async def add_admin_command(message: types.Message, is_superadmin: bool = False):
    """Add new admin - Super Admin only"""
    if not is_superadmin:
        await message.answer("❌ Access denied. Super Admin only.")
        return
    
    # Parse user_id from command
    # Add admin using AdminService
    # Log action

@router.message(Command("remove_admin"))
async def remove_admin_command(message: types.Message, is_superadmin: bool = False):
    """Remove admin - Super Admin only"""
    if not is_superadmin:
        await message.answer("❌ Access denied. Super Admin only.")
        return
    
    # Parse user_id from command
    # Remove admin using AdminService
    # Log action

@router.message(Command("list_admins"))
async def list_admins_command(message: types.Message, is_admin: bool = False):
    """List all admins"""
    if not is_admin:
        await message.answer("❌ Access denied. Admin only.")
        return
    
    # Get all admins from AdminService
    # Send list message

@router.message(Command("admin_help"))
async def admin_help_command(message: types.Message, is_admin: bool = False):
    """Show admin help with available commands"""
    # Show admin commands based on role
```

### 5.4 Update Admin Keyboard
**File:** `app/keyboards/admin.py`

Add admin management keyboard options:

```python
class AdminKeyboard:
    @staticmethod
    def get_admin_panel() -> InlineKeyboardMarkup:
        keyboard = [
            # ... existing options ...
            [
                InlineKeyboardButton(
                    text=f"👥 Manage Admins",
                    callback_data="admin_manage_admins"
                ),
                # ... other options ...
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

class AdminUsersKeyboard:
    @staticmethod
    def get_user_management() -> InlineKeyboardMarkup:
        keyboard = [
            # ... existing options ...
            [
                InlineKeyboardButton(
                    text=f"🔗 View Referrals",
                    callback_data="admin_users_referrals"
                ),
                InlineKeyboardButton(
                    text=f"🏆 Top Referrers",
                    callback_data="admin_referrals_leaderboard"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
```

### 5.5 Create Admin Management Handler
**File:** `app/handlers/admin_manage.py`

```python
from aiogram import Router, types, F
from aiogram.filters import Command

router = Router()

@router.callback_query(F.data == "admin_manage_admins")
async def manage_admins_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show admin management menu"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"👥 *Admin Management*\n\n"
        f"Manage bot administrators:",
        parse_mode='Markdown',
        reply_markup=AdminManageKeyboard.get_admin_management()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_list_all_admins")
async def list_all_admins_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """List all admins"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    async for session in get_db():
        admin_repo = TelegramAdminRepository(session)
        admins = await admin_repo.list_admins()
    
    # Format and send admin list
    # ...

@router.callback_query(F.data == "admin_referrals_leaderboard")
async def referrals_leaderboard_callback(callback: types.CallbackQuery, is_admin: bool = False):
    """Show top referrers"""
    if not is_admin:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Get top referrers
    # Send leaderboard
```

---

## 🔧 PHASE 6: Configuration & Utilities

### 6.1 Update Config
**File:** `app/config.py`

Add referral settings:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Referral Configuration
    REFERRAL_REWARD_THRESHOLD: int = int(os.getenv("REFERRAL_REWARD_THRESHOLD", 5))  # Users needed for reward
    REFERRAL_REWARD_TYPE: str = os.getenv("REFERRAL_REWARD_TYPE", "premium")  # premium, premium_days
    REFERRAL_REWARD_DAYS: int = int(os.getenv("REFERRAL_REWARD_DAYS", 30))  # Days of premium for reward
    
    # Bot URL for generating referral links
    BOT_URL: str = os.getenv("BOT_URL", "https://t.me/YourBot")
```

### 6.2 Create Referral Utilities
**File:** `app/utils/referral_utils.py`

```python
import random
import string

def generate_referral_code(length: int = 8) -> str:
    """Generate unique referral code"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(chars) for _ in range(length))
    return f"REF{code}"

def parse_referral_code(deep_link: str) -> Optional[str]:
    """Parse referral code from deep link"""
    if deep_link and deep_link.startswith('ref_'):
        return deep_link[4:]
    return None

def build_referral_link(bot_username: str, referral_code: str) -> str:
    """Build full referral link"""
    return f"https://t.me/{bot_username}?start=ref_{referral_code}"
```

---

## 📝 PHASE 7: Testing & Migration

### 7.1 Migration Script
**File:** `scripts/run_referral_admin_migration.py`

```python
import asyncio
from app.db.base import engine, async_session
from sqlalchemy import text

async def run_migration():
    async with engine.begin() as conn:
        # Run migration SQL
        with open('scripts/referral_admin_migration.sql', 'r') as f:
            sql = f.read()
            for statement in sql.split(';'):
                if statement.strip():
                    await conn.execute(text(statement))
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
```

### 7.2 Data Seeding (Optional)
**File:** `scripts/seed_initial_admins.py`

```python
async def seed_initial_admins():
    """Seed initial admin from environment config"""
    # Get ADMIN_IDS from settings
    # Add them as superadmins
```

---

## ✅ PHASE 8: Final Integration

### 8.1 Update Bot Router
**File:** `app/bot.py`

```python
async def setup_handlers(self):
    # ... existing handlers ...
    from app.handlers import referral, admin_manage
    
    # Register new handlers
    self.dp.include_router(referral.router)
    self.dp.include_router(admin_manage.router)
```

### 8.2 Add to Requirements
No new dependencies required for this implementation.

---

## 📊 Summary of Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `app/db/models.py` | Modified | Add referral fields to User, create Referral and TelegramAdmin models |
| `app/repositories/referral_repo.py` | New | Repository for referral operations |
| `app/repositories/admin_repo.py` | Modified | Add TelegramAdminRepository |
| `app/services/referral_service.py` | New | Service for referral logic |
| `app/services/admin_service.py` | New | Service for admin management |
| `app/middlewares/auth.py` | Modified | Check database for admin permissions |
| `app/handlers/start.py` | Modified | Handle referral links in /start |
| `app/handlers/referral.py` | New | Referral command handler |
| `app/handlers/admin.py` | Modified | Add admin management commands |
| `app/handlers/admin_manage.py` | New | Admin management UI handlers |
| `app/keyboards/admin.py` | Modified | Add admin management keyboard options |
| `app/config.py` | Modified | Add referral configuration |
| `app/utils/referral_utils.py` | New | Referral utility functions |
| `scripts/referral_admin_migration.sql` | New | Database migration script |

---

## 🚀 Execution Order

1. Run database migration (`scripts/referral_admin_migration.sql`)
2. Create new repository files
3. Create new service files
4. Update models.py
5. Update middleware
6. Update handlers
7. Update keyboards
8. Update bot.py
9. Test functionality

