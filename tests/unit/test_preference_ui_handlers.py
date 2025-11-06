"""Unit tests for preference UI handlers.

Tests for /preferences, /prefer, /ignore commands and preference reset callback.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from linear_chief.telegram.handlers_preferences import (
    preferences_handler,
    prefer_handler,
    ignore_handler,
    format_full_preferences,
    format_topic_preferences,
    format_team_preferences,
    format_label_preferences,
    format_engagement_stats,
    _format_time_ago,
    _convert_db_prefs_to_dict,
)
from linear_chief.telegram.callbacks import preferences_reset_callback


@pytest.fixture
def mock_update():
    """Create mock Telegram Update object."""
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 12345
    update.effective_chat.send_message = AsyncMock()
    update.effective_chat.send_action = AsyncMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 67890
    update.message = MagicMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram Context object."""
    context = MagicMock()
    context.args = []
    return context


@pytest.fixture
def sample_preferences():
    """Sample preference data."""
    return {
        "topic_scores": {
            "backend": 0.9,
            "api": 0.85,
            "frontend": 0.3,
        },
        "team_scores": {
            "Backend Team": 0.85,
            "Platform Team": 0.75,
        },
        "label_scores": {
            "urgent": 0.9,
            "bug": 0.8,
        },
        "feedback_count": 25,
        "confidence": 0.85,
    }


@pytest.fixture
def sample_engagement_stats():
    """Sample engagement statistics."""
    return {
        "total_interactions": 127,
        "unique_issues": 43,
        "avg_interactions_per_issue": 2.95,
        "most_engaged_issues": ["AI-1799", "DMD-480", "AI-1820"],
        "last_interaction": "2025-11-05T16:30:00Z",
    }


class TestFormatFullPreferences:
    """Test full preferences formatting."""

    def test_format_with_all_data(self, sample_preferences, sample_engagement_stats):
        """Format full preferences with all sections."""
        result = format_full_preferences(sample_preferences, sample_engagement_stats)

        # Should include all sections
        assert "Topic Preferences" in result
        assert "Team Preferences" in result
        assert "Label Preferences" in result
        assert "Most Engaged Issues" in result

        # Should show scores
        assert "backend" in result.lower()
        assert "90%" in result
        assert "AI-1799" in result

        # Should have footer
        assert "/preferences" in result
        assert "reset" in result.lower()

    def test_format_with_empty_data(self):
        """Format preferences with no data."""
        empty_prefs = {
            "topic_scores": {},
            "team_scores": {},
            "label_scores": {},
            "feedback_count": 0,
            "confidence": 0.0,
        }
        empty_stats = {
            "unique_issues": 0,
            "most_engaged_issues": [],
        }

        result = format_full_preferences(empty_prefs, empty_stats)

        # Should still have sections but no data
        assert "Summary" in result
        assert "Feedback samples: 0" in result

    def test_shows_confidence_level(self, sample_preferences, sample_engagement_stats):
        """Confidence level is displayed."""
        result = format_full_preferences(sample_preferences, sample_engagement_stats)

        assert "Confidence: 85%" in result


class TestFormatTopicPreferences:
    """Test topic preference formatting."""

    def test_format_with_topics(self):
        """Format topic preferences with scores."""
        prefs = {
            "topic_scores": {
                "backend": 0.9,
                "api": 0.6,
                "frontend": 0.3,
            },
            "feedback_count": 20,
        }

        result = format_topic_preferences(prefs)

        # Should have all topics
        assert "Backend" in result
        assert "Api" in result
        assert "Frontend" in result

        # Should have scores
        assert "90%" in result
        assert "60%" in result
        assert "30%" in result

        # Should have progress bars
        assert "█" in result
        assert "░" in result

        # Should have emojis
        assert "❤️" in result or "😊" in result or "👎" in result

        # Should show feedback count
        assert "20 feedback" in result.lower()

    def test_format_empty_topics(self):
        """Handle empty topic preferences."""
        prefs = {
            "topic_scores": {},
            "feedback_count": 0,
        }

        result = format_topic_preferences(prefs)

        assert "No topic preferences" in result
        assert "feedback" in result.lower()

    def test_topics_sorted_by_score(self):
        """Topics sorted by score (highest first)."""
        prefs = {
            "topic_scores": {
                "frontend": 0.3,
                "backend": 0.9,
                "api": 0.6,
            },
            "feedback_count": 10,
        }

        result = format_topic_preferences(prefs)
        lines = result.split("\n")

        # Find positions
        backend_pos = next(
            i for i, line in enumerate(lines) if "backend" in line.lower()
        )
        api_pos = next(i for i, line in enumerate(lines) if "api" in line.lower())
        frontend_pos = next(
            i for i, line in enumerate(lines) if "frontend" in line.lower()
        )

        # Backend (0.9) should come before api (0.6) should come before frontend (0.3)
        assert backend_pos < api_pos < frontend_pos


class TestFormatTeamPreferences:
    """Test team preference formatting."""

    def test_format_with_teams(self):
        """Format team preferences."""
        prefs = {
            "team_scores": {
                "Backend Team": 0.85,
                "Frontend Team": 0.4,
            },
            "feedback_count": 15,
        }

        result = format_team_preferences(prefs)

        assert "Backend Team" in result
        assert "85%" in result
        assert "40%" in result
        assert "█" in result  # Progress bar

    def test_format_empty_teams(self):
        """Handle empty team preferences."""
        prefs = {"team_scores": {}, "feedback_count": 0}

        result = format_team_preferences(prefs)

        assert "No team preferences" in result


class TestFormatLabelPreferences:
    """Test label preference formatting."""

    def test_format_with_labels(self):
        """Format label preferences."""
        prefs = {
            "label_scores": {
                "urgent": 0.9,
                "bug": 0.7,
                "feature": 0.3,
            },
            "feedback_count": 30,
        }

        result = format_label_preferences(prefs)

        assert "urgent" in result
        assert "bug" in result
        assert "90%" in result
        assert "█" in result

    def test_format_empty_labels(self):
        """Handle empty label preferences."""
        prefs = {"label_scores": {}, "feedback_count": 0}

        result = format_label_preferences(prefs)

        assert "No label preferences" in result


class TestFormatEngagementStats:
    """Test engagement statistics formatting."""

    def test_format_with_stats(self):
        """Format engagement statistics."""
        stats = {
            "total_interactions": 127,
            "unique_issues": 43,
            "avg_interactions_per_issue": 2.95,
            "most_engaged_issues": ["AI-1799", "DMD-480"],
            "last_interaction": "2025-11-05T16:30:00Z",
        }

        result = format_engagement_stats(stats)

        assert "127" in result  # total_interactions
        assert "43" in result  # unique_issues
        assert "2.9" in result or "2.95" in result  # avg
        assert "AI-1799" in result
        assert "DMD-480" in result

    def test_format_with_no_engagements(self):
        """Handle zero engagement statistics."""
        stats = {
            "total_interactions": 0,
            "unique_issues": 0,
            "avg_interactions_per_issue": 0.0,
            "most_engaged_issues": [],
        }

        result = format_engagement_stats(stats)

        assert "0" in result  # Shows zeros
        assert "Engagement Statistics" in result


class TestFormatTimeAgo:
    """Test time ago formatting."""

    def test_just_now(self):
        """Recent timestamp shows 'just now'."""
        now = datetime.utcnow()
        result = _format_time_ago(now)
        assert result == "just now"

    def test_minutes_ago(self):
        """Minutes ago formatted correctly."""
        from datetime import timedelta

        timestamp = datetime.utcnow() - timedelta(minutes=5)
        result = _format_time_ago(timestamp)
        assert "5 minutes ago" in result

    def test_hours_ago(self):
        """Hours ago formatted correctly."""
        from datetime import timedelta

        timestamp = datetime.utcnow() - timedelta(hours=2)
        result = _format_time_ago(timestamp)
        assert "2 hours ago" in result

    def test_days_ago(self):
        """Days ago formatted correctly."""
        from datetime import timedelta

        timestamp = datetime.utcnow() - timedelta(days=3)
        result = _format_time_ago(timestamp)
        assert "3 days ago" in result


class TestConvertDbPrefsToDict:
    """Test database preference conversion."""

    def test_convert_preferences(self):
        """Convert database preferences to dict format."""
        # Mock database preference objects
        mock_prefs = []

        # Topic preferences
        topic1 = MagicMock()
        topic1.preference_type = "topic"
        topic1.preference_key = "backend"
        topic1.score = 0.9
        topic1.confidence = 0.85
        topic1.feedback_count = 20
        mock_prefs.append(topic1)

        # Team preferences
        team1 = MagicMock()
        team1.preference_type = "team"
        team1.preference_key = "Backend Team"
        team1.score = 0.8
        team1.confidence = 0.85
        team1.feedback_count = 20
        mock_prefs.append(team1)

        result = _convert_db_prefs_to_dict(mock_prefs)

        assert result["topic_scores"]["backend"] == 0.9
        assert result["team_scores"]["Backend Team"] == 0.8
        assert result["confidence"] == 0.85
        assert result["feedback_count"] == 20


@pytest.mark.asyncio
class TestPreferencesHandler:
    """Test /preferences command handler."""

    @patch("linear_chief.telegram.handlers_preferences.LINEAR_USER_EMAIL", "test@example.com")
    @patch("linear_chief.telegram.handlers_preferences.get_session_maker")
    @patch("linear_chief.telegram.handlers_preferences.get_db_session")
    @patch("linear_chief.telegram.handlers_preferences.EngagementTracker")
    async def test_show_all_preferences(
        self,
        mock_tracker_cls,
        mock_get_db_session,
        mock_get_session_maker,
        mock_update,
        mock_context,
    ):
        """Show all preferences when no args provided."""
        # Mock database session
        mock_session = MagicMock()
        mock_get_db_session.return_value = [mock_session]

        # Mock repository
        mock_repo = MagicMock()
        mock_repo.get_all_preferences.return_value = []
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        # Mock engagement tracker
        mock_tracker = MagicMock()
        mock_tracker.get_engagement_stats = AsyncMock(
            return_value={"unique_issues": 0, "most_engaged_issues": []}
        )
        mock_tracker_cls.return_value = mock_tracker

        # Execute
        with patch(
            "linear_chief.telegram.handlers_preferences.UserPreferenceRepository",
            return_value=mock_repo,
        ):
            await preferences_handler(mock_update, mock_context)

        # Verify message sent
        mock_update.effective_chat.send_message.assert_called_once()
        call_args = mock_update.effective_chat.send_message.call_args
        message = call_args[1]["text"]

        assert "Preferences" in message

    @patch("linear_chief.telegram.handlers_preferences.LINEAR_USER_EMAIL", None)
    async def test_no_user_email_configured(self, mock_update, mock_context):
        """Show error when LINEAR_USER_EMAIL not configured."""
        await preferences_handler(mock_update, mock_context)

        mock_update.effective_chat.send_message.assert_called_once()
        call_args = mock_update.effective_chat.send_message.call_args
        message = call_args[1]["text"]

        assert "not configured" in message.lower()

    @patch("linear_chief.telegram.handlers_preferences.LINEAR_USER_EMAIL", "test@example.com")
    async def test_reset_shows_confirmation(self, mock_update, mock_context):
        """Reset subcommand shows confirmation keyboard."""
        mock_context.args = ["reset"]

        await preferences_handler(mock_update, mock_context)

        mock_update.effective_chat.send_message.assert_called_once()
        call_args = mock_update.effective_chat.send_message.call_args
        message = call_args[1]["text"]

        assert "Reset All Preferences" in message
        assert "cannot be undone" in message.lower()
        assert call_args[1]["reply_markup"] is not None  # Keyboard present


@pytest.mark.asyncio
class TestPreferHandler:
    """Test /prefer command handler."""

    @patch("linear_chief.telegram.handlers_preferences.LINEAR_USER_EMAIL", "test@example.com")
    @patch("linear_chief.telegram.handlers_preferences.get_session_maker")
    @patch("linear_chief.telegram.handlers_preferences.get_db_session")
    async def test_prefer_saves_high_score(
        self,
        mock_get_db_session,
        mock_get_session_maker,
        mock_update,
        mock_context,
    ):
        """Prefer command saves high preference score."""
        mock_context.args = ["backend"]

        # Mock database session
        mock_session = MagicMock()
        mock_get_db_session.return_value = [mock_session]

        # Mock repository
        mock_repo = MagicMock()
        mock_repo.save_preference = MagicMock()

        with patch(
            "linear_chief.telegram.handlers_preferences.UserPreferenceRepository",
            return_value=mock_repo,
        ):
            await prefer_handler(mock_update, mock_context)

        # Verify save was called with high score
        mock_repo.save_preference.assert_called_once()
        call_args = mock_repo.save_preference.call_args[1]

        assert call_args["score"] == 0.9  # High score
        assert call_args["preference_key"] == "backend"

        # Verify confirmation message
        mock_update.effective_chat.send_message.assert_called_once()
        call_args = mock_update.effective_chat.send_message.call_args
        message = call_args[1]["text"]

        assert "Preference saved" in message
        assert "prefer" in message.lower()
        assert "90%" in message

    async def test_prefer_without_args_shows_usage(self, mock_update, mock_context):
        """Prefer without args shows usage help."""
        mock_context.args = []

        await prefer_handler(mock_update, mock_context)

        mock_update.effective_chat.send_message.assert_called_once()
        call_args = mock_update.effective_chat.send_message.call_args
        message = call_args[1]["text"]

        assert "Usage" in message
        assert "/prefer" in message


@pytest.mark.asyncio
class TestIgnoreHandler:
    """Test /ignore command handler."""

    @patch("linear_chief.telegram.handlers_preferences.LINEAR_USER_EMAIL", "test@example.com")
    @patch("linear_chief.telegram.handlers_preferences.get_session_maker")
    @patch("linear_chief.telegram.handlers_preferences.get_db_session")
    async def test_ignore_saves_low_score(
        self,
        mock_get_db_session,
        mock_get_session_maker,
        mock_update,
        mock_context,
    ):
        """Ignore command saves low preference score."""
        mock_context.args = ["frontend"]

        # Mock database session
        mock_session = MagicMock()
        mock_get_db_session.return_value = [mock_session]

        # Mock repository
        mock_repo = MagicMock()
        mock_repo.save_preference = MagicMock()

        with patch(
            "linear_chief.telegram.handlers_preferences.UserPreferenceRepository",
            return_value=mock_repo,
        ):
            await ignore_handler(mock_update, mock_context)

        # Verify save was called with low score
        mock_repo.save_preference.assert_called_once()
        call_args = mock_repo.save_preference.call_args[1]

        assert call_args["score"] == 0.1  # Low score
        assert call_args["preference_key"] == "frontend"

        # Verify confirmation message
        mock_update.effective_chat.send_message.assert_called_once()
        call_args = mock_update.effective_chat.send_message.call_args
        message = call_args[1]["text"]

        assert "Preference saved" in message
        assert "ignore" in message.lower()
        assert "10%" in message


@pytest.mark.asyncio
class TestPreferencesResetCallback:
    """Test preference reset confirmation callback."""

    @patch("linear_chief.telegram.callbacks.LINEAR_USER_EMAIL", "test@example.com")
    @patch("linear_chief.telegram.callbacks.get_session_maker")
    @patch("linear_chief.telegram.callbacks.get_db_session")
    async def test_reset_confirmed_deletes_data(
        self,
        mock_get_db_session,
        mock_get_session_maker,
    ):
        """Confirmed reset deletes all preference and engagement data."""
        # Mock callback query
        mock_query = MagicMock()
        mock_query.data = "prefs_reset_confirm"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        mock_context = MagicMock()

        # Mock database sessions
        mock_session1 = MagicMock()
        mock_session2 = MagicMock()
        mock_get_db_session.side_effect = [[mock_session1], [mock_session2]]

        # Mock repositories
        mock_pref_repo = MagicMock()
        mock_pref_repo.delete_preferences.return_value = 10  # 10 prefs deleted

        mock_eng_repo = MagicMock()
        mock_eng_repo.delete_all_engagements.return_value = 25  # 25 engagements deleted

        with patch(
            "linear_chief.telegram.callbacks.UserPreferenceRepository",
            return_value=mock_pref_repo,
        ), patch(
            "linear_chief.telegram.callbacks.IssueEngagementRepository",
            return_value=mock_eng_repo,
        ):
            await preferences_reset_callback(mock_update, mock_context)

        # Verify deletions
        mock_pref_repo.delete_preferences.assert_called_once()
        mock_eng_repo.delete_all_engagements.assert_called_once()

        # Verify confirmation message
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args
        message = call_args[1]["text"]

        assert "Reset Complete" in message
        assert "10 preference" in message
        assert "25 engagement" in message

    async def test_reset_cancelled(self):
        """Cancelled reset does not delete data."""
        # Mock callback query
        mock_query = MagicMock()
        mock_query.data = "prefs_reset_cancel"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        mock_context = MagicMock()

        await preferences_reset_callback(mock_update, mock_context)

        # Verify cancellation message
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args
        message = call_args[1]["text"]

        assert "cancelled" in message.lower()
        assert "safe" in message.lower()
