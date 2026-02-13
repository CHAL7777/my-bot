# Chapter Selection Enhancement - TODO List

## Goal
Enhance the chapter selection message to show question counts (total, simple, medium, hard) for each chapter.

## Changes Required

### 1. Modify `select_subject` handler
- [ ] Fetch question counts for each chapter within the async session
- [ ] Build enhanced message with chapter details and question counts
- [ ] Replace the simple edit_text with enhanced version

### 2. Modify `back_to_chapters` handler  
- [ ] Apply the same enhanced message format with question counts
- [ ] Ensure chapter counts are available in state or fetch from DB

### 3. Testing
- [ ] Verify the message displays correctly with question counts
- [ ] Test that keyboard navigation still works

