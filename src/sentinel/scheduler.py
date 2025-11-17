"""Scheduler configuration using SQLAlchemy job store."""

import os

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from .ormdb.database import SQLALCHEMY_DATABASE_URL


def create_scheduler() -> BackgroundScheduler:
    """
    Create and configure a BackgroundScheduler with SQLAlchemy job store.

    Returns:
        Configured BackgroundScheduler instance
    """
    # Configure job store using the same database as our application
    jobstores = {
        "default": SQLAlchemyJobStore(
            url=SQLALCHEMY_DATABASE_URL, tablename="apscheduler_jobs"
        )
    }

    # Configure executor
    executors = {
        "default": ThreadPoolExecutor(
            max_workers=int(os.getenv("SCHEDULER_MAX_WORKERS", "3"))
        )
    }

    # Job defaults
    job_defaults = {
        "coalesce": False,  # Don't combine multiple missed executions
        "max_instances": 1,  # Only one instance of each job at a time
        "misfire_grace_time": 30,  # 30 seconds grace period for missed jobs
    }

    # Create scheduler
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="UTC",  # Use UTC for consistency
    )

    # Add event listeners for logging
    scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
    scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)

    return scheduler


def job_executed_listener(event):
    """Log successful job executions."""
    print(f"Job {event.job_id} executed successfully at {event.scheduled_run_time}")


def job_error_listener(event):
    """Log job execution errors."""
    print(f"Job {event.job_id} crashed: {event.exception}")
    print(f"Traceback: {event.traceback}")


def get_global_scheduler() -> BackgroundScheduler:
    """
    Get or create the global scheduler instance.

    Returns:
        Global BackgroundScheduler instance
    """
    if not hasattr(get_global_scheduler, "_scheduler"):
        get_global_scheduler._scheduler = create_scheduler()

    return get_global_scheduler._scheduler


def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_global_scheduler()
    if not scheduler.running:
        scheduler.start()
        print("Scheduler started with SQLAlchemy job store")


def shutdown_scheduler():
    """Shutdown the global scheduler."""
    scheduler = get_global_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        print("Scheduler shutdown complete")


def add_stock_tracking_job(interval_minutes: int = 60):
    """
    Add the stock tracking job to the scheduler.

    Args:
        interval_minutes: How often to run stock tracking (default: 60 minutes)
    """
    from .core.tracker import track_stocks

    scheduler = get_global_scheduler()

    # Remove existing job if it exists
    try:
        scheduler.remove_job("stock_tracking")
    except:
        pass  # Job doesn't exist, which is fine

    # Add the job
    scheduler.add_job(
        func=track_stocks,
        trigger="interval",
        minutes=interval_minutes,
        id="stock_tracking",
        name="Stock Price Tracking",
        replace_existing=True,
    )

    print(f"Added stock tracking job with {interval_minutes} minute interval")


def list_scheduled_jobs():
    """List all currently scheduled jobs."""
    scheduler = get_global_scheduler()
    jobs = scheduler.get_jobs()

    if not jobs:
        print("No scheduled jobs")
        return

    print("Scheduled jobs:")
    for job in jobs:
        print(f"  - {job.id}: {job.name} (next run: {job.next_run_time})")
