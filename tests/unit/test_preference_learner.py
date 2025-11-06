"""Unit tests for PreferenceLearner."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from linear_chief.intelligence.preference_learner import PreferenceLearner
from linear_chief.storage.models import Feedback, IssueHistory, UserPreference
from linear_chief.storage.repositories import (
    FeedbackRepository,
    IssueHistoryRepository,
    UserPreferenceRepository,
)


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    session.commit = MagicMock()
    session.add = MagicMock()
    session.refresh = MagicMock()
    session.query = MagicMock()
    return session


@pytest.fixture
def preference_learner():
    """Create PreferenceLearner instance."""
    return PreferenceLearner(user_id="test_user")


@pytest.fixture
def sample_feedback():
    """Create sample feedback data."""
    now = datetime.utcnow()

    positive_feedback = [
        Feedback(
            id=1,
            user_id="test_user",
            briefing_id=1,
            feedback_type="positive",
            timestamp=now,
            extra_metadata={"issue_id": "PROJ-101"},
        ),
        Feedback(
            id=2,
            user_id="test_user",
            briefing_id=1,
            feedback_type="positive",
            timestamp=now,
            extra_metadata={"issue_id": "PROJ-102"},
        ),
        Feedback(
            id=3,
            user_id="test_user",
            briefing_id=2,
            feedback_type="positive",
            timestamp=now,
            extra_metadata={"issue_id": "PROJ-103"},
        ),
    ]

    negative_feedback = [
        Feedback(
            id=4,
            user_id="test_user",
            briefing_id=2,
            feedback_type="negative",
            timestamp=now,
            extra_metadata={"issue_id": "PROJ-104"},
        ),
    ]

    return positive_feedback + negative_feedback


@pytest.fixture
def sample_issues():
    """Create sample issue snapshots."""
    return {
        "PROJ-101": IssueHistory(
            id=1,
            issue_id="PROJ-101",
            linear_id="uuid-101",
            title="Fix backend API authentication bug",
            state="In Progress",
            priority=1,
            assignee_id="user1",
            assignee_name="Alice",
            team_id="team1",
            team_name="Backend Team",
            labels=["bug", "urgent"],
            extra_metadata={},
            snapshot_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ),
        "PROJ-102": IssueHistory(
            id=2,
            issue_id="PROJ-102",
            linear_id="uuid-102",
            title="Implement GraphQL API for user profiles",
            state="In Progress",
            priority=2,
            assignee_id="user2",
            assignee_name="Bob",
            team_id="team1",
            team_name="Backend Team",
            labels=["feature", "api"],
            extra_metadata={},
            snapshot_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ),
        "PROJ-103": IssueHistory(
            id=3,
            issue_id="PROJ-103",
            linear_id="uuid-103",
            title="Optimize database queries for reports",
            state="In Progress",
            priority=2,
            assignee_id="user3",
            assignee_name="Charlie",
            team_id="team2",
            team_name="Platform Team",
            labels=["performance", "database"],
            extra_metadata={},
            snapshot_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ),
        "PROJ-104": IssueHistory(
            id=4,
            issue_id="PROJ-104",
            linear_id="uuid-104",
            title="Update CSS styles for login page",
            state="Todo",
            priority=3,
            assignee_id="user4",
            assignee_name="Diana",
            team_id="team3",
            team_name="Frontend Team",
            labels=["ui", "css"],
            extra_metadata={},
            snapshot_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ),
    }


class TestPreferenceLearner:
    """Test PreferenceLearner functionality."""

    @pytest.mark.asyncio
    async def test_detect_topics_backend(self, preference_learner):
        """Test topic detection for backend-related issues."""
        issue = {
            "title": "Fix backend API authentication bug",
            "description": "The REST API endpoint returns 401 for valid tokens",
        }

        topics = preference_learner._detect_topics(issue)

        assert "backend" in topics
        # Note: "api" keyword is in the title, may also detect "security" due to "authentication"

    @pytest.mark.asyncio
    async def test_detect_topics_frontend(self, preference_learner):
        """Test topic detection for frontend-related issues."""
        issue = {
            "title": "Update React component styles",
            "description": "Need to update CSS for the login page UI",
        }

        topics = preference_learner._detect_topics(issue)

        assert "frontend" in topics

    @pytest.mark.asyncio
    async def test_detect_topics_multiple(self, preference_learner):
        """Test detection of multiple topics in single issue."""
        issue = {
            "title": "Add API tests for authentication",
            "description": "Need pytest tests for the backend API",
        }

        topics = preference_learner._detect_topics(issue)

        assert "backend" in topics
        assert "testing" in topics
        # Should detect multiple topics from title and description

    @pytest.mark.asyncio
    async def test_extract_topic_preferences_positive_only(self, preference_learner):
        """Test topic preference extraction with only positive feedback."""
        positive_issues = [
            {"title": "Backend API fix", "description": "Fix REST endpoint"},
            {"title": "Database optimization", "description": "Optimize SQL queries"},
        ]
        negative_issues = []

        prefs = await preference_learner.extract_topic_preferences(
            positive_issues, negative_issues
        )

        # Should have high scores for backend-related topics
        assert prefs.get("backend", 0) > 0.6
        # Database or performance should be detected from SQL/optimize
        assert len(prefs) > 0  # At least some topics detected

    @pytest.mark.asyncio
    async def test_extract_topic_preferences_mixed(self, preference_learner):
        """Test topic preference extraction with mixed feedback."""
        positive_issues = [
            {"title": "Backend API fix", "description": "Fix REST endpoint"},
            {"title": "Backend API fix", "description": "Fix GraphQL endpoint"},
        ]
        negative_issues = [
            {"title": "Frontend UI bug", "description": "Fix CSS issue"},
        ]

        prefs = await preference_learner.extract_topic_preferences(
            positive_issues, negative_issues
        )

        # Backend should have high score
        assert prefs.get("backend", 0) > 0.6
        # Frontend should have low score
        assert prefs.get("frontend", 1.0) < 0.5

    @pytest.mark.asyncio
    async def test_extract_team_preferences(self, preference_learner):
        """Test team preference extraction."""
        positive_issues = [
            {"team_name": "Backend Team"},
            {"team_name": "Backend Team"},
        ]
        negative_issues = [
            {"team_name": "Frontend Team"},
        ]

        prefs = await preference_learner.extract_team_preferences(
            positive_issues, negative_issues
        )

        # Backend Team should have high score
        assert prefs.get("Backend Team", 0) > 0.6
        # Frontend Team should have low score
        assert prefs.get("Frontend Team", 1.0) < 0.5

    @pytest.mark.asyncio
    async def test_extract_label_preferences(self, preference_learner):
        """Test label preference extraction."""
        positive_issues = [
            {"labels": ["bug", "urgent"]},
            {"labels": ["bug", "api"]},
        ]
        negative_issues = [
            {"labels": ["documentation"]},
        ]

        prefs = await preference_learner.extract_label_preferences(
            positive_issues, negative_issues
        )

        # bug should have high score (appears in both positive issues)
        assert prefs.get("bug", 0) > 0.6
        # documentation should have low score
        assert prefs.get("documentation", 1.0) < 0.5

    @pytest.mark.asyncio
    async def test_empty_preferences(self, preference_learner):
        """Test _empty_preferences returns correct structure."""
        prefs = preference_learner._empty_preferences()

        assert prefs["preferred_topics"] == []
        assert prefs["preferred_teams"] == []
        assert prefs["preferred_labels"] == []
        assert prefs["engagement_score"] == 0.0
        assert prefs["confidence"] == 0.0
        assert prefs["feedback_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_preferences_structure(self, preference_learner):
        """Test _empty_preferences returns correct structure."""
        prefs = preference_learner._empty_preferences()

        # Verify all required keys exist
        assert "preferred_topics" in prefs
        assert "preferred_teams" in prefs
        assert "preferred_labels" in prefs
        assert "disliked_topics" in prefs
        assert "disliked_teams" in prefs
        assert "disliked_labels" in prefs
        assert "engagement_score" in prefs
        assert "confidence" in prefs
        assert "feedback_count" in prefs
        assert "topic_scores" in prefs
        assert "team_scores" in prefs
        assert "label_scores" in prefs

    @pytest.mark.asyncio
    async def test_save_to_mem0(self, preference_learner):
        """Test save_to_mem0 stores preferences correctly."""
        preferences = {
            "preferred_topics": ["backend", "api"],
            "disliked_topics": ["frontend"],
            "preferred_teams": ["Backend Team"],
            "preferred_labels": ["bug"],
            "topic_scores": {"backend": 0.9, "api": 0.8, "frontend": 0.3},
            "team_scores": {"Backend Team": 0.85},
            "label_scores": {"bug": 0.92},
            "confidence": 0.8,
            "analysis_date": datetime.utcnow().isoformat(),
        }

        # Mock MemoryManager
        with patch.object(
            preference_learner.memory_manager, "add_user_preference", new=AsyncMock()
        ) as mock_add:
            await preference_learner.save_to_mem0(preferences)

            # Should call add_user_preference multiple times
            assert mock_add.call_count > 0
            # Verify it was called with correct structure
            calls = mock_add.call_args_list
            # Check first call for backend topic
            assert "backend" in calls[0][0][0].lower()

    @pytest.mark.asyncio
    async def test_get_preferences(self, preference_learner):
        """Test get_preferences retrieves from mem0."""
        mock_mem0_data = [
            {
                "metadata": {
                    "preference_type": "topic",
                    "preference_key": "backend",
                    "score": 0.9,
                }
            },
            {
                "metadata": {
                    "preference_type": "topic",
                    "preference_key": "frontend",
                    "score": 0.3,
                }
            },
            {
                "metadata": {
                    "preference_type": "team",
                    "preference_key": "Backend Team",
                    "score": 0.85,
                }
            },
        ]

        # Mock MemoryManager
        with patch.object(
            preference_learner.memory_manager,
            "get_user_preferences",
            new=AsyncMock(return_value=mock_mem0_data),
        ):
            prefs = await preference_learner.get_preferences()

            assert "backend" in prefs["preferred_topics"]
            assert "frontend" in prefs["disliked_topics"]
            assert "Backend Team" in prefs["preferred_teams"]


class TestUserPreferenceRepository:
    """Test UserPreferenceRepository functionality."""

    def test_save_preference_create(self, mock_session):
        """Test creating new preference."""
        repo = UserPreferenceRepository(mock_session)

        # Mock query to return None (no existing preference)
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        pref = repo.save_preference(
            user_id="test_user",
            preference_type="topic",
            preference_key="backend",
            score=0.9,
            confidence=0.8,
            feedback_count=10,
        )

        # Should add new preference
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_save_preference_update(self, mock_session):
        """Test updating existing preference."""
        repo = UserPreferenceRepository(mock_session)

        # Mock existing preference
        existing_pref = UserPreference(
            id=1,
            user_id="test_user",
            preference_type="topic",
            preference_key="backend",
            score=0.7,
            confidence=0.6,
            feedback_count=5,
            last_updated=datetime.utcnow(),
            extra_metadata=None,
        )

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = existing_pref
        mock_session.query.return_value = mock_query

        pref = repo.save_preference(
            user_id="test_user",
            preference_type="topic",
            preference_key="backend",
            score=0.9,
            confidence=0.8,
            feedback_count=10,
        )

        # Should update, not add
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()

    def test_save_preference_validation(self, mock_session):
        """Test input validation in save_preference."""
        repo = UserPreferenceRepository(mock_session)

        # Invalid preference_type
        with pytest.raises(ValueError, match="Invalid preference_type"):
            repo.save_preference(
                user_id="test_user",
                preference_type="invalid_type",
                preference_key="backend",
                score=0.9,
            )

        # Invalid score (> 1.0)
        with pytest.raises(ValueError, match="Score must be between"):
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=1.5,
            )

        # Invalid confidence (< 0.0)
        with pytest.raises(ValueError, match="Confidence must be between"):
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=-0.1,
            )

    def test_get_preferences_by_type(self, mock_session):
        """Test getting preferences by type."""
        repo = UserPreferenceRepository(mock_session)

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.query.return_value = mock_query

        prefs = repo.get_preferences_by_type("test_user", "topic")

        # Should filter and order correctly
        mock_query.filter.assert_called()
        mock_query.filter.return_value.order_by.assert_called()

    def test_get_top_preferences(self, mock_session):
        """Test getting top N preferences."""
        repo = UserPreferenceRepository(mock_session)

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )
        mock_session.query.return_value = mock_query

        prefs = repo.get_top_preferences(
            "test_user", "topic", limit=5, min_score=0.7
        )

        # Should apply limit and score filter
        mock_query.filter.assert_called()
        mock_query.filter.return_value.order_by.return_value.limit.assert_called_with(
            5
        )

    def test_delete_preferences(self, mock_session):
        """Test deleting preferences."""
        repo = UserPreferenceRepository(mock_session)

        # Create proper mock chain for query().filter().filter().delete()
        mock_query_chain = MagicMock()
        mock_query_chain.delete.return_value = 3

        mock_filter_chain = MagicMock()
        mock_filter_chain.filter.return_value = mock_query_chain

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_filter_chain
        mock_session.query.return_value = mock_query

        count = repo.delete_preferences("test_user", preference_type="topic")

        assert count == 3
        mock_session.commit.assert_called_once()

    def test_get_preference_summary(self, mock_session):
        """Test getting preference summary statistics."""
        repo = UserPreferenceRepository(mock_session)

        # Mock preferences
        prefs = [
            UserPreference(
                id=1,
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=0.8,
                feedback_count=10,
                last_updated=datetime.utcnow(),
                extra_metadata=None,
            ),
            UserPreference(
                id=2,
                user_id="test_user",
                preference_type="topic",
                preference_key="api",
                score=0.8,
                confidence=0.7,
                feedback_count=8,
                last_updated=datetime.utcnow(),
                extra_metadata=None,
            ),
            UserPreference(
                id=3,
                user_id="test_user",
                preference_type="team",
                preference_key="Backend Team",
                score=0.85,
                confidence=0.75,
                feedback_count=9,
                last_updated=datetime.utcnow(),
                extra_metadata=None,
            ),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = prefs
        mock_session.query.return_value = mock_query

        summary = repo.get_preference_summary("test_user")

        assert summary["total_count"] == 3
        assert "topic" in summary["by_type"]
        assert "team" in summary["by_type"]
        assert summary["by_type"]["topic"]["count"] == 2
        assert summary["by_type"]["team"]["count"] == 1
        assert 0.0 < summary["avg_score"] <= 1.0
        assert 0.0 < summary["avg_confidence"] <= 1.0
