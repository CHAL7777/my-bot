# Quiz Start Flow Fix - TODO List

## Problem
- `start_quiz_flow()` in `quiz.py` requires 4 parameters but callers only pass 3
- Error: "start_quiz_flow() takes 3 positional arguments but 4 were given"

## Solution
- Modify `start_quiz_flow()` to auto-create `plain_sender` internally (3 params)
- Remove `plain_sender` from function signature
- Create `plain_sender` inside the function using `PlainTextMessageSender`

## Tasks
- [ ] 1. Modify start_quiz_flow() signature to remove plain_sender parameter
- [ ] 2. Add internal plain_sender creation inside start_quiz_flow()
- [ ] 3. Update all calls in quiz.py to not pass plain_sender
- [ ] 4. Verify fix by testing webhook endpoint

