"""
Utility modules for the Telegram Quiz Bot
"""

from app.utils.constants import (
    DIFFICULTY_POINTS,
    SUBSCRIPTION_PRICES,
    DAILY_QUIZ_LIMIT,
    MAX_QUESTIONS_PER_QUIZ,
    ACCURACY_THRESHOLDS,
    PERFORMANCE_MESSAGES,
    EMOJIS,
    BOT_COMMANDS,
    ADMIN_COMMANDS
)

from app.utils.helpers import (
    format_time,
    format_number,
    truncate_text,
    format_datetime,
    calculate_percentage,
    get_difficulty_emoji,
    format_currency,
    safe_get,
    generate_progress_bar
)

from app.utils.validators import (
    InputValidator,
    validate_telegram_input,
    validate_username,
    validate_email,
    validate_phone,
    validate_date,
    validate_file_upload,
    validate_csv_row,
    sanitize_html,
    validate_password
)

from app.utils.csv_importer import (
    CSVImporter
)

from app.utils.payment_utils import (
    is_user_premium,
    has_active_subscription,
    get_safe_payment_status,
    can_user_make_payment,
    get_pending_payments_safe,
    get_payment_error_message
)

__all__ = [
    # Constants
    'DIFFICULTY_POINTS',
    'SUBSCRIPTION_PRICES',
    'DAILY_QUIZ_LIMIT',
    'MAX_QUESTIONS_PER_QUIZ',
    'ACCURACY_THRESHOLDS',
    'PERFORMANCE_MESSAGES',
    'EMOJIS',
    'BOT_COMMANDS',
    'ADMIN_COMMANDS',
    
    # Helpers
    'format_time',
    'format_number',
    'truncate_text',
    'format_datetime',
    'calculate_percentage',
    'get_difficulty_emoji',
    'format_currency',
    'safe_get',
    'generate_progress_bar',
    
    # Validators
    'InputValidator',
    'validate_telegram_input',
    'validate_username',
    'validate_email',
    'validate_phone',
    'validate_date',
    'validate_file_upload',
    'validate_csv_row',
    'sanitize_html',
    'validate_password',
    
    # CSV Importer
    'CSVImporter',
    
    # Payment Utilities (NEW - Safe Payment Handling)
    'is_user_premium',
    'has_active_subscription',
    'get_safe_payment_status',
    'can_user_make_payment',
    'get_pending_payments_safe',
    'get_payment_error_message',
]

# Version information
__version__ = '1.0.0'
__author__ = 'Quiz Bot Team'
__description__ = 'Utility functions for Telegram Quiz Bot'