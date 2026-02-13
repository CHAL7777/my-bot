"""
Database Migration Script for Payment System

This script adds the missing `subscription_days` column to the payments table.
Run this before starting the bot if the column doesn't exist.

Usage:
    python scripts/run_payment_migration.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.base import engine
from app.config import settings


def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table (MySQL/MariaDB specific)."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(f"SHOW COLUMNS FROM {table_name} LIKE '{column_name}'")
            )
            return result.fetchone() is not None
    except Exception as e:
        print(f"Error checking column: {e}")
        return False


def add_subscription_days_column(engine):
    """Add subscription_days column to payments table."""
    table_name = "payments"
    column_name = "subscription_days"
    column_definition = "subscription_days INT"
    
    if check_column_exists(engine, table_name, column_name):
        print(f"✅ Column '{column_name}' already exists in '{table_name}'. No migration needed.")
        return True
    
    print(f"Adding column '{column_name}' to '{table_name}'...")
    
    try:
        with engine.connect() as conn:
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
            conn.execute(text(alter_sql))
            conn.commit()
            print(f"✅ Successfully added column '{column_name}'.")
            return True
    except Exception as e:
        print(f"❌ Failed to add column: {e}")
        return False


def add_payment_type_column(engine):
    """Add payment_type column to payments table (optional - for future use)."""
    table_name = "payments"
    column_name = "payment_type"
    column_definition = "payment_type ENUM('lifetime', 'subscription', name='payment_type_enum')"
    
    if check_column_exists(engine, table_name, column_name):
        print(f"✅ Column '{column_name}' already exists in '{table_name}'. No migration needed.")
        return True
    
    print(f"Adding column '{column_name}' to '{table_name}'...")
    
    try:
        with engine.connect() as conn:
            # First create the enum type if it doesn't exist
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE payment_type_enum AS ENUM('lifetime', 'subscription');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            conn.commit()
            
            # Then add the column
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
            conn.execute(text(alter_sql))
            conn.commit()
            print(f"✅ Successfully added column '{column_name}'.")
            return True
    except Exception as e:
        print(f"❌ Failed to add column: {e}")
        return False


def migrate_existing_payments(engine):
    """Migrate existing payments to set subscription_days based on amount."""
    print("Migrating existing payments...")
    
    try:
        with engine.connect() as conn:
            # Update lifetime payments (based on ONE_TIME_PRICE)
            update_sql = f"""
                UPDATE {settings.ONE_TIME_PRICE}
                SET subscription_days = NULL
                WHERE amount = {settings.ONE_TIME_PRICE}
                AND subscription_days IS NULL
            """
            conn.execute(text(update_sql))
            
            # Update 30-day subscription payments
            update_sql = f"""
                UPDATE payments
                SET subscription_days = 30
                WHERE amount = {settings.SUBSCRIPTION_PRICE_30_DAYS}
                AND subscription_days IS NULL
            """
            conn.execute(text(update_sql))
            
            # Update 90-day subscription payments
            update_sql = f"""
                UPDATE payments
                SET subscription_days = 90
                WHERE amount = {settings.SUBSCRIPTION_PRICE_90_DAYS}
                AND subscription_days IS NULL
            """
            conn.execute(text(update_sql))
            
            conn.commit()
            print("✅ Successfully migrated existing payments.")
            return True
    except Exception as e:
        print(f"❌ Failed to migrate payments: {e}")
        return False


def run_migration():
    """Run all migration steps."""
    print("=" * 60)
    print("Payment System Database Migration")
    print("=" * 60)
    
    success = True
    
    # Add subscription_days column
    if not add_subscription_days_column(engine):
        success = False
    
    # Migrate existing payments
    if success:
        if not migrate_existing_payments(engine):
            success = False
    
    print("=" * 60)
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed. Please check errors above.")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    run_migration()

