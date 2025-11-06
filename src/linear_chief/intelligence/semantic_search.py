"""Semantic search service for finding similar issues using vector similarity.

This module provides semantic search capabilities leveraging ChromaDB vector store
to find similar issues based on content similarity, enabling:
- Similar issue discovery by issue ID
- Natural language search across all issues
- Metadata filtering (team, state, labels)
"""

import logging
from typing import Any, Dict, List, Optional

from linear_chief.memory.vector_store import IssueVectorStore
from linear_chief.storage import get_session_maker, get_db_session
from linear_chief.storage.repositories import IssueHistoryRepository
from linear_chief.config import LINEAR_API_KEY
from linear_chief.linear.client import LinearClient

logger = logging.getLogger(__name__)


def calculate_similarity_percentage(distance: float) -> float:
    """
    Convert ChromaDB distance to similarity percentage.

    ChromaDB uses cosine distance (0 = identical, 2 = opposite).
    Convert to similarity percentage (0-100%).

    Formula:
        similarity = (1 - distance/2) * 100

    Examples:
        distance=0.0 → 100% (identical)
        distance=0.2 → 90%
        distance=0.5 → 75%
        distance=1.0 → 50%
        distance=2.0 → 0% (opposite)

    Args:
        distance: ChromaDB cosine distance (0.0 to 2.0)

    Returns:
        Similarity percentage (0.0 to 100.0)
    """
    # Clamp distance to valid range
    if distance < 0:
        distance = 0
    if distance > 2:
        distance = 2

    # Convert to percentage: distance 0 = 100%, distance 2 = 0%
    similarity = (1 - distance / 2) * 100
    return max(0.0, min(100.0, similarity))


class SemanticSearchService:
    """Semantic search for finding similar issues using ChromaDB.

    Provides methods to:
    1. Find issues similar to a given issue
    2. Search issues by natural language query
    3. Format results for Telegram display

    Uses existing IssueVectorStore for embeddings and ChromaDB for search.
    Integrates with database and Linear API for complete issue context.

    Example:
        >>> service = SemanticSearchService()
        >>> results = await service.find_similar_issues("AI-1799", limit=5)
        >>> formatted = service.format_similarity_results(results)
    """

    def __init__(self) -> None:
        """Initialize with existing IssueVectorStore."""
        self.vector_store = IssueVectorStore()
        logger.info("SemanticSearchService initialized")

    async def find_similar_issues(
        self,
        issue_id: str,
        limit: int = 5,
        min_similarity: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Find issues similar to given issue.

        Steps:
        1. Get source issue from DB or Linear API
        2. Build query text from title + description
        3. Search vector store with this text
        4. Filter results by min_similarity threshold
        5. Exclude the source issue itself
        6. Format and return results

        Args:
            issue_id: Issue identifier (e.g., "AI-1799")
            limit: Maximum number of results (default: 5)
            min_similarity: Minimum similarity score 0.0-1.0 (default: 0.5)

        Returns:
            List of similar issues with similarity scores:
            [
                {
                    "issue_id": "AI-1820",
                    "title": "Related issue title",
                    "similarity": 0.87,
                    "url": "https://linear.app/...",
                    "team": "AI",
                    "state": "In Progress",
                    "description": "Issue description..."
                }
            ]

        Raises:
            ValueError: If issue not found or invalid issue_id format
        """
        logger.info(
            "Finding similar issues",
            extra={
                "source_issue": issue_id,
                "limit": limit,
                "min_similarity": min_similarity,
            },
        )

        # Get the source issue context
        source_issue = await self.get_issue_context(issue_id)
        if not source_issue:
            logger.warning(f"Source issue {issue_id} not found")
            raise ValueError(f"Issue {issue_id} not found")

        # Build query text from title and description
        query_text = f"{source_issue['title']}\n\n{source_issue.get('description', '')}"

        # Search vector store (get more results than needed to account for filtering)
        search_results = await self.vector_store.search_similar(
            query=query_text,
            limit=limit + 1,  # +1 to account for self-match
            filter_metadata=None,
        )

        # Process and filter results
        similar_issues = []
        for result in search_results:
            result_issue_id = result.get("issue_id", "")

            # Skip the source issue itself
            if result_issue_id == issue_id:
                continue

            # Get distance and calculate similarity
            distance = result.get("distance")
            if distance is None:
                logger.warning(f"No distance for issue {result_issue_id}, skipping")
                continue

            similarity = calculate_similarity_percentage(distance)

            # Filter by minimum similarity threshold
            if similarity / 100 < min_similarity:
                continue

            # Extract metadata
            metadata = result.get("metadata", {})

            # Format result
            similar_issues.append(
                {
                    "issue_id": result_issue_id,
                    "title": metadata.get("title", "Unknown"),
                    "similarity": similarity / 100,  # Return as 0.0-1.0
                    "url": metadata.get("url", ""),
                    "team": metadata.get("team_name", "Unknown"),
                    "state": metadata.get("state", "Unknown"),
                    "description": metadata.get("description", ""),
                }
            )

            # Stop if we have enough results
            if len(similar_issues) >= limit:
                break

        logger.info(
            f"Found {len(similar_issues)} similar issues for {issue_id}",
            extra={
                "source_issue": issue_id,
                "results_count": len(similar_issues),
            },
        )

        return similar_issues

    async def search_by_text(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.3,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search issues by natural language query.

        Uses vector similarity search to find issues matching the query text.
        Supports optional metadata filtering by team, state, or labels.

        Args:
            query: Natural language search query
            limit: Maximum number of results (default: 5)
            min_similarity: Minimum similarity threshold 0.0-1.0 (default: 0.3)
            filters: Optional metadata filters (team, state, labels)

        Returns:
            List of matching issues with scores:
            [
                {
                    "issue_id": "AI-1820",
                    "title": "Issue title",
                    "similarity": 0.73,
                    "url": "https://linear.app/...",
                    "team": "AI",
                    "state": "In Progress"
                }
            ]

        Examples:
            - "authentication issues"
            - "backend API performance problems"
            - "frontend bugs in React components"
        """
        logger.info(
            "Searching by text",
            extra={
                "query": query[:100],
                "limit": limit,
                "min_similarity": min_similarity,
                "filters": filters,
            },
        )

        # Search vector store
        search_results = await self.vector_store.search_similar(
            query=query,
            limit=limit * 2,  # Get more results to account for filtering
            filter_metadata=filters,
        )

        # Process results
        matching_issues = []
        for result in search_results:
            result_issue_id = result.get("issue_id", "")

            # Get distance and calculate similarity
            distance = result.get("distance")
            if distance is None:
                logger.warning(f"No distance for issue {result_issue_id}, skipping")
                continue

            similarity = calculate_similarity_percentage(distance)

            # Filter by minimum similarity threshold
            if similarity / 100 < min_similarity:
                continue

            # Extract metadata
            metadata = result.get("metadata", {})

            # Format result
            matching_issues.append(
                {
                    "issue_id": result_issue_id,
                    "title": metadata.get("title", "Unknown"),
                    "similarity": similarity / 100,  # Return as 0.0-1.0
                    "url": metadata.get("url", ""),
                    "team": metadata.get("team_name", "Unknown"),
                    "state": metadata.get("state", "Unknown"),
                    "description": metadata.get("description", ""),
                }
            )

            # Stop if we have enough results
            if len(matching_issues) >= limit:
                break

        logger.info(
            f"Found {len(matching_issues)} issues matching query",
            extra={
                "query": query[:100],
                "results_count": len(matching_issues),
            },
        )

        return matching_issues

    async def get_issue_context(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full context for an issue (for similarity search).

        Tries database first (fast), then falls back to Linear API if needed.

        Args:
            issue_id: Issue identifier (e.g., "AI-1799")

        Returns:
            Issue dictionary with title, description, labels, etc., or None if not found:
            {
                "issue_id": "AI-1799",
                "title": "Issue title",
                "description": "Issue description",
                "state": "In Progress",
                "team": "AI",
                "url": "https://linear.app/..."
            }
        """
        logger.debug(f"Getting issue context for {issue_id}")

        # Try database first (fast, cached)
        session_maker = get_session_maker()
        for session in get_db_session(session_maker):
            issue_repo = IssueHistoryRepository(session)

            # Try to get fresh snapshot (within 1 hour)
            snapshot = issue_repo.get_issue_snapshot_by_identifier(
                issue_id=issue_id, max_age_hours=1
            )

            if snapshot:
                logger.debug(f"Found issue {issue_id} in database cache")
                # Extract metadata
                extra_metadata = getattr(snapshot, "extra_metadata", None) or {}

                return {
                    "issue_id": issue_id,
                    "title": snapshot.title,  # type: ignore[attr-defined]
                    "description": extra_metadata.get("description", ""),
                    "state": snapshot.state,  # type: ignore[attr-defined]
                    "team": snapshot.team_name or "Unknown",  # type: ignore[attr-defined]
                    "url": extra_metadata.get("url", ""),
                }

        # Fallback to Linear API if not in DB or stale
        logger.debug(f"Issue {issue_id} not in cache, fetching from Linear API")

        try:
            async with LinearClient(LINEAR_API_KEY) as client:
                issue = await client.get_issue_by_identifier(issue_id)

                if not issue:
                    logger.warning(f"Issue {issue_id} not found in Linear API")
                    return None

                # Extract team info
                team = issue.get("team", {})
                team_name = team.get("name", "Unknown") if team else "Unknown"

                return {
                    "issue_id": issue.get("identifier", issue_id),
                    "title": issue.get("title", ""),
                    "description": issue.get("description", ""),
                    "state": issue.get("state", {}).get("name", "Unknown"),
                    "team": team_name,
                    "url": issue.get("url", ""),
                }

        except Exception as e:
            logger.error(
                f"Failed to fetch issue {issue_id} from Linear API",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            return None

    def format_similarity_results(
        self,
        results: List[Dict[str, Any]],
        include_score: bool = True,
    ) -> str:
        """
        Format similarity results for Telegram message.

        Creates a markdown-formatted message with:
        - Clickable issue links
        - Similarity percentages
        - Issue state and team
        - Professional formatting

        Args:
            results: List of similarity results from find_similar_issues or search_by_text
            include_score: Include similarity percentage (default: True)

        Returns:
            Markdown-formatted string with clickable links

        Example:
            **Similar Issues (5 found):**

            1. [**AI-1820**](url) - OAuth2 implementation (87% similar)
               State: In Progress | Team: AI

            2. [**AI-1805**](url) - Login flow refactor (73% similar)
               State: Done | Team: AI
        """
        if not results:
            return "No similar issues found."

        lines = []
        lines.append(
            f"**Found {len(results)} similar issue{'s' if len(results) != 1 else ''}:**\n"
        )

        for idx, result in enumerate(results, start=1):
            issue_id = result.get("issue_id", "Unknown")
            title = result.get("title", "Unknown")
            url = result.get("url", "")
            state = result.get("state", "Unknown")
            team = result.get("team", "Unknown")
            similarity = result.get("similarity", 0.0)

            # Format issue link
            if url:
                issue_link = f"[**{issue_id}**]({url})"
            else:
                issue_link = f"**{issue_id}**"

            # Build the result line
            result_line = f"{idx}. {issue_link} - {title}"

            # Add similarity percentage if requested
            if include_score:
                similarity_pct = int(similarity * 100)
                result_line += f" ({similarity_pct}% similar)"

            lines.append(result_line)

            # Add metadata line (state and team)
            metadata_line = f"   State: {state} | Team: {team}"
            lines.append(metadata_line)

            # Add blank line between results (except after last one)
            if idx < len(results):
                lines.append("")

        return "\n".join(lines)
