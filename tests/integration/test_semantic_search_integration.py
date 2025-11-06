"""Integration tests for semantic search with real ChromaDB."""

import pytest
import asyncio
from linear_chief.intelligence.semantic_search import SemanticSearchService
from linear_chief.memory.vector_store import IssueVectorStore


class TestSemanticSearchIntegration:
    """Integration tests for semantic search with ChromaDB."""

    @pytest.fixture
    async def vector_store(self):
        """Create a fresh vector store for testing."""
        store = IssueVectorStore()
        yield store
        # Cleanup: Delete test issues
        await store.delete_issue("TEST-1")
        await store.delete_issue("TEST-2")
        await store.delete_issue("TEST-3")
        await store.delete_issue("TEST-4")

    @pytest.fixture
    def service(self):
        """Create SemanticSearchService instance."""
        return SemanticSearchService()

    @pytest.mark.asyncio
    async def test_find_similar_issues_real_embeddings(self, service, vector_store):
        """Test finding similar issues with real embeddings."""
        # Add test issues to vector store
        await vector_store.add_issue(
            issue_id="TEST-1",
            title="OAuth2 Authentication Implementation",
            description="Implement OAuth2 authentication flow with PKCE support",
            metadata={
                "state": "In Progress",
                "team_name": "AI",
                "url": "https://linear.app/test/TEST-1",
                "title": "OAuth2 Authentication Implementation",
                "description": "Implement OAuth2 authentication flow with PKCE support",
            },
        )

        await vector_store.add_issue(
            issue_id="TEST-2",
            title="OIDC Authentication Provider",
            description="Add OpenID Connect authentication provider support",
            metadata={
                "state": "Todo",
                "team_name": "AI",
                "url": "https://linear.app/test/TEST-2",
                "title": "OIDC Authentication Provider",
                "description": "Add OpenID Connect authentication provider support",
            },
        )

        await vector_store.add_issue(
            issue_id="TEST-3",
            title="Database Migration Script",
            description="Create script to migrate user data from PostgreSQL to MySQL",
            metadata={
                "state": "Done",
                "team_name": "Backend",
                "url": "https://linear.app/test/TEST-3",
                "title": "Database Migration Script",
                "description": "Create script to migrate user data from PostgreSQL to MySQL",
            },
        )

        await vector_store.add_issue(
            issue_id="TEST-4",
            title="Login Flow Refactor",
            description="Refactor authentication and login flow for better UX",
            metadata={
                "state": "In Progress",
                "team_name": "Frontend",
                "url": "https://linear.app/test/TEST-4",
                "title": "Login Flow Refactor",
                "description": "Refactor authentication and login flow for better UX",
            },
        )

        # Give ChromaDB a moment to index
        await asyncio.sleep(0.1)

        # Mock get_issue_context to return TEST-1
        from unittest.mock import AsyncMock, patch

        with patch.object(
            service, "get_issue_context", new_callable=AsyncMock
        ) as mock_context:
            mock_context.return_value = {
                "issue_id": "TEST-1",
                "title": "OAuth2 Authentication Implementation",
                "description": "Implement OAuth2 authentication flow with PKCE support",
                "state": "In Progress",
                "team": "AI",
                "url": "https://linear.app/test/TEST-1",
            }

            # Find similar issues
            results = await service.find_similar_issues(
                "TEST-1", limit=3, min_similarity=0.3
            )

            # Verify results
            assert len(results) > 0

            # TEST-2 should be most similar (both about authentication)
            issue_ids = [r["issue_id"] for r in results]
            assert "TEST-2" in issue_ids or "TEST-4" in issue_ids

            # TEST-3 should NOT be in results (different topic)
            # (unless similarity threshold is very low)
            if len(results) < 3:
                assert "TEST-3" not in issue_ids

            # Verify result structure
            for result in results:
                assert "issue_id" in result
                assert "title" in result
                assert "similarity" in result
                assert "url" in result
                assert "state" in result
                assert "team" in result
                assert 0.0 <= result["similarity"] <= 1.0

    @pytest.mark.asyncio
    async def test_search_by_text_real_embeddings(self, service, vector_store):
        """Test searching by text with real embeddings."""
        # Add test issues
        await vector_store.add_issue(
            issue_id="TEST-1",
            title="Fix authentication bug in login flow",
            description="Users unable to login with OAuth2",
            metadata={
                "state": "In Progress",
                "team_name": "AI",
                "url": "https://linear.app/test/TEST-1",
                "title": "Fix authentication bug in login flow",
                "description": "Users unable to login with OAuth2",
            },
        )

        await vector_store.add_issue(
            issue_id="TEST-2",
            title="Database performance optimization",
            description="Optimize slow queries in user table",
            metadata={
                "state": "Todo",
                "team_name": "Backend",
                "url": "https://linear.app/test/TEST-2",
                "title": "Database performance optimization",
                "description": "Optimize slow queries in user table",
            },
        )

        # Give ChromaDB a moment to index
        await asyncio.sleep(0.1)

        # Search for authentication-related issues
        results = await service.search_by_text(
            "authentication problems", limit=5, min_similarity=0.2
        )

        # Verify results
        assert len(results) > 0

        # TEST-1 should be in results (about authentication)
        issue_ids = [r["issue_id"] for r in results]
        assert "TEST-1" in issue_ids

        # Verify result structure
        for result in results:
            assert "issue_id" in result
            assert "title" in result
            assert "similarity" in result
            assert 0.0 <= result["similarity"] <= 1.0

    @pytest.mark.asyncio
    async def test_format_results_with_real_data(self, service, vector_store):
        """Test formatting results with real issue data."""
        # Add test issue
        await vector_store.add_issue(
            issue_id="TEST-1",
            title="OAuth2 Authentication",
            description="Implement OAuth2 flow",
            metadata={
                "state": "In Progress",
                "team_name": "AI",
                "url": "https://linear.app/test/TEST-1",
                "title": "OAuth2 Authentication",
                "description": "Implement OAuth2 flow",
            },
        )

        # Give ChromaDB a moment to index
        await asyncio.sleep(0.1)

        # Search
        results = await service.search_by_text(
            "authentication", limit=1, min_similarity=0.0
        )

        # Format results
        formatted = service.format_similarity_results(results, include_score=True)

        # Verify formatting
        assert "TEST-1" in formatted
        assert "OAuth2 Authentication" in formatted
        assert "State: In Progress" in formatted
        assert "Team: AI" in formatted
        assert "%" in formatted  # Similarity percentage

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, service, vector_store):
        """Test that similarity threshold filters results correctly."""
        # Add very different issues
        await vector_store.add_issue(
            issue_id="TEST-1",
            title="Authentication implementation",
            description="OAuth2 and OIDC support",
            metadata={
                "state": "In Progress",
                "team_name": "AI",
                "url": "https://linear.app/test/TEST-1",
                "title": "Authentication implementation",
                "description": "OAuth2 and OIDC support",
            },
        )

        await vector_store.add_issue(
            issue_id="TEST-2",
            title="Kitchen sink plumbing",
            description="Fix the leaky faucet in the office kitchen",
            metadata={
                "state": "Todo",
                "team_name": "Facilities",
                "url": "https://linear.app/test/TEST-2",
                "title": "Kitchen sink plumbing",
                "description": "Fix the leaky faucet in the office kitchen",
            },
        )

        # Give ChromaDB a moment to index
        await asyncio.sleep(0.1)

        # Search with high threshold - should filter out unrelated results
        results_high = await service.search_by_text(
            "authentication", limit=5, min_similarity=0.5
        )

        # Search with low threshold - might include more results
        results_low = await service.search_by_text(
            "authentication", limit=5, min_similarity=0.1
        )

        # High threshold should have fewer or equal results
        assert len(results_high) <= len(results_low)

        # All high threshold results should have high similarity
        for result in results_high:
            assert result["similarity"] >= 0.5
