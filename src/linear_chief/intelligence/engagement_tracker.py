"""Engagement tracker for user interactions with Linear issues.

This module tracks which issues users interact with (queries, mentions, views)
to learn engagement patterns and improve issue ranking for personalized briefings.
"""

import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any

from linear_chief.storage import get_session_maker, get_db_session
from linear_chief.storage.repositories import IssueEngagementRepository
from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)


class EngagementTracker:
    """
    Track user engagement with Linear issues for intelligent ranking.

    Engagement is tracked through:
    - Queries: User explicitly asks about an issue (e.g., "what's the status of AI-1799?")
    - Views: User views issue in a briefing
    - Mentions: User mentions issue in conversation

    Engagement score (0.0 to 1.0) is calculated using:
        score = (frequency_score * 0.4) + (recency_score * 0.6)

    Where:
        - frequency_score: How often user queries this issue (normalized)
        - recency_score: How recently user interacted (exponential decay)
    """

    async def track_issue_mention(
        self,
        user_id: str,
        issue_id: str,
        interaction_type: str,
        linear_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> None:
        """
        Track when user interacts with an issue.

        Examples:
            - User queries: "dej mi detail AI-1799"
            - User mentions in conversation: "jak jde AI-1799?"
            - User views in briefing (when they ask for briefing)

        Args:
            user_id: User identifier (Telegram user_id)
            issue_id: Issue identifier (e.g., "AI-1799", "DMD-480")
            interaction_type: Type of interaction ("query", "view", "mention")
            linear_id: Linear UUID (optional, fetched if not provided)
            context: User's message or context (first 200 chars stored)

        Raises:
            ValueError: If interaction_type is invalid
            Exception: If database operation fails (logged and re-raised)
        """
        valid_types = ("query", "view", "mention")
        if interaction_type not in valid_types:
            raise ValueError(
                f"Invalid interaction_type: {interaction_type}. "
                f"Must be one of {valid_types}"
            )

        logger.info(
            "Tracking issue engagement",
            extra={
                "user_id": user_id,
                "issue_id": issue_id,
                "interaction_type": interaction_type,
            },
        )

        try:
            session_maker = get_session_maker()

            # Fetch linear_id if not provided
            if not linear_id:
                linear_id = await self._fetch_linear_id(issue_id)
                if not linear_id:
                    logger.warning(
                        f"Could not fetch linear_id for {issue_id}, using issue_id as fallback"
                    )
                    linear_id = issue_id

            # Truncate context to 200 chars
            if context and len(context) > 200:
                context = context[:200]

            for session in get_db_session(session_maker):
                repo = IssueEngagementRepository(session)

                # Record interaction (upsert)
                engagement = repo.record_interaction(
                    user_id=user_id,
                    issue_id=issue_id,
                    linear_id=linear_id,
                    interaction_type=interaction_type,
                    context=context,
                )

                # Calculate and update engagement score
                new_score = await self.calculate_engagement_score(user_id, issue_id)
                repo.update_score(user_id, issue_id, new_score)

                logger.info(
                    "Issue engagement tracked",
                    extra={
                        "user_id": user_id,
                        "issue_id": issue_id,
                        "interaction_count": engagement.interaction_count,  # type: ignore[attr-defined]
                        "engagement_score": new_score,
                    },
                )

        except Exception as e:
            logger.error(
                "Failed to track issue engagement",
                extra={
                    "user_id": user_id,
                    "issue_id": issue_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def calculate_engagement_score(
        self, user_id: str, issue_id: str
    ) -> float:
        """
        Calculate engagement score for issue (0.0 to 1.0).

        Formula:
            score = (frequency_score * 0.4) + (recency_score * 0.6)

        Where:
            - frequency_score: How often user queries this issue (normalized)
            - recency_score: How recently user interacted (exponential decay)

        Args:
            user_id: User identifier
            issue_id: Issue identifier

        Returns:
            Engagement score between 0.0 and 1.0

        Raises:
            Exception: If database query fails (logged and re-raised)
        """
        try:
            session_maker = get_session_maker()

            for session in get_db_session(session_maker):
                repo = IssueEngagementRepository(session)

                # Get engagement record
                engagement = repo.get_engagement(user_id, issue_id)

                if not engagement:
                    # No interaction yet, return default score
                    return 0.5

                # Extract interaction data
                interaction_count: int = engagement.interaction_count  # type: ignore[attr-defined]
                last_interaction: datetime = engagement.last_interaction  # type: ignore[attr-defined]

                # Calculate frequency score (normalized)
                # 1 interaction = 0.2, 5 interactions = 1.0 (max)
                frequency_score = min(1.0, interaction_count * 0.2)

                # Calculate recency score (exponential decay)
                days_since = (datetime.utcnow() - last_interaction).days
                recency_score = self._calculate_recency_score(days_since)

                # Combine with weighted formula
                score = (frequency_score * 0.4) + (recency_score * 0.6)

                logger.debug(
                    "Calculated engagement score",
                    extra={
                        "user_id": user_id,
                        "issue_id": issue_id,
                        "interaction_count": interaction_count,
                        "days_since": days_since,
                        "frequency_score": frequency_score,
                        "recency_score": recency_score,
                        "final_score": score,
                    },
                )

                return score

        except Exception as e:
            logger.error(
                "Failed to calculate engagement score",
                extra={
                    "user_id": user_id,
                    "issue_id": issue_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def get_top_engaged_issues(
        self, user_id: str, limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get issues user is most engaged with.

        Args:
            user_id: User identifier
            limit: Maximum number of issues to return

        Returns:
            List of (issue_id, engagement_score) tuples sorted by score descending

        Raises:
            Exception: If database query fails (logged and re-raised)
        """
        logger.info(
            "Getting top engaged issues",
            extra={
                "user_id": user_id,
                "limit": limit,
            },
        )

        try:
            session_maker = get_session_maker()

            for session in get_db_session(session_maker):
                repo = IssueEngagementRepository(session)

                # Get top engaged issues
                engagements = repo.get_top_engaged(user_id, limit=limit)

                # Convert to tuples
                results = [
                    (
                        eng.issue_id,  # type: ignore[attr-defined]
                        eng.engagement_score,  # type: ignore[attr-defined]
                    )
                    for eng in engagements
                ]

                logger.info(
                    "Retrieved top engaged issues",
                    extra={
                        "user_id": user_id,
                        "count": len(results),
                    },
                )

                return results

        except Exception as e:
            logger.error(
                "Failed to get top engaged issues",
                extra={
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def get_engagement_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get engagement statistics for user.

        Returns:
            {
                "total_interactions": 127,
                "unique_issues": 43,
                "avg_interactions_per_issue": 2.95,
                "most_engaged_issues": ["AI-1799", "DMD-480"],
                "last_interaction": "2025-11-05T16:30:00Z"
            }

        Args:
            user_id: User identifier

        Returns:
            Dictionary with engagement statistics

        Raises:
            Exception: If database query fails (logged and re-raised)
        """
        logger.info(
            "Getting engagement statistics",
            extra={"user_id": user_id},
        )

        try:
            session_maker = get_session_maker()

            for session in get_db_session(session_maker):
                repo = IssueEngagementRepository(session)

                # Get all engagements
                engagements = repo.get_all_engagements(user_id)

                if not engagements:
                    return {
                        "total_interactions": 0,
                        "unique_issues": 0,
                        "avg_interactions_per_issue": 0.0,
                        "most_engaged_issues": [],
                        "last_interaction": None,
                    }

                # Calculate stats
                total_interactions = sum(
                    eng.interaction_count for eng in engagements  # type: ignore[attr-defined]
                )
                unique_issues = len(engagements)
                avg_interactions = total_interactions / unique_issues if unique_issues > 0 else 0.0

                # Get top 5 most engaged issues
                top_engagements = sorted(
                    engagements,
                    key=lambda e: e.engagement_score,  # type: ignore[attr-defined]
                    reverse=True,
                )[:5]
                most_engaged_issues = [
                    eng.issue_id for eng in top_engagements  # type: ignore[attr-defined]
                ]

                # Get most recent interaction
                latest_engagement = max(
                    engagements,
                    key=lambda e: e.last_interaction,  # type: ignore[attr-defined]
                )
                last_interaction: datetime = latest_engagement.last_interaction  # type: ignore[attr-defined]

                stats = {
                    "total_interactions": total_interactions,
                    "unique_issues": unique_issues,
                    "avg_interactions_per_issue": round(avg_interactions, 2),
                    "most_engaged_issues": most_engaged_issues,
                    "last_interaction": last_interaction.isoformat() + "Z",
                }

                logger.info(
                    "Retrieved engagement statistics",
                    extra={
                        "user_id": user_id,
                        "stats": stats,
                    },
                )

                return stats

        except Exception as e:
            logger.error(
                "Failed to get engagement statistics",
                extra={
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def decay_old_engagements(self, days: int = 30) -> int:
        """
        Decay engagement scores for old interactions.

        Reduces score by 10% per week for interactions older than `days`.
        This ensures engagement scores reflect recent user interest.

        Args:
            days: Threshold in days (interactions older than this get decayed)

        Returns:
            Number of engagement records decayed

        Raises:
            Exception: If database operation fails (logged and re-raised)
        """
        logger.info(
            "Decaying old engagements",
            extra={"days_threshold": days},
        )

        try:
            session_maker = get_session_maker()

            # Note: For MVP, we'll use the recency decay built into score calculation
            # This is a placeholder for future batch decay jobs
            # In production, this would be a scheduled job

            # Get all users' engagements
            # For now, we'll just log this operation
            # Future: Implement batch decay for all users

            logger.info(
                "Old engagement decay completed",
                extra={
                    "days_threshold": days,
                    "decayed_count": 0,  # Placeholder
                },
            )

            return 0

        except Exception as e:
            logger.error(
                "Failed to decay old engagements",
                extra={
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    def _calculate_recency_score(self, days_since_interaction: int) -> float:
        """
        Calculate recency score using exponential decay.

        Examples:
            - 0 days: 1.0 (perfect)
            - 7 days: 0.7
            - 14 days: 0.5
            - 30 days: 0.2
            - 60+ days: 0.0

        Args:
            days_since_interaction: Number of days since last interaction

        Returns:
            Recency score between 0.0 and 1.0
        """
        if days_since_interaction <= 0:
            return 1.0

        # Exponential decay: score = e^(-decay_rate * days)
        # decay_rate = 0.05 means ~5% decay per day
        decay_rate = 0.05
        score = math.exp(-decay_rate * days_since_interaction)

        # Clamp to [0.0, 1.0] range
        return max(0.0, min(1.0, score))

    async def _fetch_linear_id(self, issue_id: str) -> Optional[str]:
        """
        Fetch Linear UUID for issue identifier.

        Queries IssueHistory table for the most recent snapshot of this issue.

        Args:
            issue_id: Issue identifier (e.g., "AI-1799")

        Returns:
            Linear UUID or None if not found
        """
        try:
            from linear_chief.storage.repositories import IssueHistoryRepository

            session_maker = get_session_maker()

            for session in get_db_session(session_maker):
                issue_repo = IssueHistoryRepository(session)
                snapshot = issue_repo.get_latest_snapshot(issue_id)

                if snapshot:
                    linear_id: str = snapshot.linear_id  # type: ignore[attr-defined]
                    return linear_id

            return None

        except Exception as e:
            logger.warning(
                f"Failed to fetch linear_id for {issue_id}: {e}",
                extra={"error_type": type(e).__name__},
            )
            return None
