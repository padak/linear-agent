"""ChromaDB vector store for issue embeddings and semantic search."""

import asyncio
import logging
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from ..config import CHROMADB_PATH, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class IssueVectorStore:
    """Manages issue embeddings and semantic search using ChromaDB.

    Stores Linear issue embeddings for similarity search, duplicate detection,
    and semantic clustering. Uses sentence-transformers for embedding generation.
    """

    def __init__(self) -> None:
        """Initialize ChromaDB client and embedding model."""
        try:
            # Initialize ChromaDB with persistent storage
            self._client = chromadb.PersistentClient(path=str(CHROMADB_PATH))
            self._collection = self._client.get_or_create_collection(
                name="linear_issues",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB initialized at {CHROMADB_PATH}")

            # Initialize sentence-transformers model
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Embedding model '{EMBEDDING_MODEL}' loaded")

        except Exception as e:
            logger.error(f"Failed to initialize IssueVectorStore: {e}", exc_info=True)
            raise

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using sentence-transformers.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        try:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            raise

    async def add_issue(
        self,
        issue_id: str,
        title: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an issue to the vector store with its embedding.

        Args:
            issue_id: Unique issue identifier (e.g., "PROJ-123").
            title: Issue title.
            description: Issue description.
            metadata: Optional metadata (status, assignee, labels, etc.).
        """
        metadata = metadata or {}

        # Combine title and description for embedding
        combined_text = f"{title}\n\n{description}"

        # Generate embedding in thread pool (CPU-bound operation)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self._generate_embedding, combined_text)

        try:
            self._collection.add(
                ids=[issue_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[combined_text],
            )
            logger.debug(f"Added issue {issue_id} to vector store")
        except Exception as e:
            logger.error(f"Failed to add issue {issue_id} to vector store: {e}", exc_info=True)
            raise

    async def search_similar(
        self, query: str, limit: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar issues using semantic similarity.

        Args:
            query: Search query text.
            limit: Maximum number of results to return.
            filter_metadata: Optional metadata filters (e.g., {"status": "In Progress"}).

        Returns:
            List of similar issues with metadata and similarity scores.
        """
        # Generate query embedding in thread pool
        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(None, self._generate_embedding, query)

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=filter_metadata,
            )

            # Format results
            similar_issues = []
            for i in range(len(results["ids"][0])):
                similar_issues.append(
                    {
                        "issue_id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None,
                    }
                )

            logger.info(f"Found {len(similar_issues)} similar issues for query: {query[:50]}...")
            return similar_issues

        except Exception as e:
            logger.error(f"Failed to search similar issues: {e}", exc_info=True)
            return []

    async def get_issue_embedding(self, issue_id: str) -> list[float] | None:
        """Retrieve the embedding vector for a specific issue.

        Args:
            issue_id: Issue identifier.

        Returns:
            Embedding vector or None if not found.
        """
        try:
            result = self._collection.get(ids=[issue_id], include=["embeddings"])

            if result["ids"] and len(result["embeddings"]) > 0:
                logger.debug(f"Retrieved embedding for issue {issue_id}")
                return result["embeddings"][0]
            else:
                logger.warning(f"No embedding found for issue {issue_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to get embedding for {issue_id}: {e}", exc_info=True)
            return None

    async def delete_issue(self, issue_id: str) -> None:
        """Delete an issue from the vector store.

        Args:
            issue_id: Issue identifier to delete.
        """
        try:
            self._collection.delete(ids=[issue_id])
            logger.debug(f"Deleted issue {issue_id} from vector store")
        except Exception as e:
            logger.error(f"Failed to delete issue {issue_id}: {e}", exc_info=True)
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics.

        Returns:
            Dictionary with count, model name, and storage path.
        """
        try:
            count = self._collection.count()
            return {
                "total_issues": count,
                "embedding_model": EMBEDDING_MODEL,
                "storage_path": str(CHROMADB_PATH),
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {"error": str(e)}
