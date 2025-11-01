"""Unit tests for CLI interface."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from click.testing import CliRunner

from linear_chief.__main__ import cli, init, test, briefing, start, metrics, history
from linear_chief.storage.models import Briefing


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_ensure_directories():
    """Mock ensure_directories."""
    with patch("linear_chief.__main__.ensure_directories") as mock:
        yield mock


@pytest.fixture
def mock_init_db():
    """Mock init_db."""
    with patch("linear_chief.__main__.init_db") as mock:
        yield mock


@pytest.fixture
def mock_orchestrator():
    """Mock BriefingOrchestrator."""
    with patch("linear_chief.__main__.BriefingOrchestrator") as mock_class:
        mock_instance = Mock()
        mock_instance.generate_and_send_briefing = AsyncMock()
        mock_instance.test_connections = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_scheduler():
    """Mock BriefingScheduler."""
    with patch("linear_chief.__main__.BriefingScheduler") as mock_class:
        mock_instance = Mock()
        mock_instance.start = Mock()
        mock_instance.stop = Mock()
        mock_instance.is_running = Mock(return_value=True)
        mock_instance.get_next_run_time = Mock(return_value=datetime.now())
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    with (
        patch("linear_chief.__main__.get_session_maker"),
        patch("linear_chief.__main__.get_db_session") as mock_get_session,
    ):

        # Create mock session
        mock_session = MagicMock()

        # Setup context manager
        mock_get_session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = Mock(return_value=False)

        # Make get_db_session iterable (used in metrics/history commands)
        mock_get_session.return_value.__iter__ = Mock(return_value=iter([mock_session]))

        yield mock_session


@pytest.fixture
def mock_repositories(mock_db_session):
    """Mock repository classes."""
    with (
        patch("linear_chief.__main__.BriefingRepository") as mock_briefing_repo_class,
        patch("linear_chief.__main__.MetricsRepository") as mock_metrics_repo_class,
    ):

        # Create mock repository instances
        mock_briefing_repo = Mock()
        mock_metrics_repo = Mock()

        mock_briefing_repo_class.return_value = mock_briefing_repo
        mock_metrics_repo_class.return_value = mock_metrics_repo

        yield {
            "briefing": mock_briefing_repo,
            "metrics": mock_metrics_repo,
        }


class TestInitCommand:
    """Tests for init command."""

    def test_init_success(self, runner, mock_ensure_directories, mock_init_db):
        """Test successful database initialization."""
        result = runner.invoke(init)

        assert result.exit_code == 0
        assert "Initializing database..." in result.output
        assert "✓ Database initialized:" in result.output
        mock_init_db.assert_called_once()

    def test_init_failure(self, runner, mock_ensure_directories, mock_init_db):
        """Test database initialization failure."""
        mock_init_db.side_effect = Exception("Database error")

        result = runner.invoke(init)

        assert result.exit_code == 1
        assert "✗ Database initialization failed: Database error" in result.output

    def test_init_permission_error(self, runner, mock_ensure_directories, mock_init_db):
        """Test initialization with permission error."""
        mock_init_db.side_effect = PermissionError("Permission denied")

        result = runner.invoke(init)

        assert result.exit_code == 1
        assert "Permission denied" in result.output


class TestTestCommand:
    """Tests for test command."""

    def test_all_services_ok(self, runner, mock_ensure_directories, mock_orchestrator):
        """Test when all services are connected."""
        mock_orchestrator.test_connections.return_value = {
            "linear": True,
            "telegram": True,
        }

        result = runner.invoke(test)

        assert result.exit_code == 0
        assert "Testing service connections..." in result.output
        assert "✓ Linear: OK" in result.output
        assert "✓ Telegram: OK" in result.output

    def test_linear_connection_failed(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test when Linear connection fails."""
        mock_orchestrator.test_connections.return_value = {
            "linear": False,
            "telegram": True,
        }

        result = runner.invoke(test)

        assert result.exit_code == 1
        assert "✗ Linear: FAILED" in result.output
        assert "✓ Telegram: OK" in result.output

    def test_telegram_connection_failed(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test when Telegram connection fails."""
        mock_orchestrator.test_connections.return_value = {
            "linear": True,
            "telegram": False,
        }

        result = runner.invoke(test)

        assert result.exit_code == 1
        assert "✓ Linear: OK" in result.output
        assert "✗ Telegram: FAILED" in result.output

    def test_all_services_failed(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test when all services fail."""
        mock_orchestrator.test_connections.return_value = {
            "linear": False,
            "telegram": False,
        }

        result = runner.invoke(test)

        assert result.exit_code == 1
        assert "✗ Linear: FAILED" in result.output
        assert "✗ Telegram: FAILED" in result.output

    def test_connection_test_exception(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test when connection test raises exception."""
        mock_orchestrator.test_connections.side_effect = Exception("Network error")

        result = runner.invoke(test)

        assert result.exit_code == 1
        assert "✗ Connection test failed: Network error" in result.output


class TestBriefingCommand:
    """Tests for briefing command."""

    def test_briefing_success(self, runner, mock_ensure_directories, mock_orchestrator):
        """Test successful briefing generation."""
        mock_orchestrator.generate_and_send_briefing.return_value = {
            "success": True,
            "briefing_id": 123,
            "issue_count": 5,
            "cost_usd": 0.0234,
            "duration_seconds": 3.45,
        }

        result = runner.invoke(briefing)

        assert result.exit_code == 0
        assert "Generating briefing..." in result.output
        assert "✓ Briefing generated and sent successfully!" in result.output
        assert "Issues: 5" in result.output
        assert "Cost: $0.0234" in result.output
        assert "Duration: 3.45s" in result.output
        assert "Briefing ID: 123" in result.output

    def test_briefing_success_without_optional_fields(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test successful briefing without optional fields."""
        mock_orchestrator.generate_and_send_briefing.return_value = {
            "success": True,
            "issue_count": 3,
        }

        result = runner.invoke(briefing)

        assert result.exit_code == 0
        assert "✓ Briefing generated and sent successfully!" in result.output
        assert "Issues: 3" in result.output
        assert "Cost: $0.0000" in result.output
        assert "Duration: 0.00s" in result.output

    def test_briefing_no_issues(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test briefing when no issues found."""
        mock_orchestrator.generate_and_send_briefing.return_value = {
            "success": True,
            "issue_count": 0,
        }

        result = runner.invoke(briefing)

        assert result.exit_code == 0
        assert "Issues: 0" in result.output

    def test_briefing_failed(self, runner, mock_ensure_directories, mock_orchestrator):
        """Test when briefing generation fails."""
        mock_orchestrator.generate_and_send_briefing.return_value = {
            "success": False,
            "error": "API connection failed",
        }

        result = runner.invoke(briefing)

        assert result.exit_code == 1
        assert "✗ Briefing failed: API connection failed" in result.output

    def test_briefing_failed_no_error_message(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test when briefing fails without error message."""
        mock_orchestrator.generate_and_send_briefing.return_value = {
            "success": False,
        }

        result = runner.invoke(briefing)

        assert result.exit_code == 1
        assert "✗ Briefing failed: Unknown error" in result.output

    def test_briefing_exception(
        self, runner, mock_ensure_directories, mock_orchestrator
    ):
        """Test when briefing raises exception."""
        mock_orchestrator.generate_and_send_briefing.side_effect = Exception(
            "API error"
        )

        result = runner.invoke(briefing)

        assert result.exit_code == 1
        assert "✗ Briefing failed: API error" in result.output


class TestStartCommand:
    """Tests for start command."""

    def test_start_success(
        self, runner, mock_ensure_directories, mock_orchestrator, mock_scheduler
    ):
        """Test starting scheduler successfully."""
        # Simulate user pressing Ctrl+C after one loop
        mock_scheduler.is_running.side_effect = [True, False]

        result = runner.invoke(start)

        assert result.exit_code == 0
        assert "Starting briefing scheduler..." in result.output
        assert "✓ Scheduler started successfully!" in result.output
        assert "Next briefing:" in result.output
        mock_scheduler.start.assert_called_once()

    def test_start_keyboard_interrupt(
        self, runner, mock_ensure_directories, mock_orchestrator, mock_scheduler
    ):
        """Test scheduler graceful shutdown on Ctrl+C."""
        # Make is_running raise KeyboardInterrupt on second call
        mock_scheduler.is_running.side_effect = [True, KeyboardInterrupt()]

        result = runner.invoke(start)

        assert result.exit_code == 0
        assert "Stopping scheduler..." in result.output
        assert "✓ Scheduler stopped" in result.output
        mock_scheduler.stop.assert_called_once()

    def test_start_failure(
        self, runner, mock_ensure_directories, mock_orchestrator, mock_scheduler
    ):
        """Test scheduler start failure."""
        mock_scheduler.start.side_effect = Exception("Scheduler error")

        result = runner.invoke(start)

        assert result.exit_code == 1
        assert "✗ Scheduler failed: Scheduler error" in result.output

    def test_start_invalid_time_format(
        self, runner, mock_ensure_directories, mock_orchestrator, mock_scheduler
    ):
        """Test scheduler with invalid time format."""
        mock_scheduler.start.side_effect = ValueError(
            "BRIEFING_TIME must be in HH:MM format"
        )

        result = runner.invoke(start)

        assert result.exit_code == 1
        assert "✗ Scheduler failed:" in result.output
        assert "HH:MM format" in result.output

    def test_start_invalid_timezone(
        self, runner, mock_ensure_directories, mock_orchestrator, mock_scheduler
    ):
        """Test scheduler with invalid timezone."""
        mock_scheduler.start.side_effect = Exception("Unknown timezone")

        result = runner.invoke(start)

        assert result.exit_code == 1
        assert "✗ Scheduler failed: Unknown timezone" in result.output


class TestMetricsCommand:
    """Tests for metrics command."""

    def test_metrics_with_data(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test metrics display with data."""
        # Setup mock briefings
        now = datetime.now()
        mock_briefings = [
            Briefing(
                id=1,
                generated_at=now - timedelta(days=1),
                issue_count=5,
                cost_usd=0.0234,
                delivery_status="sent",
                content="Test briefing 1",
            ),
            Briefing(
                id=2,
                generated_at=now,
                issue_count=3,
                cost_usd=0.0189,
                delivery_status="sent",
                content="Test briefing 2",
            ),
        ]

        mock_repositories["briefing"].get_recent_briefings.return_value = mock_briefings
        mock_repositories["briefing"].get_total_cost.return_value = 0.0423
        mock_repositories["metrics"].get_aggregated_metrics.return_value = {
            "count": 2,
            "sum": 0.0423,
            "avg": 0.02115,
            "min": 0.0189,
            "max": 0.0234,
        }

        result = runner.invoke(metrics, ["--days", "7"])

        assert result.exit_code == 0
        assert "Metrics for last 7 days:" in result.output
        assert "📊 Briefing Statistics:" in result.output
        assert "Total briefings: 2" in result.output
        assert "Total cost: $0.0423" in result.output
        assert "Average cost per briefing:" in result.output
        assert "Sent successfully: 2" in result.output
        assert "Failed: 0" in result.output
        assert "💰 API Cost Metrics:" in result.output
        assert "Total API calls: 2" in result.output
        assert "📝 Recent Briefings:" in result.output

    def test_metrics_with_failed_briefings(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test metrics with failed briefings."""
        now = datetime.now()
        mock_briefings = [
            Briefing(
                id=1,
                generated_at=now,
                issue_count=5,
                cost_usd=0.0234,
                delivery_status="sent",
                content="Success",
            ),
            Briefing(
                id=2,
                generated_at=now,
                issue_count=3,
                cost_usd=0.0189,
                delivery_status="failed",
                content="Failed",
            ),
        ]

        mock_repositories["briefing"].get_recent_briefings.return_value = mock_briefings
        mock_repositories["briefing"].get_total_cost.return_value = 0.0423
        mock_repositories["metrics"].get_aggregated_metrics.return_value = {
            "count": 0,
            "sum": 0,
            "avg": 0,
            "min": 0,
            "max": 0,
        }

        result = runner.invoke(metrics)

        assert result.exit_code == 0
        assert "Sent successfully: 1" in result.output
        assert "Failed: 1" in result.output

    def test_metrics_no_data(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test metrics display with no data."""
        mock_repositories["briefing"].get_recent_briefings.return_value = []
        mock_repositories["briefing"].get_total_cost.return_value = 0.0
        mock_repositories["metrics"].get_aggregated_metrics.return_value = {
            "count": 0,
            "sum": 0,
            "avg": 0,
            "min": 0,
            "max": 0,
        }

        result = runner.invoke(metrics, ["--days", "7"])

        assert result.exit_code == 0
        assert "Total briefings: 0" in result.output
        assert "Total cost: $0.0000" in result.output

    def test_metrics_with_null_costs(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test metrics with null cost values."""
        now = datetime.now()
        mock_briefings = [
            Briefing(
                id=1,
                generated_at=now,
                issue_count=5,
                cost_usd=None,
                delivery_status="sent",
                content="No cost",
            ),
        ]

        mock_repositories["briefing"].get_recent_briefings.return_value = mock_briefings
        mock_repositories["briefing"].get_total_cost.return_value = 0.0
        mock_repositories["metrics"].get_aggregated_metrics.return_value = {
            "count": 0,
        }

        result = runner.invoke(metrics)

        assert result.exit_code == 0
        assert "N/A" in result.output

    def test_metrics_custom_days(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test metrics with custom days parameter."""
        mock_repositories["briefing"].get_recent_briefings.return_value = []
        mock_repositories["briefing"].get_total_cost.return_value = 0.0
        mock_repositories["metrics"].get_aggregated_metrics.return_value = {"count": 0}

        result = runner.invoke(metrics, ["--days", "30"])

        assert result.exit_code == 0
        assert "Metrics for last 30 days:" in result.output
        mock_repositories["briefing"].get_recent_briefings.assert_called_with(days=30)

    def test_metrics_database_error(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test metrics when database error occurs."""
        mock_repositories["briefing"].get_recent_briefings.side_effect = Exception(
            "DB error"
        )

        result = runner.invoke(metrics)

        assert result.exit_code == 1
        assert "✗ Failed to fetch metrics: DB error" in result.output


class TestHistoryCommand:
    """Tests for history command."""

    def test_history_with_briefings(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test history display with briefings."""
        now = datetime.now()
        mock_briefings = [
            Briefing(
                id=1,
                generated_at=now - timedelta(days=1),
                issue_count=5,
                cost_usd=0.0234,
                delivery_status="sent",
                content="Test briefing content that is long enough to be truncated"
                * 20,
            ),
            Briefing(
                id=2,
                generated_at=now,
                issue_count=3,
                cost_usd=0.0189,
                delivery_status="sent",
                content="Another test briefing",
            ),
        ]

        mock_repositories["briefing"].get_recent_briefings.return_value = mock_briefings

        result = runner.invoke(history, ["--days", "7", "--limit", "10"])

        assert result.exit_code == 0
        assert "Briefing history (last 7 days, max 10 entries):" in result.output
        assert "Briefing #1" in result.output
        assert "Briefing #2" in result.output
        assert "Issues: 5" in result.output
        assert "Issues: 3" in result.output
        assert "Status: sent" in result.output
        assert "Cost: $0.0234" in result.output
        assert "Cost: $0.0189" in result.output
        assert "Content:" in result.output

    def test_history_no_briefings(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test history display with no briefings."""
        mock_repositories["briefing"].get_recent_briefings.return_value = []

        result = runner.invoke(history)

        assert result.exit_code == 0
        assert "No briefings found." in result.output

    def test_history_with_null_cost(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test history with null cost."""
        now = datetime.now()
        mock_briefings = [
            Briefing(
                id=1,
                generated_at=now,
                issue_count=5,
                cost_usd=None,
                delivery_status="sent",
                content="Test",
            ),
        ]

        mock_repositories["briefing"].get_recent_briefings.return_value = mock_briefings

        result = runner.invoke(history)

        assert result.exit_code == 0
        assert "Cost: N/A" in result.output

    def test_history_custom_parameters(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test history with custom days and limit."""
        mock_repositories["briefing"].get_recent_briefings.return_value = []

        result = runner.invoke(history, ["--days", "14", "--limit", "5"])

        assert result.exit_code == 0
        assert "Briefing history (last 14 days, max 5 entries):" in result.output
        mock_repositories["briefing"].get_recent_briefings.assert_called_with(days=14)

    def test_history_truncates_content(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test that long content is truncated to 500 chars."""
        now = datetime.now()
        long_content = "X" * 1000
        mock_briefings = [
            Briefing(
                id=1,
                generated_at=now,
                issue_count=5,
                cost_usd=0.0234,
                delivery_status="sent",
                content=long_content,
            ),
        ]

        mock_repositories["briefing"].get_recent_briefings.return_value = mock_briefings

        result = runner.invoke(history)

        assert result.exit_code == 0
        # Content should be truncated to 500 chars with "..." appended
        assert "X" * 500 + "..." in result.output
        assert "X" * 501 not in result.output

    def test_history_limits_display(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test that history limits number of displayed briefings."""
        now = datetime.now()
        # Create 20 briefings
        mock_briefings = [
            Briefing(
                id=i,
                generated_at=now - timedelta(days=i),
                issue_count=i,
                cost_usd=0.01 * i,
                delivery_status="sent",
                content=f"Briefing {i}",
            )
            for i in range(1, 21)
        ]

        mock_repositories["briefing"].get_recent_briefings.return_value = mock_briefings

        result = runner.invoke(history, ["--limit", "5"])

        assert result.exit_code == 0
        # Should only show first 5 briefings
        assert "Briefing #1" in result.output
        assert "Briefing #5" in result.output
        assert "Briefing #6" not in result.output

    def test_history_database_error(
        self, runner, mock_ensure_directories, mock_db_session, mock_repositories
    ):
        """Test history when database error occurs."""
        mock_repositories["briefing"].get_recent_briefings.side_effect = Exception(
            "DB error"
        )

        result = runner.invoke(history)

        assert result.exit_code == 1
        assert "✗ Failed to fetch history: DB error" in result.output


class TestCLIGroup:
    """Tests for CLI group."""

    def test_cli_help(self, runner, mock_ensure_directories):
        """Test CLI help output."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Linear Chief of Staff" in result.output
        assert "AI-powered briefing agent" in result.output

    def test_init_help(self, runner, mock_ensure_directories):
        """Test init command help."""
        result = runner.invoke(init, ["--help"])

        assert result.exit_code == 0
        assert "Initialize database schema" in result.output

    def test_test_help(self, runner, mock_ensure_directories):
        """Test test command help."""
        result = runner.invoke(test, ["--help"])

        assert result.exit_code == 0
        assert "Test connections to all services" in result.output

    def test_briefing_help(self, runner, mock_ensure_directories):
        """Test briefing command help."""
        result = runner.invoke(briefing, ["--help"])

        assert result.exit_code == 0
        assert "Generate and send briefing immediately" in result.output

    def test_start_help(self, runner, mock_ensure_directories):
        """Test start command help."""
        result = runner.invoke(start, ["--help"])

        assert result.exit_code == 0
        assert "Start the scheduler for daily briefings" in result.output

    def test_metrics_help(self, runner, mock_ensure_directories):
        """Test metrics command help."""
        result = runner.invoke(metrics, ["--help"])

        assert result.exit_code == 0
        assert "Display metrics and statistics" in result.output
        assert "--days" in result.output

    def test_history_help(self, runner, mock_ensure_directories):
        """Test history command help."""
        result = runner.invoke(history, ["--help"])

        assert result.exit_code == 0
        assert "Show briefing history" in result.output
        assert "--days" in result.output
        assert "--limit" in result.output
