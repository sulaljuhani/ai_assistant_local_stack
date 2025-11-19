"""
Scheduler Service

This module configures APScheduler for running scheduled background tasks.
It replaces n8n's scheduled workflows with Python-based cron jobs.

Usage:
    from services.scheduler import setup_scheduler

    scheduler = AsyncIOScheduler()
    setup_scheduler(scheduler)
    scheduler.start()
"""

import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from datetime import datetime

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance"""
    return _scheduler


def job_listener(event):
    """Listener for job execution events"""
    if event.exception:
        logger.error(
            f"Job {event.job_id} failed with exception: {event.exception}",
            exc_info=True
        )
    else:
        logger.info(f"Job {event.job_id} executed successfully")


def setup_scheduler(scheduler: AsyncIOScheduler) -> None:
    """
    Configure and register all scheduled jobs.

    This function will be called during application startup to register
    all scheduled tasks that replace n8n workflows.

    Args:
        scheduler: AsyncIOScheduler instance
    """
    global _scheduler
    _scheduler = scheduler

    # Configure job stores and executors
    jobstores = {
        'default': MemoryJobStore()
    }

    executors = {
        'default': AsyncIOExecutor()
    }

    job_defaults = {
        'coalesce': True,  # Combine multiple pending executions into one
        'max_instances': 1,  # Only one instance of each job at a time
        'misfire_grace_time': 300  # 5 minutes grace period for misfired jobs
    }

    scheduler.configure(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )

    # Add event listeners
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    logger.info("Scheduler configured successfully")

    # ========================================================================
    # Register Scheduled Jobs
    # ========================================================================

    from services.reminders import (
        fire_reminders,
        generate_daily_summary,
        expand_recurring_tasks
    )
    from services.maintenance import cleanup_old_data, health_check
    from services.vault_sync import scheduled_vault_sync
    from services.memory_service import enrich_memories, sync_memory_to_vault

    # Job 1: Fire Reminders - every 5 minutes
    # Replaces n8n workflow: 04-fire-reminders.json
    scheduler.add_job(
        fire_reminders,
        'interval',
        minutes=5,
        id='fire_reminders',
        name='Fire Due Reminders',
        replace_existing=True
    )
    logger.info("Registered job: fire_reminders (every 5 minutes)")

    # Job 2: Daily Summary - 8 AM daily
    # Replaces n8n workflow: 05-daily-summary.json
    scheduler.add_job(
        generate_daily_summary,
        'cron',
        hour=8,
        minute=0,
        id='daily_summary',
        name='Generate Daily Summary',
        replace_existing=True
    )
    logger.info("Registered job: daily_summary (8 AM daily)")

    # Job 3: Expand Recurring Tasks - midnight daily
    # Replaces n8n workflow: 06-expand-recurring-tasks.json
    scheduler.add_job(
        expand_recurring_tasks,
        'cron',
        hour=0,
        minute=0,
        id='expand_recurring',
        name='Expand Recurring Tasks',
        replace_existing=True
    )
    logger.info("Registered job: expand_recurring (midnight daily)")

    # Job 4: Cleanup Old Data - Sunday 2 AM weekly
    # Replaces n8n workflow: 08-cleanup-old-data.json
    scheduler.add_job(
        cleanup_old_data,
        'cron',
        day_of_week='sun',
        hour=2,
        minute=0,
        id='cleanup',
        name='Weekly Data Cleanup',
        replace_existing=True
    )
    logger.info("Registered job: cleanup (Sunday 2 AM weekly)")

    # Job 5: Health Check - every 5 minutes
    # Replaces n8n workflow: 21-health-check.json
    scheduler.add_job(
        health_check,
        'interval',
        minutes=5,
        id='health_check',
        name='System Health Check',
        replace_existing=True
    )
    logger.info("Registered job: health_check (every 5 minutes)")

    # Job 6: Vault Sync - every 12 hours
    # Replaces n8n workflow: 18-scheduled-vault-sync.json
    scheduler.add_job(
        scheduled_vault_sync,
        'interval',
        hours=12,
        id='vault_sync',
        name='Scheduled Vault Sync',
        replace_existing=True
    )
    logger.info("Registered job: vault_sync (every 12 hours)")

    # Job 7: Enrich Memories - 3 AM daily
    # Replaces n8n workflow: 11-enrich-memories.json
    scheduler.add_job(
        enrich_memories,
        'cron',
        hour=3,
        minute=0,
        id='enrich_memories',
        name='Enrich Frequently Accessed Memories',
        replace_existing=True
    )
    logger.info("Registered job: enrich_memories (3 AM daily)")

    # Job 8: Sync Memory to Vault - every 6 hours
    # Replaces n8n workflow: 12-sync-memory-to-vault.json
    scheduler.add_job(
        sync_memory_to_vault,
        'interval',
        hours=6,
        id='memory_vault_sync',
        name='Sync High-Salience Memories to Vault',
        replace_existing=True
    )
    logger.info("Registered job: memory_vault_sync (every 6 hours)")

    logger.info("All scheduled jobs registered successfully")


async def shutdown_scheduler():
    """Gracefully shutdown the scheduler"""
    global _scheduler
    if _scheduler:
        logger.info("Shutting down scheduler...")
        _scheduler.shutdown(wait=True)
        _scheduler = None
        logger.info("Scheduler shut down successfully")


def list_jobs():
    """List all registered jobs"""
    if not _scheduler:
        return []

    jobs = _scheduler.get_jobs()
    job_info = []

    for job in jobs:
        info = {
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time,
            'trigger': str(job.trigger)
        }
        job_info.append(info)

    return job_info


def pause_job(job_id: str):
    """Pause a specific job"""
    if _scheduler:
        _scheduler.pause_job(job_id)
        logger.info(f"Job {job_id} paused")


def resume_job(job_id: str):
    """Resume a paused job"""
    if _scheduler:
        _scheduler.resume_job(job_id)
        logger.info(f"Job {job_id} resumed")


def trigger_job(job_id: str):
    """Manually trigger a job immediately"""
    if _scheduler:
        job = _scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            logger.info(f"Job {job_id} triggered manually")
        else:
            logger.warning(f"Job {job_id} not found")


# ============================================================================
# Scheduler Configuration Examples
# ============================================================================
#
# The following job types will be registered once we implement the service functions:
#
# 1. INTERVAL JOBS (run every X minutes/hours)
# -----------------------------------------------
# scheduler.add_job(
#     func=fire_reminders,
#     trigger='interval',
#     minutes=5,
#     id='fire_reminders',
#     name='Fire Due Reminders',
#     replace_existing=True
# )
#
# 2. CRON JOBS (run at specific times)
# -----------------------------------------------
# scheduler.add_job(
#     func=generate_daily_summary,
#     trigger='cron',
#     hour=8,
#     minute=0,
#     id='daily_summary',
#     name='Generate Daily Summary',
#     replace_existing=True
# )
#
# 3. CRON WITH DAY OF WEEK
# -----------------------------------------------
# scheduler.add_job(
#     func=cleanup_old_data,
#     trigger='cron',
#     day_of_week='sun',
#     hour=2,
#     minute=0,
#     id='cleanup',
#     name='Weekly Data Cleanup',
#     replace_existing=True
# )
#
# ============================================================================
# Migration Mapping from n8n Schedules:
# ============================================================================
#
# n8n: every 5 minutes
# → APScheduler: trigger='interval', minutes=5
#
# n8n: every day at 8 AM
# → APScheduler: trigger='cron', hour=8, minute=0
#
# n8n: every day at midnight
# → APScheduler: trigger='cron', hour=0, minute=0
#
# n8n: every Sunday at 2 AM
# → APScheduler: trigger='cron', day_of_week='sun', hour=2, minute=0
#
# n8n: every 12 hours
# → APScheduler: trigger='interval', hours=12
#
# n8n: every 6 hours
# → APScheduler: trigger='interval', hours=6
#
# n8n: every 15 minutes
# → APScheduler: trigger='interval', minutes=15
#
# ============================================================================
