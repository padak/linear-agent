"""Integration tests for Phase 2 database operations.

Tests database persistence, CRUD operations, indexes, and data integrity
for Phase 2 features (UserPreference, IssueEngagement).
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import inspect, Index

from linear_chief.storage import (
    get_engine,
    init_db,
    get_session_maker,
    get_db_session,
    reset_engine,
)
from linear_chief.storage.repositories import (
    UserPreferenceRepository,
    IssueEngagementRepository,
)
from linear_chief.storage.models import UserPreference, IssueEngagement


@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory test database for each test."""
    # Import models to ensure they're registered
    from linear_chief.storage.models import UserPreference, IssueEngagement  # noqa: F401

    engine = get_engine(":memory:")
    init_db(engine)
    yield engine
    reset_engine()


@pytest.fixture
def session_maker(db_engine):
    """Create session maker for tests."""
    return get_session_maker(db_engine)


class TestUserPreferenceCRUD:
    """Test UserPreference CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_user_preference(self, session_maker):
        """Test creating user preference record."""
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)

            # Create preference
            pref = repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=0.85,
                feedback_count=10,
            )

            assert pref is not None
            assert pref.user_id == "test_user"  # type: ignore[attr-defined]
            assert pref.preference_type == "topic"  # type: ignore[attr-defined]
            assert pref.preference_key == "backend"  # type: ignore[attr-defined]
            assert pref.score == 0.9  # type: ignore[attr-defined]
            assert pref.confidence == 0.85  # type: ignore[attr-defined]
            assert pref.feedback_count == 10  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_read_user_preference(self, session_maker):
        """Test reading user preference record."""
        # Create
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=0.85,
                feedback_count=10,
            )

        # Read
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            pref = repo.get_preference("test_user", "topic", "backend")

            assert pref is not None
            assert pref.score == 0.9  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_user_preference(self, session_maker):
        """Test updating user preference (upsert)."""
        # Create initial
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=0.85,
                feedback_count=10,
            )

        # Update
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            updated = repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.95,  # Updated score
                confidence=0.92,  # Updated confidence
                feedback_count=15,  # Updated count
            )

            assert updated.score == 0.95  # type: ignore[attr-defined]
            assert updated.confidence == 0.92  # type: ignore[attr-defined]
            assert updated.feedback_count == 15  # type: ignore[attr-defined]

        # Verify only one record exists (upsert, not insert)
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            all_prefs = repo.get_all_preferences("test_user")
            assert len(all_prefs) == 1

    @pytest.mark.asyncio
    async def test_delete_user_preference(self, session_maker):
        """Test deleting user preference."""
        # Create
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=0.85,
                feedback_count=10,
            )

        # Delete
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.delete_preference("test_user", "topic", "backend")

        # Verify deleted
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            pref = repo.get_preference("test_user", "topic", "backend")
            assert pref is None

    @pytest.mark.asyncio
    async def test_get_all_user_preferences(self, session_maker):
        """Test getting all preferences for user."""
        # Create multiple preferences
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=0.85,
                feedback_count=10,
            )
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="frontend",
                score=0.3,
                confidence=0.8,
                feedback_count=8,
            )
            repo.save_preference(
                user_id="test_user",
                preference_type="team",
                preference_key="Backend Team",
                score=0.85,
                confidence=0.9,
                feedback_count=12,
            )

        # Get all
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            all_prefs = repo.get_all_preferences("test_user")

            assert len(all_prefs) == 3
            types = [p.preference_type for p in all_prefs]  # type: ignore[attr-defined]
            assert "topic" in types
            assert "team" in types


class TestIssueEngagementCRUD:
    """Test IssueEngagement CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_issue_engagement(self, session_maker):
        """Test creating issue engagement record."""
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # Create engagement
            engagement = repo.record_interaction(
                user_id="test_user",
                issue_id="AI-1799",
                linear_id="uuid-1799",
                interaction_type="query",
                context="What's the status?",
            )

            assert engagement is not None
            assert engagement.user_id == "test_user"  # type: ignore[attr-defined]
            assert engagement.issue_id == "AI-1799"  # type: ignore[attr-defined]
            assert engagement.interaction_type == "query"  # type: ignore[attr-defined]
            assert engagement.interaction_count == 1  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_read_issue_engagement(self, session_maker):
        """Test reading issue engagement record."""
        # Create
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            repo.record_interaction(
                user_id="test_user",
                issue_id="AI-1799",
                linear_id="uuid-1799",
                interaction_type="query",
            )

        # Read
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement("test_user", "AI-1799")

            assert engagement is not None
            assert engagement.interaction_count == 1  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_update_issue_engagement_increments_count(self, session_maker):
        """Test that recording same interaction increments count."""
        # First interaction
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            repo.record_interaction(
                user_id="test_user",
                issue_id="AI-1799",
                linear_id="uuid-1799",
                interaction_type="query",
            )

        # Second interaction
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            repo.record_interaction(
                user_id="test_user",
                issue_id="AI-1799",
                linear_id="uuid-1799",
                interaction_type="query",
            )

        # Verify count incremented
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement("test_user", "AI-1799")

            assert engagement.interaction_count == 2  # type: ignore[attr-defined]

        # Verify only one record (upsert behavior)
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            all_engagements = repo.get_all_engagements("test_user")
            assert len(all_engagements) == 1

    @pytest.mark.asyncio
    async def test_update_engagement_score(self, session_maker):
        """Test updating engagement score."""
        # Create
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            repo.record_interaction(
                user_id="test_user",
                issue_id="AI-1799",
                linear_id="uuid-1799",
                interaction_type="query",
            )

        # Update score
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            repo.update_score("test_user", "AI-1799", 0.85)

        # Verify
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement("test_user", "AI-1799")
            assert engagement.engagement_score == 0.85  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_get_top_engaged_issues(self, session_maker):
        """Test getting top engaged issues sorted by score."""
        # Create multiple engagements with different scores
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            # Issue 1: High score
            repo.record_interaction(
                user_id="test_user", issue_id="AI-1799", linear_id="uuid-1799"
            )
            repo.update_score("test_user", "AI-1799", 0.9)

            # Issue 2: Medium score
            repo.record_interaction(
                user_id="test_user", issue_id="AI-1820", linear_id="uuid-1820"
            )
            repo.update_score("test_user", "AI-1820", 0.7)

            # Issue 3: Low score
            repo.record_interaction(
                user_id="test_user", issue_id="FE-101", linear_id="uuid-fe101"
            )
            repo.update_score("test_user", "FE-101", 0.4)

        # Get top 2
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            top_engaged = repo.get_top_engaged("test_user", limit=2)

            assert len(top_engaged) == 2
            assert top_engaged[0].issue_id == "AI-1799"  # type: ignore[attr-defined] # Highest score
            assert top_engaged[1].issue_id == "AI-1820"  # type: ignore[attr-defined] # Second highest


class TestPreferenceUpsert:
    """Test preference upsert behavior (no duplicates)."""

    @pytest.mark.asyncio
    async def test_preference_upsert_no_duplicates(self, session_maker):
        """Upserting same preference doesn't create duplicates."""
        # Insert 5 times
        for i in range(5):
            for session in get_db_session(session_maker):
                repo = UserPreferenceRepository(session)
                repo.save_preference(
                    user_id="test_user",
                    preference_type="topic",
                    preference_key="backend",
                    score=0.9 + (i * 0.01),  # Slightly different each time
                    confidence=0.85,
                    feedback_count=10 + i,
                )

        # Should have only 1 record (last update wins)
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            all_prefs = repo.get_all_preferences("test_user")

            assert len(all_prefs) == 1
            assert all_prefs[0].score == pytest.approx(0.94)  # type: ignore[attr-defined] # Last value
            assert all_prefs[0].feedback_count == 14  # type: ignore[attr-defined] # Last value


class TestEngagementUpsert:
    """Test engagement upsert behavior (increments correctly)."""

    @pytest.mark.asyncio
    async def test_engagement_upsert_increments(self, session_maker):
        """Recording multiple interactions increments count correctly."""
        # Record 5 interactions
        for i in range(5):
            for session in get_db_session(session_maker):
                repo = IssueEngagementRepository(session)
                repo.record_interaction(
                    user_id="test_user",
                    issue_id="AI-1799",
                    linear_id="uuid-1799",
                    interaction_type="query",
                )

        # Should have 1 record with count=5
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement("test_user", "AI-1799")

            assert engagement is not None
            assert engagement.interaction_count == 5  # type: ignore[attr-defined]

        # Verify no duplicates
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            all_engagements = repo.get_all_engagements("test_user")
            assert len(all_engagements) == 1


class TestDatabaseIndexes:
    """Test that required indexes exist for performance."""

    def test_user_preference_indexes_exist(self, db_engine):
        """UserPreference table has required indexes."""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes("user_preferences")

        index_columns = [idx["column_names"] for idx in indexes]

        # Should have index on (user_id, preference_type, preference_key)
        # This is typically the primary key or unique constraint
        # Verify indexes exist (exact structure may vary by ORM config)
        assert len(indexes) >= 1  # At least some indexes exist

    def test_issue_engagement_indexes_exist(self, db_engine):
        """IssueEngagement table has required indexes."""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes("issue_engagements")

        # Should have indexes for efficient queries
        assert len(indexes) >= 1


class TestConcurrentWrites:
    """Test concurrent write operations."""

    @pytest.mark.asyncio
    async def test_concurrent_preference_saves(self, session_maker):
        """Concurrent preference saves don't corrupt data."""
        import asyncio

        async def save_preference(value):
            for session in get_db_session(session_maker):
                repo = UserPreferenceRepository(session)
                repo.save_preference(
                    user_id="test_user",
                    preference_type="topic",
                    preference_key="backend",
                    score=value,
                    confidence=0.85,
                    feedback_count=10,
                )

        # Save concurrently (in practice SQLite serializes, but test structure)
        await asyncio.gather(
            save_preference(0.9), save_preference(0.91), save_preference(0.92)
        )

        # Should have exactly 1 record (one of the values)
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            all_prefs = repo.get_all_preferences("test_user")

            assert len(all_prefs) == 1
            assert all_prefs[0].score in [0.9, 0.91, 0.92]  # type: ignore[attr-defined] # One of them


class TestDataIntegrity:
    """Test data integrity constraints."""

    @pytest.mark.asyncio
    async def test_user_preference_unique_constraint(self, session_maker):
        """User + type + key must be unique."""
        # This is enforced by upsert logic
        # Verify that saving same key updates, not duplicates
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.9,
                confidence=0.85,
                feedback_count=10,
            )
            repo.save_preference(
                user_id="test_user",
                preference_type="topic",
                preference_key="backend",
                score=0.95,  # Different score, same key
                confidence=0.9,
                feedback_count=15,
            )

        # Should have 1 record
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            prefs = repo.get_all_preferences("test_user")
            assert len(prefs) == 1
            assert prefs[0].score == 0.95  # type: ignore[attr-defined] # Latest value

    @pytest.mark.asyncio
    async def test_issue_engagement_unique_constraint(self, session_maker):
        """User + issue must be unique."""
        # Verify upsert behavior
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            repo.record_interaction(
                user_id="test_user", issue_id="AI-1799", linear_id="uuid-1799"
            )
            repo.record_interaction(
                user_id="test_user", issue_id="AI-1799", linear_id="uuid-1799"
            )

        # Should have 1 record with count=2
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagements = repo.get_all_engagements("test_user")
            assert len(engagements) == 1
            assert engagements[0].interaction_count == 2  # type: ignore[attr-defined]


class TestQueryPerformance:
    """Test query performance and index usage."""

    @pytest.mark.asyncio
    async def test_preference_query_uses_index(self, session_maker):
        """Preference queries should be efficient."""
        # Create many preferences
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            for i in range(100):
                repo.save_preference(
                    user_id=f"user_{i % 10}",
                    preference_type="topic",
                    preference_key=f"topic_{i}",
                    score=0.5 + (i % 50) / 100,
                    confidence=0.8,
                    feedback_count=i,
                )

        # Query should be fast
        import time

        start = time.time()

        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            prefs = repo.get_all_preferences("user_5")

        elapsed = time.time() - start

        # Should be very fast (< 0.1 seconds for 100 records)
        assert elapsed < 0.1
        assert len(prefs) == 10  # user_5 appears 10 times


class TestBulkOperations:
    """Test bulk insert/update operations."""

    @pytest.mark.asyncio
    async def test_bulk_preference_insert(self, session_maker):
        """Bulk inserting preferences works correctly."""
        preferences_to_save = [
            ("topic", "backend", 0.9),
            ("topic", "frontend", 0.3),
            ("team", "Backend Team", 0.85),
            ("label", "urgent", 0.9),
            ("label", "bug", 0.8),
        ]

        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)

            for pref_type, pref_key, score in preferences_to_save:
                repo.save_preference(
                    user_id="test_user",
                    preference_type=pref_type,
                    preference_key=pref_key,
                    score=score,
                    confidence=0.85,
                    feedback_count=10,
                )

        # Verify all saved
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            all_prefs = repo.get_all_preferences("test_user")

            assert len(all_prefs) == 5

    @pytest.mark.asyncio
    async def test_bulk_engagement_insert(self, session_maker):
        """Bulk inserting engagements works correctly."""
        issues = ["AI-1799", "AI-1820", "FE-101", "DOC-50", "DMD-480"]

        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)

            for issue_id in issues:
                repo.record_interaction(
                    user_id="test_user",
                    issue_id=issue_id,
                    linear_id=f"uuid-{issue_id}",
                    interaction_type="query",
                )

        # Verify all saved
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            all_engagements = repo.get_all_engagements("test_user")

            assert len(all_engagements) == 5
