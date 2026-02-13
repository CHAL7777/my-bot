from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserBase(BaseModel):
    """Base user model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class User(UserBase):
    """Full user model with subscription status"""
    is_premium: bool = False
    is_approved: bool = False
    referral_code: Optional[str] = None
    referral_count: int = 0
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    """Model for creating a new user"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class SubjectBase(BaseModel):
    """Base subject model"""
    subject_name: str
    description: Optional[str] = None


class Subject(SubjectBase):
    """Full subject model"""
    subject_id: int
    created_at: Optional[datetime] = None


class SubjectCreate(BaseModel):
    """Model for creating a new subject"""
    subject_name: str
    description: Optional[str] = None


class ChapterBase(BaseModel):
    """Base chapter model"""
    subject_id: int
    chapter_name: str
    description: Optional[str] = None


class Chapter(ChapterBase):
    """Full chapter model"""
    chapter_id: int
    created_at: Optional[datetime] = None


class ChapterCreate(BaseModel):
    """Model for creating a new chapter"""
    subject_id: int
    chapter_name: str
    description: Optional[str] = None


class Difficulty(str, Enum):
    """Question difficulty levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionBase(BaseModel):
    """Base question model"""
    subject_id: int
    chapter_id: int
    difficulty: Difficulty
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    explanation: Optional[str] = None


class Question(QuestionBase):
    """Full question model"""
    question_id: int
    is_active: bool = True
    created_at: Optional[datetime] = None


class QuestionCreate(BaseModel):
    """Model for creating a new question"""
    subject_id: int
    chapter_id: int
    difficulty: Difficulty
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    explanation: Optional[str] = None


class PaymentStatus(str, Enum):
    """Payment status values"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentBase(BaseModel):
    """Base payment model"""
    user_id: int
    amount: float
    screenshot_file_id: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None


class Payment(PaymentBase):
    """Full payment model"""
    payment_id: int
    status: PaymentStatus = PaymentStatus.PENDING
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class PaymentCreate(BaseModel):
    """Model for creating a new payment"""
    user_id: int
    amount: float
    screenshot_file_id: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None


class QuizAttemptBase(BaseModel):
    """Base quiz attempt model"""
    user_id: int
    question_id: int
    selected_option: str
    is_correct: bool
    time_taken: int = 0


class QuizAttempt(QuizAttemptBase):
    """Full quiz attempt model"""
    attempt_id: int
    created_at: Optional[datetime] = None


class QuizSession(BaseModel):
    """Quiz session model"""
    quiz_session_id: str
    user_id: int
    subject_id: int
    chapter_id: int
    difficulty: Difficulty
    current_question: int = 0
    score: int = 0
    total_questions: int = 0
    is_completed: bool = False


class LeaderboardPeriod(str, Enum):
    """Leaderboard period values"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    OVERALL = "overall"


class LeaderboardEntry(BaseModel):
    """Leaderboard entry model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    total_score: int
    total_accuracy: float
    rank_position: int


class ReferralStatus(str, Enum):
    """Referral status values"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReferralBase(BaseModel):
    """Base referral model"""
    referrer_id: int
    referred_id: int


class Referral(ReferralBase):
    """Full referral model"""
    referral_id: int
    status: ReferralStatus = ReferralStatus.PENDING
    reward_claimed: bool = False
    created_at: Optional[datetime] = None


class ReferralCreate(BaseModel):
    """Model for creating a new referral"""
    referrer_id: int
    referred_id: int


class SubscriptionBase(BaseModel):
    """Base subscription model"""
    user_id: int
    end_date: datetime


class Subscription(SubscriptionBase):
    """Full subscription model"""
    subscription_id: int
    is_active: bool = True
    start_date: Optional[datetime] = None


class AdminUserBase(BaseModel):
    """Base admin user model"""
    username: str
    password_hash: str


class AdminUser(AdminUserBase):
    """Full admin user model"""
    admin_id: int
    role: str = "admin"
    created_at: Optional[datetime] = None


class AdminUserCreate(BaseModel):
    """Model for creating a new admin user"""
    username: str
    password_hash: str


class UserStats(BaseModel):
    """User statistics model"""
    total_attempts: int
    correct_answers: int
    accuracy: float


class QuizQuestion(BaseModel):
    """Quiz question model for quiz sessions"""
    question_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    difficulty: Difficulty
    explanation: Optional[str] = None


class QuizResult(BaseModel):
    """Quiz result model"""
    score: int
    total_questions: int
    correct_answers: int
    accuracy: float
    total_time: float


class WebhookUpdate(BaseModel):
    """Telegram webhook update model"""
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None

