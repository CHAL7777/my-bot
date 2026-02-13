import csv
import os
import asyncio
import io
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from app.db.base import get_db
from app.repositories.question_repo import QuestionRepository
from app.utils.validators import InputValidator


class CSVHandler:
    """Utility class for CSV handling with robust delimiter detection."""
    
    DELIMITERS = [',', ';', '\t', '|']
    
    @staticmethod
    def detect_delimiter(content: str) -> str:
        """
        Detect CSV delimiter with multiple fallback strategies.
        
        Args:
            content: CSV file content as string
            
        Returns:
            Detected delimiter
        """
        # Try Python's csv.Sniffer first
        try:
            sample = content[:10240]
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except csv.Error:
            pass
        
        # Fallback to counting delimiters in first line
        lines = content.split('\n')[:5]
        if not lines:
            return ','
        
        first_line = lines[0]
        delimiter_counts = {}
        
        for delim in CSVHandler.DELIMITERS:
            count = first_line.count(delim)
            if count > 0:
                delimiter_counts[delim] = count
        
        if delimiter_counts:
            return max(delimiter_counts, key=delimiter_counts.get)
        
        # Default to comma
        return ','
    
    @staticmethod
    def parse_csv(content: str, delimiter: str = None) -> Tuple[List[Dict], str]:
        """
        Parse CSV content with robust delimiter handling.
        
        Args:
            content: CSV content as string
            delimiter: Optional delimiter override
            
        Returns:
            Tuple of (rows, detected_delimiter)
        """
        detected = delimiter or CSVHandler.detect_delimiter(content)
        rows = []
        
        try:
            reader = csv.DictReader(io.StringIO(content), delimiter=detected)
            rows = list(reader)
        except Exception:
            # Try alternative delimiters if primary fails
            for alt_delim in CSVHandler.DELIMITERS:
                if alt_delim != detected:
                    try:
                        reader = csv.DictReader(io.StringIO(content), delimiter=alt_delim)
                        rows = list(reader)
                        detected = alt_delim
                        break
                    except Exception:
                        continue
        
        return rows, detected


class CSVImporter:
    def __init__(self):
        self.validator = InputValidator()
        self.required_columns = [
            'subject', 'chapter', 'difficulty', 'question_text',
            'option_a', 'option_b', 'option_c', 'option_d',
            'correct_option', 'explanation'
        ]
    
    async def import_from_file(self, file_path: str, 
                             admin_id: int = None) -> Dict[str, any]:
        """
        Import questions from CSV file
        Returns: statistics and errors
        """
        stats = {
            'total_rows': 0,
            'valid_rows': 0,
            'imported': 0,
            'skipped': 0,
            'errors': [],
            'start_time': datetime.now(),
            'end_time': None,
            'duration': None
        }
        
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                stats['errors'].append(f"File not found: {file_path}")
                return stats
            
            # Read CSV file with robust delimiter detection
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Use robust CSV handler
                rows, detected_delimiter = CSVHandler.parse_csv(content)
                
                # Check for header
                has_header = False
                if rows:
                    normalized_fields = [f.strip().lower() for f in rows[0].keys()]
                    required_normalized = [r.lower() for r in self.required_columns]
                    if all(req in normalized_fields for req in required_normalized):
                        has_header = True
                
                # Remove header row if present
                if has_header and rows:
                    rows = rows[1:]
                
                # Create reader for validation (using detected delimiter)
                reader = csv.DictReader(io.StringIO(content), delimiter=detected_delimiter)
                fieldnames = reader.fieldnames if reader else []
                
                # Validate columns
                missing_columns = set(self.required_columns) - set(reader.fieldnames)
                if missing_columns:
                    stats['errors'].append(f"Missing required columns: {missing_columns}")
                    return stats
                
                # Process rows
                async for session in get_db():
                    question_repo = QuestionRepository(session)
                    
                    for row_num, row in enumerate(reader, start=2 if has_header else 1):
                        stats['total_rows'] += 1
                        
                        # Validate row
                        row_errors = self.validator.validate_csv_row(row, row_num)
                        
                        if row_errors:
                            stats['errors'].extend(row_errors)
                            stats['skipped'] += 1
                            continue
                        
                        # Clean and prepare data
                        cleaned_row = self._clean_row(row)
                        
                        try:
                            # Import question
                            await self._import_question(question_repo, cleaned_row)
                            stats['imported'] += 1
                            stats['valid_rows'] += 1
                            
                        except Exception as e:
                            stats['errors'].append(f"Row {row_num}: Import failed - {str(e)}")
                            stats['skipped'] += 1
        
        except Exception as e:
            stats['errors'].append(f"File processing error: {str(e)}")
        
        finally:
            stats['end_time'] = datetime.now()
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
            
            # Log import results
            self._log_import(stats, admin_id)
        
        return stats
    
    def _clean_row(self, row: Dict[str, str]) -> Dict[str, str]:
        """Clean CSV row data"""
        cleaned = {}

        for key, value in row.items():
            # Safely handle None values
            if value is None:
                cleaned_value = ""
            elif isinstance(value, str):
                # Strip whitespace
                cleaned_value = value.strip()

                # Handle special cases
                if key == 'difficulty':
                    cleaned_value = cleaned_value.lower()
                elif key == 'correct_option':
                    cleaned_value = cleaned_value.upper()
                elif key in ['question_text', 'explanation']:
                    # Preserve newlines in text fields
                    cleaned_value = cleaned_value.replace('\\n', '\n')

                cleaned[key] = cleaned_value
            else:
                cleaned[key] = str(value).strip() if value is not None else ""

        return cleaned
    
    async def _import_question(self, question_repo: QuestionRepository, 
                             row: Dict[str, str]) -> None:
        """Import a single question"""
        # Get or create subject
        subject = await question_repo.get_subject_by_name(row['subject'])
        if not subject:
            subject = await question_repo.create_subject(
                subject_name=row['subject']
            )
        
        # Get or create chapter
        chapters = await question_repo.get_chapters(subject.subject_id)
        chapter = next((c for c in chapters if c.chapter_name == row['chapter']), None)
        
        if not chapter:
            # Determine next order number
            max_order = max([c.chapter_order for c in chapters], default=0)
            chapter = await question_repo.create_chapter(
                subject_id=subject.subject_id,
                chapter_name=row['chapter'],
                chapter_order=max_order + 1
            )
        
        # Check for duplicate question
        existing_questions = await question_repo.search_questions(
            row['question_text'][:100],  # Search by first 100 chars
            limit=5
        )
        
        for existing in existing_questions:
            if (existing.subject_id == subject.subject_id and 
                existing.chapter_id == chapter.chapter_id and
                existing.question_text == row['question_text']):
                raise Exception("Duplicate question found")
        
        # Create question
        await question_repo.create_question(
            subject_id=subject.subject_id,
            chapter_id=chapter.chapter_id,
            difficulty=row['difficulty'],
            question_text=row['question_text'],
            option_a=row['option_a'],
            option_b=row['option_b'],
            option_c=row['option_c'],
            option_d=row['option_d'],
            correct_option=row['correct_option'],
            explanation=row.get('explanation', '')
        )
    
    def _log_import(self, stats: Dict[str, any], admin_id: int = None):
        """Log import results"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': admin_id,
            'stats': stats
        }
        
        # Save to log file
        log_file = os.path.join('data', 'import_logs.json')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        import json
        try:
            # Read existing logs
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Add new log
            logs.append(log_entry)
            
            # Keep only last 100 logs
            if len(logs) > 100:
                logs = logs[-100:]
            
            # Write back
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            print(f"Failed to write import log: {e}")
    
    def generate_template(self, file_path: str) -> bool:
        """Generate CSV template file"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=self.required_columns)
                writer.writeheader()
                
                # Add example rows
                examples = [
                    {
                        'subject': 'Mathematics',
                        'chapter': 'Addition',
                        'difficulty': 'simple',
                        'question_text': 'What is 2 + 2?',
                        'option_a': '3',
                        'option_b': '4',
                        'option_c': '5',
                        'option_d': '6',
                        'correct_option': 'B',
                        'explanation': '2 + 2 equals 4'
                    },
                    {
                        'subject': 'Science',
                        'chapter': 'Physics',
                        'difficulty': 'medium',
                        'question_text': 'What is the unit of force?',
                        'option_a': 'Joule',
                        'option_b': 'Watt',
                        'option_c': 'Newton',
                        'option_d': 'Pascal',
                        'correct_option': 'C',
                        'explanation': 'Force is measured in Newtons (N)'
                    }
                ]
                
                for example in examples:
                    writer.writerow(example)
            
            return True
            
        except Exception as e:
            print(f"Failed to generate template: {e}")
            return False
    
    async def validate_file(self, file_path: str) -> Tuple[bool, List[str], int]:
        """Validate CSV file without importing"""
        errors = []
        valid_rows = 0
        
        try:
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
                return False, errors, valid_rows
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Use robust CSV handler
                rows, detected_delimiter = CSVHandler.parse_csv(content)
                
                # Check for header
                has_header = False
                if rows:
                    normalized_fields = [f.strip().lower() for f in rows[0].keys()]
                    required_normalized = [r.lower() for r in self.required_columns]
                    if all(req in normalized_fields for req in required_normalized):
                        has_header = True
                
                # Create reader for validation
                reader = csv.DictReader(io.StringIO(content), delimiter=detected_delimiter)
                
                # Validate columns
                missing_columns = set(self.required_columns) - set(reader.fieldnames)
                if missing_columns:
                    errors.append(f"Missing required columns: {missing_columns}")
                    return False, errors, valid_rows
                
                # Validate rows
                for row_num, row in enumerate(reader, start=2 if has_header else 1):
                    row_errors = self.validator.validate_csv_row(row, row_num)
                    
                    if row_errors:
                        errors.extend(row_errors)
                    else:
                        valid_rows += 1
                    
                    # Stop after 100 errors or 1000 rows
                    if len(errors) >= 100 or row_num >= 1000:
                        break
            
            return len(errors) == 0, errors, valid_rows
            
        except Exception as e:
            errors.append(f"File validation error: {str(e)}")
            return False, errors, valid_rows