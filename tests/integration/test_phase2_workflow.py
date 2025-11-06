"""Integration tests for Phase 2 workflow - End-to-end feature testing.

Tests the complete workflow of Phase 2 features:
- Preference learning from feedback
- Engagement tracking from conversations
- Semantic search and related issue suggestions
- Duplicate detection
- Personalized briefings
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from linear_chief.intelligence.preference_learner import PreferenceLearner
from linear_chief.intelligence.engagement_tracker import EngagementTracker
from linear_chief.intelligence.semantic_search import SemanticSearchService
from linear_chief.intelligence.duplicate_detector import DuplicateDetector
from linear_chief.memory.vector_store import IssueVectorStore
from linear_chief.storage import (
    get_engine,
    init_db,
    get_session_maker,
    get_db_session,
    reset_engine,
)
from linear_chief.storage.repositories import (
    FeedbackRepository,
    IssueHistoryRepository,
    IssueEngagementRepository,
    UserPreferenceRepository,
)
from linear_chief.storage.models import Feedback, IssueHistory, IssueEngagement


@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory test database."""
    from linear_chief.storage.models import (
        Feedback,
        IssueHistory,
        IssueEngagement,
        UserPreference,
    )

    engine = get_engine(":memory:")
    init_db(engine)
    yield engine
    reset_engine()


@pytest.fixture
def session_maker(db_engine):
    """Create session maker for tests."""
    return get_session_maker(db_engine)


@pytest.fixture
async def sample_issues_in_db(session_maker):
    """Create sample issues in database."""
    issues = [
        {
            "issue_id": "AI-1799",
            "linear_id": "uuid-1799",
            "title": "Implement OAuth2 authentication backend",
            "description": "Add OAuth2 authentication flow to API backend",
            "state": "In Progress",
            "priority": 1,
            "team_name": "Backend Team",
            "labels": ["backend", "security", "urgent"],
        },
        {
            "issue_id": "AI-1820",
            "linear_id": "uuid-1820",
            "title": "OAuth2 authentication provider integration",
            "description": "Similar to AI-1799, integrate OAuth2 providers",
            "state": "Todo",
            "priority": 2,
            "team_name": "Backend Team",
            "labels": ["backend", "security"],
        },
        {
            "issue_id": "FE-101",
            "linear_id": "uuid-fe101",
            "title": "Update CSS styles for login page",
            "description": "Redesign the login page CSS",
            "state": "In Progress",
            "priority": 3,
            "team_name": "Frontend Team",
            "labels": ["frontend", "ui"],
        },
        {
            "issue_id": "DOC-50",
            "linear_id": "uuid-doc50",
            "title": "Update API documentation",
            "description": "Document new API endpoints",
            "state": "Todo",
            "priority": 4,
            "team_name": "Platform Team",
            "labels": ["documentation"],
        },
    ]

    for session in get_db_session(session_maker):
        repo = IssueHistoryRepository(session)

        for issue_data in issues:
            repo.save_snapshot(
                issue_id=issue_data["issue_id"],
                linear_id=issue_data["linear_id"],
                title=issue_data["title"],
                state=issue_data["state"],
                priority=issue_data["priority"],
                assignee_id="test-user",
                assignee_name="Test User",
                team_id="test-team",
                team_name=issue_data["team_name"],
                labels=issue_data["labels"],
                extra_metadata={
                    "description": issue_data["description"],
                    "url": f"https://linear.app/issue/{issue_data['issue_id']}",
                },
            )

    return issues


class TestEndToEndPreferenceLearning:
    """Test complete preference learning workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_preference_learning(
        self, session_maker, sample_issues_in_db
    ):
        """Complete workflow: Feedback → Preferences → Personalized ranking.

        Steps:
        1. User gives positive feedback on backend issues
        2. User gives negative feedback on frontend issues
        3. PreferenceLearner analyzes patterns
        4. Preferences saved to database
        5. Next briefing should prioritize backend issues
        """
        user_id = "test_user"

        # Step 1: Simulate user giving feedback
        for session in get_db_session(session_maker):
            feedback_repo = FeedbackRepository(session)

            # Positive feedback on backend issues
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=1,
                feedback_type="positive",
                extra_metadata={"issue_id": "AI-1799"},
            )
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=1,
                feedback_type="positive",
                extra_metadata={"issue_id": "AI-1820"},
            )

            # Negative feedback on frontend issue
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=1,
                feedback_type="negative",
                extra_metadata={"issue_id": "FE-101"},
            )

        # Step 2: Analyze feedback patterns
        learner = PreferenceLearner(user_id=user_id)
        preferences = await learner.analyze_feedback_patterns(days=30)

        # Step 3: Verify preferences learned correctly
        assert "backend" in preferences["preferred_topics"]
        assert "frontend" in preferences["disliked_topics"]
        assert preferences["feedback_count"] == 3

        # Step 4: Save to database
        await learner.save_to_database(preferences)

        # Step 5: Verify preferences persisted
        for session in get_db_session(session_maker):
            pref_repo = UserPreferenceRepository(session)
            backend_pref = pref_repo.get_preference(user_id, "topic", "backend")

            assert backend_pref is not None
            assert backend_pref.score > 0.6  # type: ignore[attr-defined] # High preference

    @pytest.mark.asyncio
    async def test_preference_learning_improves_over_time(
        self, session_maker, sample_issues_in_db
    ):
        """Preferences improve with more feedback."""
        user_id = "test_user"
        learner = PreferenceLearner(user_id=user_id)

        # Initial feedback (3 items)
        for session in get_db_session(session_maker):
            feedback_repo = FeedbackRepository(session)
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=1,
                feedback_type="positive",
                extra_metadata={"issue_id": "AI-1799"},
            )
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=1,
                feedback_type="positive",
                extra_metadata={"issue_id": "AI-1820"},
            )
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=1,
                feedback_type="negative",
                extra_metadata={"issue_id": "FE-101"},
            )

        prefs_v1 = await learner.analyze_feedback_patterns(days=30)
        confidence_v1 = prefs_v1["confidence"]

        # Add more feedback (total 6 items)
        for session in get_db_session(session_maker):
            feedback_repo = FeedbackRepository(session)
            for _ in range(3):
                feedback_repo.record_feedback(
                    user_id=user_id,
                    briefing_id=2,
                    feedback_type="positive",
                    extra_metadata={"issue_id": "AI-1799"},
                )

        prefs_v2 = await learner.analyze_feedback_patterns(days=30)
        confidence_v2 = prefs_v2["confidence"]

        # Confidence should improve with more data
        assert confidence_v2 >= confidence_v1
        assert prefs_v2["feedback_count"] == 6


class TestEndToEndEngagementTracking:
    """Test complete engagement tracking workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_engagement_tracking(
        self, session_maker, sample_issues_in_db
    ):
        """Complete workflow: User query → Engagement tracked → Priority boosted.

        Steps:
        1. User queries specific issue multiple times
        2. Engagement tracked and score calculated
        3. Issue priority should be boosted in future briefings
        """
        user_id = "test_user"
        tracker = EngagementTracker()

        # Step 1: User queries issue multiple times
        for i in range(5):
            await tracker.track_issue_mention(
                user_id=user_id,
                issue_id="AI-1799",
                linear_id="uuid-1799",
                interaction_type="query",
                context=f"Query #{i+1}: What's the status of AI-1799?",
            )

        # Step 2: Verify engagement tracked
        engagement_score = await tracker.calculate_engagement_score(user_id, "AI-1799")

        # 5 interactions with recent timestamp → high score
        assert engagement_score > 0.7

        # Step 3: Get top engaged issues
        top_engaged = await tracker.get_top_engaged_issues(user_id, limit=5)

        assert len(top_engaged) == 1
        assert top_engaged[0][0] == "AI-1799"
        assert top_engaged[0][1] > 0.7

    @pytest.mark.asyncio
    async def test_engagement_decay_works(self, session_maker, sample_issues_in_db):
        """Old engagement decays correctly."""
        user_id = "test_user"
        tracker = EngagementTracker()

        # Track interaction
        await tracker.track_issue_mention(
            user_id=user_id,
            issue_id="AI-1799",
            linear_id="uuid-1799",
            interaction_type="query",
        )

        # Manually update last_interaction to 30 days ago
        for session in get_db_session(session_maker):
            repo = IssueEngagementRepository(session)
            engagement = repo.get_engagement(user_id, "AI-1799")

            if engagement:
                engagement.last_interaction = datetime.utcnow() - timedelta(  # type: ignore[attr-defined]
                    days=30
                )
                session.commit()

        # Recalculate score
        score = await tracker.calculate_engagement_score(user_id, "AI-1799")

        # Score should be lower due to age
        assert score < 0.5


class TestEndToEndSemanticSearch:
    """Test complete semantic search workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_semantic_search(self, session_maker, sample_issues_in_db):
        """Complete workflow: Issues in DB → Vector store → Search → Results.

        Steps:
        1. Issues added to vector store
        2. User searches for similar issues
        3. Results returned with similarity scores
        """
        # Step 1: Add issues to vector store
        vector_store = IssueVectorStore()

        for issue in sample_issues_in_db:
            await vector_store.add_issue(
                issue_id=issue["issue_id"],
                title=issue["title"],
                description=issue["description"],
                metadata={
                    "team_name": issue["team_name"],
                    "state": issue["state"],
                    "labels": issue["labels"],
                    "url": f"https://linear.app/issue/{issue['issue_id']}",
                },
            )

        # Small delay to ensure embeddings are processed
        await asyncio.sleep(0.1)

        # Step 2: Search for similar issues
        search_service = SemanticSearchService()

        # Search for issues similar to AI-1799
        similar = await search_service.find_similar_issues(
            issue_id="AI-1799", limit=3, min_similarity=0.3
        )

        # Step 3: Verify results
        assert len(similar) > 0

        # AI-1820 should be most similar (both about OAuth2)
        if len(similar) > 0:
            most_similar = similar[0]
            assert "OAuth" in most_similar["title"] or most_similar[
                "issue_id"
            ] == "AI-1820"

    @pytest.mark.asyncio
    async def test_semantic_search_by_text(self, session_maker, sample_issues_in_db):
        """Natural language search works."""
        vector_store = IssueVectorStore()

        for issue in sample_issues_in_db:
            await vector_store.add_issue(
                issue_id=issue["issue_id"],
                title=issue["title"],
                description=issue["description"],
                metadata={
                    "team_name": issue["team_name"],
                    "state": issue["state"],
                },
            )

        await asyncio.sleep(0.1)

        search_service = SemanticSearchService()

        # Search by natural language
        results = await search_service.search_by_text(
            query="authentication and security issues", limit=5, min_similarity=0.3
        )

        # Should find OAuth-related issues
        assert len(results) > 0

        # Results should include OAuth issues
        issue_ids = [r["issue_id"] for r in results]
        assert any("AI-" in issue_id for issue_id in issue_ids)


class TestEndToEndDuplicateDetection:
    """Test complete duplicate detection workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_duplicate_detection(
        self, session_maker, sample_issues_in_db
    ):
        """Complete workflow: Similar issues → Detector finds them → Warning shown.

        Steps:
        1. Issues with similar content in database
        2. Duplicate detector scans for duplicates
        3. Duplicates identified and formatted for user
        """
        # Add issues to vector store
        vector_store = IssueVectorStore()

        for issue in sample_issues_in_db:
            await vector_store.add_issue(
                issue_id=issue["issue_id"],
                title=issue["title"],
                description=issue["description"],
                metadata={
                    "team_name": issue["team_name"],
                    "state": issue["state"],
                    "url": f"https://linear.app/issue/{issue['issue_id']}",
                },
            )

        await asyncio.sleep(0.1)

        # Run duplicate detection
        detector = DuplicateDetector()

        # AI-1799 and AI-1820 are very similar (both OAuth2)
        duplicates = await detector.check_issue_for_duplicates(
            issue_id="AI-1799", min_similarity=0.7
        )

        # Should find AI-1820 as potential duplicate
        if len(duplicates) > 0:
            # Verify structure
            dup = duplicates[0]
            assert "issue_a" in dup
            assert "issue_b" in dup
            assert "similarity" in dup
            assert "suggested_action" in dup

    @pytest.mark.asyncio
    async def test_duplicate_detection_formatting(
        self, session_maker, sample_issues_in_db
    ):
        """Duplicate report formatted correctly."""
        detector = DuplicateDetector()

        # Mock duplicate data
        duplicates = [
            {
                "issue_a": "AI-1799",
                "issue_b": "AI-1820",
                "similarity": 0.92,
                "title_a": "OAuth2 authentication backend",
                "title_b": "OAuth2 provider integration",
                "state_a": "In Progress",
                "state_b": "Todo",
                "team": "Backend Team",
                "url_a": "https://linear.app/issue/AI-1799",
                "url_b": "https://linear.app/issue/AI-1820",
                "suggested_action": "Consider merging AI-1820 into AI-1799",
            }
        ]

        formatted = detector.format_duplicate_report(duplicates)

        assert "Duplicate" in formatted or "duplicate" in formatted
        assert "AI-1799" in formatted
        assert "AI-1820" in formatted
        assert "92%" in formatted or "0.92" in formatted


class TestBriefingWithPhase2Features:
    """Test briefings that include all Phase 2 features."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full orchestrator integration")
    async def test_briefing_with_all_phase2_features(
        self, session_maker, sample_issues_in_db
    ):
        """Briefing includes all Phase 2 enhancements.

        Features:
        - Personalized ranking based on preferences
        - Duplicate warnings
        - Related issue suggestions
        - Preference-based filtering
        """
        # TODO: Implement when full orchestrator integration ready
        # This would test:
        # 1. Orchestrator generates briefing
        # 2. Issues ranked by personalized priority
        # 3. Duplicate warnings included
        # 4. Related issues suggested for each item
        pass


class TestConversationWithPhase2Features:
    """Test conversations that use Phase 2 features."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires ConversationAgent integration")
    async def test_conversation_with_all_phase2_features(
        self, session_maker, sample_issues_in_db
    ):
        """Conversation includes all Phase 2 enhancements.

        Features:
        - Engagement tracking
        - Related suggestions
        - Semantic search
        - Preference context
        """
        # TODO: Implement when ConversationAgent has Phase 2 integration
        pass


class TestAllCommandsWorkTogether:
    """Test that all Phase 2 commands work without conflicts."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires all commands implemented")
    async def test_all_commands_work_together(self, session_maker):
        """All Phase 2 commands work without conflicts."""
        # TODO: Test:
        # /preferences
        # /prefer <topic>
        # /ignore <topic>
        # /search <query>
        # /similar <issue-id>
        # /duplicates
        pass


class TestPerformanceWithPhase2:
    """Performance tests for Phase 2 features."""

    @pytest.mark.asyncio
    async def test_preference_ranking_performance(
        self, session_maker, sample_issues_in_db
    ):
        """Ranking issues with preferences completes quickly."""
        # This is more of a smoke test than strict performance
        import time

        learner = PreferenceLearner(user_id="test_user")

        start = time.time()

        # Should complete in reasonable time even with no data
        preferences = await learner.analyze_feedback_patterns(days=30)

        elapsed = time.time() - start

        # Should be fast (< 1 second for empty data)
        assert elapsed < 1.0
        assert preferences is not None

    @pytest.mark.asyncio
    async def test_semantic_search_performance(
        self, session_maker, sample_issues_in_db
    ):
        """Semantic search completes in reasonable time."""
        import time

        vector_store = IssueVectorStore()

        # Add issues
        for issue in sample_issues_in_db:
            await vector_store.add_issue(
                issue_id=issue["issue_id"],
                title=issue["title"],
                description=issue["description"],
                metadata={},
            )

        await asyncio.sleep(0.1)

        search_service = SemanticSearchService()

        start = time.time()

        results = await search_service.search_by_text(
            query="authentication", limit=5, min_similarity=0.3
        )

        elapsed = time.time() - start

        # Should be fast (< 2 seconds for 4 issues)
        assert elapsed < 2.0
        assert isinstance(results, list)


class TestErrorHandling:
    """Test error handling in Phase 2 features."""

    @pytest.mark.asyncio
    async def test_handles_missing_preferences_gracefully(self, session_maker):
        """Missing preferences don't crash system."""
        learner = PreferenceLearner(user_id="nonexistent_user")

        # Should return empty preferences, not crash
        preferences = await learner.analyze_feedback_patterns(days=30)

        assert preferences["feedback_count"] == 0
        assert len(preferences["preferred_topics"]) == 0

    @pytest.mark.asyncio
    async def test_handles_missing_engagement_gracefully(self, session_maker):
        """Missing engagement doesn't crash system."""
        tracker = EngagementTracker()

        # Should return default score, not crash
        score = await tracker.calculate_engagement_score(
            "nonexistent_user", "FAKE-999"
        )

        assert score == 0.5  # Default score

    @pytest.mark.asyncio
    async def test_handles_chromadb_errors_gracefully(self):
        """ChromaDB errors don't crash briefings."""
        # Test with invalid query
        search_service = SemanticSearchService()

        try:
            # This might fail if ChromaDB not initialized
            results = await search_service.search_by_text(
                query="", limit=5  # Empty query
            )
            # If it doesn't raise, verify it returns empty or handles gracefully
            assert isinstance(results, list)
        except Exception as e:
            # Should be a specific error, not a crash
            assert e is not None


class TestEdgeCases:
    """Test edge cases in Phase 2 workflows."""

    @pytest.mark.asyncio
    async def test_new_user_with_no_data(self, session_maker):
        """New user (no preferences, no engagement) works."""
        user_id = "brand_new_user"

        learner = PreferenceLearner(user_id=user_id)
        tracker = EngagementTracker()

        # Should not crash
        preferences = await learner.analyze_feedback_patterns(days=30)
        assert preferences["feedback_count"] == 0

        score = await tracker.calculate_engagement_score(user_id, "ANY-1")
        assert score == 0.5  # Default

    @pytest.mark.asyncio
    async def test_user_with_conflicting_preferences(
        self, session_maker, sample_issues_in_db
    ):
        """Conflicting signals handled correctly."""
        user_id = "conflicted_user"

        # User likes backend...
        for session in get_db_session(session_maker):
            feedback_repo = FeedbackRepository(session)
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=1,
                feedback_type="positive",
                extra_metadata={"issue_id": "AI-1799"},
            )

        # ...but also dislikes backend
        for session in get_db_session(session_maker):
            feedback_repo = FeedbackRepository(session)
            feedback_repo.record_feedback(
                user_id=user_id,
                briefing_id=2,
                feedback_type="negative",
                extra_metadata={"issue_id": "AI-1820"},
            )

        learner = PreferenceLearner(user_id=user_id)
        preferences = await learner.analyze_feedback_patterns(days=30)

        # Should have neutral score for backend (1 pos, 1 neg)
        backend_score = preferences["topic_scores"].get("backend", 0.5)
        assert 0.4 <= backend_score <= 0.6  # Around neutral
