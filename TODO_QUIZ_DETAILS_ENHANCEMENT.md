# Quiz Details Enhancement TODO

## Task
Enhance the `_display_question_for_review` function in `app/handlers/quiz.py` to make it more beautiful and interactive with emojis, better formatting, and learning tips.

## Implementation Steps

### Phase 1: Update _display_question_for_review Function
- [ ] 1.1 Add beautiful header with decorative dividers
- [ ] 1.2 Include subject 📚 and chapter 📖 names
- [ ] 1.3 Add difficulty badge with colored emoji
- [ ] 1.4 Show progress indicator "📊 3/10"
- [ ] 1.5 Enhance question display with badge "🔷 Question 1"
- [ ] 1.6 Improve option formatting:
  - ✅ Correct answer marker
  - ❌ Wrong answer marker
  - 👤 User's choice indicator

### Phase 2: Add Learning Tips Section
- [ ] 2.1 Add "💡 Learning Tip" section
- [ ] 2.2 Create helper function for generating learning tips
- [ ] 2.3 Include relevant educational content

### Phase 3: Improve Visual Layout
- [ ] 3.1 Use consistent emoji-based section dividers
- [ ] 3.2 Add progress bar using emojis
- [ ] 3.3 Include performance indicators

### Phase 4: Enhance Navigation
- [ ] 4.1 Update Previous/Next button labels
- [ ] 4.2 Add position indicator "◀️ 3/10 ▶️"
- [ ] 4.3 Add keyboard navigation improvements

### Phase 5: Testing
- [ ] 5.1 Test quiz details display
- [ ] 5.2 Test question navigation
- [ ] 5.3 Verify explanation display
- [ ] 5.4 Check message length handling

## Files to Modify
1. `app/handlers/quiz.py` - Update `_display_question_for_review` function

## Target Output Format
```
✨ QUIZ DETAILS ✨
─────────────────────────
📚 Subject Name
📖 Chapter Name  
⚡ Difficulty
─────────────────────────

🔷 Question 3/10 | ⏱️ 45s

Question text here...

✅ A. Correct option
❌ B. Wrong option 👤
✅ C. Correct option
❌ D. Wrong option

─────────────────────────
💡 LEARNING TIP:
Helpful hint or tip...

─────────────────────────
📘 EXPLANATION:
Detailed explanation...
```

## Completion Criteria
- ✅ Beautiful header with emojis and dividers
- ✅ Clear question and option formatting
- ✅ Learning tips section
- ✅ Navigation controls work properly
- ✅ Visual hierarchy is clear
- ✅ Message length handled correctly

