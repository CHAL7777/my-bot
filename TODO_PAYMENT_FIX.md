# Payment Handler Fix - TODO

## Problem
TypeError: payment_command() takes 2 positional arguments but 3 were given

## Root Cause
- `command_payment` alias passes `has_active_subscription` to `payment_command`
- `payment_command` only accepts 2 parameters (message, state)
- The middleware injects data into `data` dict, not as function parameters

## Solution Steps

### Step 1: Fix payment.py
- [x] Remove `command_payment` alias function (unnecessary)
- [x] Add `has_active_subscription: bool = False` parameter to `payment_command`
- [x] Use `data.get('has_active_subscription', False)` to access middleware data

### Step 2: Fix subscription.py middleware
- [x] Remove `/payment` from skip check so middleware injects data
- [x] Keep other skip conditions (start, help, payment callbacks)

### Step 3: Fix start.py handler
- [x] Update `payment_button_handler` to call via F.router pattern
- [x] Or remove extra args and let aiogram inject data

## Changes Made

### payment.py
```python
# BEFORE:
async def command_payment(message: types.Message, state: FSMContext,
                          has_active_subscription: bool = False):
    """Alias for payment_command to maintain compatibility"""
    await payment_command(message, state, has_active_subscription)

@router.message(Command("payment"))
async def payment_command(message: types.Message, state: FSMContext):
    ...

# AFTER:
@router.message(Command("payment"))
async def payment_command(message: types.Message, state: FSMContext,
                          has_active_subscription: bool = False,
                          **kwargs):
    # Access from data dict injected by middleware
    subscription_status = has_active_subscription or kwargs.get('has_active_subscription', False)
    ...
```

### subscription.py
```python
# BEFORE:
if isinstance(event, Message) and event.text and event.text.startswith('/payment'):
    return True

# AFTER:
# Remove this check - let middleware process /payment commands
```

### start.py
```python
# BEFORE:
async def payment_button_handler(message: Message, state: FSMContext,
                                  has_active_subscription: bool = False):
    from app.handlers.payment import command_payment
    await command_payment(message, state, has_active_subscription)

# AFTER:
async def payment_button_handler(message: Message, state: FSMContext,
                                  is_admin: bool = False):
    # Use F.router to properly route through aiogram's system
    # or import and call without extra params
    from app.handlers.payment import payment_command
    await payment_command(message, state)
```

## Best Practices for aiogram v3 Middleware Data

1. **Use `data` dict**: aiogram automatically injects middleware data into handler's `data` dict
2. **Function parameters**: You can add parameters with default values, and aiogram will fill them from `data`
3. **Direct access**: Access via `data.get('key', default)` inside handler
4. **Don't skip**: Don't skip routes in middleware if you need the data there
5. **Type hints**: Use type hints for better IDE support

## Why This Works

When aiogram v3 processes a handler:
1. Middleware runs and populates `data` dict
2. Handler is called with extracted values from `data`
3. If handler has a parameter matching a key in `data`, it's passed automatically
4. If not in `data`, default value is used (hence `= False`)

