# Contact System Fix - TODO

## Status: IN PROGRESS

### Step 1: Update keyboards/menu.py - Add contact start keyboard
- [ ] Add `get_contact_start_keyboard()` method
- [ ] Add `get_contact_confirmation_keyboard()` method

### Step 2: Update handlers/start.py - Fix contact flow
- [ ] Modify `command_contact` to start FSM flow
- [ ] Modify `contact_button_handler` to start FSM flow  
- [ ] Modify `inline_contact_callback` to start FSM flow
- [ ] Update `contact_category_callback` handler
- [ ] Update `contact_message_handler` with better confirmation message

### Step 3: Test the flow
- [ ] Test /contact command
- [ ] Test Contact button
- [ ] Test category selection
- [ ] Test message submission
- [ ] Verify confirmation with ticket ID

