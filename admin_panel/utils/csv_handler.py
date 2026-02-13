"""
CSV Handler for Admin Panel - Validates and processes CSV files for question import.
"""

import csv
import io
from typing import List, Dict, Tuple, Any, Optional
from app.utils.validators import InputValidator


class CSVHandler:
    """Handle CSV validation and processing for question imports."""
    
    REQUIRED_COLUMNS = [
        'subject', 'chapter', 'difficulty', 'question_text',
        'option_a', 'option_b', 'option_c', 'option_d',
        'correct_option', 'explanation'
    ]
    
    VALID_DIFFICULTIES = ['simple', 'medium', 'hard']
    VALID_CORRECT_OPTIONS = ['A', 'B', 'C', 'D']
    
    def __init__(self):
        self.validator = InputValidator()
    
    def detect_delimiter(self, content: str) -> str:
        """
        Detect CSV delimiter with multiple fallback strategies.
        
        Args:
            content: CSV file content as string
            
        Returns:
            Detected delimiter (comma, semicolon, tab, or pipe)
        """
        # Common delimiters to check
        delimiters = [',', ';', '\t', '|']
        
        # Read first few lines to analyze
        lines = content.split('\n')[:5]
        if not lines:
            return ','
        
        first_line = lines[0]
        
        # Count occurrences of each delimiter
        delimiter_counts = {}
        for delim in delimiters:
            count = first_line.count(delim)
            if count > 0:
                delimiter_counts[delim] = count
        
        if delimiter_counts:
            # Return the most common delimiter
            return max(delimiter_counts, key=delimiter_counts.get)
        
        # Default to comma if no delimiter found
        return ','
    
    def sniff_csv_dialect(self, content: str) -> Optional[str]:
        """
        Try to detect CSV dialect using Python's csv.Sniffer.
        
        Args:
            content: CSV file content
            
        Returns:
            Detected delimiter or None if detection fails
        """
        try:
            # Take a sample for sniffing (first 10KB)
            sample = content[:10240]
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except csv.Error:
            # Sniffer failed, will use fallback detection
            return None
    
    def parse_csv(self, content: str, delimiter: str = None) -> Tuple[List[Dict], str]:
        """
        Parse CSV content into list of dictionaries.
        
        Args:
            content: CSV file content as string
            delimiter: Optional delimiter to use (auto-detect if None)
            
        Returns:
            Tuple of (rows list, detected delimiter)
        """
        rows = []
        detected_delimiter = delimiter
        
        # Auto-detect delimiter if not provided
        if detected_delimiter is None:
            # First try sniffer
            detected_delimiter = self.sniff_csv_dialect(content)
            
            # If sniffer failed, use our custom detection
            if detected_delimiter is None:
                detected_delimiter = self.detect_delimiter(content)
        
        try:
            reader = csv.DictReader(
                io.StringIO(content),
                delimiter=detected_delimiter
            )
            rows = list(reader)
        except Exception as e:
            # If parsing with detected delimiter fails, try common alternatives
            for alt_delim in [',', ';', '\t']:
                if alt_delim != detected_delimiter:
                    try:
                        reader = csv.DictReader(
                            io.StringIO(content),
                            delimiter=alt_delim
                        )
                        rows = list(reader)
                        detected_delimiter = alt_delim
                        break
                    except Exception:
                        continue
            
            if not rows:
                raise ValueError(f"Failed to parse CSV: {str(e)}")
        
        return rows, detected_delimiter
    
    def validate_header(self, fieldnames: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate CSV header contains all required columns.
        
        Args:
            fieldnames: List of column names from CSV
            
        Returns:
            Tuple of (is_valid, list of missing columns)
        """
        # Normalize field names (strip whitespace, lowercase)
        normalized_fields = [f.strip().lower() for f in fieldnames]
        required_normalized = [r.lower() for r in self.REQUIRED_COLUMNS]
        
        missing = set(required_normalized) - set(normalized_fields)
        
        return len(missing) == 0, list(missing)
    
    def validate_row(self, row: Dict, row_num: int) -> List[str]:
        """
        Validate a single CSV row.
        
        Args:
            row: Dictionary of row data
            row_num: Row number for error messages
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Helper function to safely get and strip field value
        def get_field_value(field: str) -> str:
            """Safely get field value, handling None and non-string types"""
            value = row.get(field)
            if value is None:
                return ""
            if not isinstance(value, str):
                value = str(value)
            return value.strip()
        
        # Check required fields
        for field in self.REQUIRED_COLUMNS:
            value = get_field_value(field)
            if not value:
                errors.append(f"Row {row_num}: Missing required field '{field}'")
        
        # Validate difficulty
        if row.get('difficulty'):
            difficulty = str(row['difficulty']).strip().lower()
            if difficulty not in self.VALID_DIFFICULTIES:
                errors.append(
                    f"Row {row_num}: Invalid difficulty '{difficulty}'. "
                    f"Must be one of: {', '.join(self.VALID_DIFFICULTIES)}"
                )
        
        # Validate correct option
        if row.get('correct_option'):
            correct = str(row['correct_option']).strip().upper()
            if correct not in self.VALID_CORRECT_OPTIONS:
                errors.append(
                    f"Row {row_num}: Invalid correct_option '{correct}'. "
                    f"Must be one of: {', '.join(self.VALID_CORRECT_OPTIONS)}"
                )
        
        # Check for unique options
        options = [
            str(row.get('option_a', '')).strip(),
            str(row.get('option_b', '')).strip(),
            str(row.get('option_c', '')).strip(),
            str(row.get('option_d', '')).strip(),
        ]
        
        if len(set(options)) != 4:
            errors.append(f"Row {row_num}: All four options must be unique")
        
        # Check question length
        if row.get('question_text'):
            question_text = str(row['question_text']).strip()
            if len(question_text) > 1000:
                errors.append(
                    f"Row {row_num}: Question text too long "
                    f"({len(question_text)} chars, max 1000)"
                )
        
        return errors
    
    def validate_and_process_csv(self, content: str) -> Dict[str, Any]:
        """
        Validate and process CSV content.
        
        Args:
            content: CSV file content as string
            
        Returns:
            Dictionary with validation results and statistics
        """
        results = {
            'success': False,
            'valid': False,
            'rows_processed': 0,
            'valid_rows': 0,
            'invalid_rows': 0,
            'errors': [],
            'questions': [],
            'delimiter': ',',
            'message': ''
        }
        
        try:
            # Parse CSV
            rows, detected_delimiter = self.parse_csv(content)
            results['delimiter'] = detected_delimiter
            
            if not rows:
                results['errors'].append("CSV file is empty or contains no valid rows")
                results['message'] = "No questions found in CSV file"
                return results
            
            # Validate header
            fieldnames = list(rows[0].keys()) if rows else []
            is_valid, missing_cols = self.validate_header(fieldnames)
            
            if not is_valid:
                results['errors'].append(
                    f"Missing required columns: {', '.join(missing_cols)}. "
                    f"Required columns: {', '.join(self.REQUIRED_COLUMNS)}"
                )
                results['message'] = "Invalid CSV format: missing required columns"
                return results
            
            # Validate rows
            valid_questions = []
            all_errors = []
            
            for row_num, row in enumerate(rows, start=2):  # Start at 2 (1-based, after header)
                results['rows_processed'] += 1
                
                # Clean row keys (strip whitespace)
                cleaned_row = {k.strip(): v for k, v in row.items()}
                
                # Validate row
                row_errors = self.validate_row(cleaned_row, row_num)
                
                if row_errors:
                    all_errors.extend(row_errors)
                    results['invalid_rows'] += 1
                else:
                    valid_questions.append(cleaned_row)
                    results['valid_rows'] += 1
            
            results['questions'] = valid_questions
            results['errors'] = all_errors[:50]  # Limit to first 50 errors
            
            # Determine success
            results['valid'] = results['valid_rows'] > 0
            results['success'] = True
            
            if results['valid']:
                results['message'] = (
                    f"Successfully validated {results['valid_rows']} questions "
                    f"out of {results['rows_processed']} rows"
                )
            else:
                results['message'] = (
                    f"Validation failed: {results['invalid_rows']} invalid rows"
                )
                if all_errors:
                    results['message'] += f". First error: {all_errors[0]}"
            
        except Exception as e:
            results['errors'].append(f"Error processing CSV: {str(e)}")
            results['message'] = f"CSV processing failed: {str(e)}"
        
        return results


async def validate_and_process_csv(
    content: str, 
    question_repo = None
) -> Dict[str, Any]:
    """
    Convenience function to validate and process CSV content.
    
    Args:
        content: CSV file content as string
        question_repo: Optional QuestionRepository instance
        
    Returns:
        Dictionary with validation results
    """
    handler = CSVHandler()
    return handler.validate_and_process_csv(content)

