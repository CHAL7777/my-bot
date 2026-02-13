# Learning-Focused Quiz Implementation Plan

## Overview
Implement a premium learning experience using the "Check & Reveal" interaction pattern that forces users to engage with explanations before progressing.

## Files to Create/Modify

### 1. New File: `app/handlers/learning_quiz.py`
Complete implementation of learning-focused quiz system with:
- Question display with 4 options (A, B, C, D)
- Option selection → Check Answer button transition
- Answer evaluation + explanation reveal
- Auto-next after 1.5+ second delay

### 2. Enhancement: `app/repositories/attempt_repo.py`
Add methods:
- `has_attempted_question_in_session()` - Check session attempts
- `bulk_create_attempts()` - Batch save attempts

### 3. Enhancement: `app/keyboards/quiz.py`
Add keyboard builders:
- `get_learning_question_keyboard()` - Options A-D
- `get_check_answer_keyboard()` - Selected + Check button
- `get_explanation_keyboard()` - Result + explanation (no buttons)

### 4. Integration: `app/bot.py` or `app/main.py`
Register the new router

## Flow Diagram

```
User selects option (A/B/C/D)
         ↓
Options replaced with: "✓ Selected" + "✅ Check Answer → Show Why"
         ↓
User clicks "Check Answer"
         ↓
Message edited to show: ✅/❌ + Correct Answer + Explanation
         ↓
Wait 1.5 seconds (minimum)
         ↓
Auto-load next question (no user action needed)
```

## Implementation Steps

### Phase 1: Core Quiz Handler
- [ ] Create `app/handlers/learning_quiz.py`
- [ ] Implement keyboard builders
- [ ] Implement core flow functions (send_question, handle_option_select, etc.)
- [ ] Add callback handlers

### Phase 2: Data Persistence
- [ ] Enhance `attempt_repo.py` with session tracking
- [ ] Ensure all required fields are saved (user_id, question_id, selected_option, is_correct, created_at)

### Phase 3: Integration
- [ ] Update quiz selection flow to use learning mode
- [ ] Register router in main bot

### Phase 4: Testing & Refinement
- [ ] Test the complete flow
- [ ] Verify data persistence
- [ ] Ensure minimum delay is enforced

