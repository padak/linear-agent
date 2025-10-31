"""Unit tests for memory layer (MemoryManager and IssueVectorStore)."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.linear_chief.memory import IssueVectorStore, MemoryManager


class TestMemoryManager:
    """Test suite for MemoryManager."""

    @pytest.fixture
    def memory_manager_no_api_key(self):
        """Create MemoryManager without API key (in-memory mode)."""
        with patch("src.linear_chief.memory.mem0_wrapper.MEM0_API_KEY", ""):
            return MemoryManager()

    @pytest.mark.asyncio
    async def test_add_briefing_context_in_memory(self, memory_manager_no_api_key):
        """Test adding briefing context in in-memory mode."""
        briefing = "Test briefing content"
        metadata = {"issue_count": 5}

        await memory_manager_no_api_key.add_briefing_context(briefing, metadata)

        # Verify in-memory storage
        assert len(memory_manager_no_api_key._memory_store) == 1
        stored = memory_manager_no_api_key._memory_store[0]
        assert stored["content"] == briefing
        assert stored["metadata"]["issue_count"] == 5
        assert stored["type"] == "briefing"

    @pytest.mark.asyncio
    async def test_get_agent_context_in_memory(self, memory_manager_no_api_key):
        """Test retrieving agent context in in-memory mode."""
        # Add test data
        await memory_manager_no_api_key.add_briefing_context("Recent briefing", {})
        await memory_manager_no_api_key.add_user_preference("Old preference", {})

        # Mock old timestamp for one item
        memory_manager_no_api_key._memory_store[0]["metadata"]["timestamp"] = (
            datetime.utcnow() - timedelta(days=10)
        ).isoformat()

        # Get context from last 7 days
        context = await memory_manager_no_api_key.get_agent_context(days=7)

        # Should filter out old briefing
        assert len(context) == 0  # Old briefing is 10 days old

    @pytest.mark.asyncio
    async def test_add_user_preference_in_memory(self, memory_manager_no_api_key):
        """Test adding user preference in in-memory mode."""
        preference = "Focus on blocking issues"
        metadata = {"priority": "high"}

        await memory_manager_no_api_key.add_user_preference(preference, metadata)

        # Verify in-memory storage
        preferences = [
            item for item in memory_manager_no_api_key._memory_store if item["type"] == "preference"
        ]
        assert len(preferences) == 1
        assert preferences[0]["content"] == preference

    @pytest.mark.asyncio
    async def test_get_user_preferences_in_memory(self, memory_manager_no_api_key):
        """Test retrieving user preferences in in-memory mode."""
        await memory_manager_no_api_key.add_user_preference("Pref 1", {})
        await memory_manager_no_api_key.add_user_preference("Pref 2", {})
        await memory_manager_no_api_key.add_briefing_context("Briefing", {})

        preferences = await memory_manager_no_api_key.get_user_preferences()

        # Should only return preferences, not briefings
        assert len(preferences) == 2


class TestIssueVectorStore:
    """Test suite for IssueVectorStore."""

    @pytest.fixture
    def mock_chroma_client(self):
        """Mock ChromaDB client."""
        with patch("src.linear_chief.memory.vector_store.chromadb.PersistentClient") as mock_client:
            mock_collection = MagicMock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            yield mock_client, mock_collection

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer model."""
        with patch("src.linear_chief.memory.vector_store.SentenceTransformer") as mock_model:
            mock_instance = MagicMock()
            mock_instance.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
            mock_model.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_add_issue(self, mock_chroma_client, mock_sentence_transformer):
        """Test adding an issue to vector store."""
        _, mock_collection = mock_chroma_client

        store = IssueVectorStore()

        await store.add_issue(
            issue_id="PROJ-123",
            title="Test Issue",
            description="Test description",
            metadata={"status": "In Progress"},
        )

        # Verify add was called
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[1]
        assert call_args["ids"] == ["PROJ-123"]
        assert call_args["metadatas"] == [{"status": "In Progress"}]

    @pytest.mark.asyncio
    async def test_search_similar(self, mock_chroma_client, mock_sentence_transformer):
        """Test searching for similar issues."""
        _, mock_collection = mock_chroma_client

        # Mock query response
        mock_collection.query.return_value = {
            "ids": [["PROJ-456", "PROJ-789"]],
            "documents": [["Issue 456 text", "Issue 789 text"]],
            "metadatas": [[{"status": "Todo"}, {"status": "Done"}]],
            "distances": [[0.1, 0.3]],
        }

        store = IssueVectorStore()
        results = await store.search_similar("test query", limit=2)

        assert len(results) == 2
        assert results[0]["issue_id"] == "PROJ-456"
        assert results[0]["distance"] == 0.1
        assert results[1]["issue_id"] == "PROJ-789"

    @pytest.mark.asyncio
    async def test_get_issue_embedding(self, mock_chroma_client, mock_sentence_transformer):
        """Test retrieving issue embedding."""
        _, mock_collection = mock_chroma_client

        # Mock get response
        mock_collection.get.return_value = {
            "ids": ["PROJ-123"],
            "embeddings": [[0.5, 0.6, 0.7]],
        }

        store = IssueVectorStore()
        embedding = await store.get_issue_embedding("PROJ-123")

        assert embedding == [0.5, 0.6, 0.7]

    @pytest.mark.asyncio
    async def test_get_issue_embedding_not_found(self, mock_chroma_client, mock_sentence_transformer):
        """Test retrieving embedding for non-existent issue."""
        _, mock_collection = mock_chroma_client

        # Mock empty response
        mock_collection.get.return_value = {"ids": [], "embeddings": []}

        store = IssueVectorStore()
        embedding = await store.get_issue_embedding("NONEXISTENT")

        assert embedding is None

    @pytest.mark.asyncio
    async def test_delete_issue(self, mock_chroma_client, mock_sentence_transformer):
        """Test deleting an issue from vector store."""
        _, mock_collection = mock_chroma_client

        store = IssueVectorStore()
        await store.delete_issue("PROJ-123")

        mock_collection.delete.assert_called_once_with(ids=["PROJ-123"])

    def test_get_stats(self, mock_chroma_client, mock_sentence_transformer):
        """Test getting vector store statistics."""
        _, mock_collection = mock_chroma_client
        mock_collection.count.return_value = 42

        store = IssueVectorStore()
        stats = store.get_stats()

        assert stats["total_issues"] == 42
        assert "embedding_model" in stats
        assert "storage_path" in stats
