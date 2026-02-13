from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, 
    Boolean, Float, Enum, ForeignKey, Date, DateTime,
    Index, UniqueConstraint, CheckConstraint, text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(Enum('student', 'admin', name='user_role'), default='student')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    blocked = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    # Referral system fields
    referral_code = Column(String(20), unique=True, nullable=True)
    referred_by = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    referral_count = Column(Integer, default=0)
    referral_balance = Column(Float, default=0.00)  # Balance in Birr from referrals
    
    # Relationships
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    payments = relationship(
        "Payment",
        back_populates="user",
        foreign_keys="[Payment.user_id]",
        cascade="all, delete-orphan",
    )
    approved_payments = relationship(
        "Payment",
        back_populates="approver",
        foreign_keys="[Payment.approved_by]",
    )
    
    # Self-referential relationships for referral system
    # Use lambda for remote_side to avoid NameError during class definition
    referrer = relationship(
        "User",
        back_populates="referred_users",
        foreign_keys="[User.referred_by]",
        remote_side=lambda: User.user_id,
        post_update=True
    )
    
    referred_users = relationship(
        "User",
        back_populates="referrer",
        foreign_keys="[User.referred_by]",
        post_update=True
    )
    
    # Indexes for referral system
    __table_args__ = (
        Index('idx_users_referral_code', 'referral_code'),
        Index('idx_users_referred_by', 'referred_by'),
    )
    
    def __repr__(self):
        return f"<User {self.user_id}: {self.username}>"

class Subject(Base):
    __tablename__ = "subjects"
    subject_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="subject", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subject {self.subject_id}: {self.subject_name}>"

class Chapter(Base):
    __tablename__ = "chapters"
    chapter_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"))
    chapter_name = Column(String(100), nullable=False)
    chapter_order = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    subject = relationship("Subject", back_populates="chapters")
    questions = relationship("Question", back_populates="chapter", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('subject_id', 'chapter_name', name='unique_chapter'),
        Index('idx_subject_order', 'subject_id', 'chapter_order'),
    )
    
    def __repr__(self):
        return f"<Chapter {self.chapter_id}: {self.chapter_name}>"

class Question(Base):
    __tablename__ = "questions"
    question_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"))
#_id", ondelete="CASCADE")
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id", ondelete="CASCADE"))
    difficulty = Column(Enum('simple', 'medium', 'hard', name='question_difficulty'), nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    correct_option = Column(Enum('A', 'B', 'C', 'D', name='correct_option'), nullable=False)
    explanation = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    subject = relationship("Subject", back_populates="questions")
    chapter = relationship("Chapter", back_populates="questions")
    attempts = relationship("QuizAttempt", back_populates="question", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_subject_chapter', 'subject_id', 'chapter_id'),
        Index('idx_difficulty', 'difficulty'),
        Index('idx_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Question {self.question_id}: {self.question_text[:50]}...>"

class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"))
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id", ondelete="CASCADE"))
    difficulty = Column(Enum('simple', 'medium', 'hard', name='progress_difficulty'))
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    total_time_spent = Column(Integer, default=0)
    last_attempt = Column(DateTime, nullable=True)
    accuracy = Column(Float, default=0.00)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="progress")
    subject = relationship("Subject")
    chapter = relationship("Chapter")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'subject_id', 'chapter_id', 'difficulty', name='unique_user_progress'),
        Index('idx_user_progress', 'user_id', 'accuracy'),
        Index('idx_subject_progress', 'subject_id', 'chapter_id', 'difficulty'),
    )
    
    def __repr__(self):
        return f"<UserProgress {self.user_id}: {self.accuracy}%>"

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    attempt_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    question_id = Column(Integer, ForeignKey("questions.question_id", ondelete="CASCADE"))
    selected_option = Column(Enum('A', 'B', 'C', 'D', name='selected_option'))
    is_correct = Column(Boolean)
    time_taken = Column(Integer, default=0)
    quiz_session_id = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")
    
    __table_args__ = (
        Index('idx_user_attempts', 'user_id', 'created_at'),
        Index('idx_question_attempts', 'question_id', 'is_correct'),
        Index('idx_session', 'quiz_session_id'),
    )
    
    def __repr__(self):
        return f"<QuizAttempt {self.attempt_id}: {'✓' if self.is_correct else '✗'}>"

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    screenshot_file_id = Column(String(255))
    screenshot_file_path = Column(String(500))
    status = Column(Enum('pending', 'approved', 'rejected', name='payment_status'), default='pending')
    amount = Column(Float, nullable=False)
    subscription_days = Column(Integer, nullable=True)
    transaction_id = Column(String(100))
    notes = Column(Text)
    approved_by = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_reason = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="payments", foreign_keys="[Payment.user_id]")
    approver = relationship("User", back_populates="approved_payments", foreign_keys="[Payment.approved_by]")
    
    __table_args__ = (
        Index('idx_payment_status', 'status', 'created_at'),
        Index('idx_user_payments', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Payment {self.payment_id}: {self.status} - ${self.amount}>"

class Leaderboard(Base):
    __tablename__ = "leaderboard"
    leaderboard_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    period = Column(Enum('daily', 'weekly', 'monthly', 'overall', name='leaderboard_period'), nullable=False)
    total_score = Column(Integer, default=0)
    total_accuracy = Column(Float, default=0.00)
    total_questions = Column(Integer, default=0)
    rank_position = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'period', name='unique_leaderboard_entry'),
        Index('idx_leaderboard_period', 'period', 'rank_position'),
        Index('idx_user_leaderboard', 'user_id', 'period'),
    )
    
    def __repr__(self):
        return f"<Leaderboard {self.user_id}: #{self.rank_position} for {self.period}>"

class UserDailyLimit(Base):
    __tablename__ = "user_daily_limits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    date = Column(Date, nullable=False)
    quiz_count = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=func.now())
    
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='unique_user_date'),
        Index('idx_date_limit', 'date', 'quiz_count'),
    )
    
    def __repr__(self):
        return f"<UserDailyLimit {self.user_id}: {self.quiz_count} quizzes on {self.date}>"


class UserChapterDailyLimit(Base):
    """
    Tracks daily question limits per user per chapter per difficulty level.
    
    This enables the feature: 25 questions per day per chapter per level.
    """
    __tablename__ = "user_chapter_daily_limits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"))
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id", ondelete="CASCADE"))
    difficulty = Column(Enum('simple', 'medium', 'hard', name='chapter_limit_difficulty'))
    date = Column(Date, nullable=False)
    question_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=func.now())
    
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'subject_id', 'chapter_id', 'difficulty', 'date', 
                        name='unique_user_chapter_difficulty_date'),
        Index('idx_chapter_limit_lookup', 'user_id', 'chapter_id', 'difficulty', 'date'),
    )
    
    def __repr__(self):
        return f"<UserChapterDailyLimit {self.user_id}: {self.question_count} questions for Ch{self.chapter_id}/{self.difficulty} on {self.date}>"

class AdminUser(Base):
    __tablename__ = "admin_users"
    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum('superadmin', 'moderator', name='admin_role'), default='moderator')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_admin_username', 'username'),
        Index('idx_admin_email', 'email'),
    )

    def __repr__(self):
        return f"<AdminUser {self.admin_id}: {self.username} ({self.role})>"

class AdminLog(Base):
    __tablename__ = "admin_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(BigInteger, nullable=False)
    action = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<AdminLog {self.id}: admin={self.admin_user_id} action={self.action[:40]}>"

class ContactMessage(Base):
    __tablename__ = "contact_messages"
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(20), unique=True, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    category = Column(Enum('payment', 'quiz_error', 'access', 'general', 'feedback', name='contact_category'), nullable=False)
    subject = Column(String(200), nullable=True)
    message_text = Column(Text, nullable=False)
    status = Column(Enum('open', 'replied', 'closed', name='contact_status'), default='open')
    admin_reply = Column(Text, nullable=True)
    replied_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now())
    replied_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("User")

    __table_args__ = (
        Index('idx_contact_ticket_id', 'ticket_id'),
        Index('idx_contact_user', 'user_id', 'created_at'),
        Index('idx_contact_status', 'status', 'created_at'),
        Index('idx_contact_category', 'category'),
    )

    def __repr__(self):
        return f"<ContactMessage {self.ticket_id}: {self.category} - {self.status}>"

class AccessAuditLog(Base):
    __tablename__ = "access_audit_log"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    action = Column(String(50), nullable=False)
    resource = Column(String(100), nullable=False)
    access_granted = Column(Boolean, nullable=False)
    reason = Column(String(255))
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_access_audit_user', 'user_id', 'created_at'),
        Index('idx_access_audit_denied', 'access_granted', 'created_at'),
        Index('idx_access_audit_resource', 'resource', 'action'),
    )

    def __repr__(self):
        status = "GRANTED" if self.access_granted else "DENIED"
        return f"<AccessAuditLog {self.log_id}: User {self.user_id} - {self.action}/{self.resource} - {status}>"

class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    referred_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum('pending', 'approved', 'cancelled', name='referral_status'), default='pending')
    reward_claimed = Column(Boolean, default=False)
    reward_claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    approved_at = Column(DateTime, nullable=True)

    referrer_user = relationship("User", foreign_keys="[Referral.referrer_id]")
    referred_user = relationship("User", foreign_keys="[Referral.referred_id]")

    __table_args__ = (
        UniqueConstraint('referrer_id', 'referred_id', name='unique_referral'),
        Index('idx_referral_referrer', 'referrer_id'),
        Index('idx_referral_referred', 'referred_id'),
        Index('idx_referral_status', 'status'),
        Index('idx_referral_created', 'created_at'),
    )

    def __repr__(self):
        return f"<Referral {self.id}: {self.referrer_id} -> {self.referred_id} ({self.status})>"

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

    __table_args__ = (
        Index('idx_telegram_admin_user_id', 'user_id'),
        Index('idx_telegram_admin_role', 'role'),
    )

    def __repr__(self):
        return f"<TelegramAdmin {self.id}: {self.user_id} ({self.role})>"
