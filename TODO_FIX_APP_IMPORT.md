# TODO: Fix "Attribute 'app' not found in module 'app.main'" Error

## Problem
The `app/main.py` file contains two different programs merged incorrectly:
1. Telegram bot entry point (lines 1-54)
2. FastAPI webhook application (lines 57+)

This causes import issues when trying to access `app.main.app`.

## Plan
1. ✅ Create `app/webapp.py` with the FastAPI application
2. ✅ Fix `app/main.py` to only contain the bot startup logic
3. ✅ Test the fix

## Status: IN PROGRESS

