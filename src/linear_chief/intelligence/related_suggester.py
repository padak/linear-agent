"""Related issues suggester using semantic similarity.

This module provides functionality to suggest related issues based on vector similarity,
enabling automatic discovery of connected work in conversations and briefings.

Includes:
- Related issue discovery by issue ID
- Conversation-based suggestions
- Duplicate filtering (>85% similarity)
- Formatted output for Telegram display
- Briefing integration
"""

import logging
from typing import Any, Dict, List, Optional

from linear_chief.intelligence.semantic_search import SemanticSearchService

logger = logging.getLogger(__name__)


class RelatedIssuesSuggester:
    """Suggests related issues using semantic similarity.

    Provides intelligent issue suggestions based on vector embeddings:
    - Find related issues for a given issue (60% threshold)
    - Get suggestions for conversation queries
    - Filter out likely duplicates (>85% similarity)
    - Format results for display
    - Integrate with briefings

    Example:
        >>> suggester = RelatedIssuesSuggester()
        >>> related = await suggester.get_related_issues("AI-1799", limit=3)
        >>> formatted = suggester.format_related_issues(related)
    """

    def __init__(self) -> None:
        """Initialize with SemanticSearchService."""
        self.search_service = SemanticSearchService()
        logger.info("RelatedIssuesSuggester initialized")

    async def get_related_issues(
        self,
        issue_id: str,
        limit: int = 3,
        min_similarity: float = 0.6,
        exclude_duplicates: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get related issues for a given issue.

        Uses semantic similarity search to find related issues, with optional
        filtering to exclude very high similarity matches (likely duplicates).

        Args:
            issue_id: Source issue identifier (e.g., "AI-1799")
            limit: Maximum number of related issues (default: 3)
            min_similarity: Minimum similarity threshold 0.0-1.0 (default: 0.6)
            exclude_duplicates: Exclude very high similarity (>85%) duplicates

        Returns:
            List of related issues with metadata:
            [
                {
                    "issue_id": "AI-1820",
                    "title": "Related issue",
                    "similarity": 0.73,
                    "url": "https://linear.app/...",
                    "team": "AI",
                    "state": "In Progress",
                    "relation_type": "similar"  # or "duplicate" if >85%
                }
            ]

        Raises:
            ValueError: If issue not found
        """
        logger.info(
            "Getting related issues",
            extra={
                "source_issue": issue_id,
                "limit": limit,
                "min_similarity": min_similarity,
                "exclude_duplicates": exclude_duplicates,
            },
        )

        try:
            # Use semantic search to find similar issues
            # Request more results than needed to account for filtering
            search_limit = limit * 3 if exclude_duplicates else limit
            similar_issues = await self.search_service.find_similar_issues(
                issue_id=issue_id,
                limit=search_limit,
                min_similarity=min_similarity,
            )

            # Process and classify results
            related_issues = []
            duplicate_threshold = 0.85

            for issue in similar_issues:
                similarity = issue.get("similarity", 0.0)

                # Classify as similar or duplicate
                if similarity > duplicate_threshold:
                    relation_type = "duplicate"
                    # Skip if excluding duplicates
                    if exclude_duplicates:
                        logger.debug(
                            f"Excluding potential duplicate {issue['issue_id']} "
                            f"(similarity: {similarity:.2%})"
                        )
                        continue
                else:
                    relation_type = "similar"

                # Add relation type to issue metadata
                issue["relation_type"] = relation_type
                related_issues.append(issue)

                # Stop if we have enough results
                if len(related_issues) >= limit:
                    break

            logger.info(
                f"Found {len(related_issues)} related issues for {issue_id}",
                extra={
                    "source_issue": issue_id,
                    "related_count": len(related_issues),
                    "excluded_duplicates": exclude_duplicates,
                },
            )

            return related_issues

        except ValueError as e:
            # Issue not found - re-raise
            logger.warning(f"Issue {issue_id} not found: {e}")
            raise

        except Exception as e:
            logger.error(
                "Failed to get related issues",
                extra={
                    "source_issue": issue_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            # Return empty list instead of failing
            return []

    async def get_related_for_conversation(
        self,
        query: str,
        current_issue_id: Optional[str] = None,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get related issues for a conversation query.

        Searches for issues semantically similar to the user's query text,
        optionally excluding the issue currently being discussed.

        Args:
            query: User's question/query text
            current_issue_id: Optional issue being discussed (to exclude)
            limit: Maximum number of suggestions

        Returns:
            Related issues based on semantic similarity to query

        Example:
            >>> suggester = RelatedIssuesSuggester()
            >>> related = await suggester.get_related_for_conversation(
            ...     query="authentication problems",
            ...     current_issue_id="AI-1799",
            ...     limit=3
            ... )
        """
        logger.info(
            "Getting related issues for conversation",
            extra={
                "query_preview": query[:100],
                "current_issue": current_issue_id,
                "limit": limit,
            },
        )

        try:
            # Search by text
            results = await self.search_service.search_by_text(
                query=query,
                limit=limit + 1,  # +1 to account for potential exclusion
                min_similarity=0.5,  # Lower threshold for conversations
            )

            # Filter out current issue if provided
            related_issues = []
            for result in results:
                issue_id = result.get("issue_id")

                # Skip current issue
                if current_issue_id and issue_id == current_issue_id:
                    logger.debug(f"Excluding current issue {current_issue_id}")
                    continue

                # Add relation type
                result["relation_type"] = "similar"
                related_issues.append(result)

                # Stop if we have enough results
                if len(related_issues) >= limit:
                    break

            logger.info(
                f"Found {len(related_issues)} related issues for conversation query",
                extra={
                    "query_preview": query[:100],
                    "related_count": len(related_issues),
                },
            )

            return related_issues

        except Exception as e:
            logger.error(
                "Failed to get related issues for conversation",
                extra={
                    "query_preview": query[:100],
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            # Return empty list instead of failing
            return []

    def format_related_issues(
        self,
        related: List[Dict[str, Any]],
        show_similarity: bool = False,
    ) -> str:
        """
        Format related issues for display.

        Creates a markdown-formatted string with clickable links and
        optional similarity percentages.

        Args:
            related: List of related issues
            show_similarity: Include similarity percentages (default: False)

        Returns:
            Formatted Markdown string

        Example:
            **Related Issues:**
            1. [**AI-1820**](url) - OAuth2 implementation (In Progress)
            2. [**AI-1805**](url) - Login flow refactor (Done)
            3. [**DMD-480**](url) - Authentication bug fix (Todo)
        """
        if not related:
            return ""

        lines = ["**Related Issues:**"]

        for idx, issue in enumerate(related, 1):
            issue_id = issue.get("issue_id", "Unknown")
            title = issue.get("title", "Unknown")
            url = issue.get("url", "")
            state = issue.get("state", "Unknown")

            # Truncate long titles (keep it concise)
            if len(title) > 50:
                title = title[:47] + "..."

            # Format issue link
            if url:
                issue_link = f"[**{issue_id}**]({url})"
            else:
                issue_link = f"**{issue_id}**"

            # Build line
            line = f"{idx}. {issue_link} - {title} ({state})"

            # Add similarity percentage if requested
            if show_similarity and "similarity" in issue:
                similarity_pct = issue["similarity"] * 100
                line += f" - {similarity_pct:.0f}% similar"

            lines.append(line)

        return "\n".join(lines)

    async def add_to_briefing_context(
        self,
        issues: List[Dict[str, Any]],
        max_related_per_issue: int = 2,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find related issues for each issue in briefing.

        Scans through briefing issues and finds related issues for context,
        helping identify cross-issue dependencies and connections.

        Args:
            issues: Issues being briefed
            max_related_per_issue: Maximum related issues per issue (default: 2)

        Returns:
            Mapping of issue_id -> related_issues:
            {
                "AI-1799": [
                    {"issue_id": "AI-1820", "similarity": 0.73, ...},
                    {"issue_id": "AI-1805", "similarity": 0.68, ...}
                ],
                "DMD-480": [...]
            }

        Example:
            >>> suggester = RelatedIssuesSuggester()
            >>> issues = [{"identifier": "AI-1799", ...}, ...]
            >>> related_map = await suggester.add_to_briefing_context(issues)
            >>> # Use in briefing generation
        """
        logger.info(
            "Finding related issues for briefing",
            extra={
                "issue_count": len(issues),
                "max_per_issue": max_related_per_issue,
            },
        )

        related_map: Dict[str, List[Dict[str, Any]]] = {}

        for issue in issues:
            issue_id = issue.get("identifier")
            if not issue_id:
                continue

            try:
                related = await self.get_related_issues(
                    issue_id=issue_id,
                    limit=max_related_per_issue,
                    min_similarity=0.6,
                    exclude_duplicates=True,
                )

                if related:
                    related_map[issue_id] = related
                    logger.debug(
                        f"Found {len(related)} related issues for {issue_id}",
                        extra={
                            "issue_id": issue_id,
                            "related_count": len(related),
                        },
                    )

            except Exception as e:
                # Non-fatal: Log warning and continue with other issues
                logger.warning(
                    f"Failed to get related issues for {issue_id}: {e}",
                    extra={
                        "issue_id": issue_id,
                        "error_type": type(e).__name__,
                    },
                )
                continue

        logger.info(
            f"Found related issues for {len(related_map)}/{len(issues)} briefing issues",
            extra={
                "total_issues": len(issues),
                "issues_with_related": len(related_map),
            },
        )

        return related_map


def should_suggest_related(
    user_message: str,
    issue_ids: List[str],
) -> bool:
    """
    Determine if we should auto-suggest related issues.

    Uses heuristics to decide when related issue suggestions would be helpful:
    - User asks about specific issue
    - User uses keywords like "related", "similar", "connected"
    - Query is about single issue (not multiple)

    Args:
        user_message: User's message text
        issue_ids: Extracted issue IDs from message

    Returns:
        True if we should auto-suggest related issues

    Example:
        >>> should_suggest_related("what's related to AI-1799?", ["AI-1799"])
        True
        >>> should_suggest_related("status of AI-1799 and DMD-480", ["AI-1799", "DMD-480"])
        False  # Multiple issues - don't overwhelm
    """
    message_lower = user_message.lower()

    # Keywords that trigger related suggestions
    trigger_keywords = [
        "related",
        "similar",
        "connected",
        "associated",
        "linked",
        "dependency",
        "depends",
        "connection",
    ]

    # Single issue query with trigger keyword
    if len(issue_ids) == 1 and any(
        keyword in message_lower for keyword in trigger_keywords
    ):
        logger.debug(
            "Auto-suggest triggered: single issue + trigger keyword",
            extra={"issue_id": issue_ids[0]},
        )
        return True

    # User explicitly asking about one issue (short query)
    if len(issue_ids) == 1 and len(user_message.split()) <= 10:
        logger.debug(
            "Auto-suggest triggered: short single-issue query",
            extra={"issue_id": issue_ids[0]},
        )
        return True

    return False
