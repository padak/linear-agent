"""Unit tests for FeedbackRepository."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from linear_chief.storage import Base, Feedback, FeedbackRepository


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
def feedback_repo(session):
    """Create FeedbackRepository instance."""
    return FeedbackRepository(session)


@pytest.fixture
def sample_feedback(feedback_repo):
    """Create sample feedback data."""
    feedbacks = []

    # User 123 - Positive and negative feedback
    for i in range(3):
        fb = feedback_repo.save_feedback(
            user_id="123",
            briefing_id=i + 1,
            feedback_type="positive",
        )
        feedbacks.append(fb)

    fb = feedback_repo.save_feedback(
        user_id="123",
        briefing_id=4,
        feedback_type="negative",
    )
    feedbacks.append(fb)

    # User 456 - Issue actions
    fb = feedback_repo.save_feedback(
        user_id="456",
        briefing_id=None,
        feedback_type="issue_action",
        extra_metadata={"action": "done", "issue_id": "PROJ-123"},
    )
    feedbacks.append(fb)

    return feedbacks


class TestSaveFeedback:
    """Tests for save_feedback method."""

    def test_save_positive_feedback(self, feedback_repo):
        """Test saving positive feedback."""
        feedback = feedback_repo.save_feedback(
            user_id="123",
            briefing_id=1,
            feedback_type="positive",
        )

        assert feedback.id is not None
        assert feedback.user_id == "123"
        assert feedback.briefing_id == 1
        assert feedback.feedback_type == "positive"
        assert feedback.timestamp is not None

    def test_save_negative_feedback(self, feedback_repo):
        """Test saving negative feedback."""
        feedback = feedback_repo.save_feedback(
            user_id="123",
            briefing_id=1,
            feedback_type="negative",
        )

        assert feedback.feedback_type == "negative"

    def test_save_issue_action_feedback(self, feedback_repo):
        """Test saving issue action feedback."""
        metadata = {"action": "done", "issue_id": "PROJ-123"}

        feedback = feedback_repo.save_feedback(
            user_id="123",
            briefing_id=None,
            feedback_type="issue_action",
            extra_metadata=metadata,
        )

        assert feedback.feedback_type == "issue_action"
        assert feedback.briefing_id is None
        assert feedback.extra_metadata == metadata

    def test_save_feedback_with_metadata(self, feedback_repo):
        """Test saving feedback with extra metadata."""
        metadata = {
            "telegram_message_id": "12345",
            "chat_id": "67890",
            "context": "Daily briefing",
        }

        feedback = feedback_repo.save_feedback(
            user_id="123",
            briefing_id=1,
            feedback_type="positive",
            extra_metadata=metadata,
        )

        assert feedback.extra_metadata == metadata
        assert feedback.extra_metadata["telegram_message_id"] == "12345"

    def test_save_feedback_invalid_type(self, feedback_repo):
        """Test saving feedback with invalid type raises error."""
        with pytest.raises(ValueError) as exc_info:
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=1,
                feedback_type="invalid_type",
            )

        assert "Invalid feedback_type" in str(exc_info.value)
        assert "positive" in str(exc_info.value)
        assert "negative" in str(exc_info.value)
        assert "issue_action" in str(exc_info.value)

    def test_save_feedback_without_briefing_id(self, feedback_repo):
        """Test saving feedback without briefing_id (for issue actions)."""
        feedback = feedback_repo.save_feedback(
            user_id="123",
            briefing_id=None,
            feedback_type="issue_action",
            extra_metadata={"action": "unsubscribe", "issue_id": "PROJ-456"},
        )

        assert feedback.briefing_id is None
        assert feedback.id is not None


class TestGetUserFeedbackStats:
    """Tests for get_user_feedback_stats method."""

    def test_get_user_feedback_stats(self, feedback_repo, sample_feedback):
        """Test getting user feedback statistics."""
        stats = feedback_repo.get_user_feedback_stats(user_id="123", days=30)

        assert stats["positive_count"] == 3
        assert stats["negative_count"] == 1
        assert stats["issue_action_count"] == 0
        assert stats["total_count"] == 4
        assert stats["satisfaction_rate"] == 75.0  # 3/4 * 100

    def test_get_user_feedback_stats_empty(self, feedback_repo):
        """Test feedback stats for user with no feedback."""
        stats = feedback_repo.get_user_feedback_stats(user_id="999", days=30)

        assert stats["positive_count"] == 0
        assert stats["negative_count"] == 0
        assert stats["issue_action_count"] == 0
        assert stats["total_count"] == 0
        assert stats["satisfaction_rate"] == 0.0

    def test_get_user_feedback_stats_issue_actions(self, feedback_repo, sample_feedback):
        """Test feedback stats includes issue actions."""
        stats = feedback_repo.get_user_feedback_stats(user_id="456", days=30)

        assert stats["positive_count"] == 0
        assert stats["negative_count"] == 0
        assert stats["issue_action_count"] == 1
        assert stats["total_count"] == 1

    def test_get_user_feedback_stats_time_filter(self, feedback_repo, session):
        """Test feedback stats with time filter."""
        # Create old feedback (40 days ago)
        old_feedback = Feedback(
            user_id="123",
            briefing_id=1,
            feedback_type="positive",
            timestamp=datetime.utcnow() - timedelta(days=40),
        )
        session.add(old_feedback)
        session.commit()

        # Create recent feedback
        feedback_repo.save_feedback(
            user_id="123",
            briefing_id=2,
            feedback_type="positive",
        )

        # Get stats for last 30 days only
        stats = feedback_repo.get_user_feedback_stats(user_id="123", days=30)

        # Should only count recent feedback
        assert stats["total_count"] == 1

    def test_get_user_feedback_stats_satisfaction_rate(self, feedback_repo):
        """Test satisfaction rate calculation."""
        # 2 positive, 3 negative = 40% satisfaction
        for _ in range(2):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=1,
                feedback_type="positive",
            )
        for _ in range(3):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=2,
                feedback_type="negative",
            )

        stats = feedback_repo.get_user_feedback_stats(user_id="123", days=30)

        assert stats["satisfaction_rate"] == 40.0

    def test_get_user_feedback_stats_all_negative(self, feedback_repo):
        """Test satisfaction rate with all negative feedback."""
        for _ in range(5):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=1,
                feedback_type="negative",
            )

        stats = feedback_repo.get_user_feedback_stats(user_id="123", days=30)

        assert stats["satisfaction_rate"] == 0.0


class TestGetRecentFeedback:
    """Tests for get_recent_feedback method."""

    def test_get_recent_feedback(self, feedback_repo, sample_feedback):
        """Test getting recent feedback entries."""
        recent = feedback_repo.get_recent_feedback(days=7, limit=100)

        assert len(recent) == 5
        # Should be ordered by timestamp descending (most recent first)
        assert recent[0].timestamp >= recent[-1].timestamp

    def test_get_recent_feedback_with_limit(self, feedback_repo, sample_feedback):
        """Test recent feedback with limit."""
        recent = feedback_repo.get_recent_feedback(days=7, limit=3)

        assert len(recent) == 3

    def test_get_recent_feedback_filter_by_type(self, feedback_repo, sample_feedback):
        """Test filtering recent feedback by type."""
        positive = feedback_repo.get_recent_feedback(
            days=7, limit=100, feedback_type="positive"
        )
        negative = feedback_repo.get_recent_feedback(
            days=7, limit=100, feedback_type="negative"
        )
        actions = feedback_repo.get_recent_feedback(
            days=7, limit=100, feedback_type="issue_action"
        )

        assert len(positive) == 3
        assert len(negative) == 1
        assert len(actions) == 1

    def test_get_recent_feedback_time_filter(self, feedback_repo, session):
        """Test recent feedback with time filter."""
        # Create old feedback (10 days ago)
        old_feedback = Feedback(
            user_id="123",
            briefing_id=1,
            feedback_type="positive",
            timestamp=datetime.utcnow() - timedelta(days=10),
        )
        session.add(old_feedback)
        session.commit()

        # Create recent feedback
        feedback_repo.save_feedback(
            user_id="123",
            briefing_id=2,
            feedback_type="positive",
        )

        # Get feedback from last 7 days
        recent = feedback_repo.get_recent_feedback(days=7, limit=100)

        assert len(recent) == 1

    def test_get_recent_feedback_empty(self, feedback_repo):
        """Test recent feedback when no feedback exists."""
        recent = feedback_repo.get_recent_feedback(days=7, limit=100)

        assert len(recent) == 0

    def test_get_recent_feedback_ordering(self, feedback_repo):
        """Test recent feedback is ordered by timestamp descending."""
        # Add feedback with slight delays
        for i in range(3):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=i + 1,
                feedback_type="positive",
            )

        recent = feedback_repo.get_recent_feedback(days=7, limit=100)

        # Most recent should be first
        assert recent[0].briefing_id == 3
        assert recent[-1].briefing_id == 1


class TestGetBriefingFeedback:
    """Tests for get_briefing_feedback method."""

    def test_get_briefing_feedback(self, feedback_repo, sample_feedback):
        """Test getting feedback for specific briefing."""
        feedback = feedback_repo.get_briefing_feedback(briefing_id=1)

        assert len(feedback) == 1
        assert feedback[0].briefing_id == 1
        assert feedback[0].feedback_type == "positive"

    def test_get_briefing_feedback_multiple(self, feedback_repo):
        """Test getting multiple feedback entries for same briefing."""
        # Add multiple feedback for same briefing
        feedback_repo.save_feedback(
            user_id="123",
            briefing_id=1,
            feedback_type="positive",
        )
        feedback_repo.save_feedback(
            user_id="456",
            briefing_id=1,
            feedback_type="negative",
        )

        feedback = feedback_repo.get_briefing_feedback(briefing_id=1)

        assert len(feedback) == 2

    def test_get_briefing_feedback_none(self, feedback_repo):
        """Test getting feedback for briefing with no feedback."""
        feedback = feedback_repo.get_briefing_feedback(briefing_id=999)

        assert len(feedback) == 0

    def test_get_briefing_feedback_ordering(self, feedback_repo):
        """Test briefing feedback is ordered by timestamp descending."""
        # Add feedback at different times
        for i in range(3):
            feedback_repo.save_feedback(
                user_id=str(100 + i),
                briefing_id=1,
                feedback_type="positive",
            )

        feedback = feedback_repo.get_briefing_feedback(briefing_id=1)

        # Should be ordered by timestamp descending
        assert feedback[0].timestamp >= feedback[-1].timestamp


class TestGetOverallFeedbackStats:
    """Tests for get_overall_feedback_stats method."""

    def test_get_overall_feedback_stats(self, feedback_repo, sample_feedback):
        """Test getting overall feedback statistics."""
        stats = feedback_repo.get_overall_feedback_stats(days=30)

        assert stats["positive_count"] == 3
        assert stats["negative_count"] == 1
        assert stats["issue_action_count"] == 1
        assert stats["total_count"] == 5
        assert stats["unique_users"] == 2
        assert stats["satisfaction_rate"] == 60.0  # 3/5 * 100

    def test_get_overall_feedback_stats_empty(self, feedback_repo):
        """Test overall feedback stats when no feedback exists."""
        stats = feedback_repo.get_overall_feedback_stats(days=30)

        assert stats["positive_count"] == 0
        assert stats["negative_count"] == 0
        assert stats["issue_action_count"] == 0
        assert stats["total_count"] == 0
        assert stats["unique_users"] == 0
        assert stats["satisfaction_rate"] == 0.0

    def test_get_overall_feedback_stats_time_filter(self, feedback_repo, session):
        """Test overall stats with time filter."""
        # Create old feedback (40 days ago)
        old_feedback = Feedback(
            user_id="old_user",
            briefing_id=1,
            feedback_type="positive",
            timestamp=datetime.utcnow() - timedelta(days=40),
        )
        session.add(old_feedback)
        session.commit()

        # Create recent feedback
        feedback_repo.save_feedback(
            user_id="recent_user",
            briefing_id=2,
            feedback_type="positive",
        )

        # Get stats for last 30 days
        stats = feedback_repo.get_overall_feedback_stats(days=30)

        assert stats["total_count"] == 1
        assert stats["unique_users"] == 1

    def test_get_overall_feedback_stats_unique_users(self, feedback_repo):
        """Test unique users count in overall stats."""
        # Multiple feedback from same users
        for i in range(3):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=i + 1,
                feedback_type="positive",
            )
        for i in range(2):
            feedback_repo.save_feedback(
                user_id="456",
                briefing_id=i + 1,
                feedback_type="negative",
            )

        stats = feedback_repo.get_overall_feedback_stats(days=30)

        assert stats["total_count"] == 5
        assert stats["unique_users"] == 2

    def test_get_overall_feedback_stats_satisfaction_calculation(
        self, feedback_repo
    ):
        """Test satisfaction rate calculation in overall stats."""
        # 7 positive, 3 negative = 70% satisfaction
        for i in range(7):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=i + 1,
                feedback_type="positive",
            )
        for i in range(3):
            feedback_repo.save_feedback(
                user_id="456",
                briefing_id=i + 1,
                feedback_type="negative",
            )

        stats = feedback_repo.get_overall_feedback_stats(days=30)

        assert stats["satisfaction_rate"] == 70.0

    def test_get_overall_feedback_stats_includes_actions_in_calculation(
        self, feedback_repo
    ):
        """Test satisfaction rate calculation includes all feedback types."""
        # 2 positive, 1 negative, 3 actions = satisfaction is 2/6 = 33.3%
        for _ in range(2):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=1,
                feedback_type="positive",
            )
        feedback_repo.save_feedback(
            user_id="123",
            briefing_id=2,
            feedback_type="negative",
        )
        for i in range(3):
            feedback_repo.save_feedback(
                user_id="123",
                briefing_id=None,
                feedback_type="issue_action",
                extra_metadata={"action": "done", "issue_id": f"PROJ-{i}"},
            )

        stats = feedback_repo.get_overall_feedback_stats(days=30)

        assert stats["total_count"] == 6
        assert stats["satisfaction_rate"] == 33.3
