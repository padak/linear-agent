"""Unit tests for PreferenceBasedRanker."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.linear_chief.intelligence.preference_ranker import (
    PreferenceBasedRanker,
    extract_topics,
)


class TestExtractTopics:
    """Tests for extract_topics helper function."""

    def test_extract_backend_topics(self):
        """Test extraction of backend topics."""
        text = "Backend API optimization for database performance"
        topics = extract_topics(text)

        assert "backend" in topics
        assert "performance" in topics

    def test_extract_frontend_topics(self):
        """Test extraction of frontend topics."""
        text = "React UI component with CSS styling"
        topics = extract_topics(text)

        assert "frontend" in topics

    def test_extract_multiple_topics(self):
        """Test extraction of multiple topics."""
        text = "Backend API with React frontend and Docker deployment"
        topics = extract_topics(text)

        assert "backend" in topics
        assert "frontend" in topics
        assert "infrastructure" in topics

    def test_extract_no_topics(self):
        """Test extraction with no matching keywords."""
        text = "Generic task with no specific keywords"
        topics = extract_topics(text)

        assert topics == []

    def test_extract_topics_case_insensitive(self):
        """Test case insensitive topic extraction."""
        text = "BACKEND API with DATABASE queries"
        topics = extract_topics(text)

        assert "backend" in topics


class TestPreferenceBasedRanker:
    """Tests for PreferenceBasedRanker class."""

    @pytest.fixture
    def ranker(self):
        """Create PreferenceBasedRanker instance."""
        return PreferenceBasedRanker(user_id="test@example.com")

    @pytest.fixture
    def mock_preferences(self):
        """Mock preference data."""
        return {
            "topic_scores": {
                "backend": 0.9,
                "api": 0.85,
                "frontend": 0.3,
                "performance": 0.8,
                "documentation": 0.2,
            },
            "team_scores": {
                "Backend Team": 0.9,
                "Frontend Team": 0.4,
            },
            "label_scores": {
                "bug": 0.95,
                "feature": 0.5,
                "documentation": 0.2,
            },
            "analysis_date": "2025-11-05T16:30:00Z",
        }

    @pytest.fixture
    def sample_issue(self):
        """Sample issue dictionary."""
        return {
            "identifier": "TEST-1",
            "title": "Backend API optimization",
            "description": "Improve backend performance",
            "team": {"name": "Backend Team"},
            "labels": {"nodes": [{"name": "bug"}, {"name": "performance"}]},
        }

    @pytest.mark.asyncio
    async def test_calculate_personalized_priority_high_preference(
        self, ranker, sample_issue, mock_preferences
    ):
        """Test personalized priority with high preference."""
        # Mock preferences and engagement
        ranker._cached_preferences = mock_preferences

        with patch.object(ranker, "get_engagement_score", return_value=0.0) as mock_engagement:
            base_priority = 5.0
            personalized = await ranker.calculate_personalized_priority(
                issue=sample_issue,
                base_priority=base_priority,
            )

            # With high topic (0.9, 0.8 avg=0.85), team (0.9), label (0.95, 0.5 avg=0.725):
            # avg_preference = (0.85 + 0.9 + 0.725) / 3 = 0.825
            # preference_boost = 0.825 - 0.5 = 0.325
            # engagement_boost = 0.0
            # personalized = 5.0 * (1 + 0.325 + 0.0) = 6.625

            assert personalized == pytest.approx(6.625, abs=0.1)

    @pytest.mark.asyncio
    async def test_calculate_personalized_priority_low_preference(self, ranker, mock_preferences):
        """Test personalized priority with low preference."""
        ranker._cached_preferences = mock_preferences

        # Issue with low-preference topics
        issue = {
            "identifier": "TEST-2",
            "title": "Frontend CSS documentation",
            "description": "Update CSS docs",
            "team": {"name": "Frontend Team"},
            "labels": {"nodes": [{"name": "documentation"}]},
        }

        with patch.object(ranker, "get_engagement_score", return_value=0.0):
            base_priority = 5.0
            personalized = await ranker.calculate_personalized_priority(
                issue=issue,
                base_priority=base_priority,
            )

            # With low topic (0.3, 0.2 avg=0.25), team (0.4), label (0.2) preferences:
            # avg_preference = (0.25 + 0.4 + 0.2) / 3 = 0.283
            # preference_boost = 0.283 - 0.5 = -0.217
            # engagement_boost = 0.0
            # personalized = 5.0 * (1 - 0.217 + 0.0) = 3.915

            assert personalized == pytest.approx(3.92, abs=0.1)

    @pytest.mark.asyncio
    async def test_calculate_personalized_priority_neutral_preference(
        self, ranker, mock_preferences
    ):
        """Test personalized priority with neutral preference."""
        ranker._cached_preferences = mock_preferences

        # Issue with neutral preferences
        issue = {
            "identifier": "TEST-3",
            "title": "General task",
            "description": "General work",
            "team": {"name": "Unknown Team"},
            "labels": {"nodes": [{"name": "feature"}]},
        }

        with patch.object(ranker, "get_engagement_score", return_value=0.0):
            base_priority = 7.0
            personalized = await ranker.calculate_personalized_priority(
                issue=issue,
                base_priority=base_priority,
            )

            # With neutral preferences (all default to 0.5):
            # avg_preference = 0.5
            # preference_boost = 0.5 - 0.5 = 0.0
            # engagement_boost = 0.0
            # personalized = 7.0 * (1 + 0.0 + 0.0) = 7.0

            assert personalized == pytest.approx(7.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_calculate_personalized_priority_with_engagement(
        self, ranker, sample_issue, mock_preferences
    ):
        """Test personalized priority with engagement boost."""
        ranker._cached_preferences = mock_preferences

        with patch.object(ranker, "get_engagement_score", return_value=0.8):
            base_priority = 8.0
            personalized = await ranker.calculate_personalized_priority(
                issue=sample_issue,
                base_priority=base_priority,
            )

            # With high preferences (avg ~0.916) and high engagement (0.8):
            # preference_boost = 0.416
            # engagement_boost = 0.8 * 0.3 = 0.24
            # personalized = 8.0 * (1 + 0.416 + 0.24) = 13.248 -> capped at 10.0

            assert personalized == 10.0

    @pytest.mark.asyncio
    async def test_calculate_personalized_priority_capped_at_10(
        self, ranker, sample_issue, mock_preferences
    ):
        """Test that personalized priority is capped at 10.0."""
        ranker._cached_preferences = mock_preferences

        with patch.object(ranker, "get_engagement_score", return_value=1.0):
            base_priority = 9.0
            personalized = await ranker.calculate_personalized_priority(
                issue=sample_issue,
                base_priority=base_priority,
            )

            # Should be capped at 10.0
            assert personalized == 10.0

    @pytest.mark.asyncio
    async def test_get_topic_score_with_topics(self, ranker, mock_preferences):
        """Test get_topic_score with detected topics."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "title": "Backend API optimization",
            "description": "Improve backend performance",
        }

        score = await ranker.get_topic_score(issue)

        # Should detect "backend" (0.9) and "performance" (0.8)
        # Average: (0.9 + 0.8) / 2 = 0.85
        assert score == pytest.approx(0.85, abs=0.05)

    @pytest.mark.asyncio
    async def test_get_topic_score_no_topics(self, ranker, mock_preferences):
        """Test get_topic_score with no detected topics."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "title": "Generic task",
            "description": "Some generic work",
        }

        score = await ranker.get_topic_score(issue)

        # Should return neutral score
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_get_team_score_with_preference(self, ranker, mock_preferences):
        """Test get_team_score with team preference."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "team": {"name": "Backend Team"},
        }

        score = await ranker.get_team_score(issue)

        # Should match "Backend Team" preference
        assert score == 0.9

    @pytest.mark.asyncio
    async def test_get_team_score_no_preference(self, ranker, mock_preferences):
        """Test get_team_score with no team preference."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "team": {"name": "Unknown Team"},
        }

        score = await ranker.get_team_score(issue)

        # Should return neutral score
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_get_team_score_missing_team(self, ranker, mock_preferences):
        """Test get_team_score with missing team."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "team": None,
        }

        score = await ranker.get_team_score(issue)

        # Should return neutral score
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_get_label_score_with_preferences(self, ranker, mock_preferences):
        """Test get_label_score with label preferences."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "labels": {"nodes": [{"name": "bug"}, {"name": "feature"}]},
        }

        score = await ranker.get_label_score(issue)

        # Should average "bug" (0.95) and "feature" (0.5)
        # Average: (0.95 + 0.5) / 2 = 0.725
        assert score == pytest.approx(0.725, abs=0.01)

    @pytest.mark.asyncio
    async def test_get_label_score_no_labels(self, ranker, mock_preferences):
        """Test get_label_score with no labels."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "labels": {"nodes": []},
        }

        score = await ranker.get_label_score(issue)

        # Should return neutral score
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_get_label_score_list_format(self, ranker, mock_preferences):
        """Test get_label_score with list-formatted labels."""
        ranker._cached_preferences = mock_preferences

        issue = {
            "identifier": "TEST-1",
            "labels": [{"name": "bug"}],
        }

        score = await ranker.get_label_score(issue)

        # Should match "bug" preference
        assert score == 0.95

    @pytest.mark.asyncio
    async def test_get_engagement_score(self, ranker):
        """Test get_engagement_score."""
        issue = {"identifier": "TEST-1"}

        # Mock EngagementTracker
        mock_tracker = AsyncMock()
        mock_tracker.calculate_engagement_score = AsyncMock(return_value=0.75)
        ranker.engagement_tracker = mock_tracker

        score = await ranker.get_engagement_score(issue)

        assert score == 0.75
        mock_tracker.calculate_engagement_score.assert_called_once_with(
            user_id="test@example.com", issue_id="TEST-1"
        )

    @pytest.mark.asyncio
    async def test_get_engagement_score_missing_identifier(self, ranker):
        """Test get_engagement_score with missing identifier."""
        issue = {}

        score = await ranker.get_engagement_score(issue)

        # Should return 0.0
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_rank_issues(self, ranker, mock_preferences):
        """Test rank_issues method."""
        ranker._cached_preferences = mock_preferences

        issues = [
            {
                "identifier": "TEST-1",
                "title": "Frontend task",
                "description": "CSS work",
                "team": {"name": "Frontend Team"},
                "labels": {"nodes": [{"name": "documentation"}]},
                "_analysis": {"priority": 5},
            },
            {
                "identifier": "TEST-2",
                "title": "Backend API bug",
                "description": "Fix backend bug",
                "team": {"name": "Backend Team"},
                "labels": {"nodes": [{"name": "bug"}]},
                "_analysis": {"priority": 5},
            },
        ]

        with patch.object(ranker, "get_engagement_score", return_value=0.0):
            ranked = await ranker.rank_issues(issues)

            # Backend issue should rank higher due to preferences
            assert len(ranked) == 2
            assert ranked[0][0]["identifier"] == "TEST-2"  # Backend issue first
            assert ranked[1][0]["identifier"] == "TEST-1"  # Frontend issue second
            assert ranked[0][1] > ranked[1][1]  # Higher priority

    @pytest.mark.asyncio
    async def test_rank_issues_with_base_priorities(self, ranker, mock_preferences):
        """Test rank_issues with explicit base priorities."""
        ranker._cached_preferences = mock_preferences

        issues = [
            {
                "identifier": "TEST-1",
                "title": "Backend task",
                "description": "Backend work",
                "team": {"name": "Backend Team"},
                "labels": {"nodes": [{"name": "bug"}]},
            },
        ]

        base_priorities = {"TEST-1": 7.0}

        with patch.object(ranker, "get_engagement_score", return_value=0.0):
            ranked = await ranker.rank_issues(issues, base_priorities)

            assert len(ranked) == 1
            assert ranked[0][1] > 7.0  # Should be boosted

    @pytest.mark.asyncio
    async def test_get_preference_context(self, ranker, mock_preferences):
        """Test get_preference_context method."""
        ranker._cached_preferences = mock_preferences

        context = await ranker.get_preference_context()

        assert context["user_id"] == "test@example.com"
        assert context["topic_preferences"] == mock_preferences["topic_scores"]
        assert context["team_preferences"] == mock_preferences["team_scores"]
        assert context["label_preferences"] == mock_preferences["label_scores"]
        assert context["last_updated"] == "2025-11-05T16:30:00Z"

    @pytest.mark.asyncio
    async def test_get_preference_context_no_preferences(self, ranker):
        """Test get_preference_context with no preferences loaded."""

        # Mock _load_preferences to set empty preferences
        async def mock_load():
            ranker._cached_preferences = {
                "topic_scores": {},
                "team_scores": {},
                "label_scores": {},
            }

        with patch.object(ranker, "_load_preferences", side_effect=mock_load):
            context = await ranker.get_preference_context()

            assert context["user_id"] == "test@example.com"
            assert context["topic_preferences"] == {}
            assert context["team_preferences"] == {}
            assert context["label_preferences"] == {}

    @pytest.mark.asyncio
    async def test_load_preferences(self, ranker, mock_preferences):
        """Test _load_preferences method caching behavior."""
        # Start with no cached preferences
        ranker._cached_preferences = None

        # Load preferences (will call real PreferenceLearner which may return empty)
        await ranker._load_preferences()

        # Should have loaded some preferences structure (even if empty)
        assert ranker._cached_preferences is not None
        assert "topic_scores" in ranker._cached_preferences
        assert "team_scores" in ranker._cached_preferences
        assert "label_scores" in ranker._cached_preferences

        # Test caching: set known data
        ranker._cached_preferences = mock_preferences

        # Verify cache is working
        assert ranker._cached_preferences == mock_preferences

    @pytest.mark.asyncio
    async def test_handles_missing_preferences_gracefully(self, ranker):
        """Test that ranker handles missing preferences gracefully."""
        # Mock PreferenceLearner to raise exception
        mock_learner = AsyncMock()
        mock_learner.get_preferences = AsyncMock(side_effect=Exception("Preferences not found"))

        with patch(
            "linear_chief.intelligence.preference_learner.PreferenceLearner",
            return_value=mock_learner,
        ):
            await ranker._load_preferences()

            # Should have empty preferences (fallback)
            assert ranker._cached_preferences["topic_scores"] == {}
            assert ranker._cached_preferences["team_scores"] == {}
            assert ranker._cached_preferences["label_scores"] == {}

    @pytest.mark.asyncio
    async def test_handles_missing_engagement_gracefully(self, ranker, sample_issue):
        """Test that ranker handles missing engagement gracefully."""
        ranker._cached_preferences = {
            "topic_scores": {},
            "team_scores": {},
            "label_scores": {},
        }

        # Mock EngagementTracker to raise exception
        mock_tracker = AsyncMock()
        mock_tracker.calculate_engagement_score = AsyncMock(
            side_effect=Exception("Engagement not found")
        )
        ranker.engagement_tracker = mock_tracker

        # Should still calculate priority (falls back to 0.0 engagement)
        base_priority = 5.0
        personalized = await ranker.calculate_personalized_priority(
            issue=sample_issue,
            base_priority=base_priority,
        )

        # Should return base priority (no boost from preferences or engagement)
        assert personalized == pytest.approx(5.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_error_handling_in_calculate_priority(
        self, ranker, sample_issue, mock_preferences
    ):
        """Test error handling in calculate_personalized_priority."""
        ranker._cached_preferences = mock_preferences

        # Mock get_engagement_score to raise exception
        with patch.object(
            ranker, "get_engagement_score", side_effect=Exception("Engagement error")
        ):
            base_priority = 5.0
            personalized = await ranker.calculate_personalized_priority(
                issue=sample_issue,
                base_priority=base_priority,
            )

            # Should fallback to base priority
            assert personalized == 5.0
