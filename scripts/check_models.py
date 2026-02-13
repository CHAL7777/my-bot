import sys
import os
import asyncio
from sqlalchemy import create_engine

# Ensure project root is on sys.path (same trick as app/main.py)
if __package__ is None:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Import app models and Base
try:
    from app.db import models
    from app.db.base import Base
except Exception as e:
    print("Failed to import models:", e)
    sys.exit(2)

print("Imported models successfully. Creating in-memory SQLite schema...")

engine = create_engine('sqlite:///:memory:')

try:
    Base.metadata.create_all(engine)
    print("Schema created successfully in SQLite in-memory database.")
    sys.exit(0)
except Exception as e:
    print("Failed to create schema:", e)
    sys.exit(3)
