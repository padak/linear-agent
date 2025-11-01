"""Unit tests for storage layer (database, models, repositories)."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from linear_chief.storage import (
    Base,
    IssueHistory,
    Briefing,
    Metrics,
    IssueHistoryRepository,
    BriefingRepository,
    MetricsRepository,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    yield session
    session.close()


@pytest.fixture
def issue_repo(session):
    """Create IssueHistoryRepository instance."""
    return IssueHistoryRepository(session)


@pytest.fixture
def briefing_repo(session):
    """Create BriefingRepository instance."""
    return BriefingRepository(session)


@pytest.fixture
def metrics_repo(session):
    """Create MetricsRepository instance."""
    return MetricsRepository(session)


class TestIssueHistory:
    """Tests for IssueHistory model."""

    def test_create_issue_snapshot(self, session):
        """Test creating issue snapshot."""
        snapshot = IssueHistory(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test Issue",
            state="In Progress",
            priority=2,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.id is not None
        assert snapshot.issue_id == "PROJ-123"
        assert snapshot.state == "In Progress"

    def test_snapshot_timestamp(self, session):
        """Test automatic snapshot timestamp."""
        snapshot = IssueHistory(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test",
            state="Todo",
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.snapshot_at is not None
        assert snapshot.created_at is not None


class TestIssueHistoryRepository:
    """Tests for IssueHistoryRepository."""

    def test_save_snapshot(self, issue_repo):
        """Test saving issue snapshot."""
        snapshot = issue_repo.save_snapshot(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test Issue",
            state="In Progress",
            priority=2,
            assignee_name="John Doe",
            team_name="Engineering",
            labels=["bug", "urgent"],
        )

        assert snapshot.id is not None
        assert snapshot.issue_id == "PROJ-123"
        assert snapshot.assignee_name == "John Doe"
        assert "bug" in snapshot.labels

    def test_get_latest_snapshot(self, issue_repo):
        """Test retrieving latest snapshot for an issue."""
        # Create multiple snapshots
        issue_repo.save_snapshot(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test",
            state="Todo",
        )

        issue_repo.save_snapshot(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test",
            state="In Progress",
        )

        latest = issue_repo.get_latest_snapshot("PROJ-123")
        assert latest is not None
        assert latest.state == "In Progress"

    def test_get_snapshots_since(self, issue_repo):
        """Test retrieving snapshots since a specific time."""
        # Create old snapshot
        old_snapshot = issue_repo.save_snapshot(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test",
            state="Todo",
        )

        # Manually set old timestamp
        old_snapshot.snapshot_at = datetime.utcnow() - timedelta(days=10)
        issue_repo.session.commit()

        # Create recent snapshot
        issue_repo.save_snapshot(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test",
            state="In Progress",
        )

        # Query snapshots from last 7 days
        recent = issue_repo.get_snapshots_since(
            "PROJ-123",
            datetime.utcnow() - timedelta(days=7),
        )

        assert len(recent) == 1
        assert recent[0].state == "In Progress"

    def test_get_all_latest_snapshots(self, issue_repo):
        """Test retrieving latest snapshot for each issue."""
        # Create snapshots for multiple issues
        issue_repo.save_snapshot(
            issue_id="PROJ-123",
            linear_id="uuid-123",
            title="Test 1",
            state="Done",
        )

        issue_repo.save_snapshot(
            issue_id="PROJ-456",
            linear_id="uuid-456",
            title="Test 2",
            state="In Progress",
        )

        latest_snapshots = issue_repo.get_all_latest_snapshots(days=30)
        assert len(latest_snapshots) == 2

        issue_ids = [s.issue_id for s in latest_snapshots]
        assert "PROJ-123" in issue_ids
        assert "PROJ-456" in issue_ids


class TestBriefing:
    """Tests for Briefing model."""

    def test_create_briefing(self, session):
        """Test creating briefing record."""
        briefing = Briefing(
            content="Test briefing content",
            issue_count=5,
            cost_usd=0.05,
            input_tokens=1000,
            output_tokens=500,
            model_name="claude-sonnet-4-20250514",
        )
        session.add(briefing)
        session.commit()

        assert briefing.id is not None
        assert briefing.issue_count == 5
        assert briefing.delivery_status == "pending"


class TestBriefingRepository:
    """Tests for BriefingRepository."""

    def test_create_briefing(self, briefing_repo):
        """Test creating briefing via repository."""
        briefing = briefing_repo.create_briefing(
            content="Test briefing",
            issue_count=3,
            cost_usd=0.03,
            input_tokens=1000,
            output_tokens=500,
            model_name="claude-sonnet-4-20250514",
        )

        assert briefing.id is not None
        assert briefing.issue_count == 3

    def test_mark_as_sent(self, briefing_repo):
        """Test marking briefing as sent."""
        briefing = briefing_repo.create_briefing(
            content="Test",
            issue_count=1,
        )

        briefing_repo.mark_as_sent(briefing.id, telegram_message_id="12345")

        # Refresh from DB
        briefing_repo.session.refresh(briefing)
        assert briefing.delivery_status == "sent"
        assert briefing.telegram_message_id == "12345"
        assert briefing.sent_at is not None

    def test_mark_as_failed(self, briefing_repo):
        """Test marking briefing as failed."""
        briefing = briefing_repo.create_briefing(
            content="Test",
            issue_count=1,
        )

        briefing_repo.mark_as_failed(briefing.id, "Connection timeout")

        # Refresh from DB
        briefing_repo.session.refresh(briefing)
        assert briefing.delivery_status == "failed"
        assert briefing.error_message == "Connection timeout"

    def test_get_recent_briefings(self, briefing_repo):
        """Test retrieving recent briefings."""
        # Create old briefing
        old_briefing = briefing_repo.create_briefing(
            content="Old",
            issue_count=1,
        )
        old_briefing.generated_at = datetime.utcnow() - timedelta(days=10)
        briefing_repo.session.commit()

        # Create recent briefing
        briefing_repo.create_briefing(
            content="Recent",
            issue_count=1,
        )

        recent = briefing_repo.get_recent_briefings(days=7)
        assert len(recent) == 1
        assert recent[0].content == "Recent"

    def test_get_total_cost(self, briefing_repo):
        """Test calculating total cost."""
        briefing_repo.create_briefing(
            content="Test 1",
            issue_count=1,
            cost_usd=0.05,
        )

        briefing_repo.create_briefing(
            content="Test 2",
            issue_count=1,
            cost_usd=0.03,
        )

        total_cost = briefing_repo.get_total_cost(days=30)
        assert total_cost == pytest.approx(0.08)


class TestMetrics:
    """Tests for Metrics model."""

    def test_create_metric(self, session):
        """Test creating metric record."""
        metric = Metrics(
            metric_type="api_call",
            metric_name="linear_fetch",
            value=1.5,
            unit="seconds",
        )
        session.add(metric)
        session.commit()

        assert metric.id is not None
        assert metric.value == 1.5


class TestMetricsRepository:
    """Tests for MetricsRepository."""

    def test_record_metric(self, metrics_repo):
        """Test recording a metric."""
        metric = metrics_repo.record_metric(
            metric_type="api_call",
            metric_name="test_metric",
            value=100,
            unit="count",
            extra_metadata={"test": "data"},
        )

        assert metric.id is not None
        assert metric.value == 100
        assert metric.extra_metadata["test"] == "data"

    def test_get_metrics_filtered(self, metrics_repo):
        """Test querying metrics with filters."""
        # Create metrics
        metrics_repo.record_metric(
            metric_type="api_call",
            metric_name="metric_a",
            value=1,
            unit="count",
        )

        metrics_repo.record_metric(
            metric_type="api_cost",
            metric_name="metric_b",
            value=0.05,
            unit="usd",
        )

        # Query by type
        api_calls = metrics_repo.get_metrics(metric_type="api_call", days=7)
        assert len(api_calls) == 1
        assert api_calls[0].metric_name == "metric_a"

    def test_get_aggregated_metrics(self, metrics_repo):
        """Test aggregated metrics calculation."""
        # Create multiple metrics
        for value in [1, 2, 3, 4, 5]:
            metrics_repo.record_metric(
                metric_type="test",
                metric_name="test_metric",
                value=value,
                unit="count",
            )

        agg = metrics_repo.get_aggregated_metrics(
            metric_type="test",
            metric_name="test_metric",
            days=7,
        )

        assert agg["sum"] == 15
        assert agg["avg"] == 3
        assert agg["min"] == 1
        assert agg["max"] == 5
        assert agg["count"] == 5
