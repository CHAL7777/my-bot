"""
Application constants and configuration
"""

from enum import Enum
from typing import Dict, List, Tuple

# ==================== DIFFICULTY SETTINGS ====================

class Difficulty(Enum):
    """Difficulty levels for questions"""
    SIMPLE = 'simple'
    MEDIUM = 'medium'
    HARD = 'hard'

# Points awarded for correct answers by difficulty
DIFFICULTY_POINTS: Dict[str, int] = {
    Difficulty.SIMPLE.value: 1,
    Difficulty.MEDIUM.value: 2,
    Difficulty.HARD.value: 3
}

# Time limits per question (in seconds)
TIME_LIMITS: Dict[str, int] = {
    Difficulty.SIMPLE.value: 60,    # 1 minute
    Difficulty.MEDIUM.value: 90,    # 1.5 minutes
    Difficulty.HARD.value: 120      # 2 minutes
}

# Question distribution weights for quizzes
DIFFICULTY_WEIGHTS: Dict[str, float] = {
    Difficulty.SIMPLE.value: 0.4,   # 40% simple
    Difficulty.MEDIUM.value: 0.35,  # 35% medium
    Difficulty.HARD.value: 0.25     # 25% hard
}

# ==================== SUBSCRIPTION SETTINGS ====================

# Subscription prices in ETB (Ethiopian Birr)
SUBSCRIPTION_PRICES: Dict[int, float] = {
    7: 0,      # Free trial (7 days)
    30: 500,   # 30 days - 500 ETB
    90: 1200,  # 90 days - 1200 ETB (save ETB 300)
    180: 2000, # 180 days - 2000 ETB (save ETB 1000)
    365: 3500  # 365 days - 3500 ETB (save ETB 2500)
}

# Subscription features by plan
SUBSCRIPTION_FEATURES: Dict[str, List[str]] = {
    'free': [
        'Simple difficulty quizzes',
        'Daily quiz limit: 3 quizzes',
        'Basic progress tracking',
        'Weekly leaderboard access'
    ],
    'premium': [
        'All difficulty levels (Simple, Medium, Hard)',
        'Unlimited daily quizzes',
        'Advanced analytics & insights',
        'All leaderboards (Daily, Weekly, Monthly, Overall)',
        'Personalized recommendations',
        'Priority support',
        'Weak area detection',
        'Detailed performance reports'
    ]
}

# ==================== QUIZ SETTINGS ====================

# Quiz limits
DAILY_QUIZ_LIMIT: int = 20
MAX_QUESTIONS_PER_QUIZ: int = 10
MIN_QUESTIONS_PER_QUIZ: int = 5
MAX_QUESTIONS_PER_DAY: int = 100

# Quiz session timeout (in minutes)
QUIZ_TIMEOUT_MINUTES: int = 30

# Quiz retry settings
MAX_RETRY_ATTEMPTS: int = 3
RETRY_COOLDOWN_MINUTES: int = 5

# ==================== ACCURACY SETTINGS ====================

# Accuracy thresholds for performance evaluation
ACCURACY_THRESHOLDS: Dict[str, float] = {
    'excellent': 85.0,  # 85% and above
    'good': 70.0,       # 70% - 84.9%
    'average': 50.0,    # 50% - 69.9%
    'poor': 0.0         # Below 50%
}

# Performance messages based on accuracy
PERFORMANCE_MESSAGES: Dict[str, Tuple[str, str]] = {
    'excellent': (
        "🎉 *Excellent Performance!*\n",
        "You're mastering this topic! Consider trying a higher difficulty level."
    ),
    'good': (
        "👍 *Good Job!*\n",
        "Solid understanding. Keep practicing to reach excellence."
    ),
    'average': (
        "📚 *Average Performance*\n",
        "You're on the right track. Review explanations and try again."
    ),
    'poor': (
        "💪 *Needs Improvement*\n",
        "This topic needs more practice. Review the material and retry."
    )
}

# ==================== EMOJI CONSTANTS ====================

EMOJIS: Dict[str, str] = {
    # Quiz-related emojis
    'quiz': '🎯',
    'question': '❓',
    'questions': '❓',  # Alias for question
    'answer': '📝',
    'correct': '✅',
    'wrong': '❌',
    'time': '⏱️',
    'score': '🏆',
    'stats': '📈',  # Statistics
    'accuracy': '📊',
    'progress': '📈',
    'trophy': '🏅',
    'medal_gold': '🥇',
    'medal_silver': '🥈',
    'medal_bronze': '🥉',
    'dashboard': '📊',  # Dashboard overview
    
    # Subject and chapter emojis
    'subject': '📚',
    'chapter': '📖',
    'mathematics': '🧮',
    'science': '🔬',
    'english': '📝',
    'history': '🏛️',
    'geography': '🌍',
    
    # Difficulty emojis
    'easy': '🟢',
    'medium': '🟡',
    'hard': '🔴',
    'difficulty': '⚡',
    
    # User and admin emojis
    'user': '👤',
    'users': '👥',  # Multiple users
    'admin': '👑',
    'teacher': '👨‍🏫',
    'student': '👨‍🎓',
    
    # Payment and subscription emojis
    'payment': '💰',
    'payments': '💰',  # Alias for payment
    'money': '💵',  # Money/currency
    'subscription': '🎫',
    'free': '🆓',
    'premium': '💎',
    'trial': '🎁',
    'gift': '🎁',  # Gift/referral emoji
    'share': '📤',  # Share action
    'pending': '⏳',  # Pending payment
    'screenshot': '📸',  # Payment screenshot
    
    # Status and notification emojis
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'loading': '⏳',
    'done': '✅',
    'clock': '🕒',
    'calendar': '📅',
    'list': '📋',  # List view
    'view': '👁️',  # View action
    
    # Action emojis
    'start': '▶️',
    'stop': '⏹️',
    'pause': '⏸️',
    'refresh': '🔄',
    'download': '📥',
    'upload': '📤',
    'search': '🔍',
    'settings': '⚙️',
    'help': '❓',
    'back': '◀️',
    'next': '▶️',
    'home': '🏠',
    'menu': '📋',
    'add': '➕',  # Add action
    'edit': '✏️',  # Edit action
    'delete': '🗑️',  # Delete action
    'template': '📄',  # Template document
    'file': '📄',  # Generic file/document
    'approve': '✅',  # Approve action
    'block': '🚫',  # Block action
    'unblock': '✅',  # Unblock action
    
    # Communication emojis
    'message': '💬',
    'notification': '🔔',
    'email': '📧',
    'phone': '📱',
    'contact': '📞',
    'support': '🎧',
    'broadcast': '📢',  # Broadcast message
    
    # Learning and education emojis
    'learn': '🧠',
    'practice': '📝',
    'test': '📋',
    'exam': '📚',
    'graduate': '🎓',
    'certificate': '📜',
    
# Fun and encouragement emojis
    'party': '🎉',
    'fire': '🔥',
    'star': '⭐',
    'rocket': '🚀',
    'target': '🎯',
    'lightbulb': '💡',
    'thumbs_up': '👍',
    'clap': '👏',
    'celebrate': '🥳',
    'copy': '📋',  # Copy to clipboard
    
    # Additional celebration and encouragement emojis
    'trophy': '🏆',
    'medal': '🏅',
    'gold': '🥇',
    'silver': '🥈',
    'bronze': '🥉',
    'crown': '👑',
    'rocket': '🚀',
    'zap': '⚡',
    'brain': '🧠',
    'seedling': '🌱',
    'plant': '🌱',
    'growth': '🌱',
    'bulb': '💡',
    'sparkles': '✨',
    'confetti': '🎊',
    ' streamers': '🎊',
    'champion': '🏆',
    'winner': '🏆',
    'perfect': '💯',
    'bullseye': '🎯',
    'strong': '💪',
    'muscle': '💪',
    'smile': '😊',
    'happy': '😊',
    'wink': '😉',
    'thinking': '🤔',
    'raised_hands': '🙌',
    'high_five': '🙌',
    'wave': '👋',
    'point_right': '👉',
    'check': '✅',
    'cross': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'question': '❓',
    'exclamation': '❗',
    'star_struck': '🤩',
    'sunglasses': '😎',
    'rainbow': '🌈',
    'moon': '🌙',
    'sun': '☀️',
    'cloud': '☁️',
    'rain': '🌧️',
    'snowflake': '❄️',
    'wind': '💨',
    'leaf': '🍃',
    'tree': '🌳',
    'flower': '🌸',
    'bell': '🔔',
    'alarm': '⏰',
    'stopwatch': '⏱️',
    'hourglass': '⏳',
    'calendar': '📅',
    'clipboard': '📋',
    'books': '📚',
    'notebook': '📓',
    'pencil': '✏️',
    'pen': '🖊️',
    'ruler': '📏',
    'calculator': '🧮',
    'microscope': '🔬',
    'telescope': '🔭',
    'computer': '💻',
    'mobile': '📱',
    'tv': '📺',
    'camera': '📷',
    'video': '🎥',
    'headphones': '🎧',
    'musical_note': '🎵',
    'musical_notes': '🎶',
    'guitar': '🎸',
    'piano': '🎹',
    'drum': '🥁',
    'balloon': '🎈',
    'gift': '🎁',
    'cake': '🎂',
    'cookie': '🍪',
    'coffee': '☕',
    'tea': '🍵',
    'water': '💧',
    'apple': '🍎',
    'banana': '🍌',
    'pizza': '🍕',
    'burger': '🍔',
    'fries': '🍟',
    'ice_cream': '🍦',
    'cake_piece': '🍰',
    'candy': '🍬',
    'chocolate': '🍫',
    'beer': '🍺',
    'wine': '🍷',
    'clinking_glasses': '🥂',
    'cheers': '🥂',
    'football': '🏈',
    'basketball': '🏀',
    'soccer': '⚽',
    'baseball': '⚾',
    'tennis': '🎾',
    'volleyball': '🏐',
    '8ball': '🎱',
    'bowling': '🎳',
    'golf': '⛳',
    'skiing': '⛷️',
    'snowboarding': '🏂',
    'swimming': '🏊',
    'running': '🏃',
    'walking': '🚶',
    'dancing': '💃',
    'sleeping': '😴',
    'pray': '🙏',
    'love': '❤️',
    'hug': '🤗',
    'kiss': '💋',
    'cat': '🐱',
    'dog': '🐶',
    'mouse': '🐭',
    'rabbit': '🐰',
    'bear': '🐻',
    'panda': '🐼',
    'koala': '🐨',
    'tiger': '🐯',
    'lion': '🦁',
    'cow': '🐮',
    'pig': '🐷',
    'chicken': '🐔',
    'penguin': '🐧',
    'bird': '🐦',
    'eagle': '🦅',
    'owl': '🦉',
    'fish': '🐟',
    'whale': '🐳',
    'dolphin': '🐬',
    'crab': '🦀',
    'snake': '🐍',
    'lizard': '🦎',
    'frog': '🐸',
    'turtle': '🐢',
    'bug': '🐛',
    'ant': '🐜',
    'bee': '🐝',
    'butterfly': '🦋',
    'snail': '🐌',
    'octopus': '🐙',
    'dragon': '🐉',
    'cactus': '🌵',
    'mushroom': '🍄',
    'shell': '🐚',
    'earth': '🌍',
    'globe': '🌐',
    'map': '🗺️',
    'compass': '🧭',
    'mountain': '⛰️',
    'beach': '🏖️',
    'desert': '🏜️',
    'island': '🏝️',
    'park': '🏞️',
    'building': '🏢',
    'house': '🏠',
    'school': '🏫',
    'office': '🏢',
    'hospital': '🏥',
    'bank': '🏦',
    'hotel': '🏨',
    'store': '🏪',
    'factory': '🏭',
    'church': '⛪',
    'mosque': '🕌',
    'temple': '🛕',
    'shrine': '⛩️',
    'kaaba': '🕋',
    'fountain': '⛲',
    'statue': '🗿',
    'wedding': '💒',
    'castle': '🏰',
    'bridge': '🌉',
    'road': '🛣️',
    'car': '🚗',
    'taxi': '🚕',
    'bus': '🚌',
    'truck': '🚚',
    'train': '🚆',
    'subway': '🚇',
    'tram': '🚊',
    'bicycle': '🚲',
    'motorcycle': '🏍️',
    'airplane': '✈️',
    'rocket_ship': '🚀',
    'helicopter': '🚁',
    'boat': '⛵',
    'ship': '🚢',
    'anchor': '⚓',
    'traffic_light': '🚦',
    'construction': '🚧',
    'warning_sign': '⚠️',
    'no_entry': '⛔',
    'stop_sign': '🛑',
    'railway': '🛤️',
    'ticket': '🎫',
    'passport': '🛂',
    'luggage': '🧳',
    'shopping_cart': '🛒',
    'gift_box': '🎁',
    'balloon': '🎈',
    'ribbon': '🎀',
    'crackers': '🎉',
    'party_popper': '🎊',
    'joker': '🃏',
    'playing_cards': '🀄',
    'mahjong': '🀄',
    'game_die': '🎲',
    'dart': '🎯',
    'video_game': '🎮',
    'joystick': '🕹️',
    'slot_machine': '🎰',
    'bowling_pin': '🎳',
    'pool': '🎱',
    'crystal_ball': '🔮',
    'magic_wand': '🪄',
    'puzzle': '🧩',
    'teddy_bear': '🧸',
    'robot': '🤖',
    'alien': '👽',
    'ghost': '👻',
    'skull': '💀',
    'skeleton': '💀',
    'zombie': '🧟',
    'vampire': '🧛',
    'genie': '🧞',
    'fairy': '🧚',
    'mermaid': '🧜',
    'elf': '🧝',
    'angel': '👼',
    'santa': '🎅',
    'claus': '🎅',
    'superhero': '🦸',
    'villain': '🦹',
    'mage': '🧙',
    'pirate': '🏴‍☠️',
    'guardsman': '💂',
    'construction_worker': '👷',
    'farmer': '👨‍🌾',
    'cook': '👨‍🍳',
    'mechanic': '👨‍🔧',
    'scientist': '👨‍🔬',
    'astronaut': '👨‍🚀',
    'firefighter': '👨‍🚒',
    'detective': '🕵️',
    'spider_man': '🕷️',
    'bat_man': '🦇'
}

# Emoji aliases for easy access
EMOJI = EMOJIS  # Alias for backward compatibility

# ==================== BOT COMMANDS ====================

# User commands
BOT_COMMANDS: Dict[str, str] = {
    'start': "🚀 Start the bot",
    'quiz': "🎯 Start a new quiz",
    'progress': "📊 View your progress",
    'leaderboard': "🏆 View leaderboards",
    'payment': "💰 Subscription & payment",
    'contact': "📞 Contact support",
    'help': "❓ Get help",
    'about': "ℹ️ About this bot",
    'settings': "⚙️ Settings (coming soon)",
    'profile': "👤 View profile (coming soon)",
    'notifications': "🔔 Notifications (coming soon)"
}

# Admin commands
ADMIN_COMMANDS: Dict[str, str] = {
    'admin': "👑 Admin panel",
    'admin_stats': "📈 View statistics",
    'admin_users': "👥 Manage users",
    'admin_questions': "❓ Manage questions",
    'admin_payments': "💰 Manage payments",
    'admin_import': "📁 Import CSV",
    'admin_export': "📤 Export data",
    'admin_system': "⚙️ System settings",
    'admin_broadcast': "📢 Broadcast message"
}

# ==================== DATABASE SETTINGS ====================

# Default pagination limits
PAGINATION_LIMITS: Dict[str, int] = {
    'users': 50,
    'questions': 20,
    'payments': 20,
    'attempts': 50,
    'leaderboard': 100
}

# Cache TTL (Time To Live) in seconds
CACHE_TTL: Dict[str, int] = {
    'leaderboard': 3600,      # 1 hour
    'user_profile': 300,      # 5 minutes
    'question_stats': 1800,   # 30 minutes
    'system_stats': 60        # 1 minute
}

# ==================== FILE SETTINGS ====================

# Allowed file types for uploads
ALLOWED_FILE_TYPES: Dict[str, List[str]] = {
    'image': ['image/jpeg', 'image/png', 'image/jpg', 'image/gif'],
    'document': ['application/pdf', 'text/csv', 'application/json'],
    'spreadsheet': ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
}

# Maximum file sizes (in bytes)
MAX_FILE_SIZES: Dict[str, int] = {
    'image': 5 * 1024 * 1024,      # 5MB
    'document': 10 * 1024 * 1024,   # 10MB
    'spreadsheet': 5 * 1024 * 1024  # 5MB
}

# ==================== SECURITY SETTINGS ====================

# Rate limiting settings
RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    'messages': (10, 60),          # 10 messages per minute
    'quizzes': (5, 300),           # 5 quizzes per 5 minutes
    'payments': (3, 86400),        # 3 payments per day
    'api_calls': (100, 3600)       # 100 API calls per hour
}

# Password requirements
PASSWORD_REQUIREMENTS: Dict[str, any] = {
    'min_length': 8,
    'max_length': 128,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_digits': True,
    'require_special': True,
    'special_chars': '!@#$%^&*(),.?":{}|<>'
}

# ==================== NOTIFICATION SETTINGS ====================

# Notification types
NOTIFICATION_TYPES: Dict[str, str] = {
    'quiz_reminder': "📚 Time for your daily quiz!",
    'progress_update': "📊 Your weekly progress report is ready!",
    'leaderboard_update': "🏆 Weekly leaderboard updated!",
    'subscription_expiry': "⏰ Your subscription expires soon!",
    'payment_approved': "✅ Your payment has been approved!",
    'payment_rejected': "❌ Your payment was rejected. Please check and resubmit.",
    'achievement_unlocked': "🎖️ You've unlocked a new achievement!",
    'system_announcement': "📢 Important system announcement"
}

# Notification schedules (in hours, 24-hour format)
NOTIFICATION_SCHEDULES: Dict[str, List[int]] = {
    'daily_reminder': [9, 14, 20],      # 9AM, 2PM, 8PM
    'weekly_report': [18],              # 6PM on Sundays
    'subscription_reminder': [10, 18]   # 10AM, 6PM
}

# ==================== ANALYTICS SETTINGS ====================

# Analytics time periods (in days)
ANALYTICS_PERIODS: Dict[str, int] = {
    'daily': 1,
    'weekly': 7,
    'monthly': 30,
    'quarterly': 90,
    'yearly': 365
}

# Performance metrics weights (for health score)
METRIC_WEIGHTS: Dict[str, float] = {
    'user_retention': 0.25,
    'quiz_completion': 0.20,
    'accuracy_rate': 0.25,
    'revenue_growth': 0.15,
    'system_health': 0.15
}

# ==================== ERROR MESSAGES ====================

# User-facing error messages
ERROR_MESSAGES: Dict[str, str] = {
    'invalid_input': "❌ Invalid input. Please try again.",
    'access_denied': "🚫 Access denied. You don't have permission for this action.",
    'not_found': "🔍 The requested resource was not found.",
    'already_exists': "⚠️ This already exists. Please try a different one.",
    'limit_reached': "⏰ You've reached the limit for this action. Please try again later.",
    'subscription_required': "🔒 This feature requires a subscription. Use /payment to upgrade.",
    'payment_pending': "⏳ You already have a pending payment. Please wait for approval.",
    'system_error': "💥 System error. Please try again later or contact support.",
    'timeout': "⏱️ The operation timed out. Please try again.",
    'validation_error': "📋 Please check your input and try again.",
    'file_too_large': "📁 File too large. Maximum size is {size}.",
    'invalid_file_type': "📄 Invalid file type. Allowed types: {types}."
}

# Admin error messages
ADMIN_ERRORS: Dict[str, str] = {
    'db_connection': "Database connection failed",
    'import_failed': "CSV import failed: {error}",
    'export_failed': "Data export failed",
    'backup_failed': "Backup creation failed",
    'user_not_found': "User not found: {user_id}",
    'payment_not_found': "Payment not found: {payment_id}",
    'question_not_found': "Question not found: {question_id}"
}

# ==================== SUCCESS MESSAGES ====================

# User-facing success messages
SUCCESS_MESSAGES: Dict[str, str] = {
    'quiz_completed': "✅ Quiz completed successfully!",
    'payment_submitted': "💰 Payment submitted successfully. Waiting for approval.",
    'payment_approved': "✅ Payment approved! Your subscription is now active.",
    'profile_updated': "👤 Profile updated successfully.",
    'question_answered': "📝 Answer submitted successfully.",
    'subscription_activated': "🎫 Subscription activated successfully!",
    'data_exported': "📤 Data exported successfully.",
    'settings_saved': "⚙️ Settings saved successfully."
}

# Admin success messages
ADMIN_SUCCESS: Dict[str, str] = {
    'user_blocked': "User blocked successfully",
    'user_unblocked': "User unblocked successfully",
    'question_added': "Question added successfully",
    'question_updated': "Question updated successfully",
    'question_deleted': "Question deleted successfully",
    'payment_approved': "Payment approved successfully",
    'payment_rejected': "Payment rejected successfully",
    'import_success': "CSV import completed: {imported} questions imported",
    'backup_created': "Backup created successfully"
}

# ==================== FORMATTING CONSTANTS ====================

# Date and time formats
DATE_FORMATS: Dict[str, str] = {
    'display': "%d %b %Y",
    'display_with_time': "%d %b %Y %H:%M",
    'iso': "%Y-%m-%d",
    'iso_with_time': "%Y-%m-%d %H:%M:%S",
    'filename': "%Y%m%d_%H%M%S"
}

# Number formatting
NUMBER_FORMATS: Dict[str, str] = {
    'currency': "{amount:,.2f} ETB",
    'percentage': "{value:.1f}%",
    'decimal': "{value:.2f}",
    'integer': "{value:,}"
}

# Text formatting limits
TEXT_LIMITS: Dict[str, int] = {
    'telegram_message': 4096,
    'telegram_caption': 1024,
    'question_text': 1000,
    'option_text': 500,
    'explanation': 2000,
    'username': 32,
    'subject_name': 100,
    'chapter_name': 100
}

# ==================== API ENDPOINTS ====================

# Internal API endpoints (for future web interface)
API_ENDPOINTS: Dict[str, str] = {
    'users': "/api/v1/users",
    'questions': "/api/v1/questions",
    'quizzes': "/api/v1/quizzes",
    'payments': "/api/v1/payments",
    'analytics': "/api/v1/analytics",
    'reports': "/api/v1/reports",
    'export': "/api/v1/export"
}

# ==================== ENVIRONMENT SETTINGS ====================

# Environment types
ENVIRONMENTS: Dict[str, str] = {
    'development': "Development",
    'staging': "Staging",
    'production': "Production"
}

# Feature flags (for gradual rollout)
FEATURE_FLAGS: Dict[str, bool] = {
    'enable_achievements': False,
    'enable_social_features': False,
    'enable_gamification': True,
    'enable_notifications': True,
    'enable_analytics': True,
    'enable_export': True
}

# ==================== MISC CONSTANTS ====================

# Default values
DEFAULTS: Dict[str, any] = {
    'user_role': 'student',
    'question_difficulty': 'simple',
    'question_status': 'active',
    'payment_status': 'pending',
    'subscription_status': 'active',
    'leaderboard_period': 'weekly',
    'quiz_score': 0,
    'quiz_accuracy': 0.0
}

# Supported languages (for future i18n)
LANGUAGES: Dict[str, str] = {
    'en': 'English',
    'hi': 'Hindi',
    'te': 'Telugu',
    'ta': 'Tamil',
    'ml': 'Malayalam'
}

# ==================== VALIDATION REGEX PATTERNS ====================

REGEX_PATTERNS: Dict[str, str] = {
    'username': r'^[a-zA-Z0-9_]{5,32}$',
    'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'phone': r'^\+?[1-9]\d{7,14}$',
    'password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
    'url': r'^(https?://)?([\da-z.-]+)\.([a-z.]{2,6})([/\w .-]*)*/?$',
    'date_iso': r'^\d{4}-\d{2}-\d{2}$',
    'time_24h': r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
}