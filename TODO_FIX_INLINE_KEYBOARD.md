# Fix: Replace get_main_menu() with get_main_menu_inline() for edit_text()

## Problem
`callback.message.edit_text()` requires `InlineKeyboardMarkup`, but `MainMenuKeyboard.get_main_menu()` returns `ReplyKeyboardMarkup`.

## Fix
Replace `MainMenuKeyboard.get_main_menu()` with `MainMenuKeyboard.get_main_menu_inline()` in all callback handlers using `edit_text()`.

## Files to Fix

- [ ] app/handlers/leaderboard.py - 3 occurrences
- [ ] app/handlers/quiz.py - 5 occurrences
- [ ] app/handlers/payment.py - 5 occurrences
- [ ] app/handlers/progress.py - 1 occurrence
- [ ] app/handlers/start.py - 1 occurrence

## Progress

### leaderboard.py
- [ ] Line ~112: Error loading leaderboard
- [ ] Line ~172: Error loading statistics
- [ ] Line ~224: Error loading top performers

### quiz.py
- [ ] Line ~230: No questions available
- [ ] Line ~271: Daily limit reached
- [ ] ~274: Error starting quiz
- [ ] ~377: Quiz cancelled
- [ ] ~527: Try again quiz

### payment.py
- [ ] ~85: Error loading payment info
- [ ] ~207: Payment already pending
- [ ] ~211: Error payment
- [ ] ~329: Error loading status
- [ ] ~517: Error loading payment history

### progress.py
- [ ] ~147: Error loading progress

### start.py
- [ ] ~61: Already in quiz

