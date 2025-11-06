"""Integration tests for duplicate detection with real ChromaDB."""

import pytest
from datetime import datetime

from linear_chief.intelligence.duplicate_detector import DuplicateDetector
from linear_chief.memory.vector_store import IssueVectorStore
from linear_chief.storage import get_session_maker, get_db_session
from linear_chief.storage.repositories import IssueHistoryRepository


@pytest.fixture
async def populated_vector_store():
    """Create vector store populated with test issues."""
    store = IssueVectorStore()

    # Add test issues
    test_issues = [
        {
            "id": "AI-1799",
            "title": "OAuth implementation",
            "description": "Implement OAuth2 authentication flow for user login",
            "metadata": {
                "state": "In Progress",
                "team": "AI",
                "url": "https://linear.app/ai/issue/AI-1799",
            },
        },
        {
            "id": "AI-1820",
            "title": "OAuth2 auth flow",
            "description": "Add OAuth2 authentication for users",
            "metadata": {
                "state": "Todo",
                "team": "AI",
                "url": "https://linear.app/ai/issue/AI-1820",
            },
        },
        {
            "id": "DMD-480",
            "title": "Fix login bug",
            "description": "Login flow is broken and users cannot authenticate",
            "metadata": {
                "state": "Done",
                "team": "DMD",
                "url": "https://linear.app/dmd/issue/DMD-480",
            },
        },
        {
            "id": "DMD-485",
            "title": "Login flow broken",
            "description": "Users can't log in to the system",
            "metadata": {
                "state": "Todo",
                "team": "DMD",
                "url": "https://linear.app/dmd/issue/DMD-485",
            },
        },
        {
            "id": "ENG-100",
            "title": "Refactor database schema",
            "description": "Completely different issue about database refactoring",
            "metadata": {
                "state": "In Progress",
                "team": "ENG",
                "url": "https://linear.app/eng/issue/ENG-100",
            },
        },
    ]

    for issue in test_issues:
        await store.add_issue(
            issue_id=issue["id"],
            title=issue["title"],
            description=issue["description"],
            metadata=issue["metadata"],
        )

    yield store

    # Cleanup: delete test issues
    for issue in test_issues:
        await store.delete_issue(issue["id"])


@pytest.fixture
def populated_database():
    """Create database snapshots for test issues."""
    session_maker = get_session_maker()

    test_snapshots = [
        {
            "issue_id": "AI-1799",
            "linear_id": "test-uuid-1799",
            "title": "OAuth implementation",
            "state": "In Progress",
            "team_name": "AI",
            "extra_metadata": {
                "url": "https://linear.app/ai/issue/AI-1799",
                "description": "Implement OAuth2 authentication flow for user login",
            },
        },
        {
            "issue_id": "AI-1820",
            "linear_id": "test-uuid-1820",
            "title": "OAuth2 auth flow",
            "state": "Todo",
            "team_name": "AI",
            "extra_metadata": {
                "url": "https://linear.app/ai/issue/AI-1820",
                "description": "Add OAuth2 authentication for users",
            },
        },
        {
            "issue_id": "DMD-480",
            "linear_id": "test-uuid-480",
            "title": "Fix login bug",
            "state": "Done",
            "team_name": "DMD",
            "extra_metadata": {
                "url": "https://linear.app/dmd/issue/DMD-480",
                "description": "Login flow is broken and users cannot authenticate",
            },
        },
        {
            "issue_id": "DMD-485",
            "linear_id": "test-uuid-485",
            "title": "Login flow broken",
            "state": "Todo",
            "team_name": "DMD",
            "extra_metadata": {
                "url": "https://linear.app/dmd/issue/DMD-485",
                "description": "Users can't log in to the system",
            },
        },
        {
            "issue_id": "ENG-100",
            "linear_id": "test-uuid-100",
            "title": "Refactor database schema",
            "state": "In Progress",
            "team_name": "ENG",
            "extra_metadata": {
                "url": "https://linear.app/eng/issue/ENG-100",
                "description": "Completely different issue about database refactoring",
            },
        },
    ]

    # Save snapshots
    for session in get_db_session(session_maker):
        repo = IssueHistoryRepository(session)
        for snapshot in test_snapshots:
            repo.save_snapshot(**snapshot)

    yield session_maker

    # Cleanup: delete test snapshots
    # Note: In a real test environment, you might want to use a separate test database
    # For now, we'll leave the test data (it will be overwritten by real data)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_find_duplicates_detects_similar_issues(
    populated_vector_store, populated_database
):
    """Test that find_duplicates correctly identifies similar issues."""
    detector = DuplicateDetector()

    # Find duplicates (active issues only)
    duplicates = await detector.find_duplicates(min_similarity=0.70, active_only=True)

    # Should find at least the OAuth pair (AI-1799 and AI-1820)
    # DMD-480 is Done, so should be excluded with active_only=True
    oauth_pair = next(
        (
            d
            for d in duplicates
            if set([d["issue_a"], d["issue_b"]]) == {"AI-1799", "AI-1820"}
        ),
        None,
    )

    assert oauth_pair is not None, "Should detect OAuth duplicate pair"
    assert oauth_pair["similarity"] >= 0.70
    assert oauth_pair["team"] == "AI"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_find_duplicates_includes_inactive_with_flag(
    populated_vector_store, populated_database
):
    """Test that find_duplicates includes Done/Canceled issues with --all flag."""
    detector = DuplicateDetector()

    # Find duplicates (all issues)
    duplicates = await detector.find_duplicates(min_similarity=0.70, active_only=False)

    # Should now include DMD-480 (Done) and DMD-485 (Todo)
    login_pair = next(
        (
            d
            for d in duplicates
            if set([d["issue_a"], d["issue_b"]]) == {"DMD-480", "DMD-485"}
        ),
        None,
    )

    assert (
        login_pair is not None
    ), "Should detect login duplicate pair when --all is used"
    assert login_pair["similarity"] >= 0.70


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_issue_for_duplicates_finds_similar(
    populated_vector_store, populated_database
):
    """Test checking a specific issue for duplicates."""
    detector = DuplicateDetector()

    # Check AI-1799 for duplicates
    duplicates = await detector.check_issue_for_duplicates(
        "AI-1799", min_similarity=0.70
    )

    # Should find AI-1820 as similar
    assert len(duplicates) > 0
    assert any(d["issue_b"] == "AI-1820" for d in duplicates)

    # Check similarity score
    oauth_dup = next((d for d in duplicates if d["issue_b"] == "AI-1820"), None)
    assert oauth_dup is not None
    assert oauth_dup["similarity"] >= 0.70


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_issue_excludes_dissimilar(
    populated_vector_store, populated_database
):
    """Test that dissimilar issues are not flagged as duplicates."""
    detector = DuplicateDetector()

    # Check ENG-100 (database refactoring) for duplicates
    # Should NOT match OAuth or login issues
    duplicates = await detector.check_issue_for_duplicates(
        "ENG-100", min_similarity=0.70
    )

    # Should not find OAuth or login issues as duplicates
    oauth_ids = {"AI-1799", "AI-1820"}
    login_ids = {"DMD-480", "DMD-485"}

    for dup in duplicates:
        assert dup["issue_b"] not in oauth_ids
        assert dup["issue_b"] not in login_ids


@pytest.mark.asyncio
@pytest.mark.integration
async def test_similarity_threshold_filtering(
    populated_vector_store, populated_database
):
    """Test that similarity threshold correctly filters results."""
    detector = DuplicateDetector()

    # Use very high threshold (95%)
    duplicates_high = await detector.find_duplicates(
        min_similarity=0.95, active_only=True
    )

    # Use medium threshold (70%)
    duplicates_medium = await detector.find_duplicates(
        min_similarity=0.70, active_only=True
    )

    # Medium threshold should find more or equal duplicates
    assert len(duplicates_medium) >= len(duplicates_high)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_format_duplicate_report_with_real_data(
    populated_vector_store, populated_database
):
    """Test formatting duplicate report with real duplicate data."""
    detector = DuplicateDetector()

    duplicates = await detector.find_duplicates(min_similarity=0.70, active_only=True)

    if len(duplicates) > 0:
        formatted = detector.format_duplicate_report(duplicates)

        # Should contain markdown formatting
        assert "**" in formatted
        assert "Warning" in formatted or "⚠️" in formatted

        # Should contain issue IDs
        for dup in duplicates:
            assert dup["issue_a"] in formatted
            assert dup["issue_b"] in formatted

        # Should contain similarity percentages
        assert "%" in formatted


@pytest.mark.asyncio
@pytest.mark.integration
async def test_duplicate_detection_with_empty_description(
    populated_vector_store, populated_database
):
    """Test duplicate detection works even with empty descriptions."""
    from linear_chief.storage import get_session_maker, get_db_session
    from linear_chief.storage.repositories import IssueHistoryRepository

    store = IssueVectorStore()
    session_maker = get_session_maker()

    # Add issue with no description to vector store AND database
    await store.add_issue(
        issue_id="TEST-1",
        title="Test issue with no description",
        description="",
        metadata={"state": "Todo", "team": "TEST"},
    )

    await store.add_issue(
        issue_id="TEST-2",
        title="Test issue with no description",
        description="",
        metadata={"state": "Todo", "team": "TEST"},
    )

    # Add to database as well
    for session in get_db_session(session_maker):
        repo = IssueHistoryRepository(session)
        repo.save_snapshot(
            issue_id="TEST-1",
            linear_id="test-uuid-1",
            title="Test issue with no description",
            state="Todo",
            team_name="TEST",
            extra_metadata={"description": ""},
        )
        repo.save_snapshot(
            issue_id="TEST-2",
            linear_id="test-uuid-2",
            title="Test issue with no description",
            state="Todo",
            team_name="TEST",
            extra_metadata={"description": ""},
        )

    detector = DuplicateDetector()

    # Should still work based on title similarity
    duplicates = await detector.check_issue_for_duplicates(
        "TEST-1", min_similarity=0.80
    )

    # Cleanup
    await store.delete_issue("TEST-1")
    await store.delete_issue("TEST-2")

    # Should find TEST-2 as duplicate based on identical title
    assert len(duplicates) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_suggestion_generation_logic(populated_vector_store, populated_database):
    """Test that merge suggestions are generated correctly."""
    detector = DuplicateDetector()

    duplicates = await detector.find_duplicates(min_similarity=0.70, active_only=True)

    # Find OAuth pair
    oauth_pair = next(
        (
            d
            for d in duplicates
            if set([d["issue_a"], d["issue_b"]]) == {"AI-1799", "AI-1820"}
        ),
        None,
    )

    if oauth_pair:
        # AI-1799 is "In Progress", AI-1820 is "Todo"
        # Should suggest merging Todo into In Progress
        suggestion = oauth_pair["suggested_action"]
        # Check for "merg" (covers "merge" and "merging") or "check"
        assert "merg" in suggestion.lower() or "check" in suggestion.lower()
        assert "AI-1799" in suggestion or "AI-1820" in suggestion
