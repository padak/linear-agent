"""Duplicate issue detection using vector similarity.

This module provides functionality to detect potential duplicate issues in Linear
by comparing embeddings in the vector store and calculating similarity scores.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta

from linear_chief.memory.vector_store import IssueVectorStore
from linear_chief.storage.database import get_session_maker, get_db_session
from linear_chief.storage.repositories import IssueHistoryRepository

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects potential duplicate issues using vector similarity.

    Uses semantic search in ChromaDB to find similar issues based on title
    and description embeddings. Provides suggestions for merging duplicates
    and alerts users in briefings.

    Example:
        >>> detector = DuplicateDetector()
        >>> duplicates = await detector.find_duplicates(min_similarity=0.85)
        >>> for dup in duplicates:
        ...     print(f"{dup['issue_a']} is {dup['similarity']:.0%} similar to {dup['issue_b']}")
    """

    # States considered "active" for duplicate detection
    ACTIVE_STATES = [
        "todo",
        "in progress",
        "started",
        "active",
        "backlog",
    ]

    # States considered "inactive" (completed/cancelled)
    INACTIVE_STATES = [
        "done",
        "completed",
        "canceled",
        "cancelled",
        "archived",
    ]

    def __init__(self) -> None:
        """Initialize DuplicateDetector with IssueVectorStore."""
        self.vector_store = IssueVectorStore()

    async def find_duplicates(
        self,
        min_similarity: float = 0.85,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Find all potential duplicate pairs in the database.

        Performs semantic similarity search across all issues to identify
        potential duplicates based on title and description embeddings.

        Args:
            min_similarity: Minimum similarity to consider duplicate (default: 85%)
            active_only: Only check active issues (not Done/Canceled)

        Returns:
            List of duplicate pairs with metadata:
            [
                {
                    "issue_a": "AI-1799",
                    "issue_b": "AI-1820",
                    "similarity": 0.92,
                    "title_a": "OAuth implementation",
                    "title_b": "OAuth2 auth flow",
                    "state_a": "In Progress",
                    "state_b": "Todo",
                    "team": "AI",
                    "url_a": "https://linear.app/...",
                    "url_b": "https://linear.app/...",
                    "suggested_action": "Consider merging AI-1820 into AI-1799"
                }
            ]
        """
        logger.info(
            "Starting duplicate detection scan",
            extra={
                "min_similarity": min_similarity,
                "active_only": active_only,
            },
        )

        # Get all latest issue snapshots from database
        session_maker = get_session_maker()
        all_issues = []

        for session in get_db_session(session_maker):
            issue_repo = IssueHistoryRepository(session)
            # Get issues from last 90 days
            snapshots = issue_repo.get_all_latest_snapshots(days=90)

            # Convert to issue list with metadata
            for snapshot in snapshots:
                issue_id: str = snapshot.issue_id  # type: ignore[assignment]
                state: str = snapshot.state  # type: ignore[assignment]
                title: str = snapshot.title  # type: ignore[assignment]
                team_name: Optional[str] = snapshot.team_name  # type: ignore[assignment]
                extra_metadata = getattr(snapshot, "extra_metadata", None)

                # Filter by active state if requested
                if active_only and state.lower() in self.INACTIVE_STATES:
                    continue

                # Extract URL from metadata
                url = None
                if extra_metadata and isinstance(extra_metadata, dict):
                    url = extra_metadata.get("url")

                all_issues.append(
                    {
                        "issue_id": issue_id,
                        "title": title,
                        "state": state,
                        "team": team_name or "Unknown",
                        "url": url,
                        "description": (
                            extra_metadata.get("description", "")
                            if extra_metadata
                            else ""
                        ),
                    }
                )

        logger.info(f"Scanning {len(all_issues)} issues for duplicates")

        # Find similar pairs
        duplicate_pairs = await self._scan_all_issues_for_duplicates(
            all_issues, min_similarity
        )

        # Format results
        duplicates = []
        for issue_a_id, issue_b_id, similarity in duplicate_pairs:
            # Find issue details
            issue_a = next((i for i in all_issues if i["issue_id"] == issue_a_id), None)
            issue_b = next((i for i in all_issues if i["issue_id"] == issue_b_id), None)

            if not issue_a or not issue_b:
                continue

            # Generate suggested action
            suggested_action = self._generate_merge_suggestion(
                issue_a, issue_b, similarity
            )

            duplicates.append(
                {
                    "issue_a": issue_a_id,
                    "issue_b": issue_b_id,
                    "similarity": similarity,
                    "title_a": issue_a["title"],
                    "title_b": issue_b["title"],
                    "state_a": issue_a["state"],
                    "state_b": issue_b["state"],
                    "team": issue_a["team"],
                    "url_a": issue_a.get("url"),
                    "url_b": issue_b.get("url"),
                    "suggested_action": suggested_action,
                }
            )

        # Sort by similarity descending
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(f"Found {len(duplicates)} potential duplicate pairs")
        return duplicates

    async def check_issue_for_duplicates(
        self,
        issue_id: str,
        min_similarity: float = 0.85,
    ) -> List[Dict[str, Any]]:
        """Check if specific issue has duplicates.

        Searches for similar issues using semantic similarity and returns
        potential duplicates above the threshold.

        Args:
            issue_id: Issue to check (e.g., "AI-1799")
            min_similarity: Minimum similarity threshold

        Returns:
            List of potential duplicates with metadata
        """
        logger.info(
            f"Checking {issue_id} for duplicates",
            extra={"min_similarity": min_similarity},
        )

        # Get issue details from database
        session_maker = get_session_maker()
        title: Optional[str] = None
        state: Optional[str] = None
        team_name: Optional[str] = None
        description = ""
        url = None

        for session in get_db_session(session_maker):
            issue_repo = IssueHistoryRepository(session)
            issue_snapshot = issue_repo.get_latest_snapshot(issue_id)

            if not issue_snapshot:
                logger.warning(f"Issue {issue_id} not found in database")
                return []

            # Extract ALL issue metadata WHILE IN SESSION
            title = issue_snapshot.title  # type: ignore[assignment]
            state = issue_snapshot.state  # type: ignore[assignment]
            team_name = issue_snapshot.team_name  # type: ignore[assignment]
            extra_metadata = getattr(issue_snapshot, "extra_metadata", None)

            if extra_metadata and isinstance(extra_metadata, dict):
                description = extra_metadata.get("description", "")
                url = extra_metadata.get("url")

        # Search for similar issues
        query_text = f"{title}\n\n{description}"
        similar_issues = await self.vector_store.search_similar(
            query=query_text,
            limit=10,
        )

        # Filter and format results
        duplicates = []
        for result in similar_issues:
            result_id = result.get("issue_id")

            # Skip self-matches
            if result_id == issue_id:
                continue

            # Calculate similarity (ChromaDB returns distance, need to convert)
            distance = result.get("distance", 1.0)
            # Cosine distance to similarity: similarity = 1 - distance
            similarity = 1.0 - distance

            # Check similarity threshold
            if similarity < min_similarity:
                continue

            # Get metadata for duplicate issue
            duplicate_metadata = result.get("metadata", {})
            duplicate_title = result.get("document", "").split("\n\n")[0]  # First line

            # Get full details from database WITHIN SESSION
            duplicate_state = "Unknown"
            duplicate_team = "Unknown"
            duplicate_url = None

            for session in get_db_session(session_maker):
                issue_repo = IssueHistoryRepository(session)
                dup_snapshot = issue_repo.get_latest_snapshot(result_id)

                # Access all attributes WHILE IN SESSION
                if dup_snapshot:
                    duplicate_state = dup_snapshot.state  # type: ignore[assignment]
                    duplicate_team = dup_snapshot.team_name or "Unknown"  # type: ignore[assignment]
                    dup_metadata = getattr(dup_snapshot, "extra_metadata", None)
                    if dup_metadata and isinstance(dup_metadata, dict):
                        duplicate_url = dup_metadata.get("url")
                        # Use title from snapshot (more reliable than parsed document)
                        duplicate_title = dup_snapshot.title  # type: ignore[assignment]

            # Generate suggestion
            issue_a = {
                "issue_id": issue_id,
                "title": title,
                "state": state,
                "team": team_name or "Unknown",
                "url": url,
            }
            issue_b = {
                "issue_id": result_id,
                "title": duplicate_title,
                "state": duplicate_state,
                "team": duplicate_team,
                "url": duplicate_url,
            }

            suggested_action = self._generate_merge_suggestion(
                issue_a, issue_b, similarity
            )

            duplicates.append(
                {
                    "issue_a": issue_id,
                    "issue_b": result_id,
                    "similarity": similarity,
                    "title_a": title,
                    "title_b": duplicate_title,
                    "state_a": state,
                    "state_b": duplicate_state,
                    "team": team_name or "Unknown",
                    "url_a": url,
                    "url_b": duplicate_url,
                    "suggested_action": suggested_action,
                }
            )

        # Sort by similarity descending
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(
            f"Found {len(duplicates)} potential duplicates for {issue_id}",
        )

        return duplicates

    async def _scan_all_issues_for_duplicates(
        self,
        all_issues: List[Dict[str, Any]],
        min_similarity: float = 0.85,
    ) -> List[Tuple[str, str, float]]:
        """Efficiently scan all issues for duplicates.

        Args:
            all_issues: List of issue dictionaries
            min_similarity: Minimum similarity threshold

        Returns:
            List of (issue_a, issue_b, similarity) tuples
        """
        duplicates: List[Tuple[str, str, float]] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for issue in all_issues:
            issue_id = issue["issue_id"]
            query_text = f"{issue['title']}\n\n{issue.get('description', '')}"

            # Search for similar issues
            similar = await self.vector_store.search_similar(
                query=query_text,
                limit=10,
            )

            for result in similar:
                result_id = result.get("issue_id")

                # Skip self-matches
                if result_id == issue_id:
                    continue

                # Calculate similarity (convert distance to similarity)
                distance = result.get("distance", 1.0)
                similarity = 1.0 - distance

                # Check similarity threshold
                if similarity < min_similarity:
                    continue

                # Ensure we don't add both (A,B) and (B,A)
                pair = tuple(sorted([issue_id, result_id]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    duplicates.append((pair[0], pair[1], similarity))

        return duplicates

    def _generate_merge_suggestion(
        self,
        issue_a: Dict[str, Any],
        issue_b: Dict[str, Any],
        similarity: float,
    ) -> str:
        """Generate actionable suggestion for duplicate pair.

        Determines which issue to keep based on:
        1. Which is further along (In Progress > Todo)
        2. Which has more activity (state-based heuristic)

        Args:
            issue_a: First issue dictionary
            issue_b: Second issue dictionary
            similarity: Similarity score

        Returns:
            Suggestion string
        """
        state_a = issue_a.get("state", "").lower()
        state_b = issue_b.get("state", "").lower()
        id_a = issue_a.get("issue_id")
        id_b = issue_b.get("issue_id")

        # Priority: In Progress > Started > Active > Todo > Backlog
        state_priority = {
            "in progress": 5,
            "started": 4,
            "active": 3,
            "todo": 2,
            "backlog": 1,
        }

        priority_a = state_priority.get(state_a, 0)
        priority_b = state_priority.get(state_b, 0)

        if priority_a > priority_b:
            return f"Consider merging {id_b} into {id_a} ({similarity:.0%} similar)"
        elif priority_b > priority_a:
            return f"Consider merging {id_a} into {id_b} ({similarity:.0%} similar)"
        elif state_a in self.INACTIVE_STATES and state_b not in self.INACTIVE_STATES:
            return f"Check if {id_b} is still relevant ({id_a} is {state_a})"
        elif state_b in self.INACTIVE_STATES and state_a not in self.INACTIVE_STATES:
            return f"Check if {id_a} is still relevant ({id_b} is {state_b})"
        else:
            return (
                f"Check if {id_a} and {id_b} are duplicates ({similarity:.0%} similar)"
            )

    def format_duplicate_report(
        self,
        duplicates: List[Dict[str, Any]],
    ) -> str:
        """Format duplicate report for Telegram.

        Creates a Markdown-formatted report with clickable links and
        actionable suggestions for each duplicate pair.

        Args:
            duplicates: List of duplicate dictionaries

        Returns:
            Markdown-formatted duplicate report

        Example:
            **Warning Potential Duplicates Detected (3 pairs):**

            1. [**AI-1799**](url) Double-arrows [**AI-1820**](url) - 92% similar
               Bullet AI-1799: OAuth implementation (In Progress)
               Bullet AI-1820: OAuth2 auth flow (Todo)
               Right-arrow Consider merging AI-1820 into AI-1799

            2. [**DMD-480**](url) Double-arrows [**DMD-485**](url) - 87% similar
               Bullet DMD-480: Fix login bug (Done)
               Bullet DMD-485: Login flow broken (Todo)
               Right-arrow Check if DMD-485 is still relevant
        """
        if not duplicates:
            return ""

        lines = [
            f"**Warning Potential Duplicates Detected ({len(duplicates)} pairs):**\n"
        ]

        for idx, dup in enumerate(duplicates, 1):
            # Format issue links (use plain text if URL not available)
            issue_a = dup["issue_a"]
            issue_b = dup["issue_b"]
            url_a = dup.get("url_a")
            url_b = dup.get("url_b")

            if url_a:
                link_a = f"[**{issue_a}**]({url_a})"
            else:
                link_a = f"**{issue_a}**"

            if url_b:
                link_b = f"[**{issue_b}**]({url_b})"
            else:
                link_b = f"**{issue_b}**"

            # Build pair header
            similarity_pct = f"{dup['similarity']:.0%}"
            lines.append(
                f"{idx}. {link_a} Double-arrows {link_b} - {similarity_pct} similar"
            )

            # Add issue details
            lines.append(f"   Bullet {issue_a}: {dup['title_a']} ({dup['state_a']})")
            lines.append(f"   Bullet {issue_b}: {dup['title_b']} ({dup['state_b']})")

            # Add suggestion
            lines.append(f"   Right-arrow {dup['suggested_action']}\n")

        return "\n".join(lines)
