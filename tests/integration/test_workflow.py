"""Integration tests for full briefing workflow."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from linear_chief.orchestrator import BriefingOrchestrator
from linear_chief.storage import (
    get_engine,
    Base,
    get_session_maker,
    get_db_session,
    BriefingRepository,
    MetricsRepository,
)


@pytest.fixture
def test_engine():
    """Create in-memory test database."""
    engine = get_engine(database_path=":memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def mock_linear_issues():
    """Mock Linear issues data."""
    return [
        {
            "id": "uuid-1",
            "identifier": "PROJ-123",
            "title": "Fix login bug",
            "state": {"name": "In Progress"},
            "priority": 1,
            "priorityLabel": "Urgent",
            "assignee": {"id": "user-1", "name": "John Doe"},
            "team": {"id": "team-1", "name": "Engineering"},
            "description": "Users cannot log in after password reset",
            "updatedAt": datetime.utcnow().isoformat(),
            "labels": {"nodes": [{"name": "bug"}, {"name": "urgent"}]},
            "comments": {"nodes": []},
        },
        {
            "id": "uuid-2",
            "identifier": "PROJ-124",
            "title": "Add dark mode",
            "state": {"name": "Todo"},
            "priority": 3,
            "priorityLabel": "Normal",
            "assignee": None,
            "team": {"id": "team-1", "name": "Engineering"},
            "description": "Implement dark mode theme",
            "updatedAt": datetime.utcnow().isoformat(),
            "labels": {"nodes": [{"name": "feature"}]},
            "comments": {"nodes": []},
        },
    ]


@pytest.mark.asyncio
class TestBriefingWorkflow:
    """Integration tests for briefing workflow."""

    async def test_full_workflow_success(self, test_engine, mock_linear_issues, monkeypatch):
        """Test successful end-to-end briefing workflow."""
        # Mock external API calls
        mock_linear_client = AsyncMock()
        mock_linear_client.get_my_relevant_issues = AsyncMock(return_value=mock_linear_issues)

        mock_agent = AsyncMock()
        mock_agent.generate_briefing = AsyncMock(return_value="Test briefing content")
        mock_agent.estimate_cost = Mock(return_value=0.05)
        mock_agent.model = "claude-sonnet-4-20250514"

        mock_telegram = AsyncMock()
        mock_telegram.send_briefing = AsyncMock(return_value=True)

        mock_memory = AsyncMock()
        mock_memory.get_agent_context = AsyncMock(return_value="Previous context")
        mock_memory.add_briefing_context = AsyncMock()

        mock_vector_store = AsyncMock()
        mock_vector_store.add_issue = AsyncMock()

        # Patch session maker to use test database
        monkeypatch.setattr(
            "linear_chief.orchestrator.get_session_maker",
            lambda: get_session_maker(test_engine),
        )

        # Create orchestrator
        orchestrator = BriefingOrchestrator()

        # Replace components with mocks
        orchestrator.linear_client = mock_linear_client
        orchestrator.agent = mock_agent
        orchestrator.telegram_bot = mock_telegram
        orchestrator.memory_manager = mock_memory
        orchestrator.vector_store = mock_vector_store
        orchestrator.session_maker = get_session_maker(test_engine)

        # Execute workflow
        result = await orchestrator.generate_and_send_briefing()

        # Verify result
        assert result["success"] is True
        assert result["issue_count"] == 2
        assert result["briefing_id"] is not None
        assert result["cost_usd"] == 0.05
        assert result["duration_seconds"] is not None

        # Verify API calls
        mock_linear_client.get_my_relevant_issues.assert_called_once()
        mock_agent.generate_briefing.assert_called_once()
        mock_telegram.send_briefing.assert_called_once()
        mock_memory.add_briefing_context.assert_called_once()

        # Verify database records
        for session in get_db_session(get_session_maker(test_engine)):
            briefing_repo = BriefingRepository(session)
            metrics_repo = MetricsRepository(session)

            # Check briefing was saved
            briefings = briefing_repo.get_recent_briefings(days=1)
            assert len(briefings) == 1
            assert briefings[0].content == "Test briefing content"
            assert briefings[0].delivery_status == "sent"

            # Check metrics were recorded
            metrics = metrics_repo.get_metrics(metric_type="briefing_generated", days=1)
            assert len(metrics) > 0

    async def test_workflow_no_issues(self, test_engine, monkeypatch):
        """Test workflow when no issues are found."""
        mock_linear_client = AsyncMock()
        mock_linear_client.get_my_relevant_issues = AsyncMock(return_value=[])

        monkeypatch.setattr(
            "linear_chief.orchestrator.get_session_maker",
            lambda: get_session_maker(test_engine),
        )

        orchestrator = BriefingOrchestrator()
        orchestrator.linear_client = mock_linear_client
        orchestrator.session_maker = get_session_maker(test_engine)

        result = await orchestrator.generate_and_send_briefing()

        assert result["success"] is True
        assert result["issue_count"] == 0
        assert result["briefing_id"] is None

    async def test_workflow_telegram_failure(self, test_engine, mock_linear_issues, monkeypatch):
        """Test workflow when Telegram send fails."""
        mock_linear_client = AsyncMock()
        mock_linear_client.get_my_relevant_issues = AsyncMock(return_value=mock_linear_issues)

        mock_agent = AsyncMock()
        mock_agent.generate_briefing = AsyncMock(return_value="Test briefing")
        mock_agent.estimate_cost = Mock(return_value=0.05)
        mock_agent.model = "claude-sonnet-4-20250514"

        mock_telegram = AsyncMock()
        mock_telegram.send_briefing = AsyncMock(return_value=False)  # Failure

        mock_memory = AsyncMock()
        mock_memory.get_agent_context = AsyncMock(return_value=None)
        mock_memory.add_briefing_context = AsyncMock()

        mock_vector_store = AsyncMock()
        mock_vector_store.add_issue = AsyncMock()

        monkeypatch.setattr(
            "linear_chief.orchestrator.get_session_maker",
            lambda: get_session_maker(test_engine),
        )

        orchestrator = BriefingOrchestrator()
        orchestrator.linear_client = mock_linear_client
        orchestrator.agent = mock_agent
        orchestrator.telegram_bot = mock_telegram
        orchestrator.memory_manager = mock_memory
        orchestrator.vector_store = mock_vector_store
        orchestrator.session_maker = get_session_maker(test_engine)

        result = await orchestrator.generate_and_send_briefing()

        # Workflow should succeed but mark delivery as failed
        assert result["success"] is True

        # Check briefing marked as failed
        for session in get_db_session(get_session_maker(test_engine)):
            briefing_repo = BriefingRepository(session)
            briefings = briefing_repo.get_recent_briefings(days=1)
            assert len(briefings) == 1
            assert briefings[0].delivery_status == "failed"

    async def test_workflow_api_error(self, test_engine, monkeypatch):
        """Test workflow when API call fails."""
        mock_linear_client = AsyncMock()
        mock_linear_client.get_my_relevant_issues = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        monkeypatch.setattr(
            "linear_chief.orchestrator.get_session_maker",
            lambda: get_session_maker(test_engine),
        )

        orchestrator = BriefingOrchestrator()
        orchestrator.linear_client = mock_linear_client
        orchestrator.session_maker = get_session_maker(test_engine)

        with pytest.raises(Exception, match="API connection failed"):
            await orchestrator.generate_and_send_briefing()

        # Verify error metric was recorded
        for session in get_db_session(get_session_maker(test_engine)):
            metrics_repo = MetricsRepository(session)
            error_metrics = metrics_repo.get_metrics(
                metric_type="briefing_error",
                days=1,
            )
            assert len(error_metrics) == 1

    async def test_test_connections(self, monkeypatch):
        """Test connection testing functionality."""
        mock_linear_client = AsyncMock()
        mock_linear_client.get_viewer = AsyncMock(return_value={"id": "user-1", "name": "Test User"})

        mock_telegram = AsyncMock()
        mock_telegram.test_connection = AsyncMock(return_value=True)

        orchestrator = BriefingOrchestrator()
        orchestrator.linear_client = mock_linear_client
        orchestrator.telegram_bot = mock_telegram

        results = await orchestrator.test_connections()

        assert results["linear"] is True
        assert results["telegram"] is True

        mock_linear_client.get_viewer.assert_called_once()
        mock_telegram.test_connection.assert_called_once()

    async def test_test_connections_failure(self, monkeypatch):
        """Test connection testing with failures."""
        mock_linear_client = AsyncMock()
        mock_linear_client.get_viewer = AsyncMock(side_effect=Exception("Connection failed"))

        mock_telegram = AsyncMock()
        mock_telegram.test_connection = AsyncMock(return_value=False)

        orchestrator = BriefingOrchestrator()
        orchestrator.linear_client = mock_linear_client
        orchestrator.telegram_bot = mock_telegram

        results = await orchestrator.test_connections()

        assert results["linear"] is False
        assert results["telegram"] is False
