# Quiz HTML Migration TODO

## Phase 1: Import and Helper Changes
- [ ] 1.1 Update imports: remove escape_html from helpers, use SafeMessageSender
- [ ] 1.2 Remove `_build_chapter_selection_message()` function
- [ ] 1.3 Add SafeMessageSender helper instance for the module

## Phase 2: Message Format Changes (replace Markdown with HTML)
- [ ] 2.1 `send_access_denied()` - update parse_mode and message
- [ ] 2.2 `command_quiz()` - update message if quiz in progress
- [ ] 2.3 `_send_quiz_subjects()` - update parse_mode
- [ ] 2.4 `select_subject()` - update parse_mode and message
- [ ] 2.5 `back_to_subjects()` - update parse_mode
- [ ] 2.6 `select_chapter()` - update parse_mode and message
- [ ] 2.7 `back_to_chapters()` - update parse_mode and message
- [ ] 2.8 `select_difficulty()` - update parse_mode and message
- [ ] 2.9 `cancel_quiz_confirmation()` - update parse_mode
- [ ] 2.10 `confirm_cancel_quiz()` - update parse_mode
- [ ] 2.11 `continue_quiz()` - update parse_mode and message
- [ ] 2.12 `finish_quiz()` - update parse_mode and message
- [ ] 2.13 `show_quiz_details()` - update parse_mode
- [ ] 2.14 `_display_question_for_review()` - update parse_mode and message
- [ ] 2.15 `review_question()` - update parse_mode
- [ ] 2.16 `back_to_quiz_results()` - update parse_mode and message
- [ ] 2.17 `try_again_quiz()` - update parse_mode
- [ ] 2.18 `show_weak_areas()` - update parse_mode and message
- [ ] 2.19 `get_recommendations()` - update parse_mode and message
- [ ] 2.20 `start_recommended_quiz()` - update parse_mode and message
- [ ] 2.21 `practice_weak_area()` - update parse_mode and message
- [ ] 2.22 `show_quiz_summary()` - update parse_mode and message
- [ ] 2.23 `back_to_menu_from_subjects()` - update parse_mode and message

## Phase 3: Escaping Function Changes
- [ ] 3.1 Replace `escape_markdown_content()` with `SafeMessageSender.escape_html()`
- [ ] 3.2 Replace `escape_markdown_dict()` with `SafeMessageSender.escape_html_dict()`

## Phase 4: Testing
- [ ] 4.1 Run syntax check on the refactored file
- [ ] 4.2 Test quiz flow with special characters in subject/chapter names
- [ ] 4.3 Verify no "can't parse entities" errors

## Notes
- Inline keyboard labels must NOT be escaped
- User-generated content (subject names, chapter names, question text) must be escaped exactly once
- All logic, behavior, and callback flows remain unchanged

