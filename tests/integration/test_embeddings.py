"""Integration tests for embeddings and semantic search with real ChromaDB."""

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest

from src.linear_chief.memory import IssueVectorStore


@pytest.fixture
def temp_chromadb_path(monkeypatch):
    """Create temporary ChromaDB directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("src.linear_chief.memory.vector_store.CHROMADB_PATH", temp_dir)
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_issues():
    """Sample Linear issues for testing."""
    return [
        {
            "id": "PROJ-101",
            "title": "Fix authentication bug in login form",
            "description": "Users are unable to log in with valid credentials. The auth service returns 401 errors.",
            "metadata": {"status": "In Progress", "priority": "High"},
        },
        {
            "id": "PROJ-102",
            "title": "Add user authentication to API endpoints",
            "description": "Implement JWT-based authentication for all API routes to secure access.",
            "metadata": {"status": "Todo", "priority": "Medium"},
        },
        {
            "id": "PROJ-103",
            "title": "Refactor database schema for better performance",
            "description": "Optimize database indexes and table structure to reduce query latency.",
            "metadata": {"status": "In Progress", "priority": "Low"},
        },
        {
            "id": "PROJ-104",
            "title": "Implement caching layer with Redis",
            "description": "Add Redis caching to reduce database load and improve API response times.",
            "metadata": {"status": "Todo", "priority": "Medium"},
        },
        {
            "id": "PROJ-105",
            "title": "Fix broken login button on mobile",
            "description": "The login button doesn't work on mobile devices due to CSS issue.",
            "metadata": {"status": "Blocked", "priority": "High"},
        },
    ]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_and_retrieve_embeddings(temp_chromadb_path, sample_issues):
    """Test adding issues and retrieving their embeddings."""
    store = IssueVectorStore()

    # Add all sample issues
    for issue in sample_issues:
        await store.add_issue(
            issue_id=issue["id"],
            title=issue["title"],
            description=issue["description"],
            metadata=issue["metadata"],
        )

    # Retrieve embedding for one issue
    embedding = await store.get_issue_embedding("PROJ-101")

    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # all-MiniLM-L6-v2 embedding dimension

    # Check stats
    stats = store.get_stats()
    assert stats["total_issues"] == 5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_semantic_search_similarity(temp_chromadb_path, sample_issues):
    """Test semantic search finds similar issues."""
    store = IssueVectorStore()

    # Add all sample issues
    for issue in sample_issues:
        await store.add_issue(
            issue_id=issue["id"],
            title=issue["title"],
            description=issue["description"],
            metadata=issue["metadata"],
        )

    # Search for authentication-related issues
    results = await store.search_similar("authentication and login problems", limit=3)

    assert len(results) > 0
    assert len(results) <= 3

    # Top result should be authentication-related
    top_result_ids = [r["issue_id"] for r in results]
    assert "PROJ-101" in top_result_ids or "PROJ-102" in top_result_ids or "PROJ-105" in top_result_ids

    # Results should have expected fields
    for result in results:
        assert "issue_id" in result
        assert "document" in result
        assert "metadata" in result
        assert "distance" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_semantic_search_with_metadata_filter(temp_chromadb_path, sample_issues):
    """Test semantic search with metadata filtering."""
    store = IssueVectorStore()

    # Add all sample issues
    for issue in sample_issues:
        await store.add_issue(
            issue_id=issue["id"],
            title=issue["title"],
            description=issue["description"],
            metadata=issue["metadata"],
        )

    # Search for high priority issues only
    results = await store.search_similar(
        "urgent problems",
        limit=5,
        filter_metadata={"priority": "High"},
    )

    # All results should be high priority
    for result in results:
        assert result["metadata"]["priority"] == "High"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_issue_from_vector_store(temp_chromadb_path, sample_issues):
    """Test deleting an issue from vector store."""
    store = IssueVectorStore()

    # Add one issue
    issue = sample_issues[0]
    await store.add_issue(
        issue_id=issue["id"],
        title=issue["title"],
        description=issue["description"],
        metadata=issue["metadata"],
    )

    # Verify it exists
    embedding = await store.get_issue_embedding(issue["id"])
    assert embedding is not None

    # Delete it
    await store.delete_issue(issue["id"])

    # Verify it's gone
    embedding_after = await store.get_issue_embedding(issue["id"])
    assert embedding_after is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_semantic_search_finds_relevant_results(temp_chromadb_path, sample_issues):
    """Test that semantic search finds semantically relevant results."""
    store = IssueVectorStore()

    # Add all sample issues
    for issue in sample_issues:
        await store.add_issue(
            issue_id=issue["id"],
            title=issue["title"],
            description=issue["description"],
            metadata=issue["metadata"],
        )

    # Search for performance-related issues
    results = await store.search_similar("slow queries and performance optimization", limit=2)

    assert len(results) > 0

    # Should find database or caching issues (PROJ-103 or PROJ-104)
    top_ids = [r["issue_id"] for r in results]
    assert "PROJ-103" in top_ids or "PROJ-104" in top_ids


@pytest.mark.asyncio
@pytest.mark.integration
async def test_persistence_across_instances(temp_chromadb_path, sample_issues):
    """Test that ChromaDB persists data across IssueVectorStore instances."""
    # First instance: add issues
    store1 = IssueVectorStore()
    issue = sample_issues[0]
    await store1.add_issue(
        issue_id=issue["id"],
        title=issue["title"],
        description=issue["description"],
        metadata=issue["metadata"],
    )

    # Second instance: should retrieve the same data
    store2 = IssueVectorStore()
    embedding = await store2.get_issue_embedding(issue["id"])

    assert embedding is not None
    assert len(embedding) == 384


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embedding_generation_consistency(temp_chromadb_path):
    """Test that same text generates consistent embeddings."""
    store = IssueVectorStore()

    # Add same issue twice with different IDs
    await store.add_issue(
        issue_id="TEST-1",
        title="Identical Issue",
        description="Same description",
        metadata={},
    )

    await store.add_issue(
        issue_id="TEST-2",
        title="Identical Issue",
        description="Same description",
        metadata={},
    )

    # Retrieve both embeddings
    emb1 = await store.get_issue_embedding("TEST-1")
    emb2 = await store.get_issue_embedding("TEST-2")

    # They should be identical (same text → same embedding)
    assert emb1 == emb2
