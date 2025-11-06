"""Unit tests for duplicate detection functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from linear_chief.intelligence.duplicate_detector import DuplicateDetector


@pytest.fixture
def detector():
    """Create DuplicateDetector instance."""
    with patch("linear_chief.intelligence.duplicate_detector.IssueVectorStore"):
        return DuplicateDetector()


@pytest.fixture
def sample_issues():
    """Sample issue data for testing."""
    return [
        {
            "issue_id": "AI-1799",
            "title": "OAuth implementation",
            "state": "In Progress",
            "team": "AI",
            "url": "https://linear.app/ai/issue/AI-1799",
            "description": "Implement OAuth2 authentication flow",
        },
        {
            "issue_id": "AI-1820",
            "title": "OAuth2 auth flow",
            "state": "Todo",
            "team": "AI",
            "url": "https://linear.app/ai/issue/AI-1820",
            "description": "Add OAuth2 authentication",
        },
        {
            "issue_id": "DMD-480",
            "title": "Fix login bug",
            "state": "Done",
            "team": "DMD",
            "url": "https://linear.app/dmd/issue/DMD-480",
            "description": "Login flow broken",
        },
        {
            "issue_id": "DMD-485",
            "title": "Login flow broken",
            "state": "Todo",
            "team": "DMD",
            "url": "https://linear.app/dmd/issue/DMD-485",
            "description": "Users can't log in",
        },
    ]


@pytest.fixture
def sample_duplicate_pairs():
    """Sample duplicate pairs with similarity scores."""
    return [
        ("AI-1799", "AI-1820", 0.92),
        ("DMD-480", "DMD-485", 0.87),
    ]


class TestDuplicateDetector:
    """Test DuplicateDetector class."""

    def test_init(self):
        """Test DuplicateDetector initialization."""
        with patch("linear_chief.intelligence.duplicate_detector.IssueVectorStore"):
            detector = DuplicateDetector()
            assert detector.vector_store is not None

    @pytest.mark.asyncio
    async def test_find_duplicates_no_issues(self, detector):
        """Test find_duplicates with no issues in database."""
        with (
            patch(
                "linear_chief.intelligence.duplicate_detector.get_session_maker"
            ) as mock_session_maker,
            patch(
                "linear_chief.intelligence.duplicate_detector.get_db_session"
            ) as mock_db_session,
        ):
            # Mock empty database
            mock_session = MagicMock()
            mock_db_session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_repo = MagicMock()
            mock_repo.get_all_latest_snapshots.return_value = []

            with patch(
                "linear_chief.intelligence.duplicate_detector.IssueHistoryRepository",
                return_value=mock_repo,
            ):
                duplicates = await detector.find_duplicates()
                assert duplicates == []

    @pytest.mark.asyncio
    async def test_find_duplicates_with_active_filter(self, detector, sample_issues):
        """Test find_duplicates with active_only filter."""
        with (
            patch(
                "linear_chief.intelligence.duplicate_detector.get_session_maker"
            ) as mock_session_maker,
            patch(
                "linear_chief.intelligence.duplicate_detector.get_db_session"
            ) as mock_db_session,
        ):
            # Mock database with sample issues
            mock_session = MagicMock()
            mock_db_session.return_value = [mock_session]

            # Create mock snapshots
            mock_snapshots = []
            for issue in sample_issues:
                snapshot = MagicMock()
                snapshot.issue_id = issue["issue_id"]
                snapshot.title = issue["title"]
                snapshot.state = issue["state"]
                snapshot.team_name = issue["team"]
                snapshot.extra_metadata = {
                    "url": issue["url"],
                    "description": issue["description"],
                }
                mock_snapshots.append(snapshot)

            mock_repo = MagicMock()
            mock_repo.get_all_latest_snapshots.return_value = mock_snapshots

            with patch(
                "linear_chief.intelligence.duplicate_detector.IssueHistoryRepository",
                return_value=mock_repo,
            ):
                # Mock vector store search
                detector.vector_store.search_similar = AsyncMock(return_value=[])

                duplicates = await detector.find_duplicates(active_only=True)

                # Should filter out "Done" state (DMD-480)
                # Only AI-1799, AI-1820, DMD-485 should be scanned
                assert mock_repo.get_all_latest_snapshots.called

    @pytest.mark.asyncio
    async def test_check_issue_for_duplicates_not_found(self, detector):
        """Test check_issue_for_duplicates with non-existent issue."""
        with (
            patch(
                "linear_chief.intelligence.duplicate_detector.get_session_maker"
            ) as mock_session_maker,
            patch(
                "linear_chief.intelligence.duplicate_detector.get_db_session"
            ) as mock_db_session,
        ):
            # Mock empty result
            mock_session = MagicMock()
            mock_db_session.return_value = [mock_session]

            mock_repo = MagicMock()
            mock_repo.get_latest_snapshot.return_value = None

            with patch(
                "linear_chief.intelligence.duplicate_detector.IssueHistoryRepository",
                return_value=mock_repo,
            ):
                duplicates = await detector.check_issue_for_duplicates("AI-9999")
                assert duplicates == []

    @pytest.mark.asyncio
    async def test_check_issue_for_duplicates_with_results(self, detector):
        """Test check_issue_for_duplicates with similar issues found."""
        with (
            patch(
                "linear_chief.intelligence.duplicate_detector.get_session_maker"
            ) as mock_session_maker,
            patch(
                "linear_chief.intelligence.duplicate_detector.get_db_session"
            ) as mock_db_session,
        ):
            # Mock issue snapshot
            mock_session = MagicMock()
            mock_db_session.return_value = [mock_session]

            mock_snapshot = MagicMock()
            mock_snapshot.issue_id = "AI-1799"
            mock_snapshot.title = "OAuth implementation"
            mock_snapshot.state = "In Progress"
            mock_snapshot.team_name = "AI"
            mock_snapshot.extra_metadata = {
                "url": "https://linear.app/ai/issue/AI-1799",
                "description": "Implement OAuth2 authentication flow",
            }

            mock_repo = MagicMock()
            mock_repo.get_latest_snapshot.return_value = mock_snapshot

            with patch(
                "linear_chief.intelligence.duplicate_detector.IssueHistoryRepository",
                return_value=mock_repo,
            ):
                # Mock vector store search with similar issue
                detector.vector_store.search_similar = AsyncMock(
                    return_value=[
                        {
                            "issue_id": "AI-1820",
                            "document": "OAuth2 auth flow\n\nAdd OAuth2 authentication",
                            "metadata": {},
                            "distance": 0.08,  # 92% similar (1 - 0.08)
                        }
                    ]
                )

                duplicates = await detector.check_issue_for_duplicates(
                    "AI-1799", min_similarity=0.85
                )

                assert len(duplicates) == 1
                assert duplicates[0]["issue_a"] == "AI-1799"
                assert duplicates[0]["issue_b"] == "AI-1820"
                assert duplicates[0]["similarity"] >= 0.85

    @pytest.mark.asyncio
    async def test_check_issue_filters_by_similarity(self, detector):
        """Test that low similarity results are filtered out."""
        with (
            patch(
                "linear_chief.intelligence.duplicate_detector.get_session_maker"
            ) as mock_session_maker,
            patch(
                "linear_chief.intelligence.duplicate_detector.get_db_session"
            ) as mock_db_session,
        ):
            # Mock issue snapshot
            mock_session = MagicMock()
            mock_db_session.return_value = [mock_session]

            mock_snapshot = MagicMock()
            mock_snapshot.issue_id = "AI-1799"
            mock_snapshot.title = "OAuth implementation"
            mock_snapshot.state = "In Progress"
            mock_snapshot.team_name = "AI"
            mock_snapshot.extra_metadata = {
                "url": "https://linear.app/ai/issue/AI-1799",
                "description": "Implement OAuth2 authentication flow",
            }

            mock_repo = MagicMock()
            mock_repo.get_latest_snapshot.return_value = mock_snapshot

            with patch(
                "linear_chief.intelligence.duplicate_detector.IssueHistoryRepository",
                return_value=mock_repo,
            ):
                # Mock vector store with low similarity result
                detector.vector_store.search_similar = AsyncMock(
                    return_value=[
                        {
                            "issue_id": "AI-1820",
                            "document": "Completely different issue",
                            "metadata": {},
                            "distance": 0.5,  # 50% similar - below threshold
                        }
                    ]
                )

                duplicates = await detector.check_issue_for_duplicates(
                    "AI-1799", min_similarity=0.85
                )

                # Should be filtered out
                assert len(duplicates) == 0

    def test_generate_merge_suggestion_in_progress_vs_todo(self, detector):
        """Test suggestion generation for In Progress vs Todo."""
        issue_a = {
            "issue_id": "AI-1799",
            "state": "In Progress",
        }
        issue_b = {
            "issue_id": "AI-1820",
            "state": "Todo",
        }

        suggestion = detector._generate_merge_suggestion(issue_a, issue_b, 0.92)

        assert "AI-1820" in suggestion
        assert "AI-1799" in suggestion
        assert "92%" in suggestion
        assert "merging" in suggestion.lower()

    def test_generate_merge_suggestion_done_vs_todo(self, detector):
        """Test suggestion generation for Done vs Todo."""
        issue_a = {
            "issue_id": "DMD-480",
            "state": "Done",
        }
        issue_b = {
            "issue_id": "DMD-485",
            "state": "Todo",
        }

        suggestion = detector._generate_merge_suggestion(issue_a, issue_b, 0.87)

        assert "DMD-485" in suggestion
        # Since DMD-480 is Done (priority 0) and DMD-485 is Todo (priority 2),
        # it should suggest merging DMD-480 into DMD-485
        assert "87%" in suggestion

    def test_generate_merge_suggestion_equal_states(self, detector):
        """Test suggestion generation for equal state priorities."""
        issue_a = {
            "issue_id": "AI-100",
            "state": "Todo",
        }
        issue_b = {
            "issue_id": "AI-200",
            "state": "Todo",
        }

        suggestion = detector._generate_merge_suggestion(issue_a, issue_b, 0.90)

        assert "AI-100" in suggestion
        assert "AI-200" in suggestion
        assert "duplicates" in suggestion.lower()

    def test_format_duplicate_report_empty(self, detector):
        """Test formatting empty duplicate list."""
        formatted = detector.format_duplicate_report([])
        assert formatted == ""

    def test_format_duplicate_report_with_duplicates(self, detector):
        """Test formatting duplicate report with results."""
        duplicates = [
            {
                "issue_a": "AI-1799",
                "issue_b": "AI-1820",
                "similarity": 0.92,
                "title_a": "OAuth implementation",
                "title_b": "OAuth2 auth flow",
                "state_a": "In Progress",
                "state_b": "Todo",
                "team": "AI",
                "url_a": "https://linear.app/ai/issue/AI-1799",
                "url_b": "https://linear.app/ai/issue/AI-1820",
                "suggested_action": "Consider merging AI-1820 into AI-1799 (92% similar)",
            }
        ]

        formatted = detector.format_duplicate_report(duplicates)

        assert "AI-1799" in formatted
        assert "AI-1820" in formatted
        assert "92%" in formatted
        assert "OAuth implementation" in formatted
        assert "OAuth2 auth flow" in formatted
        assert "In Progress" in formatted
        assert "Todo" in formatted

    def test_format_duplicate_report_without_urls(self, detector):
        """Test formatting duplicate report when URLs are missing."""
        duplicates = [
            {
                "issue_a": "AI-1799",
                "issue_b": "AI-1820",
                "similarity": 0.92,
                "title_a": "OAuth implementation",
                "title_b": "OAuth2 auth flow",
                "state_a": "In Progress",
                "state_b": "Todo",
                "team": "AI",
                "url_a": None,
                "url_b": None,
                "suggested_action": "Consider merging AI-1820 into AI-1799 (92% similar)",
            }
        ]

        formatted = detector.format_duplicate_report(duplicates)

        # Should still include issue IDs without links
        assert "AI-1799" in formatted
        assert "AI-1820" in formatted
        # Should NOT have markdown link syntax when URLs missing
        assert "[**AI-1799**]" not in formatted or "](http" not in formatted

    @pytest.mark.asyncio
    async def test_scan_deduplicates_pairs(self, detector, sample_issues):
        """Test that scanning doesn't return both (A,B) and (B,A)."""

        # Mock vector store to return symmetric matches
        async def mock_search(query, limit):
            # If searching for AI-1799, return AI-1820
            if "OAuth implementation" in query:
                return [
                    {
                        "issue_id": "AI-1820",
                        "distance": 0.08,
                    }
                ]
            # If searching for AI-1820, return AI-1799
            elif "OAuth2 auth flow" in query:
                return [
                    {
                        "issue_id": "AI-1799",
                        "distance": 0.08,
                    }
                ]
            return []

        detector.vector_store.search_similar = mock_search

        # Scan only the two OAuth issues
        oauth_issues = [
            sample_issues[0],  # AI-1799
            sample_issues[1],  # AI-1820
        ]

        pairs = await detector._scan_all_issues_for_duplicates(oauth_issues, 0.85)

        # Should only have one pair, not two
        assert len(pairs) == 1
        # The pair should be sorted
        assert pairs[0][0] < pairs[0][1]  # Alphabetically sorted

    @pytest.mark.asyncio
    async def test_scan_skips_self_matches(self, detector, sample_issues):
        """Test that scanning skips self-matches."""

        # Mock vector store to return self-match
        async def mock_search(query, limit):
            if "OAuth implementation" in query:
                return [
                    {
                        "issue_id": "AI-1799",  # Self-match
                        "distance": 0.0,
                    }
                ]
            return []

        detector.vector_store.search_similar = mock_search

        pairs = await detector._scan_all_issues_for_duplicates([sample_issues[0]], 0.85)

        # Should not include self-match
        assert len(pairs) == 0


class TestDuplicateDetectorIntegration:
    """Integration tests for DuplicateDetector (requires ChromaDB)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_duplicate_detection_workflow(self):
        """Test complete duplicate detection workflow with real vector store."""
        # This test requires ChromaDB and sentence-transformers
        # Skip if not in integration test mode
        pytest.skip("Integration test - requires ChromaDB setup")
