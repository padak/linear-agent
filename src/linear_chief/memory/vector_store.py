"""ChromaDB vector store for issue embeddings and semantic search."""

import asyncio
import logging
from typing import Any
import numpy as np

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
            # Handle different return types from sentence-transformers
            if isinstance(embedding, np.ndarray):
                return embedding.tolist()  # type: ignore[no-any-return]
            elif hasattr(embedding, "tolist"):
                return embedding.tolist()  # type: ignore[no-any-return]
            else:
                # Already a list - sentence-transformers can return various types
                return list(embedding)  # type: ignore[arg-type]
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
        # ChromaDB requires metadata to be either None or a non-empty dict
        # Default to a minimal metadata dict if none provided
        if not metadata:
            metadata = {"_placeholder": "true"}

        # Combine title and description for embedding
        combined_text = f"{title}\n\n{description}"

        # Generate embedding in thread pool (CPU-bound operation)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, self._generate_embedding, combined_text
        )

        try:
            # ChromaDB type hints are imprecise for embeddings parameter
            self._collection.upsert(
                ids=[issue_id],
                embeddings=[embedding],  # type: ignore[arg-type]
                metadatas=[metadata],
                documents=[combined_text],
            )
            logger.debug(f"Upserted issue {issue_id} to vector store")
        except Exception as e:
            logger.error(
                f"Failed to add issue {issue_id} to vector store: {e}", exc_info=True
            )
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
        query_embedding = await loop.run_in_executor(
            None, self._generate_embedding, query
        )

        try:
            # ChromaDB type hints are imprecise for query_embeddings parameter
            results = self._collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                n_results=limit,
                where=filter_metadata,
            )

            # Format results
            similar_issues = []
            ids = results["ids"][0] if results["ids"] is not None else []
            documents = (
                results["documents"][0] if results["documents"] is not None else []
            )
            metadatas = (
                results["metadatas"][0] if results["metadatas"] is not None else []
            )
            distances = (
                results["distances"][0]
                if "distances" in results and results["distances"] is not None
                else None
            )

            for i in range(len(ids)):
                similar_issues.append(
                    {
                        "issue_id": ids[i],
                        "document": documents[i] if i < len(documents) else "",
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "distance": (
                            distances[i] if distances and i < len(distances) else None
                        ),
                    }
                )

            logger.info(
                f"Found {len(similar_issues)} similar issues for query: {query[:50]}..."
            )
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

            if (
                result["ids"]
                and result["embeddings"] is not None
                and len(result["embeddings"]) > 0
            ):
                logger.debug(f"Retrieved embedding for issue {issue_id}")
                # Convert to list[float] - ChromaDB returns Sequence types
                embedding = result["embeddings"][0]
                return list(embedding) if embedding else None
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
