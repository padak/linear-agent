"""Unit tests for semantic search service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from linear_chief.intelligence.semantic_search import (
    SemanticSearchService,
    calculate_similarity_percentage,
)


class TestSimilarityCalculation:
    """Test similarity percentage calculation."""

    def test_identical_vectors(self):
        """Test distance of 0 gives 100% similarity."""
        assert calculate_similarity_percentage(0.0) == 100.0

    def test_opposite_vectors(self):
        """Test distance of 2 gives 0% similarity."""
        assert calculate_similarity_percentage(2.0) == 0.0

    def test_midpoint_similarity(self):
        """Test distance of 1 gives 50% similarity."""
        assert calculate_similarity_percentage(1.0) == 50.0

    def test_75_percent_similarity(self):
        """Test distance of 0.5 gives 75% similarity."""
        assert calculate_similarity_percentage(0.5) == 75.0

    def test_90_percent_similarity(self):
        """Test distance of 0.2 gives 90% similarity."""
        assert calculate_similarity_percentage(0.2) == 90.0

    def test_negative_distance_clamped(self):
        """Test negative distance is clamped to 0."""
        assert calculate_similarity_percentage(-0.5) == 100.0

    def test_large_distance_clamped(self):
        """Test distance > 2 is clamped to 2."""
        assert calculate_similarity_percentage(3.0) == 0.0


class TestSemanticSearchService:
    """Test SemanticSearchService class."""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock IssueVectorStore."""
        with patch(
            "linear_chief.intelligence.semantic_search.IssueVectorStore"
        ) as mock:
            # Make search_similar async
            mock.return_value.search_similar = AsyncMock()
            yield mock.return_value

    @pytest.fixture
    def service(self, mock_vector_store):
        """Create SemanticSearchService instance with mocked dependencies."""
        return SemanticSearchService()

    @pytest.mark.asyncio
    async def test_find_similar_issues_success(self, service, mock_vector_store):
        """Test finding similar issues successfully."""
        # Mock get_issue_context
        with patch.object(
            service, "get_issue_context", new_callable=AsyncMock
        ) as mock_context:
            mock_context.return_value = {
                "issue_id": "AI-1799",
                "title": "OAuth2 Authentication",
                "description": "Implement OAuth2 flow",
                "state": "In Progress",
                "team": "AI",
                "url": "https://linear.app/ai/AI-1799",
            }

            # Mock vector store search
            mock_vector_store.search_similar.return_value = [
                {
                    "issue_id": "AI-1799",  # Self-match (should be filtered)
                    "distance": 0.0,
                    "metadata": {
                        "title": "OAuth2 Authentication",
                        "state": "In Progress",
                        "team_name": "AI",
                        "url": "https://linear.app/ai/AI-1799",
                    },
                },
                {
                    "issue_id": "AI-1820",
                    "distance": 0.26,  # 87% similarity
                    "metadata": {
                        "title": "OIDC Authentication",
                        "state": "Todo",
                        "team_name": "AI",
                        "url": "https://linear.app/ai/AI-1820",
                    },
                },
                {
                    "issue_id": "AI-1805",
                    "distance": 0.54,  # 73% similarity
                    "metadata": {
                        "title": "Login flow refactor",
                        "state": "Done",
                        "team_name": "AI",
                        "url": "https://linear.app/ai/AI-1805",
                    },
                },
            ]

            # Execute
            results = await service.find_similar_issues("AI-1799", limit=5)

            # Verify
            assert len(results) == 2  # Excludes self-match
            assert results[0]["issue_id"] == "AI-1820"
            assert results[0]["similarity"] == pytest.approx(0.87, abs=0.01)
            assert results[0]["title"] == "OIDC Authentication"
            assert results[1]["issue_id"] == "AI-1805"
            assert results[1]["similarity"] == pytest.approx(0.73, abs=0.01)

    @pytest.mark.asyncio
    async def test_find_similar_issues_min_similarity_filter(
        self, service, mock_vector_store
    ):
        """Test minimum similarity threshold filtering."""
        with patch.object(
            service, "get_issue_context", new_callable=AsyncMock
        ) as mock_context:
            mock_context.return_value = {
                "issue_id": "AI-1799",
                "title": "OAuth2 Authentication",
                "description": "Implement OAuth2 flow",
                "state": "In Progress",
                "team": "AI",
                "url": "https://linear.app/ai/AI-1799",
            }

            # Mock results with varying similarity
            mock_vector_store.search_similar.return_value = [
                {
                    "issue_id": "AI-1820",
                    "distance": 0.26,  # 87% similarity - above threshold
                    "metadata": {
                        "title": "OIDC Auth",
                        "state": "Todo",
                        "team_name": "AI",
                        "url": "https://linear.app/ai/AI-1820",
                    },
                },
                {
                    "issue_id": "AI-1805",
                    "distance": 1.2,  # 40% similarity - below 50% threshold
                    "metadata": {
                        "title": "Different issue",
                        "state": "Done",
                        "team_name": "AI",
                        "url": "https://linear.app/ai/AI-1805",
                    },
                },
            ]

            # Execute with 50% min_similarity
            results = await service.find_similar_issues(
                "AI-1799", limit=5, min_similarity=0.5
            )

            # Verify - only high similarity result returned
            assert len(results) == 1
            assert results[0]["issue_id"] == "AI-1820"

    @pytest.mark.asyncio
    async def test_find_similar_issues_not_found(self, service):
        """Test finding similar issues when source issue not found."""
        with patch.object(
            service, "get_issue_context", new_callable=AsyncMock
        ) as mock_context:
            mock_context.return_value = None

            # Execute and verify exception
            with pytest.raises(ValueError, match="Issue AI-9999 not found"):
                await service.find_similar_issues("AI-9999")

    @pytest.mark.asyncio
    async def test_search_by_text_success(self, service, mock_vector_store):
        """Test searching by natural language query."""
        # Mock vector store search
        mock_vector_store.search_similar.return_value = [
            {
                "issue_id": "AI-1820",
                "distance": 0.4,  # 80% similarity
                "metadata": {
                    "title": "OAuth2 implementation",
                    "state": "In Progress",
                    "team_name": "AI",
                    "url": "https://linear.app/ai/AI-1820",
                },
            },
            {
                "issue_id": "AI-1799",
                "distance": 0.6,  # 70% similarity
                "metadata": {
                    "title": "Authentication refactor",
                    "state": "Todo",
                    "team_name": "AI",
                    "url": "https://linear.app/ai/AI-1799",
                },
            },
        ]

        # Execute
        results = await service.search_by_text("authentication issues", limit=5)

        # Verify
        assert len(results) == 2
        assert results[0]["issue_id"] == "AI-1820"
        assert results[0]["similarity"] == pytest.approx(0.80, abs=0.01)
        assert results[1]["issue_id"] == "AI-1799"
        assert results[1]["similarity"] == pytest.approx(0.70, abs=0.01)

        # Verify vector store was called correctly
        mock_vector_store.search_similar.assert_called_once_with(
            query="authentication issues", limit=10, filter_metadata=None
        )

    @pytest.mark.asyncio
    async def test_search_by_text_with_filters(self, service, mock_vector_store):
        """Test searching with metadata filters."""
        mock_vector_store.search_similar.return_value = []

        # Execute with filters
        filters = {"team_name": "AI", "state": "In Progress"}
        await service.search_by_text("performance", limit=5, filters=filters)

        # Verify filters were passed
        mock_vector_store.search_similar.assert_called_once_with(
            query="performance", limit=10, filter_metadata=filters
        )

    @pytest.mark.asyncio
    async def test_search_by_text_min_similarity_filter(
        self, service, mock_vector_store
    ):
        """Test minimum similarity filtering in text search."""
        # Mock results with varying similarity
        mock_vector_store.search_similar.return_value = [
            {
                "issue_id": "AI-1820",
                "distance": 0.4,  # 80% similarity - above 30% threshold
                "metadata": {
                    "title": "High match",
                    "state": "Todo",
                    "team_name": "AI",
                    "url": "https://linear.app/ai/AI-1820",
                },
            },
            {
                "issue_id": "AI-1799",
                "distance": 1.6,  # 20% similarity - below 30% threshold
                "metadata": {
                    "title": "Low match",
                    "state": "Todo",
                    "team_name": "AI",
                    "url": "https://linear.app/ai/AI-1799",
                },
            },
        ]

        # Execute with 30% min_similarity
        results = await service.search_by_text(
            "test query", limit=5, min_similarity=0.3
        )

        # Verify only high similarity result
        assert len(results) == 1
        assert results[0]["issue_id"] == "AI-1820"

    @pytest.mark.asyncio
    async def test_get_issue_context_from_db(self):
        """Test getting issue context from database."""
        # Need to create a fresh service with properly mocked dependencies
        with (
            patch("linear_chief.intelligence.semantic_search.IssueVectorStore"),
            patch(
                "linear_chief.intelligence.semantic_search.get_session_maker"
            ) as mock_session_maker,
            patch(
                "linear_chief.intelligence.semantic_search.get_db_session"
            ) as mock_db_session,
            patch(
                "linear_chief.intelligence.semantic_search.IssueHistoryRepository"
            ) as mock_repo,
        ):

            # Mock database snapshot
            mock_snapshot = MagicMock()
            mock_snapshot.title = "OAuth2 Auth"
            mock_snapshot.state = "In Progress"
            mock_snapshot.team_name = "AI"
            mock_snapshot.extra_metadata = {
                "description": "Implement OAuth2",
                "url": "https://linear.app/ai/AI-1799",
            }

            # Mock repository
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_issue_snapshot_by_identifier.return_value = (
                mock_snapshot
            )
            mock_repo.return_value = mock_repo_instance

            # Mock session context manager
            mock_session = MagicMock()
            mock_db_session.return_value = [mock_session]

            # Create service and execute
            service = SemanticSearchService()
            result = await service.get_issue_context("AI-1799")

            # Verify
            assert result is not None
            assert result["issue_id"] == "AI-1799"
            assert result["title"] == "OAuth2 Auth"
            assert result["description"] == "Implement OAuth2"
            assert result["state"] == "In Progress"
            assert result["team"] == "AI"
            assert result["url"] == "https://linear.app/ai/AI-1799"

    @pytest.mark.asyncio
    async def test_get_issue_context_from_linear_api(self, service):
        """Test getting issue context from Linear API when not in DB."""
        with (
            patch(
                "linear_chief.intelligence.semantic_search.get_session_maker"
            ) as mock_session_maker,
            patch(
                "linear_chief.intelligence.semantic_search.get_db_session"
            ) as mock_db_session,
            patch(
                "linear_chief.intelligence.semantic_search.IssueHistoryRepository"
            ) as mock_repo,
            patch(
                "linear_chief.intelligence.semantic_search.LinearClient"
            ) as mock_client,
        ):

            # Mock empty database
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_issue_snapshot_by_identifier.return_value = None
            mock_repo.return_value = mock_repo_instance

            mock_session = MagicMock()
            mock_db_session.return_value.__enter__.return_value = mock_session

            # Mock Linear API response
            mock_client_instance = MagicMock()
            mock_client_instance.get_issue_by_identifier = AsyncMock(
                return_value={
                    "identifier": "AI-1799",
                    "title": "OAuth2 Auth",
                    "description": "Implement OAuth2",
                    "state": {"name": "In Progress"},
                    "team": {"name": "AI"},
                    "url": "https://linear.app/ai/AI-1799",
                }
            )
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Execute
            result = await service.get_issue_context("AI-1799")

            # Verify
            assert result is not None
            assert result["issue_id"] == "AI-1799"
            assert result["title"] == "OAuth2 Auth"
            assert result["description"] == "Implement OAuth2"

    def test_format_similarity_results_with_score(self, service):
        """Test formatting results with similarity scores."""
        results = [
            {
                "issue_id": "AI-1820",
                "title": "OAuth2 implementation",
                "similarity": 0.87,
                "url": "https://linear.app/ai/AI-1820",
                "state": "In Progress",
                "team": "AI",
            },
            {
                "issue_id": "AI-1799",
                "title": "Auth refactor",
                "similarity": 0.73,
                "url": "https://linear.app/ai/AI-1799",
                "state": "Done",
                "team": "AI",
            },
        ]

        formatted = service.format_similarity_results(results, include_score=True)

        # Verify formatting
        assert "Found 2 similar issues:" in formatted
        assert "[**AI-1820**](https://linear.app/ai/AI-1820)" in formatted
        assert "OAuth2 implementation (87% similar)" in formatted
        assert "State: In Progress | Team: AI" in formatted
        assert "[**AI-1799**](https://linear.app/ai/AI-1799)" in formatted
        assert "Auth refactor (73% similar)" in formatted

    def test_format_similarity_results_without_score(self, service):
        """Test formatting results without similarity scores."""
        results = [
            {
                "issue_id": "AI-1820",
                "title": "OAuth2 implementation",
                "similarity": 0.87,
                "url": "https://linear.app/ai/AI-1820",
                "state": "In Progress",
                "team": "AI",
            }
        ]

        formatted = service.format_similarity_results(results, include_score=False)

        # Verify no similarity percentage shown
        assert "87% similar" not in formatted
        assert "OAuth2 implementation" in formatted
        assert "State: In Progress | Team: AI" in formatted

    def test_format_similarity_results_empty(self, service):
        """Test formatting empty results."""
        formatted = service.format_similarity_results([])
        assert formatted == "No similar issues found."

    def test_format_similarity_results_no_url(self, service):
        """Test formatting results without URLs."""
        results = [
            {
                "issue_id": "AI-1820",
                "title": "OAuth2 implementation",
                "similarity": 0.87,
                "url": "",  # No URL
                "state": "In Progress",
                "team": "AI",
            }
        ]

        formatted = service.format_similarity_results(results)

        # Verify issue ID is shown as bold text (not link)
        assert "**AI-1820**" in formatted
        assert "[**AI-1820**]" not in formatted  # Not a markdown link
