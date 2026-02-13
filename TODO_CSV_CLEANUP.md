# CSV Cleanup Plan for pyscho.csv

## Issues Identified

1. **Malformed triple quotes** - Lines with `"""text"""` instead of properly escaped `"text"`
2. **Truncated question** - "Which Big Five trait relates to curiosity" is incomplete
3. **Inconsistent quoting** - Mix of quoted and unquoted text fields
4. **Missing proper escaping** - Internal quotes need escaping with `""`

## Corrections Needed

### Fix 1: Convert triple quotes to single properly escaped quotes
- `"""Question?"""` → `"Question?"`
- `"""Option text"""` → `"Option text"`

### Fix 2: Complete the truncated question
- "Which Big Five trait relates to curiosity" needs completion based on Big Five traits

### Fix 3: Ensure all text fields are wrapped in double quotes
- question_text, option_a, option_b, option_c, option_d, explanation

### Fix 4: Escape internal quotes
- Any `"` inside text fields becomes `""`

## Target Format
```
subject,chapter,difficulty,"question_text","option_a","option_b","option_c","option_d",correct_option,"explanation"
```

## Rows to Check
- All ~350+ rows need verification for correct_option validity (A, B, C, D)
- Verify correct_option matches explanation

