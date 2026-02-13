import csv

# Read the CSV file
with open('data/questions/pyscho.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print('=== CSV Validation Report ===')
print(f'Total questions: {len(rows)}')

# Comprehensive validation
errors = []

for i, row in enumerate(rows, start=2):
    # Check required fields
    required_fields = ['subject', 'chapter', 'difficulty', 'question_text',
                       'option_a', 'option_b', 'option_c', 'option_d',
                       'correct_option', 'explanation']
    
    for field in required_fields:
        value = row.get(field, '')
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(f'Row {i}: Missing required field {field}')
    
    # Validate difficulty
    difficulty = row.get('difficulty', '').strip().lower()
    if difficulty and difficulty not in ['simple', 'medium', 'hard']:
        errors.append(f'Row {i}: Invalid difficulty {difficulty}')
    
    # Validate correct option
    correct = row.get('correct_option', '').strip().upper()
    if correct and correct not in ['A', 'B', 'C', 'D']:
        errors.append(f'Row {i}: Invalid correct_option {correct}')
    
    # Check for duplicate options
    options = [row.get('option_a', '').strip(), row.get('option_b', '').strip(),
               row.get('option_c', '').strip(), row.get('option_d', '').strip()]
    if all(options) and len(set(options)) != 4:
        errors.append(f'Row {i}: Options must be unique')
    
    # Check question length
    question_text = row.get('question_text', '').strip()
    if len(question_text) > 1000:
        errors.append(f'Row {i}: Question text too long ({len(question_text)} chars)')

# Summary
print(f'ERRORS: {len(errors)}')
if errors:
    for err in errors[:20]:
        print(f'  - {err}')
    if len(errors) > 20:
        print(f'  ... and {len(errors) - 20} more errors')
print()

if not errors:
    print('All questions passed validation!')
else:
    print(f'Found {len(errors)} validation errors')

