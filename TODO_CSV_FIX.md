# CSV Import Fix - TODO

## Task
Fix the "Could not determine delimiter csv file not uploaded" error.

## Issues Identified
1. Missing file: `admin_panel/utils/csv_handler.py`
2. CSV delimiter detection can fail with edge cases

## Implementation Steps

### Step 1: Create admin_panel/utils/__init__.py
- [x] Create package initialization file

### Step 2: Create admin_panel/utils/csv_handler.py
- [x] Create CSV validation and processing module
- [x] Add robust delimiter detection with fallback
- [x] Implement question validation logic

### Step 3: Improve app/utils/csv_importer.py
- [x] Add fallback to comma delimiter when sniffer fails
- [x] Add better error handling for delimiter detection
- [x] Improve error messages

## Files Created
- admin_panel/utils/__init__.py
- admin_panel/utils/csv_handler.py

## Files Modified
- app/utils/csv_importer.py

## Testing
- [ ] Test CSV upload from Telegram bot
- [ ] Test CSV upload from admin panel
- [ ] Test with various CSV formats (comma, semicolon, tab)
- [ ] Test with edge cases (empty file, single row, etc.)

