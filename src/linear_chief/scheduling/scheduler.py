"""APScheduler wrapper for briefing automation."""

from typing import Callable, Optional
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
import pytz

from linear_chief.config import LOCAL_TIMEZONE, BRIEFING_TIME
from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)


class BriefingScheduler:
    """
    Scheduler for automated daily briefings.

    Wraps APScheduler with timezone support and error handling.
    """

    def __init__(
        self,
        timezone: str = LOCAL_TIMEZONE,
        briefing_time: str = BRIEFING_TIME,
    ):
        """
        Initialize scheduler with configuration.

        Args:
            timezone: Timezone name (e.g., "Europe/Prague")
            briefing_time: Daily briefing time in HH:MM format (e.g., "09:00")
        """
        self.timezone = pytz.timezone(timezone)
        self.briefing_time = briefing_time
        self.scheduler: Optional[BackgroundScheduler] = None
        self._is_running = False

        logger.info(
            "Scheduler initialized",
            extra={
                "component": "scheduler",
                "briefing_time": briefing_time,
                "timezone": timezone,
            },
        )

    def start(self, briefing_job: Callable) -> None:
        """
        Start scheduler with daily briefing job.

        Args:
            briefing_job: Callable to execute for briefing generation
                         (should be async-safe or wrapped)

        Raises:
            RuntimeError: If scheduler is already running
        """
        if self._is_running:
            raise RuntimeError("Scheduler is already running")

        # Parse briefing time (HH:MM)
        try:
            hour, minute = map(int, self.briefing_time.split(":"))
        except ValueError as e:
            logger.error(
                f"Invalid briefing time format: {self.briefing_time}", exc_info=True
            )
            raise ValueError(
                f"BRIEFING_TIME must be in HH:MM format, got: {self.briefing_time}"
            ) from e

        # Create scheduler
        self.scheduler = BackgroundScheduler(timezone=self.timezone)

        # Add listeners for job events
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED,
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR,
        )

        # Add daily briefing job
        trigger = CronTrigger(hour=hour, minute=minute, timezone=self.timezone)
        self.scheduler.add_job(
            briefing_job,
            trigger=trigger,
            id="daily_briefing",
            name="Daily Briefing Generation",
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True

        next_run = self.get_next_run_time()
        logger.info(f"Scheduler started. Next briefing: {next_run}")

    def stop(self, wait: bool = True) -> None:
        """
        Stop scheduler gracefully.

        Args:
            wait: If True, wait for running jobs to complete
        """
        if not self._is_running or self.scheduler is None:
            logger.warning("Scheduler is not running")
            return

        self.scheduler.shutdown(wait=wait)
        self._is_running = False
        logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        Returns:
            True if scheduler is active
        """
        return self._is_running

    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get next scheduled briefing time.

        Returns:
            Next run datetime or None if scheduler not running
        """
        if not self._is_running or self.scheduler is None:
            return None

        job = self.scheduler.get_job("daily_briefing")
        if job and job.next_run_time:
            # APScheduler's next_run_time is a datetime from the scheduler library
            return job.next_run_time  # type: ignore[no-any-return]

        return None

    def trigger_now(self) -> None:
        """
        Trigger briefing job immediately (for manual execution).

        Raises:
            RuntimeError: If scheduler is not running
        """
        if not self._is_running or self.scheduler is None:
            raise RuntimeError("Scheduler is not running. Use start() first.")

        job = self.scheduler.get_job("daily_briefing")
        if job:
            job.modify(next_run_time=datetime.now(self.timezone))
            logger.info("Briefing job triggered manually")
        else:
            logger.error("Daily briefing job not found")
            raise RuntimeError("Daily briefing job not found")

    def _job_executed_listener(self, event) -> None:
        """
        Listener for successful job execution.

        Args:
            event: APScheduler JobExecutionEvent
        """
        logger.info(
            f"Job executed successfully: {event.job_id} at {event.scheduled_run_time}"
        )

    def _job_error_listener(self, event) -> None:
        """
        Listener for job execution errors.

        Args:
            event: APScheduler JobExecutionEvent with exception
        """
        logger.error(
            f"Job failed: {event.job_id} at {event.scheduled_run_time}",
            exc_info=event.exception,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop(wait=True)
