"""Context builder for conversation agent.

This module provides utilities to build rich context for the conversation agent,
including recent issues, briefings, and semantic search capabilities.
"""

import re
import unicodedata
from datetime import datetime
from typing import List, Dict, Any, Optional

from linear_chief.storage import get_session_maker, get_db_session
from linear_chief.storage.repositories import IssueHistoryRepository, BriefingRepository
from linear_chief.memory.vector_store import IssueVectorStore
from linear_chief.utils.logging import get_logger
from linear_chief.config import CACHE_TTL_HOURS

logger = get_logger(__name__)


def _normalize_name(name: str) -> str:
    """
    Normalize name for matching (remove diacritics, lowercase).

    Handles Czech diacritics: á→a, č→c, ď→d, é→e, ě→e, í→i, ň→n,
    ó→o, ř→r, š→s, ť→t, ú→u, ů→u, ý→y, ž→z

    Examples:
        >>> _normalize_name("Petr Šimeček")
        'petr simecek'
        >>> _normalize_name("Petr Simecek")
        'petr simecek'
        >>> _normalize_name("PETR ŠIMEČEK")
        'petr simecek'
        >>> _normalize_name("Tomáš Fejfar")
        'tomas fejfar'

    Args:
        name: Name to normalize (may contain diacritics)

    Returns:
        Normalized name (lowercase, no diacritics)
    """
    # Normalize to NFD (decomposed form): "é" → "e" + combining accent
    normalized = unicodedata.normalize("NFD", name)

    # Remove combining characters (category 'Mn' = Mark, nonspacing)
    # This strips all diacritics: "e" + combining accent → "e"
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )

    # Lowercase and strip whitespace
    return normalized.lower().strip()


def _is_user_assignee(
    assignee_name: Optional[str],
    assignee_email: Optional[str],
    user_name: str,
    user_email: str,
) -> bool:
    """
    Check if assignee matches configured user.

    Uses two matching strategies:
    1. Email matching (exact, case-insensitive) - most reliable
    2. Name matching (normalized, diacritic-insensitive)

    Examples:
        >>> _is_user_assignee("Petr Šimeček", "petr@keboola.com", "Petr Simecek", "petr@keboola.com")
        True
        >>> _is_user_assignee("Petr Šimeček", None, "Petr Simecek", "petr@keboola.com")
        True
        >>> _is_user_assignee("Tomáš Fejfar", "tomas@keboola.com", "Petr Simecek", "petr@keboola.com")
        False

    Args:
        assignee_name: Name from Linear (may have diacritics)
        assignee_email: Email from Linear
        user_name: Configured user name (from .env)
        user_email: Configured user email (from .env)

    Returns:
        True if assignee matches the configured user
    """
    # Strategy 1: Email match (most reliable)
    if assignee_email and user_email:
        if assignee_email.lower().strip() == user_email.lower().strip():
            logger.debug(f"User match via email: {assignee_email} == {user_email}")
            return True

    # Strategy 2: Name match (normalized, diacritic-insensitive)
    if assignee_name and user_name:
        normalized_assignee = _normalize_name(assignee_name)
        normalized_user = _normalize_name(user_name)

        if normalized_assignee == normalized_user:
            logger.debug(
                f"User match via name: '{assignee_name}' (normalized: '{normalized_assignee}') "
                f"== '{user_name}' (normalized: '{normalized_user}')"
            )
            return True

    return False


async def build_conversation_context(
    user_id: str, include_vector_search: bool = False, query: Optional[str] = None
) -> str:
    """
    Build context string for conversation agent.

    Now includes real-time issue fetching when specific IDs are mentioned.

    Includes:
    - Real-time issue details (if specific issue IDs are mentioned)
    - Recent issues (last 30 days)
    - Recent briefings (last 7 days)
    - Optionally: Relevant issues from vector search

    Args:
        user_id: User identifier (for future user preferences)
        include_vector_search: Whether to include semantically similar issues
        query: User query (used for issue ID extraction and vector search)

    Returns:
        Formatted context string

    Raises:
        Exception: If database access fails (logged and re-raised)
    """
    logger.info(
        "Building conversation context",
        extra={
            "user_id": user_id,
            "include_vector_search": include_vector_search,
        },
    )

    try:
        context_parts = []

        # Extract issue IDs from query if provided
        fetched_issues = []
        if query:
            issue_ids = extract_issue_ids(query)
            if issue_ids:
                logger.info(f"Detected issue IDs in query: {issue_ids}")
                fetched_issues = await fetch_issue_details(issue_ids)
                logger.info(f"Fetched {len(fetched_issues)} issues from Linear API")

        # Add fetched issues FIRST (highest priority)
        if fetched_issues:
            context_parts.append("**Real-time Issue Details:**")
            context_parts.append(format_fetched_issues(fetched_issues))
            context_parts.append("")

        session_maker = get_session_maker()

        # Get recent issues and briefings from database
        for session in get_db_session(session_maker):
            issue_repo = IssueHistoryRepository(session)
            briefing_repo = BriefingRepository(session)

            # Recent issues (last 30 days)
            recent_issues = issue_repo.get_all_latest_snapshots(days=30)
            if recent_issues:
                # Filter user's assigned issues
                from linear_chief.config import LINEAR_USER_NAME, LINEAR_USER_EMAIL

                user_issues = []
                other_issues = []

                for issue in recent_issues:
                    assignee_name = getattr(issue, "assignee_name", None)
                    assignee_email = getattr(issue, "assignee_email", None)

                    # Check if assigned to configured user (with diacritic-aware matching)
                    is_user_issue = _is_user_assignee(
                        assignee_name=assignee_name,
                        assignee_email=assignee_email,
                        user_name=LINEAR_USER_NAME or "",
                        user_email=LINEAR_USER_EMAIL or "",
                    )

                    if is_user_issue:
                        user_issues.append(issue)
                    else:
                        other_issues.append(issue)

                # Add user's issues FIRST (highest priority)
                if user_issues:
                    context_parts.append(_format_user_assigned_issues(user_issues))

                # Then add other team issues
                if other_issues:
                    context_parts.append(_format_recent_issues(other_issues))

            # Recent briefings (last 7 days)
            recent_briefings = briefing_repo.get_recent_briefings(days=7)
            if recent_briefings:
                context_parts.append(_format_recent_briefings(recent_briefings))

        # Add semantically similar issues if requested
        if include_vector_search and query:
            similar_issues = await get_relevant_issues(query, limit=5)
            if similar_issues:
                context_parts.append(_format_similar_issues(similar_issues))

        # Add current date
        context_parts.append(f"Current Date: {datetime.utcnow().strftime('%Y-%m-%d')}")

        context = "\n\n---\n\n".join(context_parts)

        logger.info(
            "Context built successfully",
            extra={
                "context_length": len(context),
                "sections": len(context_parts),
                "real_time_issues": len(fetched_issues),
            },
        )

        return context

    except Exception as e:
        logger.error(
            "Failed to build conversation context",
            extra={
                "user_id": user_id,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        # Return minimal context instead of failing completely
        return f"Current Date: {datetime.utcnow().strftime('%Y-%m-%d')}\n\nNote: Unable to load full context due to an error."


async def get_relevant_issues(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get issues relevant to user query using vector search.

    Args:
        query: User's query text
        limit: Max number of issues to return

    Returns:
        List of relevant issues with metadata

    Raises:
        Exception: If vector search fails (logged and re-raised)
    """
    logger.info(
        "Searching for relevant issues",
        extra={
            "query_length": len(query),
            "limit": limit,
        },
    )

    try:
        vector_store = IssueVectorStore()
        similar_issues = await vector_store.search_similar(query, limit=limit)

        logger.info(
            "Found relevant issues",
            extra={
                "count": len(similar_issues),
            },
        )

        return similar_issues

    except Exception as e:
        logger.error(
            "Failed to search relevant issues",
            extra={
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return []


def _format_user_assigned_issues(issues: List[Any]) -> str:
    """
    Format issues assigned to the configured user.

    Args:
        issues: List of IssueHistory instances assigned to user

    Returns:
        Formatted string emphasizing these are USER's issues
    """
    from linear_chief.config import LINEAR_USER_NAME

    lines = [f"**YOUR Assigned Issues** ({LINEAR_USER_NAME or 'You'}):"]

    # Group by state
    by_state: Dict[str, List[Any]] = {}
    for issue in issues:
        state = issue.state  # type: ignore[attr-defined]
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(issue)

    # Format each state group
    for state, state_issues in sorted(by_state.items()):
        lines.append(f"\n{state} ({len(state_issues)}):")

        # Show all user's issues (not just top 3)
        for issue in state_issues:
            issue_id = issue.issue_id  # type: ignore[attr-defined]
            title = issue.title  # type: ignore[attr-defined]

            # Truncate long titles
            if len(title) > 60:
                title = title[:57] + "..."

            lines.append(f"  - {issue_id}: {title}")

    return "\n".join(lines)


def _format_recent_issues(issues: List[Any]) -> str:
    """
    Format recent issues for context.

    Args:
        issues: List of IssueHistory instances

    Returns:
        Formatted string
    """
    lines = ["Recent Issues (last 30 days):"]

    # Group by state and sort by priority
    by_state: Dict[str, List[Any]] = {}
    for issue in issues:
        state = issue.state  # type: ignore[attr-defined]
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(issue)

    # Format each state group
    for state, state_issues in sorted(by_state.items()):
        lines.append(f"\n{state} ({len(state_issues)}):")

        # Show top 3 issues per state
        for issue in state_issues[:3]:
            issue_id = issue.issue_id  # type: ignore[attr-defined]
            title = issue.title  # type: ignore[attr-defined]
            assignee = issue.assignee_name or "Unassigned"  # type: ignore[attr-defined]

            # Truncate long titles
            if len(title) > 60:
                title = title[:57] + "..."

            lines.append(f"  • {issue_id}: {title} (Assignee: {assignee})")

        if len(state_issues) > 3:
            lines.append(f"  ... and {len(state_issues) - 3} more")

    return "\n".join(lines)


def _format_recent_briefings(briefings: List[Any]) -> str:
    """
    Format recent briefings for context.

    Args:
        briefings: List of Briefing instances

    Returns:
        Formatted string
    """
    lines = ["Recent Briefings (last 7 days):"]

    for briefing in briefings[:3]:  # Show top 3 briefings
        generated_at = briefing.generated_at  # type: ignore[attr-defined]
        issue_count = briefing.issue_count  # type: ignore[attr-defined]
        content = briefing.content  # type: ignore[attr-defined]

        # Format timestamp
        days_ago = (datetime.utcnow() - generated_at).days
        if days_ago == 0:
            time_str = "Today"
        elif days_ago == 1:
            time_str = "Yesterday"
        else:
            time_str = f"{days_ago} days ago"

        lines.append(f"\n{time_str} ({issue_count} issues):")

        # Extract first section (usually Key Issues or summary)
        # Take first 500 chars to provide more context for briefing queries
        content_preview = content[:500]
        if len(content) > 500:
            content_preview += "..."

        lines.append(f"  {content_preview}")

    return "\n".join(lines)


def _format_similar_issues(issues: List[Dict[str, Any]]) -> str:
    """
    Format semantically similar issues for context.

    Args:
        issues: List of issue dicts from vector search

    Returns:
        Formatted string
    """
    lines = ["Issues Related to Your Query:"]

    for issue in issues:
        issue_id = issue.get("issue_id", "Unknown")
        document = issue.get("document", "")
        distance = issue.get("distance")

        # Extract title from document (first line)
        title = document.split("\n")[0] if document else "No title"
        if len(title) > 60:
            title = title[:57] + "..."

        # Format similarity score (lower distance = more similar)
        if distance is not None:
            similarity = max(0, 1 - distance) * 100
            lines.append(f"  • {issue_id}: {title} (similarity: {similarity:.0f}%)")
        else:
            lines.append(f"  • {issue_id}: {title}")

    return "\n".join(lines)


def check_issue_query(query: str) -> bool:
    """
    Check if query is likely about specific issues (for vector search).

    Args:
        query: User's query text

    Returns:
        True if query seems issue-specific, False otherwise
    """
    issue_keywords = [
        "issue",
        "task",
        "bug",
        "feature",
        "ticket",
        "blocked",
        "blocker",
        "priority",
        "status",
        "working on",
        "assigned to",
    ]

    query_lower = query.lower()
    return any(keyword in query_lower for keyword in issue_keywords)


def extract_issue_ids(query: str) -> List[str]:
    """
    Extract Linear issue IDs from user query.

    Detects patterns like:
    - DMD-480
    - CSM-93
    - AI-1799

    Args:
        query: User's query text

    Returns:
        List of issue IDs found (e.g., ['CSM-93', 'DMD-480'])
    """
    # Pattern: 1-4 uppercase letters, dash, 1-5 digits
    # Examples: DMD-480, CSM-93, AI-1799, PROJ-12345
    pattern = r"\b([A-Z]{1,4}-\d{1,5})\b"

    issue_ids = re.findall(pattern, query)
    return list(set(issue_ids))  # Deduplicate


def _issue_history_to_dict(issue: Any) -> Dict[str, Any]:
    """
    Convert IssueHistory ORM model to Linear API dict format.

    Reconstructs the same structure that Linear API returns for consistency
    with the rest of the application.

    Args:
        issue: IssueHistory ORM instance

    Returns:
        Dict matching Linear API structure
    """
    # Extract metadata fields
    metadata = issue.extra_metadata or {}

    # Reconstruct issue dict
    issue_dict = {
        "id": issue.linear_id,
        "identifier": issue.issue_id,
        "title": issue.title,
        "state": {"name": issue.state},
        "priority": issue.priority or 0,
        "priorityLabel": metadata.get("priority_label", "None"),
        "url": metadata.get("url"),
        "createdAt": metadata.get("created_at"),
        "updatedAt": metadata.get("updated_at"),
        "completedAt": metadata.get("completed_at"),
        "canceledAt": metadata.get("canceled_at"),
        "description": metadata.get("description", ""),
    }

    # Add assignee if present
    if issue.assignee_id:
        issue_dict["assignee"] = {
            "id": issue.assignee_id,
            "name": issue.assignee_name,
            "email": metadata.get("assignee_email"),
        }

    # Add team if present
    if issue.team_id:
        issue_dict["team"] = {
            "id": issue.team_id,
            "name": issue.team_name,
        }

    # Add creator if present in metadata
    creator_name = metadata.get("creator")
    if creator_name:
        issue_dict["creator"] = {"name": creator_name}

    # Add labels
    if issue.labels:
        issue_dict["labels"] = {"nodes": [{"name": label} for label in issue.labels]}

    # Add comments if present in metadata
    comments = metadata.get("comments", [])
    if comments:
        issue_dict["comments"] = {"nodes": comments}

    return issue_dict


async def fetch_issue_details(issue_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch full issue details with intelligent caching.

    Workflow:
    1. Check DB for fresh data (age < CACHE_TTL_HOURS) for each issue
    2. If found in cache, use cached data (log: "Using cached data for {issue_id}")
    3. If not found or stale, fetch from Linear API (log: "Fetching {issue_id} from Linear API")
    4. Save API results to DB for future caching

    Benefits:
    - Reduces API calls when user queries same issues repeatedly
    - Faster responses for cached issues
    - Fallback to API if cache is stale
    - Non-fatal DB failures (always falls back to API)
    - Configurable cache TTL via CACHE_TTL_HOURS environment variable

    Args:
        issue_ids: List of issue identifiers (e.g., ['CSM-93', 'DMD-480'])

    Returns:
        List of issue dictionaries with full details
    """
    from linear_chief.config import LINEAR_API_KEY
    from linear_chief.linear.client import LinearClient

    if not issue_ids:
        return []

    if not LINEAR_API_KEY:
        logger.warning("LINEAR_API_KEY not configured, cannot fetch issues")
        return []

    issues = []

    # Step 1: Check DB cache for each issue
    cached_issues: Dict[str, Dict[str, Any]] = {}
    uncached_issue_ids: List[str] = []

    try:
        session_maker = get_session_maker()
        for session in get_db_session(session_maker):
            issue_repo = IssueHistoryRepository(session)

            for issue_id in issue_ids:
                cached = issue_repo.get_issue_snapshot_by_identifier(
                    issue_id, max_age_hours=CACHE_TTL_HOURS
                )

                if cached:
                    logger.info(f"Using cached data for {issue_id}")
                    cached_issues[issue_id] = _issue_history_to_dict(cached)
                else:
                    logger.info(f"Cache miss for {issue_id}, will fetch from API")
                    uncached_issue_ids.append(issue_id)

    except Exception as e:
        logger.warning(
            "DB cache lookup failed (non-fatal), falling back to API",
            extra={"error_type": type(e).__name__, "error": str(e)},
        )
        # Fall back to fetching all issues from API
        uncached_issue_ids = issue_ids
        cached_issues = {}

    # Step 2: Add cached issues to results
    for issue_id in issue_ids:
        if issue_id in cached_issues:
            issues.append(cached_issues[issue_id])

    # Step 3: Fetch uncached issues from Linear API
    if uncached_issue_ids:
        try:
            async with LinearClient(LINEAR_API_KEY) as client:
                for issue_id in uncached_issue_ids:
                    logger.info(f"Fetching {issue_id} from Linear API")
                    issue = await client.get_issue_by_identifier(issue_id)

                    if issue:
                        issues.append(issue)

                        # Step 4: Save to DB for future caching
                        try:
                            await _save_fetched_issue_to_db(issue)
                            logger.info(f"Saved {issue_id} to local DB cache")
                        except Exception as e:
                            logger.warning(
                                f"Failed to save {issue_id} to DB cache (non-fatal)",
                                extra={"error": str(e)},
                            )

        except Exception as e:
            logger.error(
                "Failed to fetch issue details from Linear API",
                extra={
                    "issue_ids": uncached_issue_ids,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

    logger.info(
        "Issue fetch completed",
        extra={
            "requested_count": len(issue_ids),
            "cached_count": len(cached_issues),
            "fetched_count": len(uncached_issue_ids),
            "total_returned": len(issues),
        },
    )

    return issues


async def _save_fetched_issue_to_db(issue: Dict[str, Any]) -> None:
    """
    Save fetched issue to local DB for historical tracking.

    Uses IssueHistoryRepository.save_snapshot() to store issue details.
    This is a non-blocking helper - failures are logged but don't crash fetch.

    Args:
        issue: Issue dictionary from Linear API

    Raises:
        Exception: If database save fails (caller should catch and log)
    """
    # Extract fields for snapshot
    issue_id = issue.get("identifier")
    if not issue_id:
        logger.warning("Issue missing identifier, cannot save")
        return

    # Import here to avoid circular dependencies
    session_maker = get_session_maker()

    for session in get_db_session(session_maker):
        repo = IssueHistoryRepository(session)

        # Extract label names from nodes structure
        labels_data = issue.get("labels", {}).get("nodes", [])
        labels = [label.get("name") for label in labels_data if label.get("name")]

        # Extract assignee email if available
        assignee_email = None
        if issue.get("assignee"):
            assignee_email = issue.get("assignee", {}).get("email")

        # Extract comments if available
        comments_data = issue.get("comments", {}).get("nodes", [])

        # Save snapshot with all available data
        repo.save_snapshot(
            issue_id=issue_id,
            linear_id=issue.get("id", ""),
            title=issue.get("title", ""),
            state=issue.get("state", {}).get("name", "Unknown"),
            priority=issue.get("priority", 0),
            assignee_id=(
                issue.get("assignee", {}).get("id") if issue.get("assignee") else None
            ),
            assignee_name=(
                issue.get("assignee", {}).get("name") if issue.get("assignee") else None
            ),
            team_id=(issue.get("team", {}).get("id") if issue.get("team") else None),
            team_name=(
                issue.get("team", {}).get("name") if issue.get("team") else None
            ),
            labels=labels if labels else None,
            extra_metadata={
                "url": issue.get("url"),
                "created_at": issue.get("createdAt"),
                "updated_at": issue.get("updatedAt"),
                "completed_at": issue.get("completedAt"),
                "canceled_at": issue.get("canceledAt"),
                "priority_label": issue.get("priorityLabel"),
                "description": issue.get("description", ""),
                "assignee_email": assignee_email,
                "creator": (
                    issue.get("creator", {}).get("name")
                    if issue.get("creator")
                    else None
                ),
                "comments": comments_data if comments_data else None,
            },
        )

        logger.debug(f"Saved snapshot for {issue_id} to DB")


def format_fetched_issues(issues: List[Dict[str, Any]]) -> str:
    """
    Format real-time fetched issues for context.

    Provides FULL details unlike stored snapshots.

    Args:
        issues: List of issue dictionaries from Linear API

    Returns:
        Formatted string with full issue details
    """
    if not issues:
        return ""

    formatted = []
    for issue in issues:
        identifier = issue.get("identifier", "N/A")
        title = issue.get("title", "Untitled")
        state = issue.get("state", {}).get("name", "Unknown")
        priority = issue.get("priorityLabel", "None")
        assignee_data = issue.get("assignee")
        assignee = (
            assignee_data.get("name", "Unassigned") if assignee_data else "Unassigned"
        )

        # Full description (not truncated!)
        description = issue.get("description", "")
        if not description:
            description = "(No description)"

        # All comments (not just latest!)
        comments = issue.get("comments", {}).get("nodes", [])

        issue_text = f"""
{identifier}: {title}
Status: {state}
Priority: {priority}
Assignee: {assignee}
URL: {issue.get("url", "N/A")}

Description:
{description}
"""

        if comments:
            issue_text += f"\nComments ({len(comments)}):\n"
            for comment in comments:
                # Handle None user (deleted users or system comments)
                user = comment.get("user") or {}
                author = user.get("name", "Unknown")
                body = comment.get("body", "")
                created = (
                    comment.get("createdAt", "")[:10]
                    if comment.get("createdAt")
                    else "Unknown"
                )
                issue_text += f"\n[{created}] {author}:\n{body}\n"

        formatted.append(issue_text.strip())

    return "\n\n---\n\n".join(formatted)
