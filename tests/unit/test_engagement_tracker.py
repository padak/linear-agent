"""Unit tests for engagement tracker."""

import pytest
from datetime import datetime, timedelta
from linear_chief.intelligence.engagement_tracker import EngagementTracker
from linear_chief.storage import (
    get_engine,
    init_db,
    get_session_maker,
    get_db_session,
    reset_engine,
)
from linear_chief.storage.repositories import IssueEngagementRepository


@pytest.fixture
def db_engine():
    """Create in-memory test database."""
    # Import all models to ensure they're registered with Base.metadata
    from linear_chief.storage.models import IssueEngagement  # noqa: F401

    engine = get_engine(":memory:")
    init_db(engine)
    yield engine
    reset_engine()


@pytest.fixture
def session_maker(db_engine):
    """Create session maker for tests."""
    return get_session_maker(db_engine)


@pytest.fixture
def engagement_tracker(session_maker):
    """Create engagement tracker instance."""
    # session_maker dependency ensures DB is initialized
    return EngagementTracker()


class TestEngagementTracking:
    """Test issue engagement tracking functionality."""

    @pytest.mark.asyncio
    async def test_track_issue_mention_creates_record(
        self, session_maker, engagement_tracker
    ):
        """Test tracking creates new engagement record."""
        # Track first interaction
        await engagement_tracker.track_issue_mention(
            user_id="test_user",
            issue_id="AI-1799",
            interaction_type="query",
            linear_id="test-linear-id",
            context="What's the status of AI-1799?",
        )

        # Verify record created
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement("test_user", "AI-1799")

            assert engagement is not None
            assert engagement.user_id == "test_user"  # type: ignore[attr-defined]
            assert engagement.issue_id == "AI-1799"  # type: ignore[attr-defined]
            assert engagement.interaction_type == "query"  # type: ignore[attr-defined]
            assert engagement.interaction_count == 1  # type: ignore[attr-defined]
            assert engagement.engagement_score == 0.5  # type: ignore[attr-defined] # Default score
            assert engagement.context == "What's the status of AI-1799?"  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_track_issue_mention_increments_count(
        self, session_maker, engagement_tracker
    ):
        """Test tracking same issue multiple times increments counter."""
        # Track first interaction
        await engagement_tracker.track_issue_mention(
            user_id="test_user",
            issue_id="DMD-480",
            interaction_type="query",
            linear_id="test-linear-id",
        )

        # Track second interaction
        await engagement_tracker.track_issue_mention(
            user_id="test_user",
            issue_id="DMD-480",
            interaction_type="query",
            linear_id="test-linear-id",
        )

        # Track third interaction
        await engagement_tracker.track_issue_mention(
            user_id="test_user",
            issue_id="DMD-480",
            interaction_type="mention",
            linear_id="test-linear-id",
        )

        # Verify count incremented
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement("test_user", "DMD-480")

            assert engagement is not None
            assert engagement.interaction_count == 3  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_track_issue_mention_invalid_type_raises_error(
        self, engagement_tracker
    ):
        """Test invalid interaction type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid interaction_type"):
            await engagement_tracker.track_issue_mention(
                user_id="test_user",
                issue_id="AI-1799",
                interaction_type="invalid",
                linear_id="test-linear-id",
            )


class TestEngagementScoreCalculation:
    """Test engagement score calculation."""

    @pytest.mark.asyncio
    async def test_calculate_score_no_interactions(
        self, session_maker, engagement_tracker
    ):
        """Test score calculation with no prior interactions returns default."""
        score = await engagement_tracker.calculate_engagement_score(
            "test_user", "NONEXISTENT-123"
        )

        assert score == 0.5  # Default score for no interactions

    @pytest.mark.asyncio
    async def test_calculate_score_recent_interaction(
        self, session_maker, engagement_tracker
    ):
        """Test score calculation for recent interaction."""
        # Track interaction
        await engagement_tracker.track_issue_mention(
            user_id="test_user",
            issue_id="AI-1799",
            interaction_type="query",
            linear_id="test-linear-id",
        )

        # Calculate score
        score = await engagement_tracker.calculate_engagement_score(
            "test_user", "AI-1799"
        )

        # Should be higher than default (recency = 1.0, frequency = 0.2)
        # score = (0.2 * 0.4) + (1.0 * 0.6) = 0.08 + 0.6 = 0.68
        assert score > 0.5
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_score_multiple_interactions(
        self, session_maker, engagement_tracker
    ):
        """Test score calculation with multiple interactions."""
        # Track 5 interactions (max frequency score)
        for _ in range(5):
            await engagement_tracker.track_issue_mention(
                user_id="test_user",
                issue_id="DMD-480",
                interaction_type="query",
                linear_id="test-linear-id",
            )

        # Calculate score
        score = await engagement_tracker.calculate_engagement_score(
            "test_user", "DMD-480"
        )

        # Should be maximum (frequency = 1.0, recency = 1.0)
        # score = (1.0 * 0.4) + (1.0 * 0.6) = 1.0
        assert score == 1.0

    def test_recency_score_decay(self, engagement_tracker):
        """Test recency score decays exponentially over time."""
        # 0 days = 1.0
        assert engagement_tracker._calculate_recency_score(0) == 1.0

        # 7 days ≈ 0.7
        score_7d = engagement_tracker._calculate_recency_score(7)
        assert 0.6 < score_7d < 0.8

        # 14 days ≈ 0.5
        score_14d = engagement_tracker._calculate_recency_score(14)
        assert 0.4 < score_14d < 0.6

        # 30 days ≈ 0.2
        score_30d = engagement_tracker._calculate_recency_score(30)
        assert 0.1 < score_30d < 0.3

        # 60+ days ≈ 0.0
        score_60d = engagement_tracker._calculate_recency_score(60)
        assert score_60d < 0.1

        # Verify exponential decay (newer is proportionally more valuable)
        assert score_7d > score_14d > score_30d > score_60d


class TestEngagementQueries:
    """Test engagement querying and statistics."""

    @pytest.mark.asyncio
    async def test_get_top_engaged_issues(self, session_maker, engagement_tracker):
        """Test retrieving top engaged issues."""
        # Track multiple issues with different engagement
        await engagement_tracker.track_issue_mention(
            "user1", "AI-1799", "query", "linear-1"
        )
        await engagement_tracker.track_issue_mention(
            "user1", "AI-1799", "query", "linear-1"
        )
        await engagement_tracker.track_issue_mention(
            "user1", "AI-1799", "query", "linear-1"
        )  # High engagement

        await engagement_tracker.track_issue_mention(
            "user1", "DMD-480", "query", "linear-2"
        )  # Low engagement

        # Get top engaged
        top_issues = await engagement_tracker.get_top_engaged_issues("user1", limit=5)

        assert len(top_issues) == 2
        # AI-1799 should be first (higher score)
        assert top_issues[0][0] == "AI-1799"
        assert top_issues[1][0] == "DMD-480"
        # Verify scores are sorted descending
        assert top_issues[0][1] > top_issues[1][1]

    @pytest.mark.asyncio
    async def test_get_engagement_stats(self, session_maker, engagement_tracker):
        """Test engagement statistics calculation."""
        # Track multiple interactions
        await engagement_tracker.track_issue_mention(
            "user1", "AI-1799", "query", "linear-1"
        )
        await engagement_tracker.track_issue_mention(
            "user1", "AI-1799", "query", "linear-1"
        )
        await engagement_tracker.track_issue_mention(
            "user1", "DMD-480", "query", "linear-2"
        )
        await engagement_tracker.track_issue_mention(
            "user1", "CSM-93", "mention", "linear-3"
        )

        # Get stats
        stats = await engagement_tracker.get_engagement_stats("user1")

        assert stats["total_interactions"] == 4
        assert stats["unique_issues"] == 3
        assert stats["avg_interactions_per_issue"] == pytest.approx(1.33, abs=0.01)
        assert len(stats["most_engaged_issues"]) <= 5
        assert "AI-1799" in stats["most_engaged_issues"]
        assert "last_interaction" is not None

    @pytest.mark.asyncio
    async def test_get_engagement_stats_no_data(self, session_maker, engagement_tracker):
        """Test stats with no engagement data."""
        stats = await engagement_tracker.get_engagement_stats("nonexistent_user")

        assert stats["total_interactions"] == 0
        assert stats["unique_issues"] == 0
        assert stats["avg_interactions_per_issue"] == 0.0
        assert stats["most_engaged_issues"] == []
        assert stats["last_interaction"] is None


class TestEngagementRepository:
    """Test IssueEngagementRepository directly."""

    def test_record_interaction_creates_new(self, session_maker):
        """Test recording first interaction creates new record."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            engagement = repo.record_interaction(
                user_id="user1",
                issue_id="AI-1799",
                linear_id="linear-id-1",
                interaction_type="query",
                context="test context",
            )

            assert engagement.user_id == "user1"  # type: ignore[attr-defined]
            assert engagement.issue_id == "AI-1799"  # type: ignore[attr-defined]
            assert engagement.interaction_count == 1  # type: ignore[attr-defined]
            assert engagement.engagement_score == 0.5  # type: ignore[attr-defined]
            assert engagement.context == "test context"  # type: ignore[attr-defined]

    def test_record_interaction_updates_existing(self, session_maker):
        """Test recording interaction on existing record increments count."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # First interaction
            repo.record_interaction(
                user_id="user1",
                issue_id="AI-1799",
                linear_id="linear-id-1",
                interaction_type="query",
            )

            # Second interaction
            engagement = repo.record_interaction(
                user_id="user1",
                issue_id="AI-1799",
                linear_id="linear-id-1",
                interaction_type="mention",
                context="updated context",
            )

            assert engagement.interaction_count == 2  # type: ignore[attr-defined]
            assert engagement.interaction_type == "mention"  # type: ignore[attr-defined] # Updated
            assert engagement.context == "updated context"  # type: ignore[attr-defined]

    def test_get_all_engagements(self, session_maker):
        """Test retrieving all engagements for user."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # Create multiple engagements
            repo.record_interaction("user1", "AI-1799", "linear-1", "query")
            repo.record_interaction("user1", "DMD-480", "linear-2", "query")
            repo.record_interaction("user1", "CSM-93", "linear-3", "query")

            # Get all
            engagements = repo.get_all_engagements("user1")

            assert len(engagements) == 3
            issue_ids = [e.issue_id for e in engagements]  # type: ignore[attr-defined]
            assert "AI-1799" in issue_ids
            assert "DMD-480" in issue_ids
            assert "CSM-93" in issue_ids

    def test_get_all_engagements_with_min_score(self, session_maker):
        """Test filtering engagements by minimum score."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # Create engagements with different scores
            repo.record_interaction("user1", "AI-1799", "linear-1", "query")
            repo.update_score("user1", "AI-1799", 0.8)

            repo.record_interaction("user1", "DMD-480", "linear-2", "query")
            repo.update_score("user1", "DMD-480", 0.3)

            # Get only high-score engagements
            high_score = repo.get_all_engagements("user1", min_score=0.5)

            assert len(high_score) == 1
            assert high_score[0].issue_id == "AI-1799"  # type: ignore[attr-defined]

    def test_update_score(self, session_maker):
        """Test updating engagement score."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # Create engagement
            repo.record_interaction("user1", "AI-1799", "linear-1", "query")

            # Update score
            repo.update_score("user1", "AI-1799", 0.9)

            # Verify
            engagement = repo.get_engagement("user1", "AI-1799")
            assert engagement is not None
            assert engagement.engagement_score == 0.9  # type: ignore[attr-defined]

    def test_update_score_invalid_range_raises_error(self, session_maker):
        """Test updating score outside valid range raises error."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # Create engagement
            repo.record_interaction("user1", "AI-1799", "linear-1", "query")

            # Try invalid scores
            with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
                repo.update_score("user1", "AI-1799", 1.5)

            with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
                repo.update_score("user1", "AI-1799", -0.1)

    def test_decay_old_engagements(self, session_maker):
        """Test decaying old engagement scores."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # Create engagement
            engagement = repo.record_interaction(
                "user1", "AI-1799", "linear-1", "query"
            )
            repo.update_score("user1", "AI-1799", 0.8)

            # Manually set old timestamp (simulate 31 days ago)
            from linear_chief.storage.models import IssueEngagement

            old_engagement = session.query(IssueEngagement).filter(
                IssueEngagement.user_id == "user1",
                IssueEngagement.issue_id == "AI-1799",
            ).first()

            old_engagement.last_interaction = datetime.utcnow() - timedelta(days=31)  # type: ignore[assignment]
            session.commit()

            # Apply decay (10% reduction)
            decayed_count = repo.decay_old_engagements("user1", days_threshold=30, decay_factor=0.1)

            assert decayed_count == 1

            # Verify score reduced
            updated_engagement = repo.get_engagement("user1", "AI-1799")
            assert updated_engagement is not None
            # 0.8 * (1 - 0.1) = 0.72
            assert updated_engagement.engagement_score == pytest.approx(0.72, abs=0.01)  # type: ignore[attr-defined]


class TestEngagementTrackerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_track_multiple_users_same_issue(
        self, session_maker, engagement_tracker
    ):
        """Test different users can track same issue independently."""
        await engagement_tracker.track_issue_mention(
            "user1", "AI-1799", "query", "linear-1"
        )
        await engagement_tracker.track_issue_mention(
            "user2", "AI-1799", "query", "linear-1"
        )

        # Each user should have separate engagement
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            engagement1 = repo.get_engagement("user1", "AI-1799")
            engagement2 = repo.get_engagement("user2", "AI-1799")

            assert engagement1 is not None
            assert engagement2 is not None
            assert engagement1.id != engagement2.id  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_context_truncation(self, session_maker, engagement_tracker):
        """Test context is truncated to 200 characters."""
        long_context = "x" * 300

        await engagement_tracker.track_issue_mention(
            user_id="user1",
            issue_id="AI-1799",
            interaction_type="query",
            linear_id="linear-1",
            context=long_context,
        )

        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement("user1", "AI-1799")

            assert engagement is not None
            assert len(engagement.context) == 200  # type: ignore[attr-defined]
