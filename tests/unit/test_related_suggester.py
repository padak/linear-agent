"""Tests for related issues suggester."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from linear_chief.intelligence.related_suggester import (
    RelatedIssuesSuggester,
    should_suggest_related,
)


@pytest.fixture
def mock_search_service():
    """Mock SemanticSearchService for testing."""
    with patch(
        "linear_chief.intelligence.related_suggester.SemanticSearchService"
    ) as mock_cls:
        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        yield mock_service


@pytest.mark.asyncio
async def test_get_related_issues_basic(mock_search_service):
    """Test basic related issues retrieval."""
    # Mock search results
    mock_search_service.find_similar_issues = AsyncMock(
        return_value=[
            {
                "issue_id": "AI-1820",
                "title": "OAuth2 implementation",
                "similarity": 0.73,
                "url": "https://linear.app/ai/issue/AI-1820",
                "team": "AI",
                "state": "In Progress",
            },
            {
                "issue_id": "AI-1805",
                "title": "Login flow refactor",
                "similarity": 0.68,
                "url": "https://linear.app/ai/issue/AI-1805",
                "team": "AI",
                "state": "Done",
            },
        ]
    )

    suggester = RelatedIssuesSuggester()
    related = await suggester.get_related_issues("AI-1799", limit=3)

    assert len(related) == 2
    assert related[0]["issue_id"] == "AI-1820"
    assert related[0]["relation_type"] == "similar"
    assert related[1]["issue_id"] == "AI-1805"
    assert related[1]["relation_type"] == "similar"

    # Verify search was called with correct parameters
    mock_search_service.find_similar_issues.assert_called_once()
    call_args = mock_search_service.find_similar_issues.call_args
    assert call_args[1]["issue_id"] == "AI-1799"
    assert call_args[1]["min_similarity"] == 0.6


@pytest.mark.asyncio
async def test_get_related_issues_excludes_duplicates(mock_search_service):
    """Test that high-similarity duplicates are excluded."""
    # Mock search results with mix of similar and duplicates
    mock_search_service.find_similar_issues = AsyncMock(
        return_value=[
            {
                "issue_id": "AI-1820",
                "title": "Exact duplicate",
                "similarity": 0.92,  # Duplicate (>85%)
                "url": "https://linear.app/ai/issue/AI-1820",
                "team": "AI",
                "state": "Todo",
            },
            {
                "issue_id": "AI-1805",
                "title": "Related issue",
                "similarity": 0.73,  # Related
                "url": "https://linear.app/ai/issue/AI-1805",
                "team": "AI",
                "state": "In Progress",
            },
            {
                "issue_id": "AI-1800",
                "title": "Another duplicate",
                "similarity": 0.88,  # Duplicate (>85%)
                "url": "https://linear.app/ai/issue/AI-1800",
                "team": "AI",
                "state": "Todo",
            },
            {
                "issue_id": "DMD-480",
                "title": "Another related",
                "similarity": 0.65,  # Related
                "url": "https://linear.app/dmd/issue/DMD-480",
                "team": "DMD",
                "state": "Backlog",
            },
        ]
    )

    suggester = RelatedIssuesSuggester()
    related = await suggester.get_related_issues(
        "AI-1799",
        limit=5,
        min_similarity=0.6,
        exclude_duplicates=True,
    )

    # Should only return the 2 related issues (similarity <85%)
    assert len(related) == 2
    assert related[0]["issue_id"] == "AI-1805"
    assert related[0]["similarity"] == 0.73
    assert related[0]["relation_type"] == "similar"
    assert related[1]["issue_id"] == "DMD-480"
    assert related[1]["similarity"] == 0.65
    assert related[1]["relation_type"] == "similar"

    # Verify no duplicates included
    assert all(r["similarity"] < 0.85 for r in related)


@pytest.mark.asyncio
async def test_get_related_issues_includes_duplicates_when_not_excluded(
    mock_search_service,
):
    """Test that duplicates are included when exclude_duplicates=False."""
    # Mock search results with duplicates
    mock_search_service.find_similar_issues = AsyncMock(
        return_value=[
            {
                "issue_id": "AI-1820",
                "title": "Exact duplicate",
                "similarity": 0.92,
                "url": "https://linear.app/ai/issue/AI-1820",
                "team": "AI",
                "state": "Todo",
            },
            {
                "issue_id": "AI-1805",
                "title": "Related issue",
                "similarity": 0.73,
                "url": "https://linear.app/ai/issue/AI-1805",
                "team": "AI",
                "state": "In Progress",
            },
        ]
    )

    suggester = RelatedIssuesSuggester()
    related = await suggester.get_related_issues(
        "AI-1799",
        limit=5,
        exclude_duplicates=False,
    )

    # Should include both issues
    assert len(related) == 2
    assert related[0]["issue_id"] == "AI-1820"
    assert related[0]["relation_type"] == "duplicate"  # Classified as duplicate
    assert related[1]["issue_id"] == "AI-1805"
    assert related[1]["relation_type"] == "similar"


@pytest.mark.asyncio
async def test_get_related_issues_respects_limit(mock_search_service):
    """Test that limit parameter is respected."""
    # Mock 5 search results
    mock_results = [
        {
            "issue_id": f"AI-{i}",
            "title": f"Issue {i}",
            "similarity": 0.7 - (i * 0.05),  # Decreasing similarity
            "url": f"https://linear.app/ai/issue/AI-{i}",
            "team": "AI",
            "state": "Todo",
        }
        for i in range(5)
    ]
    mock_search_service.find_similar_issues = AsyncMock(return_value=mock_results)

    suggester = RelatedIssuesSuggester()
    related = await suggester.get_related_issues("AI-1799", limit=3)

    # Should only return top 3
    assert len(related) == 3
    assert related[0]["issue_id"] == "AI-0"
    assert related[1]["issue_id"] == "AI-1"
    assert related[2]["issue_id"] == "AI-2"


@pytest.mark.asyncio
async def test_get_related_issues_not_found(mock_search_service):
    """Test handling when source issue is not found."""
    # Mock ValueError from semantic search
    mock_search_service.find_similar_issues = AsyncMock(
        side_effect=ValueError("Issue AI-9999 not found")
    )

    suggester = RelatedIssuesSuggester()

    # Should re-raise ValueError
    with pytest.raises(ValueError, match="Issue AI-9999 not found"):
        await suggester.get_related_issues("AI-9999")


@pytest.mark.asyncio
async def test_get_related_issues_error_handling(mock_search_service):
    """Test graceful error handling for unexpected errors."""
    # Mock unexpected error
    mock_search_service.find_similar_issues = AsyncMock(
        side_effect=Exception("Unexpected error")
    )

    suggester = RelatedIssuesSuggester()
    related = await suggester.get_related_issues("AI-1799")

    # Should return empty list instead of crashing
    assert related == []


@pytest.mark.asyncio
async def test_get_related_for_conversation(mock_search_service):
    """Test getting related issues for conversation query."""
    # Mock search results
    mock_search_service.search_by_text = AsyncMock(
        return_value=[
            {
                "issue_id": "AI-1820",
                "title": "Auth issue",
                "similarity": 0.75,
                "url": "https://linear.app/ai/issue/AI-1820",
                "team": "AI",
                "state": "In Progress",
            },
            {
                "issue_id": "DMD-480",
                "title": "Login problem",
                "similarity": 0.68,
                "url": "https://linear.app/dmd/issue/DMD-480",
                "team": "DMD",
                "state": "Todo",
            },
        ]
    )

    suggester = RelatedIssuesSuggester()
    related = await suggester.get_related_for_conversation(
        query="authentication issues",
        limit=3,
    )

    assert len(related) == 2
    assert related[0]["issue_id"] == "AI-1820"
    assert related[0]["relation_type"] == "similar"
    assert related[1]["issue_id"] == "DMD-480"

    # Verify search was called correctly
    mock_search_service.search_by_text.assert_called_once()
    call_args = mock_search_service.search_by_text.call_args
    assert call_args[1]["query"] == "authentication issues"
    assert call_args[1]["min_similarity"] == 0.5


@pytest.mark.asyncio
async def test_get_related_for_conversation_excludes_current(mock_search_service):
    """Test that current issue is excluded from conversation suggestions."""
    # Mock search results including current issue
    mock_search_service.search_by_text = AsyncMock(
        return_value=[
            {
                "issue_id": "AI-1799",  # Current issue
                "title": "Current issue",
                "similarity": 0.95,
                "url": "https://linear.app/ai/issue/AI-1799",
                "team": "AI",
                "state": "In Progress",
            },
            {
                "issue_id": "AI-1820",
                "title": "Related issue",
                "similarity": 0.75,
                "url": "https://linear.app/ai/issue/AI-1820",
                "team": "AI",
                "state": "Todo",
            },
        ]
    )

    suggester = RelatedIssuesSuggester()
    related = await suggester.get_related_for_conversation(
        query="related to AI-1799",
        current_issue_id="AI-1799",
        limit=3,
    )

    # Should exclude AI-1799
    assert len(related) == 1
    assert related[0]["issue_id"] == "AI-1820"


def test_format_related_issues_basic():
    """Test basic formatting of related issues."""
    related = [
        {
            "issue_id": "AI-1820",
            "title": "OAuth2 implementation",
            "url": "https://linear.app/ai/issue/AI-1820",
            "state": "In Progress",
            "similarity": 0.73,
        },
        {
            "issue_id": "AI-1805",
            "title": "Login flow refactor",
            "url": "https://linear.app/ai/issue/AI-1805",
            "state": "Done",
            "similarity": 0.68,
        },
    ]

    suggester = RelatedIssuesSuggester()
    formatted = suggester.format_related_issues(related)

    # Check structure
    assert "**Related Issues:**" in formatted
    assert "[**AI-1820**](https://linear.app/ai/issue/AI-1820)" in formatted
    assert "OAuth2 implementation" in formatted
    assert "(In Progress)" in formatted
    assert "[**AI-1805**](https://linear.app/ai/issue/AI-1805)" in formatted
    assert "Login flow refactor" in formatted
    assert "(Done)" in formatted

    # Should NOT show similarity by default
    assert "73%" not in formatted
    assert "68%" not in formatted


def test_format_related_issues_with_similarity():
    """Test formatting with similarity scores."""
    related = [
        {
            "issue_id": "AI-1820",
            "title": "OAuth2 implementation",
            "url": "https://linear.app/ai/issue/AI-1820",
            "state": "In Progress",
            "similarity": 0.73,
        },
    ]

    suggester = RelatedIssuesSuggester()
    formatted = suggester.format_related_issues(related, show_similarity=True)

    # Should show similarity percentage
    assert "73% similar" in formatted


def test_format_related_issues_empty():
    """Test formatting empty list."""
    suggester = RelatedIssuesSuggester()
    formatted = suggester.format_related_issues([])

    assert formatted == ""


def test_format_related_issues_truncates_long_titles():
    """Test that long titles are truncated."""
    related = [
        {
            "issue_id": "AI-1820",
            "title": "This is a very long issue title that exceeds fifty characters and should be truncated",
            "url": "https://linear.app/ai/issue/AI-1820",
            "state": "Todo",
            "similarity": 0.73,
        },
    ]

    suggester = RelatedIssuesSuggester()
    formatted = suggester.format_related_issues(related)

    # Should truncate with ellipsis
    assert "..." in formatted
    assert len(formatted) < 200  # Sanity check


@pytest.mark.asyncio
async def test_add_to_briefing_context(mock_search_service):
    """Test finding related issues for briefing."""

    # Mock get_related_issues to return different results per issue
    async def mock_get_related(issue_id, **kwargs):
        if issue_id == "AI-1799":
            return [
                {
                    "issue_id": "AI-1820",
                    "title": "Related A",
                    "similarity": 0.73,
                },
            ]
        elif issue_id == "DMD-480":
            return [
                {
                    "issue_id": "DMD-500",
                    "title": "Related B",
                    "similarity": 0.68,
                },
            ]
        return []

    mock_search_service.find_similar_issues = AsyncMock(side_effect=mock_get_related)

    # Create suggester and patch get_related_issues
    suggester = RelatedIssuesSuggester()
    suggester.get_related_issues = AsyncMock(side_effect=mock_get_related)

    issues = [
        {"identifier": "AI-1799", "title": "Issue 1"},
        {"identifier": "DMD-480", "title": "Issue 2"},
        {"identifier": "CSM-93", "title": "Issue 3"},  # No related
    ]

    related_map = await suggester.add_to_briefing_context(
        issues, max_related_per_issue=2
    )

    # Should have related issues for 2 out of 3 issues
    assert len(related_map) == 2
    assert "AI-1799" in related_map
    assert "DMD-480" in related_map
    assert "CSM-93" not in related_map

    assert related_map["AI-1799"][0]["issue_id"] == "AI-1820"
    assert related_map["DMD-480"][0]["issue_id"] == "DMD-500"


@pytest.mark.asyncio
async def test_add_to_briefing_context_handles_errors(mock_search_service):
    """Test that briefing context handles errors gracefully."""

    # Mock get_related_issues to fail for some issues
    async def mock_get_related(issue_id, **kwargs):
        if issue_id == "AI-1799":
            raise Exception("API error")
        else:
            return [{"issue_id": "RELATED", "similarity": 0.7}]

    suggester = RelatedIssuesSuggester()
    suggester.get_related_issues = AsyncMock(side_effect=mock_get_related)

    issues = [
        {"identifier": "AI-1799", "title": "Failing issue"},
        {"identifier": "DMD-480", "title": "Working issue"},
    ]

    related_map = await suggester.add_to_briefing_context(issues)

    # Should continue with working issue despite error
    assert len(related_map) == 1
    assert "DMD-480" in related_map
    assert "AI-1799" not in related_map


def test_should_suggest_related_with_trigger_keyword():
    """Test should_suggest_related with trigger keywords."""
    assert should_suggest_related("what's related to AI-1799?", ["AI-1799"]) is True
    assert (
        should_suggest_related("show me similar issues to DMD-480", ["DMD-480"]) is True
    )
    assert should_suggest_related("what's connected to AI-1799", ["AI-1799"]) is True
    assert should_suggest_related("any dependencies for CSM-93?", ["CSM-93"]) is True


def test_should_suggest_related_single_short_query():
    """Test should_suggest_related with short single-issue query."""
    assert should_suggest_related("AI-1799", ["AI-1799"]) is True
    assert should_suggest_related("status of AI-1799", ["AI-1799"]) is True
    assert should_suggest_related("what about DMD-480?", ["DMD-480"]) is True


def test_should_suggest_related_multiple_issues():
    """Test should_suggest_related with multiple issues (should not suggest)."""
    # Multiple issues - don't overwhelm user
    assert (
        should_suggest_related("status of AI-1799 and DMD-480", ["AI-1799", "DMD-480"])
        is False
    )
    assert (
        should_suggest_related(
            "related to AI-1799 and DMD-480", ["AI-1799", "DMD-480"]
        )  # Even with keyword
        is False
    )


def test_should_suggest_related_long_query_without_trigger():
    """Test should_suggest_related with long query but no trigger (should not suggest)."""
    long_query = (
        "Can you explain the current status and timeline for issue AI-1799 in detail?"
    )
    assert should_suggest_related(long_query, ["AI-1799"]) is False


def test_should_suggest_related_no_issues():
    """Test should_suggest_related with no issues (should not suggest)."""
    assert should_suggest_related("what's related to this?", []) is False
    assert should_suggest_related("show me similar issues", []) is False
