"""Unit tests for scheduler."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch
import pytz

from linear_chief.scheduling import BriefingScheduler


@pytest.fixture
def mock_job():
    """Create a mock job function."""
    return Mock()


class TestBriefingScheduler:
    """Tests for BriefingScheduler."""

    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = BriefingScheduler(
            timezone="Europe/Prague",
            briefing_time="09:00",
        )

        assert scheduler.timezone.zone == "Europe/Prague"
        assert scheduler.briefing_time == "09:00"
        assert not scheduler.is_running()

    def test_invalid_briefing_time_format(self, mock_job):
        """Test scheduler with invalid time format."""
        scheduler = BriefingScheduler(briefing_time="invalid")

        with pytest.raises(ValueError, match="BRIEFING_TIME must be in HH:MM format"):
            scheduler.start(mock_job)

    def test_start_scheduler(self, mock_job):
        """Test starting scheduler."""
        scheduler = BriefingScheduler(briefing_time="09:00")

        try:
            scheduler.start(mock_job)
            assert scheduler.is_running()

            next_run = scheduler.get_next_run_time()
            assert next_run is not None
            assert next_run.hour == 9
            assert next_run.minute == 0

        finally:
            scheduler.stop()

    def test_start_already_running(self, mock_job):
        """Test starting scheduler when already running."""
        scheduler = BriefingScheduler(briefing_time="09:00")

        try:
            scheduler.start(mock_job)

            with pytest.raises(RuntimeError, match="Scheduler is already running"):
                scheduler.start(mock_job)

        finally:
            scheduler.stop()

    def test_stop_scheduler(self, mock_job):
        """Test stopping scheduler."""
        scheduler = BriefingScheduler(briefing_time="09:00")

        scheduler.start(mock_job)
        assert scheduler.is_running()

        scheduler.stop()
        assert not scheduler.is_running()

    def test_stop_not_running(self):
        """Test stopping scheduler when not running."""
        scheduler = BriefingScheduler(briefing_time="09:00")

        # Should not raise error
        scheduler.stop()
        assert not scheduler.is_running()

    def test_get_next_run_time_not_running(self):
        """Test getting next run time when scheduler not running."""
        scheduler = BriefingScheduler(briefing_time="09:00")

        next_run = scheduler.get_next_run_time()
        assert next_run is None

    def test_trigger_now(self, mock_job):
        """Test manually triggering job."""
        scheduler = BriefingScheduler(briefing_time="23:59")

        try:
            scheduler.start(mock_job)

            # Trigger job manually
            scheduler.trigger_now()

            # Wait for job execution
            time.sleep(2)

            # Job should have been called
            assert mock_job.call_count >= 1

        finally:
            scheduler.stop()

    def test_trigger_now_not_running(self):
        """Test triggering job when scheduler not running."""
        scheduler = BriefingScheduler(briefing_time="09:00")

        with pytest.raises(RuntimeError, match="Scheduler is not running"):
            scheduler.trigger_now()

    def test_timezone_handling(self, mock_job):
        """Test scheduler with different timezones."""
        # Test with UTC
        scheduler_utc = BriefingScheduler(
            timezone="UTC",
            briefing_time="12:00",
        )

        try:
            scheduler_utc.start(mock_job)
            next_run = scheduler_utc.get_next_run_time()

            assert next_run is not None
            assert next_run.tzinfo.zone == "UTC"

        finally:
            scheduler_utc.stop()

        # Test with US/Eastern
        scheduler_eastern = BriefingScheduler(
            timezone="US/Eastern",
            briefing_time="09:00",
        )

        try:
            scheduler_eastern.start(mock_job)
            next_run = scheduler_eastern.get_next_run_time()

            assert next_run is not None
            assert "Eastern" in next_run.tzinfo.zone or next_run.tzinfo.zone == "US/Eastern"

        finally:
            scheduler_eastern.stop()

    def test_job_execution_listener(self, mock_job):
        """Test job execution listener is called."""
        scheduler = BriefingScheduler(briefing_time="23:59")

        try:
            scheduler.start(mock_job)
            scheduler.trigger_now()
            time.sleep(2)

            # Verify job was executed via listener logs
            # (actual verification would require inspecting logs)
            assert mock_job.call_count >= 1

        finally:
            scheduler.stop()

    def test_context_manager(self, mock_job):
        """Test scheduler as context manager."""
        with BriefingScheduler(briefing_time="09:00") as scheduler:
            scheduler.start(mock_job)
            assert scheduler.is_running()

        # Should be stopped after context exit
        assert not scheduler.is_running()

    def test_briefing_time_parsing(self, mock_job):
        """Test various briefing time formats."""
        # Valid formats
        valid_times = ["00:00", "09:30", "23:59", "12:00"]

        for time_str in valid_times:
            scheduler = BriefingScheduler(briefing_time=time_str)
            try:
                scheduler.start(mock_job)
                next_run = scheduler.get_next_run_time()

                hour, minute = map(int, time_str.split(":"))
                assert next_run.hour == hour
                assert next_run.minute == minute

            finally:
                scheduler.stop()

    def test_job_error_listener(self, mock_job):
        """Test job error listener handles exceptions."""
        # Create job that raises exception
        error_job = Mock(side_effect=Exception("Test error"))

        scheduler = BriefingScheduler(briefing_time="23:59")

        try:
            scheduler.start(error_job)
            scheduler.trigger_now()
            time.sleep(2)

            # Job should have been called and error logged
            assert error_job.call_count >= 1

        finally:
            scheduler.stop()
