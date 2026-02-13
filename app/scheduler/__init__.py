from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.scheduler.reminders import ReminderScheduler
from app.scheduler.expiry_check import ExpiryChecker

def setup_scheduler(bot):
    """Setup and start all scheduled tasks"""
    scheduler = AsyncIOScheduler()
    
    # Setup reminder scheduler
    reminder_scheduler = ReminderScheduler(bot)
    expiry_checker = ExpiryChecker(bot)
    
    # Add jobs
    scheduler.add_job(
        reminder_scheduler.send_daily_reminders,
        CronTrigger(hour=9, minute=0),  # 9 AM daily
        id='daily_reminders'
    )
    
    scheduler.add_job(
        expiry_checker.check_subscription_expiry,
        CronTrigger(hour=0, minute=0),  # Midnight daily
        id='subscription_expiry_check'
    )
    
    scheduler.add_job(
        reminder_scheduler.send_weekly_leaderboard,
        CronTrigger(day_of_week='sun', hour=20, minute=0),  # Sunday 8 PM
        id='weekly_leaderboard'
    )
    
    scheduler.add_job(
        expiry_checker.cleanup_old_data,
        CronTrigger(day=1, hour=2, minute=0),  # 1st of month, 2 AM
        id='data_cleanup'
    )
    
    return scheduler