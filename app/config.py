import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Bot Configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "").rstrip("/") if os.getenv("WEBHOOK_URL") else ""
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
    WEBHOOK_PORT: int = int(os.getenv("PORT", 10000))

    @property
    def COMPLETE_WEBHOOK_URL(self) -> str:
        """
        Build the complete webhook URL, avoiding duplicate paths.
        
        If WEBHOOK_URL already ends with WEBHOOK_PATH, don't add it again.
        """
        if not self.WEBHOOK_URL:
            return ""
        
        clean_url = self.WEBHOOK_URL.rstrip('/')
        webhook_path = self.WEBHOOK_PATH.strip('/')
        
        # Check if URL already ends with the webhook path
        if clean_url.endswith(f"/{webhook_path}"):
            return clean_url
        
        return f"{clean_url}/{webhook_path}"
    WEBAPP_HOST: str = os.getenv("WEBAPP_HOST", "0.0.0.0")
    
    # Database Configuration
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")  # sqlite, mysql, mariadb
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_NAME: str = os.getenv("DB_NAME", "quiz_bot")
    DB_USER: str = os.getenv("DB_USER", "quiz_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", 10))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", 20))
    # SQLite specific configuration
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "/data/quizbot.db")
    
    # Admin Configuration (stored as comma-separated string in env)
    ADMIN_IDS: Optional[str] = ""
    
    # Security
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    API_RATE_LIMIT: int = int(os.getenv("API_RATE_LIMIT", 100))
    
    # Payment Configuration
    SUBSCRIPTION_PRICE_30_DAYS: float = float(os.getenv("SUBSCRIPTION_PRICE_30_DAYS", 500))
    SUBSCRIPTION_PRICE_90_DAYS: float = float(os.getenv("SUBSCRIPTION_PRICE_90_DAYS", 1200))
    CURRENCY: str = os.getenv("CURRENCY", "ETB")  # Default to Ethiopian Birr
    CURRENCY_SYMBOL: str = os.getenv("CURRENCY_SYMBOL", "ETB")  # Currency symbol for display
    # One-time lifetime price (in local currency)
    ONE_TIME_PRICE: float = float(os.getenv("ONE_TIME_PRICE", 150))  # 150 ETB
    
    # Feature Flags
    # ⚠️ SECURITY: ENABLE_TRIAL is now IGNORED for quiz access.
    # Users must be explicitly approved by an admin (approved = 1).
    # This setting is kept for backwards compatibility but has no effect.
    ENABLE_TRIAL: bool = os.getenv("ENABLE_TRIAL", "false").lower() == "true"
    TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", 7))
    DAILY_QUIZ_LIMIT: int = int(os.getenv("DAILY_QUIZ_LIMIT", 20))
    MAX_QUESTIONS_PER_QUIZ: int = int(os.getenv("MAX_QUESTIONS_PER_QUIZ", 10))
    
    # Global Daily Question Limit (500 questions per day total across all chapters and levels)
    DAILY_QUESTION_LIMIT: int = int(os.getenv("DAILY_QUESTION_LIMIT", 500))
    
    # Paths
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    LOGS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    
    # Redis (optional)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # Referral System Configuration
    REFERRAL_REWARD_THRESHOLD: int = int(os.getenv("REFERRAL_REWARD_THRESHOLD", 5))  # Users needed for reward
    REFERRAL_REWARD_TYPE: str = os.getenv("REFERRAL_REWARD_TYPE", "premium")  # premium, premium_days, per_student
    REFERRAL_REWARD_DAYS: int = int(os.getenv("REFERRAL_REWARD_DAYS", 30))  # Days of premium for reward
    # Per-student reward in local currency (e.g., 20 Birr per approved student)
    REFERRAL_REWARD_PER_STUDENT: float = float(os.getenv("REFERRAL_REWARD_PER_STUDENT", 20))
    # Bot username for generating referral links
    # ⚠️ IMPORTANT: Set this to your actual bot username (without @)
    # This is required for referral links to work correctly
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "SmartITestExambot")
    
    @property
    def DATABASE_URL(self) -> str:
        """
        Build database URL based on configuration.
        
        Priority:
        1. DATABASE_URL env var (highest priority, allows full control)
        2. DB_TYPE setting (sqlite, postgresql, mysql, mariadb)
        """
        # Allow explicit override via env var for flexibility
        env_db = os.getenv("DATABASE_URL")
        if env_db:
            return env_db
        
        # Use DB_TYPE to determine database type
        db_type = self.DB_TYPE.lower() if self.DB_TYPE else "sqlite"
        
        if db_type == "sqlite":
            # SQLite with aiosqlite driver for async support
            return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"
        elif db_type == "postgresql":
            # PostgreSQL: use asyncpg driver for async support
            # Format: postgresql+asyncpg://user:password@host:port/dbname
            password = self.DB_PASSWORD
            # URL encode password if it contains special characters
            import urllib.parse
            encoded_password = urllib.parse.quote(password, safe='')
            
            return (
                f"postgresql+asyncpg://{self.DB_USER}:{encoded_password}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        elif db_type in ("mysql", "mariadb"):
            # MySQL/MariaDB: use aiomysql driver for async support
            return (
                f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        else:
            # Default to SQLite with aiosqlite driver
            return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"

    # Optional engine hint: set to 'mariadb' if you're running MariaDB.
    DB_ENGINE: Optional[str] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse admin IDs from comma-separated string and store as list
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        parsed_admin_ids = []
        if admin_ids_str:
            parsed_admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
        # Attach a list to the instance for easy consumption elsewhere
        object.__setattr__(self, 'ADMIN_IDS', parsed_admin_ids)
        
        # Create necessary directories
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.LOGS_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.DATA_DIR, "questions"), exist_ok=True)
        os.makedirs(os.path.join(self.DATA_DIR, "exports"), exist_ok=True)
        os.makedirs(os.path.join(self.DATA_DIR, "screenshots"), exist_ok=True)

settings = Settings()