#!/usr/bin/env python3
"""
CSV Fixing Script for pyscho.csv
Validates and fixes CSV formatting issues:
- Wraps text fields in double quotes
- Escapes internal quotes
- Ensures proper CSV format for Excel/Google Sheets
"""

import csv
import re

def escape_csv_field(field):
    """Escape a field for CSV output"""
    if field is None:
        return ""
    field_str = str(field)
    # Escape internal double quotes by doubling them
    field_str = field_str.replace('"', '""')
    # Wrap in double quotes
    return f'"{field_str}"'

def fix_csv(input_path, output_path):
    """Fix the CSV file"""
    rows = []
    
    # Read the original CSV
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    print(f"Read {len(rows)} questions from {input_path}")
    print(f"Columns: {fieldnames}")
    
    # Write the fixed CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header (not quoted per CSV standard, but can be if needed)
        writer.writerow(fieldnames)
        
        # Write data rows with proper quoting
        text_fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation']
        
        for row in rows:
            # Keep subject, chapter, difficulty, correct_option as-is (no quotes needed)
            # Wrap text fields in quotes
            fixed_row = []
            for field in fieldnames:
                if field in text_fields:
                    fixed_row.append(escape_csv_field(row.get(field, '')))
                else:
                    fixed_row.append(row.get(field, ''))
            writer.writerow(fixed_row)
    
    print(f"Wrote {len(rows)} fixed questions to {output_path}")

if __name__ == "__main__":
    input_file = "data/questions/pyscho.csv"
    output_file = "data/questions/pyscho_fixed.csv"
    
    fix_csv(input_file, output_file)
    print("CSV fixing complete!")

