"""Background job for decaying old engagement scores.

This module provides a scheduled job to periodically decay engagement scores
for issues that haven't been interacted with recently. This ensures engagement
scores reflect current user interest, not just historical activity.
"""

from linear_chief.intelligence.engagement_tracker import EngagementTracker
from linear_chief.storage import get_session_maker, get_db_session
from linear_chief.storage.repositories import ConversationRepository
from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)


async def decay_engagement_scores_job():
    """
    Periodic job to decay old engagement scores.

    Schedule: Daily at midnight (after briefing generation)
    Effect: Reduces scores for issues user hasn't interacted with recently

    This ensures engagement scores reflect CURRENT interest, not just
    historical activity. Issues not mentioned in 30+ days get lower scores.

    Example APScheduler integration:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            decay_engagement_scores_job,
            trigger=CronTrigger(hour=0, minute=0),  # Midnight
            id="engagement_decay",
            name="Decay old engagement scores",
        )
        scheduler.start()
    """
    logger.info("Starting engagement decay job")

    try:
        tracker = EngagementTracker()

        # Get all active users (users who have had conversations in last 30 days)
        session_maker = get_session_maker()
        active_users = []

        for session in get_db_session(session_maker):
            conv_repo = ConversationRepository(session)
            active_users = conv_repo.get_active_users(since_days=30)

        logger.info(
            f"Found {len(active_users)} active users for engagement decay",
            extra={"active_users_count": len(active_users)},
        )

        # Decay engagements for each active user
        total_decayed = 0
        for user_id in active_users:
            try:
                # Decay interactions older than 30 days by 10%
                decayed_count = await tracker.decay_old_engagements(days=30)
                total_decayed += decayed_count

                logger.debug(
                    f"Decayed {decayed_count} engagements for user {user_id}",
                    extra={"user_id": user_id, "decayed_count": decayed_count},
                )

            except Exception as e:
                logger.error(
                    f"Failed to decay engagements for user {user_id}",
                    extra={"user_id": user_id, "error_type": type(e).__name__},
                    exc_info=True,
                )
                # Continue with other users

        logger.info(
            f"Engagement decay job completed: {total_decayed} engagements decayed",
            extra={
                "total_decayed": total_decayed,
                "users_processed": len(active_users),
            },
        )

    except Exception as e:
        logger.error(
            "Engagement decay job failed",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        raise


async def cleanup_zero_engagements_job():
    """
    Periodic job to clean up engagement records with zero scores.

    Schedule: Weekly (Sunday at 2 AM)
    Effect: Deletes engagement records with score = 0.0 older than 90 days

    This prevents the engagement table from growing indefinitely with
    stale, zero-scored records that no longer provide value.

    Example APScheduler integration:
        scheduler.add_job(
            cleanup_zero_engagements_job,
            trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
            id="engagement_cleanup",
            name="Clean up zero-scored engagements",
        )
    """
    logger.info("Starting engagement cleanup job")

    try:
        from datetime import datetime, timedelta
        from linear_chief.storage.models import IssueEngagement

        session_maker = get_session_maker()
        cutoff_date = datetime.utcnow() - timedelta(days=90)

        deleted_count = 0
        for session in get_db_session(session_maker):
            # Delete zero-scored engagements older than 90 days
            result = (
                session.query(IssueEngagement)
                .filter(
                    IssueEngagement.engagement_score <= 0.0,
                    IssueEngagement.last_interaction < cutoff_date,
                )
                .delete()
            )

            deleted_count = result
            session.commit()

        logger.info(
            f"Engagement cleanup completed: {deleted_count} records deleted",
            extra={"deleted_count": deleted_count, "cutoff_days": 90},
        )

    except Exception as e:
        logger.error(
            "Engagement cleanup job failed",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        raise


# Example: Integration with existing BriefingScheduler
def add_engagement_jobs_to_scheduler(scheduler):
    """
    Add engagement maintenance jobs to existing scheduler.

    Args:
        scheduler: BriefingScheduler instance

    Example:
        from linear_chief.scheduling import BriefingScheduler
        from linear_chief.scheduling.engagement_decay_job import (
            add_engagement_jobs_to_scheduler
        )

        scheduler = BriefingScheduler()
        add_engagement_jobs_to_scheduler(scheduler)
        scheduler.start(briefing_job_callback)
    """
    from apscheduler.triggers.cron import CronTrigger
    import asyncio

    # Wrapper for async job execution
    def async_job_wrapper(async_job_func):
        def wrapper():
            asyncio.run(async_job_func())

        return wrapper

    # Add decay job: Daily at midnight
    scheduler.scheduler.add_job(
        async_job_wrapper(decay_engagement_scores_job),
        trigger=CronTrigger(hour=0, minute=0),
        id="engagement_decay",
        name="Decay old engagement scores",
    )

    logger.info("Added engagement decay job to scheduler (daily at midnight)")

    # Add cleanup job: Weekly on Sunday at 2 AM
    scheduler.scheduler.add_job(
        async_job_wrapper(cleanup_zero_engagements_job),
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="engagement_cleanup",
        name="Clean up zero-scored engagements",
    )

    logger.info("Added engagement cleanup job to scheduler (weekly Sunday 2 AM)")
