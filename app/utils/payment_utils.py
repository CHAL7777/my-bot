"""
Safe Payment Utilities - Payment System Redesign

This module provides safe, production-ready functions for checking payment status,
subscription eligibility, and handling edge cases. All functions are designed to:
- Handle missing columns gracefully
- Return safe default values for non-existent records
- Avoid crashes when database state is unexpected
- Provide clear, user-friendly error messages

Usage:
    from app.utils.payment_utils import (
        is_user_premium,
        has_active_subscription,
        get_safe_payment_status,
        can_user_make_payment
    )
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ============== Safe Payment Check Functions ==============

async def is_user_premium(user) -> bool:
    """
    Safely check if a user has lifetime premium access.
    
    This function handles:
    - User object is None
    - is_premium attribute doesn't exist (old database schemas)
    - is_premium is None
    
    Args:
        user: SQLAlchemy User model instance or None
        
    Returns:
        bool: True if user has lifetime premium, False otherwise
        
    Examples:
        >>> user = await user_repo.get_user(12345)
        >>> if is_user_premium(user):
        ...     print("User has premium access")
    """
    # Handle None user
    if user is None:
        return False
    
    # Safely get is_premium attribute with fallback
    # This handles cases where column doesn't exist in older schemas
    try:
        is_premium = getattr(user, 'is_premium', False)
        return bool(is_premium)
    except Exception as e:
        # Log but don't crash - fall back to approved flag
        logger.warning(f"Error checking is_premium for user {getattr(user, 'user_id', 'unknown')}: {e}")
        # Fall back to approved flag for backward compatibility
        return getattr(user, 'approved', False)


async def has_active_subscription(user, payment_repo) -> Dict[str, Any]:
    """
    Check if a user has an active subscription.
    
    This function handles:
    - No subscription records
    - Expired subscriptions
    - Missing subscription table/columns
    - Legacy subscription models
    
    Args:
        user: SQLAlchemy User model instance or None
        payment_repo: PaymentRepository instance for database queries
        
    Returns:
        Dict with keys:
        - has_subscription: bool
        - days_left: int or None
        - end_date: datetime or None
        - is_trial: bool
        
    Examples:
        >>> sub_status = await has_active_subscription(user, payment_repo)
        >>> if sub_status['has_subscription']:
        ...     print(f"Subscription valid for {sub_status['days_left']} days")
    """
    # Handle None user
    if user is None:
        return {
            'has_subscription': False,
            'days_left': None,
            'end_date': None,
            'is_trial': False,
            'reason': 'user_not_found'
        }
    
    try:
        # Try to get active subscription from repository
        subscription = await payment_repo.get_active_subscription(user.user_id)
        
        if subscription is None:
            return {
                'has_subscription': False,
                'days_left': None,
                'end_date': None,
                'is_trial': False,
                'reason': 'no_active_subscription'
            }
        
        # Calculate days remaining
        if hasattr(subscription, 'end_date') and subscription.end_date:
            now = datetime.utcnow()
            if subscription.end_date > now:
                days_left = (subscription.end_date - now).days
            else:
                days_left = 0
        else:
            days_left = None
        
        return {
            'has_subscription': subscription is not None,
            'days_left': days_left,
            'end_date': getattr(subscription, 'end_date', None),
            'is_trial': getattr(subscription, 'is_trial', False),
            'reason': None
        }
        
    except Exception as e:
        # If subscription table/column doesn't exist, treat as no subscription
        logger.warning(f"Error checking subscription for user {user.user_id}: {e}")
        return {
            'has_subscription': False,
            'days_left': None,
            'end_date': None,
            'is_trial': False,
            'reason': 'subscription_check_error'
        }


async def get_safe_payment_status(user, payment_repo) -> Dict[str, Any]:
    """
    Get a comprehensive, safe payment status for a user.
    
    This function provides a complete view of user's payment state,
    handling all edge cases gracefully.
    
    Args:
        user: SQLAlchemy User model instance or None
        payment_repo: PaymentRepository instance for database queries
        
    Returns:
        Dict containing:
        - is_premium: bool - Has lifetime premium access
        - has_active_subscription: bool - Has active subscription
        - subscription_details: dict or None
        - pending_payments: int - Count of pending payments
        - recent_payments: list - Last few payments
        - can_make_payment: bool - Whether user can initiate new payment
        - block_reason: str or None - Reason if payment is blocked
        
    Examples:
        >>> status = await get_safe_payment_status(user, payment_repo)
        >>> if status['is_premium']:
        ...     print("User has lifetime access")
        >>> elif status['can_make_payment']:
        ...     print("User can make a payment")
    """
    # Default response structure
    result = {
        'is_premium': False,
        'has_active_subscription': False,
        'subscription_details': None,
        'pending_payments': 0,
        'recent_payments': [],
        'can_make_payment': True,
        'block_reason': None
    }
    
    # Handle None user
    if user is None:
        result['block_reason'] = 'user_not_found'
        return result
    
    try:
        # Check premium status
        result['is_premium'] = await is_user_premium(user)
        
        if result['is_premium']:
            # User has lifetime premium - no need to check further
            result['can_make_payment'] = False
            result['block_reason'] = 'already_premium'
            return result
        
        # Check subscription status
        sub_status = await has_active_subscription(user, payment_repo)
        result['has_active_subscription'] = sub_status['has_subscription']
        result['subscription_details'] = sub_status
        
        if result['has_active_subscription']:
            result['can_make_payment'] = False
            result['block_reason'] = 'has_active_subscription'
            result['subscription_details'] = {
                'days_left': sub_status['days_left'],
                'end_date': sub_status['end_date'],
                'is_trial': sub_status['is_trial']
            }
            return result
        
        # Check for pending payments
        try:
            user_payments = await payment_repo.get_user_payments(user.user_id)
            pending_payments = [p for p in user_payments if p.status == 'pending']
            result['pending_payments'] = len(pending_payments)
            
            if result['pending_payments'] > 0:
                result['can_make_payment'] = False
                result['block_reason'] = 'pending_payment'
                result['pending_payment_id'] = pending_payments[0].payment_id if pending_payments else None
                return result
                
        except Exception as e:
            logger.warning(f"Error checking payments for user {user.user_id}: {e}")
            # Continue - pending check is not critical
        
        # User can make a payment
        result['can_make_payment'] = True
        result['block_reason'] = None
        
        # Get recent payment history (if available)
        try:
            user_payments = await payment_repo.get_user_payments(user.user_id)
            result['recent_payments'] = [
                {
                    'payment_id': p.payment_id,
                    'amount': getattr(p, 'amount', 0),
                    'status': p.status,
                    'created_at': p.created_at,
                    'approved_at': getattr(p, 'approved_at', None)
                }
                for p in user_payments[:5]  # Last 5 payments
            ]
        except Exception as e:
            logger.warning(f"Error getting payment history for user {user.user_id}: {e}")
            # Continue - payment history is not critical
        
        return result
        
    except Exception as e:
        logger.error(f"Critical error getting payment status for user {getattr(user, 'user_id', 'unknown')}: {e}")
        result['error'] = str(e)
        result['can_make_payment'] = False
        result['block_reason'] = 'error_checking_status'
        return result


async def can_user_make_payment(user, payment_repo) -> Dict[str, Any]:
    """
    Check if a user is eligible to make a new payment.
    
    This is a simplified check focusing only on whether the user
    can initiate a payment.
    
    Args:
        user: SQLAlchemy User model instance or None
        payment_repo: PaymentRepository instance for database queries
        
    Returns:
        Dict with keys:
        - can_pay: bool
        - reason: str or None (if can_pay is False)
        - payment_id: int or None (if pending payment exists)
        
    Examples:
        >>> eligibility = await can_user_make_payment(user, payment_repo)
        >>> if eligibility['can_pay']:
        ...     await initiate_payment(user.id)
        >>> else:
        ...     print(f"Cannot pay: {eligibility['reason']}")
    """
    # Handle None user
    if user is None:
        return {
            'can_pay': False,
            'reason': 'user_not_found',
            'payment_id': None
        }
    
    try:
        # Check premium status
        if await is_user_premium(user):
            return {
                'can_pay': False,
                'reason': 'already_premium',
                'payment_id': None
            }
        
        # Check subscription
        sub_status = await has_active_subscription(user, payment_repo)
        if sub_status['has_subscription']:
            return {
                'can_pay': False,
                'reason': 'has_active_subscription',
                'payment_id': None,
                'subscription_end': sub_status['end_date']
            }
        
        # Check for pending payments
        try:
            user_payments = await payment_repo.get_user_payments(user.user_id)
            pending_payments = [p for p in user_payments if p.status == 'pending']
            
            if pending_payments:
                return {
                    'can_pay': False,
                    'reason': 'pending_payment_exists',
                    'payment_id': pending_payments[0].payment_id
                }
        except Exception as e:
            logger.warning(f"Error checking pending payments for user {user.user_id}: {e}")
        
        # User can make a payment
        return {
            'can_pay': True,
            'reason': None,
            'payment_id': None
        }
        
    except Exception as e:
        logger.error(f"Error checking payment eligibility for user {user.user_id}: {e}")
        return {
            'can_pay': False,
            'reason': 'error_checking_eligibility',
            'payment_id': None
        }


# ============== Admin Review Utilities ==============

async def get_pending_payments_safe(payment_repo, user_repo, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get pending payments with user details, handling all edge cases.
    
    Args:
        payment_repo: PaymentRepository instance
        user_repo: UserRepository instance
        limit: Maximum number of payments to return
        
    Returns:
        List of payment dicts with user info, safely handling missing data
    """
    try:
        pending_payments = await payment_repo.get_pending_payments(limit=limit)
        result = []
        
        for payment in pending_payments:
            try:
                user = await user_repo.get_user(payment.user_id)
                
                payment_info = {
                    'payment_id': payment.payment_id,
                    'user_id': payment.user_id,
                    'username': getattr(user, 'username', None) if user else None,
                    'first_name': getattr(user, 'first_name', 'Unknown', ) if user else 'Unknown',
                    'last_name': getattr(user, 'last_name', None) if user else None,
                    'amount': getattr(payment, 'amount', 0),
                    'subscription_days': getattr(payment, 'subscription_days', 30),
                    'created_at': payment.created_at,
                    'screenshot_file_id': getattr(payment, 'screenshot_file_id', None),
                    'screenshot_file_path': getattr(payment, 'screenshot_file_path', None),
                    'transaction_id': getattr(payment, 'transaction_id', None),
                    'notes': getattr(payment, 'notes', None)
                }
                result.append(payment_info)
                
            except Exception as e:
                logger.warning(f"Error processing payment {payment.payment_id}: {e}")
                # Include payment with minimal info
                result.append({
                    'payment_id': payment.payment_id,
                    'user_id': payment.user_id,
                    'username': None,
                    'first_name': 'Unknown',
                    'amount': getattr(payment, 'amount', 0),
                    'error': str(e)
                })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting pending payments: {e}")
        return []


# ============== Error Message Utilities ==============

def get_payment_error_message(error_key: str, **kwargs) -> str:
    """
    Get user-friendly error messages for payment errors.
    
    Args:
        error_key: Key identifying the type of error
        **kwargs: Additional context for the message
        
    Returns:
        User-friendly error message string
    """
    error_messages = {
        'already_premium': (
            "✅ You've already unlocked full access!\n\n"
            "Your account is approved and you have access to all quiz levels. "
            "No additional payment is needed.\n\n"
            "Use /quiz to start learning!"
        ),
        'has_active_subscription': (
            "📅 You already have an active subscription!\n\n"
            "Your subscription is valid until {end_date}. "
            "No additional payment is needed."
        ),
        'pending_payment_exists': (
            "⏳ Payment Already Pending\n\n"
            "You have a payment (ID: #{payment_id}) waiting for review.\n"
            "Please wait for admin approval before submitting a new payment.\n\n"
            "Contact @admin if you need assistance."
        ),
        'user_not_found': (
            "❌ User account not found.\n\n"
            "Please start a conversation with the bot first using /start."
        ),
        'subscription_check_error': (
            "⚠️ Unable to verify subscription status.\n\n"
            "Please try again later or contact support."
        ),
        'error_checking_eligibility': (
            "❌ Error checking payment eligibility.\n\n"
            "Please try again later or contact support."
        ),
        'screenshot_upload_failed': (
            "❌ Failed to process screenshot.\n\n"
            "Please ensure you upload a valid image file."
        ),
        'payment_approval_failed': (
            "❌ Payment approval failed.\n\n"
            "Error: {error}\n\n"
            "Please try again or contact support."
        ),
        'payment_rejection_failed': (
            "❌ Payment rejection failed.\n\n"
            "Error: {error}\n\n"
            "Please try again or contact support."
        )
    }
    
    message = error_messages.get(error_key, "An unexpected error occurred.")
    
    # Format message with provided kwargs
    if kwargs:
        message = message.format(**kwargs)
    
    return message


# ============== Database Migration Helpers ==============

def check_column_exists(session, table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a table (MySQL/MariaDB specific).
    
    Args:
        session: SQLAlchemy session
        table_name: Name of the table
        column_name: Name of the column to check
        
    Returns:
        True if column exists, False otherwise
    """
    try:
        from sqlalchemy import text
        result = session.execute(
            text(f"SHOW COLUMNS FROM {table_name} LIKE '{column_name}'")
        )
        return result.fetchone() is not None
    except Exception:
        return False


def add_missing_columns(session, model_class, column_definitions: dict):
    """
    Add missing columns to a table.
    
    Args:
        session: SQLAlchemy session
        model_class: SQLAlchemy model class
        column_definitions: Dict of column_name -> column_definition
    """
    from sqlalchemy import text
    
    table_name = model_class.__tablename__
    
    for column_name, column_def in column_definitions.items():
        if not check_column_exists(session, table_name, column_name):
            try:
                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_def}"
                session.execute(text(alter_sql))
                session.commit()
                logger.info(f"Added column {column_name} to {table_name}")
            except Exception as e:
                logger.error(f"Failed to add column {column_name}: {e}")
                session.rollback()

