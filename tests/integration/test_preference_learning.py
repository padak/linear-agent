"""Integration tests for Preference Learning Engine.

Tests the complete workflow: feedback → analysis → storage → retrieval.
"""

import pytest
from datetime import datetime
import tempfile
import shutil
from pathlib import Path

from linear_chief.intelligence.preference_learner import PreferenceLearner
from linear_chief.storage import (
    init_db,
    get_session_maker,
    get_db_session,
    FeedbackRepository,
    IssueHistoryRepository,
    UserPreferenceRepository,
    reset_engine,
)
from linear_chief.config import DATABASE_PATH


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    temp_db_path = Path(temp_dir) / "test_preferences.db"

    # Initialize database
    from linear_chief.storage.database import get_engine
    from linear_chief.config import config

    # Override DATABASE_PATH temporarily
    original_db_path = DATABASE_PATH
    with patch("linear_chief.config.DATABASE_PATH", temp_db_path):
        reset_engine()  # Reset any cached engine
        init_db()

        yield temp_db_path

    # Cleanup
    reset_engine()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def session_maker(temp_db):
    """Get session maker for temp database."""
    return get_session_maker()


@pytest.fixture
def setup_test_data(session_maker):
    """Setup test feedback and issue data."""
    for session in get_db_session(session_maker):
        feedback_repo = FeedbackRepository(session)
        issue_repo = IssueHistoryRepository(session)

        # Create issue snapshots
        issues = [
            {
                "issue_id": "TEST-101",
                "linear_id": "uuid-101",
                "title": "Fix backend API authentication bug",
                "state": "In Progress",
                "priority": 1,
                "assignee_id": "user1",
                "assignee_name": "Alice",
                "team_id": "team1",
                "team_name": "Backend Team",
                "labels": ["bug", "urgent", "api"],
            },
            {
                "issue_id": "TEST-102",
                "linear_id": "uuid-102",
                "title": "Implement GraphQL API for profiles",
                "state": "In Progress",
                "priority": 2,
                "assignee_id": "user2",
                "assignee_name": "Bob",
                "team_id": "team1",
                "team_name": "Backend Team",
                "labels": ["feature", "api", "graphql"],
            },
            {
                "issue_id": "TEST-103",
                "linear_id": "uuid-103",
                "title": "Optimize database queries",
                "state": "In Progress",
                "priority": 2,
                "assignee_id": "user3",
                "assignee_name": "Charlie",
                "team_id": "team2",
                "team_name": "Platform Team",
                "labels": ["performance", "database"],
            },
            {
                "issue_id": "TEST-104",
                "linear_id": "uuid-104",
                "title": "Update CSS styles for login page",
                "state": "Todo",
                "priority": 3,
                "assignee_id": "user4",
                "assignee_name": "Diana",
                "team_id": "team3",
                "team_name": "Frontend Team",
                "labels": ["ui", "css", "design"],
            },
        ]

        for issue_data in issues:
            issue_repo.save_snapshot(**issue_data)

        # Create feedback entries
        feedback_entries = [
            # Positive feedback for backend issues
            {
                "user_id": "test_user",
                "briefing_id": 1,
                "feedback_type": "positive",
                "extra_metadata": {"issue_id": "TEST-101"},
            },
            {
                "user_id": "test_user",
                "briefing_id": 1,
                "feedback_type": "positive",
                "extra_metadata": {"issue_id": "TEST-102"},
            },
            {
                "user_id": "test_user",
                "briefing_id": 2,
                "feedback_type": "positive",
                "extra_metadata": {"issue_id": "TEST-103"},
            },
            # Negative feedback for frontend issue
            {
                "user_id": "test_user",
                "briefing_id": 2,
                "feedback_type": "negative",
                "extra_metadata": {"issue_id": "TEST-104"},
            },
        ]

        for feedback_data in feedback_entries:
            feedback_repo.save_feedback(**feedback_data)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_preference_learning_workflow(session_maker, setup_test_data):
    """Test complete preference learning workflow."""
    learner = PreferenceLearner(user_id="test_user")

    # Override session_maker to use test database
    learner.session_maker = session_maker

    # Step 1: Analyze feedback patterns
    preferences = await learner.analyze_feedback_patterns(days=30, min_feedback_count=1)

    # Verify basic structure
    assert "preferred_topics" in preferences
    assert "preferred_teams" in preferences
    assert "preferred_labels" in preferences
    assert "feedback_count" in preferences

    # Should have found 4 feedback entries
    assert preferences["feedback_count"] == 4

    # Confidence should be > 0 with 4 feedback entries
    assert preferences["confidence"] > 0

    # Should prefer backend-related topics
    assert "backend" in preferences["preferred_topics"] or "api" in preferences[
        "preferred_topics"
    ]

    # Should prefer Backend Team
    assert "Backend Team" in preferences["preferred_teams"]

    # Should have topic scores
    assert len(preferences["topic_scores"]) > 0

    # Step 2: Save to database
    await learner.save_to_database(preferences)

    # Step 3: Verify database storage
    for session in get_db_session(session_maker):
        pref_repo = UserPreferenceRepository(session)

        # Get all preferences
        all_prefs = pref_repo.get_all_preferences("test_user")
        assert len(all_prefs) > 0

        # Get topic preferences
        topic_prefs = pref_repo.get_preferences_by_type("test_user", "topic")
        assert len(topic_prefs) > 0

        # Get preference summary
        summary = pref_repo.get_preference_summary("test_user")
        assert summary["total_count"] > 0
        assert "topic" in summary["by_type"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_preference_update_workflow(session_maker, setup_test_data):
    """Test updating preferences with new feedback."""
    learner = PreferenceLearner(user_id="test_user")
    learner.session_maker = session_maker

    # First analysis
    prefs1 = await learner.analyze_feedback_patterns(days=30)
    await learner.save_to_database(prefs1)

    # Add more feedback
    for session in get_db_session(session_maker):
        feedback_repo = FeedbackRepository(session)

        # Add more positive feedback for backend
        feedback_repo.save_feedback(
            user_id="test_user",
            briefing_id=3,
            feedback_type="positive",
            extra_metadata={"issue_id": "TEST-101"},
        )

    # Second analysis
    prefs2 = await learner.analyze_feedback_patterns(days=30)
    await learner.save_to_database(prefs2)

    # Verify preferences were updated
    for session in get_db_session(session_maker):
        pref_repo = UserPreferenceRepository(session)

        # Should have more feedback_count
        backend_pref = pref_repo.get_preference("test_user", "topic", "backend")
        if backend_pref:
            assert backend_pref.feedback_count == prefs2["feedback_count"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_preference_repository_operations(session_maker):
    """Test UserPreferenceRepository CRUD operations."""
    for session in get_db_session(session_maker):
        repo = UserPreferenceRepository(session)

        # Create preference
        pref = repo.save_preference(
            user_id="test_user",
            preference_type="topic",
            preference_key="backend",
            score=0.9,
            confidence=0.8,
            feedback_count=10,
        )

        assert pref.id is not None
        assert pref.score == 0.9
        assert pref.confidence == 0.8

        # Update preference
        updated_pref = repo.save_preference(
            user_id="test_user",
            preference_type="topic",
            preference_key="backend",
            score=0.95,
            confidence=0.85,
            feedback_count=15,
        )

        assert updated_pref.id == pref.id  # Same record
        assert updated_pref.score == 0.95
        assert updated_pref.feedback_count == 15

        # Get specific preference
        retrieved = repo.get_preference("test_user", "topic", "backend")
        assert retrieved is not None
        assert retrieved.score == 0.95

        # Get top preferences
        repo.save_preference(
            user_id="test_user",
            preference_type="topic",
            preference_key="api",
            score=0.85,
            confidence=0.8,
            feedback_count=8,
        )

        top_prefs = repo.get_top_preferences(
            "test_user", "topic", limit=5, min_score=0.8
        )
        assert len(top_prefs) == 2  # backend and api

        # Delete preferences
        count = repo.delete_preferences("test_user", preference_type="topic")
        assert count == 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_topic_detection_accuracy(session_maker):
    """Test topic detection accuracy with various issue titles."""
    learner = PreferenceLearner(user_id="test_user")

    test_cases = [
        {
            "issue": {
                "title": "Fix backend API authentication",
                "description": "REST endpoint returns 401",
            },
            "expected_topics": ["backend", "api"],
        },
        {
            "issue": {
                "title": "Update React component styles",
                "description": "CSS for login page",
            },
            "expected_topics": ["frontend"],
        },
        {
            "issue": {
                "title": "Setup Kubernetes deployment",
                "description": "Configure Docker and CI/CD",
            },
            "expected_topics": ["infrastructure"],
        },
        {
            "issue": {
                "title": "Add pytest tests for API",
                "description": "Automated test coverage",
            },
            "expected_topics": ["testing", "api"],
        },
        {
            "issue": {
                "title": "Optimize database queries",
                "description": "SQL performance improvements",
            },
            "expected_topics": ["performance", "backend", "database"],
        },
    ]

    for test_case in test_cases:
        detected = learner._detect_topics(test_case["issue"])

        # Check if at least one expected topic was detected
        assert any(
            topic in detected for topic in test_case["expected_topics"]
        ), f"Expected {test_case['expected_topics']}, got {detected} for {test_case['issue']['title']}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_preference_scoring(session_maker, setup_test_data):
    """Test preference score calculation is accurate."""
    learner = PreferenceLearner(user_id="test_user")
    learner.session_maker = session_maker

    preferences = await learner.analyze_feedback_patterns(days=30)

    # With 3 positive backend-related feedback and 1 negative frontend feedback:
    # Backend topics should have high scores
    backend_score = preferences["topic_scores"].get("backend", 0)
    api_score = preferences["topic_scores"].get("api", 0)

    # At least one of these should be high
    assert backend_score > 0.5 or api_score > 0.5

    # Frontend should have low score (1 negative, 0 positive)
    frontend_score = preferences["topic_scores"].get("frontend", 1.0)
    assert frontend_score < 0.5


# Import patch for mocking
from unittest.mock import patch
