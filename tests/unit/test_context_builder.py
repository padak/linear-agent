"""Unit tests for context builder."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from linear_chief.agent.context_builder import (
    build_conversation_context,
    get_relevant_issues,
    check_issue_query,
    extract_issue_ids,
    fetch_issue_details,
    format_fetched_issues,
    _format_recent_issues,
    _format_recent_briefings,
    _format_similar_issues,
    _format_user_assigned_issues,
)


def test_check_issue_query_true():
    """Test issue query detection with issue-related keywords."""
    assert check_issue_query("What issues are blocked?") is True
    assert check_issue_query("Show me my tasks") is True
    assert check_issue_query("What's the status of the bug?") is True
    assert check_issue_query("Which features am I working on?") is True


def test_check_issue_query_false():
    """Test issue query detection with non-issue queries."""
    assert check_issue_query("What's the weather like?") is False
    assert check_issue_query("How are you doing?") is False
    assert check_issue_query("Tell me a joke") is False


def test_extract_issue_ids_single():
    """Test extracting a single issue ID from query."""
    assert extract_issue_ids("dej mi detail CSM-93") == ["CSM-93"]
    assert extract_issue_ids("What's the status of DMD-480?") == ["DMD-480"]
    assert extract_issue_ids("AI-1799 is blocked") == ["AI-1799"]


def test_extract_issue_ids_multiple():
    """Test extracting multiple issue IDs from query."""
    result = extract_issue_ids("co je s DMD-480 a AI-1799?")
    assert len(result) == 2
    assert "DMD-480" in result
    assert "AI-1799" in result


def test_extract_issue_ids_none():
    """Test when no issue IDs are present."""
    assert extract_issue_ids("žádné issue ID") == []
    assert extract_issue_ids("No issues here") == []
    assert extract_issue_ids("lowercase-123 should not match") == []


def test_extract_issue_ids_deduplication():
    """Test that duplicate IDs are removed."""
    result = extract_issue_ids("DMD-480 and DMD-480 again")
    assert len(result) == 1
    assert result == ["DMD-480"]


def test_extract_issue_ids_edge_cases():
    """Test edge cases for issue ID patterns."""
    # Valid patterns
    assert extract_issue_ids("PROJ-12345") == ["PROJ-12345"]
    assert extract_issue_ids("A-1") == ["A-1"]
    assert extract_issue_ids("ABCD-99999") == ["ABCD-99999"]

    # Invalid patterns (should not match)
    assert extract_issue_ids("toolong-123") == []  # More than 4 letters
    assert extract_issue_ids("CSM-") == []  # No digits
    assert extract_issue_ids("-123") == []  # No prefix


def test_format_fetched_issues_full_details():
    """Test formatting of fetched issues with full details."""
    issues = [
        {
            "identifier": "CSM-93",
            "title": "Test Issue",
            "state": {"name": "In Progress"},
            "priorityLabel": "High",
            "assignee": {"name": "Alice"},
            "url": "https://linear.app/issue/CSM-93",
            "description": "This is a test description",
            "comments": {
                "nodes": [
                    {
                        "user": {"name": "Bob"},
                        "body": "This is a comment",
                        "createdAt": "2024-01-15T10:00:00Z",
                    }
                ]
            },
        }
    ]

    formatted = format_fetched_issues(issues)

    # Verify all details are present
    assert "CSM-93" in formatted
    assert "Test Issue" in formatted
    assert "In Progress" in formatted
    assert "High" in formatted
    assert "Alice" in formatted
    assert "https://linear.app/issue/CSM-93" in formatted
    assert "This is a test description" in formatted
    assert "Comments (1)" in formatted
    assert "Bob" in formatted
    assert "This is a comment" in formatted


def test_format_fetched_issues_empty():
    """Test formatting when no issues are provided."""
    assert format_fetched_issues([]) == ""


def test_format_fetched_issues_no_description():
    """Test formatting when issue has no description."""
    issues = [
        {
            "identifier": "TEST-1",
            "title": "No description",
            "state": {"name": "Todo"},
            "priorityLabel": "None",
            "assignee": None,
            "url": "https://linear.app/issue/TEST-1",
            "description": "",
            "comments": {"nodes": []},
        }
    ]

    formatted = format_fetched_issues(issues)

    assert "No description" in formatted
    assert "(No description)" in formatted
    assert "Unassigned" in formatted


def test_format_fetched_issues_multiple():
    """Test formatting multiple issues."""
    issues = [
        {
            "identifier": "PROJ-1",
            "title": "First Issue",
            "state": {"name": "Done"},
            "priorityLabel": "Low",
            "assignee": {"name": "Alice"},
            "url": "https://linear.app/issue/PROJ-1",
            "description": "First description",
            "comments": {"nodes": []},
        },
        {
            "identifier": "PROJ-2",
            "title": "Second Issue",
            "state": {"name": "Todo"},
            "priorityLabel": "High",
            "assignee": {"name": "Bob"},
            "url": "https://linear.app/issue/PROJ-2",
            "description": "Second description",
            "comments": {"nodes": []},
        },
    ]

    formatted = format_fetched_issues(issues)

    # Both issues should be present
    assert "PROJ-1" in formatted
    assert "PROJ-2" in formatted
    assert "First Issue" in formatted
    assert "Second Issue" in formatted
    # Should be separated by divider
    assert "---" in formatted


@pytest.mark.asyncio
async def test_fetch_issue_details_success():
    """Test successful fetching of issue details."""
    mock_issue = {
        "identifier": "CSM-93",
        "title": "Test Issue",
        "state": {"name": "In Progress"},
    }

    with (
        patch("linear_chief.config.LINEAR_API_KEY", "test_key"),
        patch("linear_chief.linear.client.LinearClient") as mock_linear_client,
        patch(
            "linear_chief.agent.context_builder.get_session_maker"
        ) as mock_session_maker,
        patch(
            "linear_chief.agent.context_builder.get_db_session"
        ) as mock_get_db_session,
    ):
        # Mock database session to return None (cache miss)
        mock_session = Mock()
        mock_get_db_session.return_value = [mock_session]
        mock_repo = Mock()
        mock_repo.get_issue_snapshot_by_identifier = Mock(return_value=None)

        with patch(
            "linear_chief.agent.context_builder.IssueHistoryRepository",
            return_value=mock_repo,
        ):
            # Mock the async context manager and client
            mock_client_instance = Mock()
            mock_client_instance.get_issue_by_identifier = AsyncMock(
                return_value=mock_issue
            )
            mock_linear_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_linear_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_issue_details(["CSM-93"])

            assert len(result) == 1
            assert result[0] == mock_issue
            mock_client_instance.get_issue_by_identifier.assert_called_once_with(
                "CSM-93"
            )


@pytest.mark.asyncio
async def test_fetch_issue_details_multiple():
    """Test fetching multiple issues."""
    mock_issues = {
        "CSM-93": {"identifier": "CSM-93", "title": "First"},
        "DMD-480": {"identifier": "DMD-480", "title": "Second"},
    }

    async def mock_get_issue(issue_id):
        return mock_issues.get(issue_id)

    with (
        patch("linear_chief.config.LINEAR_API_KEY", "test_key"),
        patch("linear_chief.linear.client.LinearClient") as mock_linear_client,
    ):
        mock_client_instance = Mock()
        mock_client_instance.get_issue_by_identifier = AsyncMock(
            side_effect=mock_get_issue
        )
        mock_linear_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_linear_client.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await fetch_issue_details(["CSM-93", "DMD-480"])

        assert len(result) == 2
        assert result[0]["identifier"] == "CSM-93"
        assert result[1]["identifier"] == "DMD-480"


@pytest.mark.asyncio
async def test_fetch_issue_details_no_api_key():
    """Test fetching when API key is not configured."""
    with patch("linear_chief.config.LINEAR_API_KEY", ""):
        result = await fetch_issue_details(["CSM-93"])
        assert result == []


@pytest.mark.asyncio
async def test_fetch_issue_details_empty_list():
    """Test fetching with empty issue ID list."""
    result = await fetch_issue_details([])
    assert result == []


@pytest.mark.asyncio
async def test_fetch_issue_details_handles_error():
    """Test that errors during fetching are handled gracefully."""
    with (
        patch("linear_chief.config.LINEAR_API_KEY", "test_key"),
        patch("linear_chief.linear.client.LinearClient") as mock_linear_client,
        patch(
            "linear_chief.agent.context_builder.get_session_maker"
        ) as mock_session_maker,
        patch(
            "linear_chief.agent.context_builder.get_db_session"
        ) as mock_get_db_session,
    ):
        # Mock database session to return None (cache miss)
        mock_session = Mock()
        mock_get_db_session.return_value = [mock_session]
        mock_repo = Mock()
        mock_repo.get_issue_snapshot_by_identifier = Mock(return_value=None)

        with patch(
            "linear_chief.agent.context_builder.IssueHistoryRepository",
            return_value=mock_repo,
        ):
            # Mock client that raises an error
            mock_client_instance = Mock()
            mock_client_instance.get_issue_by_identifier = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_linear_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_linear_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_issue_details(["CSM-93"])

            # Should return empty list on error
            assert result == []


def test_format_recent_issues():
    """Test formatting of recent issues."""
    # Mock IssueHistory objects
    mock_issues = [
        Mock(
            issue_id="PROJ-123",
            title="Fix login bug",
            state="In Progress",
            assignee_name="Alice",
        ),
        Mock(
            issue_id="PROJ-124",
            title="Add new feature",
            state="In Progress",
            assignee_name="Bob",
        ),
        Mock(
            issue_id="PROJ-125",
            title="Update documentation",
            state="Done",
            assignee_name=None,
        ),
    ]

    formatted = _format_recent_issues(mock_issues)

    # Verify structure
    assert "Recent Issues" in formatted
    assert "In Progress" in formatted
    assert "Done" in formatted
    assert "PROJ-123" in formatted
    assert "Fix login bug" in formatted
    assert "Alice" in formatted
    assert "Unassigned" in formatted  # For PROJ-125 with no assignee


def test_format_recent_issues_long_title():
    """Test that long titles are truncated."""
    mock_issue = Mock(
        issue_id="PROJ-999",
        title="A" * 100,  # 100 char title
        state="Todo",
        assignee_name="Alice",
    )

    formatted = _format_recent_issues([mock_issue])

    # Should be truncated to 60 chars (57 + "...")
    assert "A" * 57 + "..." in formatted


def test_format_recent_briefings():
    """Test formatting of recent briefings."""
    now = datetime.utcnow()

    mock_briefings = [
        Mock(
            generated_at=now,
            issue_count=5,
            content="Today's key issues:\n- PROJ-123: High priority",
        ),
        Mock(
            generated_at=now - timedelta(days=1),
            issue_count=3,
            content="Yesterday's summary",
        ),
    ]

    formatted = _format_recent_briefings(mock_briefings)

    # Verify structure
    assert "Recent Briefings" in formatted
    assert "Today" in formatted
    assert "5 issues" in formatted
    assert "Yesterday" in formatted


def test_format_recent_briefings_truncates_content():
    """Test that long briefing content is truncated."""
    mock_briefing = Mock(
        generated_at=datetime.utcnow(),
        issue_count=10,
        content="A" * 600,  # Long content
    )

    formatted = _format_recent_briefings([mock_briefing])

    # Content should be truncated to 500 chars
    assert "A" * 500 in formatted
    assert "..." in formatted


def test_format_similar_issues():
    """Test formatting of similar issues from vector search."""
    similar_issues = [
        {
            "issue_id": "PROJ-100",
            "document": "Fix authentication\n\nDetails here...",
            "distance": 0.2,
        },
        {
            "issue_id": "PROJ-101",
            "document": "Add login feature",
            "distance": 0.3,
        },
    ]

    formatted = _format_similar_issues(similar_issues)

    assert "Issues Related to Your Query" in formatted
    assert "PROJ-100" in formatted
    assert "Fix authentication" in formatted
    assert "similarity: 80%" in formatted  # 1 - 0.2 = 0.8 = 80%
    assert "similarity: 70%" in formatted  # 1 - 0.3 = 0.7 = 70%


def test_format_similar_issues_without_distance():
    """Test formatting when distance is not provided."""
    similar_issues = [
        {
            "issue_id": "PROJ-100",
            "document": "Some issue",
            "distance": None,
        }
    ]

    formatted = _format_similar_issues(similar_issues)

    # Should still show issue without similarity score
    assert "PROJ-100" in formatted
    assert "similarity" not in formatted


@pytest.mark.asyncio
async def test_get_relevant_issues_success():
    """Test getting relevant issues via vector search."""
    mock_results = [
        {
            "issue_id": "PROJ-123",
            "document": "Bug fix",
            "distance": 0.1,
        }
    ]

    with patch(
        "linear_chief.agent.context_builder.IssueVectorStore"
    ) as mock_vector_store:
        mock_instance = Mock()
        mock_instance.search_similar = AsyncMock(return_value=mock_results)
        mock_vector_store.return_value = mock_instance

        results = await get_relevant_issues("test query", limit=5)

        assert results == mock_results
        mock_instance.search_similar.assert_called_once_with("test query", limit=5)


@pytest.mark.asyncio
async def test_get_relevant_issues_handles_error():
    """Test that errors in vector search are handled gracefully."""
    with patch(
        "linear_chief.agent.context_builder.IssueVectorStore"
    ) as mock_vector_store:
        mock_instance = Mock()
        mock_instance.search_similar = AsyncMock(side_effect=Exception("Search failed"))
        mock_vector_store.return_value = mock_instance

        results = await get_relevant_issues("test query")

        # Should return empty list on error
        assert results == []


@pytest.mark.asyncio
async def test_build_conversation_context_success():
    """Test building conversation context with all data."""
    # Mock database repositories
    mock_issues = [
        Mock(
            issue_id="PROJ-123",
            title="Test issue",
            state="In Progress",
            assignee_name="Alice",
        )
    ]

    mock_briefings = [
        Mock(
            generated_at=datetime.utcnow(),
            issue_count=1,
            content="Test briefing",
        )
    ]

    with (
        patch("linear_chief.agent.context_builder.get_session_maker"),
        patch("linear_chief.agent.context_builder.get_db_session") as mock_get_session,
    ):
        # Mock session context manager
        mock_session = Mock()
        mock_get_session.return_value = [mock_session]

        # Mock repositories
        with (
            patch(
                "linear_chief.agent.context_builder.IssueHistoryRepository"
            ) as mock_issue_repo,
            patch(
                "linear_chief.agent.context_builder.BriefingRepository"
            ) as mock_briefing_repo,
        ):

            mock_issue_repo.return_value.get_all_latest_snapshots.return_value = (
                mock_issues
            )
            mock_briefing_repo.return_value.get_recent_briefings.return_value = (
                mock_briefings
            )

            context = await build_conversation_context(user_id="test_user")

            # Verify context contains expected sections
            assert "Recent Issues" in context
            assert "Recent Briefings" in context
            assert "Current Date" in context
            assert "PROJ-123" in context


@pytest.mark.asyncio
async def test_build_conversation_context_with_vector_search():
    """Test building context with vector search enabled."""
    mock_issues = []
    mock_briefings = []
    mock_similar = [
        {
            "issue_id": "PROJ-999",
            "document": "Similar issue",
            "distance": 0.1,
        }
    ]

    with (
        patch("linear_chief.agent.context_builder.get_session_maker"),
        patch("linear_chief.agent.context_builder.get_db_session") as mock_get_session,
    ):

        mock_session = Mock()
        mock_get_session.return_value = [mock_session]

        with (
            patch(
                "linear_chief.agent.context_builder.IssueHistoryRepository"
            ) as mock_issue_repo,
            patch(
                "linear_chief.agent.context_builder.BriefingRepository"
            ) as mock_briefing_repo,
            patch(
                "linear_chief.agent.context_builder.get_relevant_issues",
                new_callable=AsyncMock,
            ) as mock_get_relevant,
        ):

            mock_issue_repo.return_value.get_all_latest_snapshots.return_value = (
                mock_issues
            )
            mock_briefing_repo.return_value.get_recent_briefings.return_value = (
                mock_briefings
            )
            mock_get_relevant.return_value = mock_similar

            context = await build_conversation_context(
                user_id="test_user",
                include_vector_search=True,
                query="test query",
            )

            # Verify vector search was called
            mock_get_relevant.assert_called_once_with("test query", limit=5)

            # Verify similar issues in context
            assert "Issues Related to Your Query" in context
            assert "PROJ-999" in context


@pytest.mark.asyncio
async def test_build_conversation_context_handles_error():
    """Test that errors are handled gracefully with fallback context."""
    with patch(
        "linear_chief.agent.context_builder.get_session_maker",
        side_effect=Exception("DB Error"),
    ):
        context = await build_conversation_context(user_id="test_user")

        # Should return minimal context with current date
        assert "Current Date" in context
        assert "Unable to load full context" in context


@pytest.mark.asyncio
async def test_build_conversation_context_filters_user_issues_with_diacritics():
    """Test that user issues are correctly filtered even with diacritics."""
    # Mock issues with diacritics (simulating real Linear data)
    mock_issues = [
        Mock(
            issue_id="LDRS-63",
            title="Issue assigned to user",
            state="Todo",
            assignee_name="Petr Šimeček",  # With diacritics
            assignee_email="petr@keboola.com",
        ),
        Mock(
            issue_id="CSM-93",
            title="Another user issue",
            state="In Progress",
            assignee_name="Petr Šimeček",  # With diacritics
            assignee_email="petr@keboola.com",
        ),
        Mock(
            issue_id="DMD-480",
            title="Someone else's issue",
            state="Todo",
            assignee_name="Tomáš Fejfar",  # Different user
            assignee_email="tomas@keboola.com",
        ),
    ]

    mock_briefings = []

    with (
        patch("linear_chief.agent.context_builder.get_session_maker"),
        patch("linear_chief.agent.context_builder.get_db_session") as mock_get_session,
        # Configure user WITHOUT diacritics (simulating .env config)
        patch("linear_chief.config.LINEAR_USER_NAME", "Petr Simecek"),
        patch("linear_chief.config.LINEAR_USER_EMAIL", "petr@keboola.com"),
    ):
        mock_session = Mock()
        mock_get_session.return_value = [mock_session]

        with (
            patch(
                "linear_chief.agent.context_builder.IssueHistoryRepository"
            ) as mock_issue_repo,
            patch(
                "linear_chief.agent.context_builder.BriefingRepository"
            ) as mock_briefing_repo,
        ):

            mock_issue_repo.return_value.get_all_latest_snapshots.return_value = (
                mock_issues
            )
            mock_briefing_repo.return_value.get_recent_briefings.return_value = (
                mock_briefings
            )

            context = await build_conversation_context(user_id="test_user")

            # Verify user's issues are in context (with diacritics)
            assert "**YOUR Assigned Issues**" in context
            assert "LDRS-63" in context
            assert "CSM-93" in context

            # Verify other user's issue is in "Recent Issues" section (not user's)
            assert "DMD-480" in context
            assert "Recent Issues" in context

            # Verify the context distinguishes between user and non-user issues
            # User issues should appear BEFORE "Recent Issues"
            user_section_idx = context.index("**YOUR Assigned Issues**")
            recent_section_idx = context.index("Recent Issues")
            assert user_section_idx < recent_section_idx


def test_format_user_assigned_issues():
    """Test formatting of user-assigned issues."""
    mock_issues = [
        Mock(
            issue_id="LDRS-63",
            title="First issue",
            state="Todo",
        ),
        Mock(
            issue_id="CSM-93",
            title="Second issue",
            state="In Progress",
        ),
        Mock(
            issue_id="DMD-480",
            title="Third issue",
            state="In Progress",
        ),
    ]

    with patch("linear_chief.config.LINEAR_USER_NAME", "Petr Simecek"):
        formatted = _format_user_assigned_issues(mock_issues)

        # Verify structure
        assert "**YOUR Assigned Issues**" in formatted
        assert "Petr Simecek" in formatted

        # Verify all issues are present (not just top 3)
        assert "LDRS-63" in formatted
        assert "CSM-93" in formatted
        assert "DMD-480" in formatted

        # Verify grouped by state
        assert "Todo (1):" in formatted
        assert "In Progress (2):" in formatted


@pytest.mark.asyncio
async def test_fetch_issue_details_uses_cache():
    """Test that fetch_issue_details uses cached data when available."""
    from datetime import datetime, timedelta
    from linear_chief.agent.context_builder import (
        fetch_issue_details,
        _issue_history_to_dict,
    )

    # Create mock cached issue
    mock_cached_issue = Mock()
    mock_cached_issue.issue_id = "CSM-93"
    mock_cached_issue.linear_id = "test-linear-id"
    mock_cached_issue.title = "Cached Issue"
    mock_cached_issue.state = "In Progress"
    mock_cached_issue.priority = 1
    mock_cached_issue.assignee_id = "assignee-id"
    mock_cached_issue.assignee_name = "Test User"
    mock_cached_issue.team_id = "team-id"
    mock_cached_issue.team_name = "Test Team"
    mock_cached_issue.labels = ["bug", "priority"]
    mock_cached_issue.extra_metadata = {
        "url": "https://linear.app/issue/CSM-93",
        "priority_label": "High",
        "description": "Test description",
    }
    mock_cached_issue.snapshot_at = datetime.utcnow() - timedelta(minutes=30)

    with (
        patch("linear_chief.config.LINEAR_API_KEY", "test_key"),
        patch("linear_chief.linear.client.LinearClient") as mock_linear_client,
        patch(
            "linear_chief.agent.context_builder.get_session_maker"
        ) as mock_session_maker,
        patch(
            "linear_chief.agent.context_builder.get_db_session"
        ) as mock_get_db_session,
    ):
        # Mock database session to return cached issue
        mock_session = Mock()
        mock_get_db_session.return_value = [mock_session]
        mock_repo = Mock()
        mock_repo.get_issue_snapshot_by_identifier = Mock(
            return_value=mock_cached_issue
        )

        with patch(
            "linear_chief.agent.context_builder.IssueHistoryRepository",
            return_value=mock_repo,
        ):
            result = await fetch_issue_details(["CSM-93"])

            # Should use cached data
            assert len(result) == 1
            assert result[0]["identifier"] == "CSM-93"
            assert result[0]["title"] == "Cached Issue"

            # Should NOT call Linear API
            mock_linear_client.assert_not_called()

            # Should have checked cache
            mock_repo.get_issue_snapshot_by_identifier.assert_called_once_with(
                "CSM-93", max_age_hours=1
            )


@pytest.mark.asyncio
async def test_fetch_issue_details_cache_miss_fetches_from_api():
    """Test that cache miss triggers API fetch."""
    from linear_chief.agent.context_builder import fetch_issue_details

    mock_issue = {
        "identifier": "CSM-93",
        "title": "Fresh Issue",
        "state": {"name": "In Progress"},
    }

    with (
        patch("linear_chief.config.LINEAR_API_KEY", "test_key"),
        patch("linear_chief.linear.client.LinearClient") as mock_linear_client,
        patch(
            "linear_chief.agent.context_builder.get_session_maker"
        ) as mock_session_maker,
        patch(
            "linear_chief.agent.context_builder.get_db_session"
        ) as mock_get_db_session,
    ):
        # Mock database session to return None (cache miss)
        mock_session = Mock()
        mock_get_db_session.return_value = [mock_session]
        mock_repo = Mock()
        mock_repo.get_issue_snapshot_by_identifier = Mock(return_value=None)

        with patch(
            "linear_chief.agent.context_builder.IssueHistoryRepository",
            return_value=mock_repo,
        ):
            # Mock Linear API client
            mock_client_instance = Mock()
            mock_client_instance.get_issue_by_identifier = AsyncMock(
                return_value=mock_issue
            )
            mock_linear_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_linear_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_issue_details(["CSM-93"])

            # Should fetch from API
            assert len(result) == 1
            assert result[0]["title"] == "Fresh Issue"

            # Should have called Linear API
            mock_client_instance.get_issue_by_identifier.assert_called_once_with(
                "CSM-93"
            )


@pytest.mark.asyncio
async def test_fetch_issue_details_mixed_cache_and_api():
    """Test fetching multiple issues with some cached, some not."""
    from datetime import datetime, timedelta
    from linear_chief.agent.context_builder import fetch_issue_details

    # Create mock cached issue
    mock_cached_issue = Mock()
    mock_cached_issue.issue_id = "CSM-93"
    mock_cached_issue.linear_id = "test-linear-id"
    mock_cached_issue.title = "Cached Issue"
    mock_cached_issue.state = "In Progress"
    mock_cached_issue.priority = 1
    mock_cached_issue.assignee_id = None
    mock_cached_issue.assignee_name = None
    mock_cached_issue.team_id = None
    mock_cached_issue.team_name = None
    mock_cached_issue.labels = None
    mock_cached_issue.extra_metadata = {"priority_label": "High"}
    mock_cached_issue.snapshot_at = datetime.utcnow() - timedelta(minutes=30)

    # Mock API issue
    mock_api_issue = {
        "identifier": "DMD-480",
        "title": "Fresh Issue",
        "state": {"name": "Todo"},
    }

    with (
        patch("linear_chief.config.LINEAR_API_KEY", "test_key"),
        patch("linear_chief.linear.client.LinearClient") as mock_linear_client,
        patch(
            "linear_chief.agent.context_builder.get_session_maker"
        ) as mock_session_maker,
        patch(
            "linear_chief.agent.context_builder.get_db_session"
        ) as mock_get_db_session,
    ):
        # Mock database session
        mock_session = Mock()
        mock_get_db_session.return_value = [mock_session]
        mock_repo = Mock()

        # Return cached for CSM-93, None for DMD-480
        def mock_cache_lookup(issue_id, max_age_hours=1):
            if issue_id == "CSM-93":
                return mock_cached_issue
            return None

        mock_repo.get_issue_snapshot_by_identifier = Mock(side_effect=mock_cache_lookup)

        with patch(
            "linear_chief.agent.context_builder.IssueHistoryRepository",
            return_value=mock_repo,
        ):
            # Mock Linear API client
            mock_client_instance = Mock()
            mock_client_instance.get_issue_by_identifier = AsyncMock(
                return_value=mock_api_issue
            )
            mock_linear_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_linear_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_issue_details(["CSM-93", "DMD-480"])

            # Should return both issues
            assert len(result) == 2

            # Should have one cached, one from API
            identifiers = [issue["identifier"] for issue in result]
            assert "CSM-93" in identifiers
            assert "DMD-480" in identifiers

            # Should only call API for DMD-480
            mock_client_instance.get_issue_by_identifier.assert_called_once_with(
                "DMD-480"
            )


@pytest.mark.asyncio
async def test_fetch_issue_details_db_error_falls_back_to_api():
    """Test that DB errors cause graceful fallback to API."""
    from linear_chief.agent.context_builder import fetch_issue_details

    mock_issue = {
        "identifier": "CSM-93",
        "title": "API Issue",
        "state": {"name": "In Progress"},
    }

    with (
        patch("linear_chief.config.LINEAR_API_KEY", "test_key"),
        patch("linear_chief.linear.client.LinearClient") as mock_linear_client,
        patch(
            "linear_chief.agent.context_builder.get_session_maker"
        ) as mock_session_maker,
        patch(
            "linear_chief.agent.context_builder.get_db_session"
        ) as mock_get_db_session,
    ):
        # Mock database to raise an error
        mock_get_db_session.side_effect = Exception("DB Connection Error")

        # Mock Linear API client
        mock_client_instance = Mock()
        mock_client_instance.get_issue_by_identifier = AsyncMock(
            return_value=mock_issue
        )
        mock_linear_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_linear_client.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await fetch_issue_details(["CSM-93"])

        # Should fall back to API and still return data
        assert len(result) == 1
        assert result[0]["title"] == "API Issue"

        # Should have called Linear API
        mock_client_instance.get_issue_by_identifier.assert_called_once_with("CSM-93")


def test_issue_history_to_dict():
    """Test conversion of IssueHistory ORM model to dict."""
    from linear_chief.agent.context_builder import _issue_history_to_dict

    # Create mock IssueHistory
    mock_issue = Mock()
    mock_issue.issue_id = "CSM-93"
    mock_issue.linear_id = "test-linear-id"
    mock_issue.title = "Test Issue"
    mock_issue.state = "In Progress"
    mock_issue.priority = 1
    mock_issue.assignee_id = "assignee-id"
    mock_issue.assignee_name = "Test User"
    mock_issue.team_id = "team-id"
    mock_issue.team_name = "Test Team"
    mock_issue.labels = ["bug", "priority"]
    mock_issue.extra_metadata = {
        "url": "https://linear.app/issue/CSM-93",
        "priority_label": "High",
        "description": "Test description",
        "assignee_email": "test@example.com",
        "creator": "Creator User",
        "comments": [
            {
                "user": {"name": "Commenter"},
                "body": "Test comment",
                "createdAt": "2025-01-01",
            }
        ],
    }

    result = _issue_history_to_dict(mock_issue)

    # Verify structure matches Linear API format
    assert result["identifier"] == "CSM-93"
    assert result["id"] == "test-linear-id"
    assert result["title"] == "Test Issue"
    assert result["state"]["name"] == "In Progress"
    assert result["priority"] == 1
    assert result["priorityLabel"] == "High"
    assert result["url"] == "https://linear.app/issue/CSM-93"
    assert result["description"] == "Test description"

    # Verify assignee
    assert result["assignee"]["id"] == "assignee-id"
    assert result["assignee"]["name"] == "Test User"
    assert result["assignee"]["email"] == "test@example.com"

    # Verify team
    assert result["team"]["id"] == "team-id"
    assert result["team"]["name"] == "Test Team"

    # Verify creator
    assert result["creator"]["name"] == "Creator User"

    # Verify labels
    assert len(result["labels"]["nodes"]) == 2
    assert result["labels"]["nodes"][0]["name"] == "bug"

    # Verify comments
    assert len(result["comments"]["nodes"]) == 1
    assert result["comments"]["nodes"][0]["body"] == "Test comment"
