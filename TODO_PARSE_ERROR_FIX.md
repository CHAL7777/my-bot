# Parse Error Fix Implementation Plan

## Phase 1: Update safe_sender.py
- [ ] Add pure formatter functions that return raw strings
- [ ] Add send_message_html() convenience method
- [ ] Add edit_message_html() convenience method
- [ ] Add send_quiz_question_html() method
- [ ] Add edit_quiz_question_html() method

## Phase 2: Update quiz.py
- [ ] Import SafeMessageSender only
- [ ] Remove escape_markdown_content import and usage
- [ ] Replace message.edit_text() with _sender.edit_message()
- [ ] Replace message.answer() with _sender.send_message()
- [ ] Remove all parse_mode='Markdown' arguments
- [ ] Use pure formatters for text construction

## Phase 3: Update answers.py
- [ ] Import SafeMessageSender only
- [ ] Remove Markdown escaping imports
- [ ] Replace direct message methods with SafeMessageSender
- [ ] Remove all parse_mode='Markdown' arguments

## Phase 4: Update safe_edit.py
- [ ] Import SafeMessageSender
- [ ] Replace direct edit calls with SafeMessageSender.edit_message()
- [ ] Remove manual escaping logic
- [ ] Remove parse_mode arguments

## Phase 5: Clean up helpers.py
- [ ] Remove escape_markdown_content() and related functions
- [ ] Keep only HTML escaping (for backward compatibility)

## Phase 6: Testing
- [ ] Test quiz start flow
- [ ] Test question display with special characters
- [ ] Test answer selection
- [ ] Test quiz completion
- [ ] Verify no parse errors

