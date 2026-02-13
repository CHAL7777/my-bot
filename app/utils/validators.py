import re
import os
from typing import Optional, Tuple, List
from datetime import datetime

class InputValidator:
    @staticmethod
    def validate_telegram_input(text: str, max_length: int = 4000) -> Optional[str]:
        """Sanitize and validate Telegram input"""
        if not text or not isinstance(text, str):
            return None
        
        # Remove potential harmful characters
        text = re.sub(r'[<>{}[\]\\]', '', text)
        
        # Trim whitespace
        text = text.strip()
        
        # Check length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text if text else None
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username:
            return False
        
        # Telegram username format
        pattern = r'^[a-zA-Z0-9_]{5,32}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Check if it's a valid length (10-15 digits)
        return 10 <= len(digits) <= 15
    
    @staticmethod
    def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
        """Validate date string"""
        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_file_upload(file_info: dict) -> Tuple[bool, str]:
        """Validate uploaded file"""
        allowed_types = {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'image/gif': ['.gif'],
            'application/pdf': ['.pdf'],
            'text/csv': ['.csv']
        }
        
        max_size = 10 * 1024 * 1024  # 10MB
        
        # Check file type
        mime_type = file_info.get('mime_type', '')
        if mime_type not in allowed_types:
            return False, f"File type {mime_type} not allowed"
        
        # Check file size
        file_size = file_info.get('file_size', 0)
        if file_size > max_size:
            return False, f"File size {file_size} exceeds limit of {max_size}"
        
        # Check file extension
        file_name = file_info.get('file_name', '')
        if not file_name:
            return False, "No filename provided"
        
        _, ext = os.path.splitext(file_name)
        allowed_extensions = allowed_types.get(mime_type, [])
        
        if ext.lower() not in allowed_extensions:
            return False, f"File extension {ext} not allowed for {mime_type}"
        
        return True, "File validation passed"
    
    @staticmethod
    def validate_csv_row(row: dict, row_num: int) -> List[str]:
        """Validate a CSV row for question import"""
        errors = []
        
        required_fields = [
            'subject', 'chapter', 'difficulty', 'question_text',
            'option_a', 'option_b', 'option_c', 'option_d',
            'correct_option', 'explanation'
        ]
        
        # Helper function to safely get field value
        def get_field_value(field):
            if field not in row:
                return ""
            value = row[field]
            # Handle None values and convert to stripped string
            if value is None:
                return ""
            if not isinstance(value, str):
                value = str(value)
            return value.strip()
        
        # Check required fields
        for field in required_fields:
            field_value = get_field_value(field)
            if not field_value:
                errors.append(f"Row {row_num}: Missing required field '{field}'")
        
        # Validate difficulty
        difficulty_raw = row.get('difficulty')
        if difficulty_raw is not None:
            if isinstance(difficulty_raw, str):
                difficulty = difficulty_raw.lower().strip()
            else:
                difficulty = str(difficulty_raw).lower().strip()
            if difficulty not in ['simple', 'medium', 'hard']:
                errors.append(f"Row {row_num}: Invalid difficulty '{difficulty}'")
        
        # Validate correct option
        correct_raw = row.get('correct_option')
        if correct_raw is not None:
            if isinstance(correct_raw, str):
                correct_option = correct_raw.upper().strip()
            else:
                correct_option = str(correct_raw).upper().strip()
            if correct_option not in ['A', 'B', 'C', 'D']:
                errors.append(f"Row {row_num}: Invalid correct_option '{correct_option}'")
        
        # Check for duplicate options
        option_a_raw = row.get('option_a')
        option_b_raw = row.get('option_b')
        option_c_raw = row.get('option_c')
        option_d_raw = row.get('option_d')
        
        if all(v is not None for v in [option_a_raw, option_b_raw, option_c_raw, option_d_raw]):
            if isinstance(option_a_raw, str):
                options = [option_a_raw.strip(), option_b_raw.strip(), option_c_raw.strip(), option_d_raw.strip()]
            else:
                options = [str(option_a_raw).strip(), str(option_b_raw).strip(), str(option_c_raw).strip(), str(option_d_raw).strip()]
            if len(set(options)) != 4:
                errors.append(f"Row {row_num}: Options must be unique")
        
        # Check question length
        question_raw = row.get('question_text')
        if question_raw is not None:
            if isinstance(question_raw, str):
                question_text = question_raw.strip()
            else:
                question_text = str(question_raw).strip()
            if len(question_text) > 1000:
                errors.append(f"Row {row_num}: Question text too long (max 1000 characters)")
        
        return errors
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML text"""
        if not text:
            return ""
        
        # Remove script tags
        text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove other dangerous tags
        dangerous_tags = ['iframe', 'object', 'embed', 'link', 'meta', 'style']
        for tag in dangerous_tags:
            text = re.sub(f'<{tag}.*?>.*?</{tag}>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Escape remaining HTML
        text = (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))
        
        return text
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong"


# Module-level wrapper functions for convenience imports
def validate_telegram_input(text: str, max_length: int = 4000) -> Optional[str]:
    return InputValidator.validate_telegram_input(text, max_length)


def validate_username(username: str) -> bool:
    return InputValidator.validate_username(username)


def validate_email(email: str) -> bool:
    return InputValidator.validate_email(email)


def validate_phone(phone: str) -> bool:
    return InputValidator.validate_phone(phone)


def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
    return InputValidator.validate_date(date_str, format)


def validate_file_upload(file_info: dict) -> Tuple[bool, str]:
    return InputValidator.validate_file_upload(file_info)


def validate_csv_row(row: dict, row_num: int) -> List[str]:
    return InputValidator.validate_csv_row(row, row_num)


def sanitize_html(text: str) -> str:
    return InputValidator.sanitize_html(text)


def validate_password(password: str) -> Tuple[bool, str]:
    return InputValidator.validate_password(password)