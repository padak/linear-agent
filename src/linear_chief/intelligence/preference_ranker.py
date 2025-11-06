"""Preference-based ranking enhancer for personalized issue prioritization.

This module enhances the base issue priority calculation by incorporating learned
user preferences (topics, teams, labels) and engagement history to create
personalized priority scores for briefings.

Example Usage:

    from linear_chief.intelligence.preference_ranker import PreferenceBasedRanker

    ranker = PreferenceBasedRanker(user_id="user@example.com")

    # Calculate personalized priority for a single issue
    personalized_priority = await ranker.calculate_personalized_priority(
        issue=issue_dict,
        base_priority=7.0,
    )

    # Rank multiple issues
    ranked_issues = await ranker.rank_issues(issues, base_priorities)
"""

import logging
from typing import Any, Optional
from collections import defaultdict

from ..config import LINEAR_USER_EMAIL
from .preference_learner import TOPIC_KEYWORDS

logger = logging.getLogger(__name__)


def extract_topics(text: str) -> list[str]:
    """
    Extract topics from text using keyword matching.

    Uses TOPIC_KEYWORDS dictionary to detect topics in issue titles and descriptions.

    Args:
        text: Combined title + description

    Returns:
        List of detected topics (e.g., ["backend", "api"])

    Example:
        >>> extract_topics("Backend API optimization for database performance")
        ["backend", "performance"]
    """
    text_lower = text.lower()
    detected = []

    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            detected.append(topic)

    return detected


class PreferenceBasedRanker:
    """
    Enhances issue ranking with user preference data.

    Combines base priority (urgency, blocking, stagnation) with learned preferences
    (topics, teams, labels) to create personalized priority scores.

    The personalized priority is calculated using:
        personalized = base_priority * (1 + preference_boost + engagement_boost)

    Where:
        - preference_boost: Average of topic/team/label preference scores (-0.5 to +0.5)
        - engagement_boost: User engagement with this specific issue (0.0 to +0.3)

    Attributes:
        user_id: User identifier for preference lookup
        preference_learner: Lazy-loaded PreferenceLearner instance
        engagement_tracker: Lazy-loaded EngagementTracker instance
        _cached_preferences: Cached preference data
    """

    def __init__(self, user_id: str | None = None) -> None:
        """
        Initialize PreferenceBasedRanker.

        Args:
            user_id: User identifier (defaults to LINEAR_USER_EMAIL from config)
        """
        self.user_id = user_id or LINEAR_USER_EMAIL or "default_user"
        self.preference_learner = None  # Lazy load
        self.engagement_tracker = None  # Lazy load
        self._cached_preferences: dict[str, Any] | None = None

        logger.info(f"Initialized PreferenceBasedRanker for user {self.user_id}")

    async def calculate_personalized_priority(
        self,
        issue: dict[str, Any],
        base_priority: float,
        context: dict[str, Any] | None = None,
    ) -> float:
        """
        Calculate personalized priority for an issue.

        Combines base priority with user preferences and engagement to create
        a personalized score that reflects user interests.

        Args:
            issue: Issue dictionary with title, description, team, labels, etc.
            base_priority: Base priority from IssueAnalyzer (0.0 to 10.0)
            context: Optional context (preferences, engagement scores)

        Returns:
            Personalized priority score (0.0 to 10.0)

        Formula:
            personalized = base_priority * (1 + preference_boost + engagement_boost)

        Where:
            preference_boost = (topic_score + team_score + label_score) / 3 - 0.5
                              # Range: -0.5 to +0.5 (neutral at 0.5 preference)
            engagement_boost = engagement_score * 0.3
                              # Range: 0.0 to +0.3

        Examples:
            base=8.0, prefs=0.9, engagement=0.8 → 8.0 * (1 + 0.4 + 0.24) = 13.12 → 10.0
            base=5.0, prefs=0.3, engagement=0.1 → 5.0 * (1 - 0.2 + 0.03) = 4.15
            base=7.0, prefs=0.5, engagement=0.0 → 7.0 * (1 + 0.0 + 0.0) = 7.0

        Raises:
            Exception: If preference/engagement loading fails (logged and continued)
        """
        try:
            # Load preferences if not cached
            if not self._cached_preferences:
                await self._load_preferences()

            # Calculate preference component scores
            topic_score = await self.get_topic_score(issue)
            team_score = await self.get_team_score(issue)
            label_score = await self.get_label_score(issue)

            # Calculate preference boost (-0.5 to +0.5)
            # Average preference of 0.5 = neutral (no boost)
            avg_preference = (topic_score + team_score + label_score) / 3
            preference_boost = avg_preference - 0.5

            # Calculate engagement boost (0.0 to +0.3)
            engagement_score = await self.get_engagement_score(issue)
            engagement_boost = engagement_score * 0.3

            # Apply formula
            personalized = base_priority * (1 + preference_boost + engagement_boost)

            # Cap at 10.0
            personalized = min(personalized, 10.0)

            logger.debug(
                f"Personalized priority for {issue.get('identifier', 'unknown')}: "
                f"base={base_priority:.2f}, topic={topic_score:.2f}, "
                f"team={team_score:.2f}, label={label_score:.2f}, "
                f"engagement={engagement_score:.2f}, "
                f"personalized={personalized:.2f}"
            )

            return personalized

        except Exception as e:
            logger.error(
                f"Error calculating personalized priority for issue "
                f"{issue.get('identifier', 'unknown')}: {e}",
                exc_info=True,
            )
            # Fallback to base priority on error
            return base_priority

    async def get_topic_score(self, issue: dict[str, Any]) -> float:
        """
        Get preference score for issue topics.

        Analyzes title + description for topic keywords using extract_topics().
        Returns average preference score for detected topics.

        Args:
            issue: Issue dictionary with title and description

        Returns:
            Average topic preference score (0.0 to 1.0), 0.5 if no topics detected
        """
        try:
            # Extract topics from title + description
            title = issue.get("title", "")
            description = issue.get("description", "")
            combined_text = f"{title} {description}"

            detected_topics = extract_topics(combined_text)

            if not detected_topics:
                return 0.5  # Neutral score

            # Get preferences
            if not self._cached_preferences:
                await self._load_preferences()

            topic_scores = self._cached_preferences.get("topic_scores", {})

            # Calculate average score for detected topics
            scores = [topic_scores.get(topic, 0.5) for topic in detected_topics]
            avg_score = sum(scores) / len(scores) if scores else 0.5

            logger.debug(
                f"Topic score for {issue.get('identifier', 'unknown')}: "
                f"topics={detected_topics}, score={avg_score:.2f}"
            )

            return avg_score

        except Exception as e:
            logger.error(f"Error calculating topic score: {e}", exc_info=True)
            return 0.5  # Neutral score on error

    async def get_team_score(self, issue: dict[str, Any]) -> float:
        """
        Get preference score for issue team.

        Args:
            issue: Issue dictionary with team information

        Returns:
            Team preference score (0.0 to 1.0), 0.5 if no preference
        """
        try:
            # Extract team name
            team = issue.get("team", {})
            team_name = team.get("name") if isinstance(team, dict) else None

            if not team_name:
                return 0.5  # Neutral score

            # Get preferences
            if not self._cached_preferences:
                await self._load_preferences()

            team_scores = self._cached_preferences.get("team_scores", {})
            score = team_scores.get(team_name, 0.5)

            logger.debug(
                f"Team score for {issue.get('identifier', 'unknown')}: "
                f"team={team_name}, score={score:.2f}"
            )

            return score

        except Exception as e:
            logger.error(f"Error calculating team score: {e}", exc_info=True)
            return 0.5  # Neutral score on error

    async def get_label_score(self, issue: dict[str, Any]) -> float:
        """
        Get preference score for issue labels.

        Args:
            issue: Issue dictionary with labels

        Returns:
            Average label preference score (0.0 to 1.0), 0.5 if no labels/preferences
        """
        try:
            # Extract label names
            labels = issue.get("labels", {})

            # Handle both list and dict formats
            if isinstance(labels, dict):
                label_nodes = labels.get("nodes", [])
            elif isinstance(labels, list):
                label_nodes = labels
            else:
                return 0.5  # Neutral score

            label_names = [
                label.get("name")
                for label in label_nodes
                if isinstance(label, dict) and label.get("name")
            ]

            if not label_names:
                return 0.5  # Neutral score

            # Get preferences
            if not self._cached_preferences:
                await self._load_preferences()

            label_scores = self._cached_preferences.get("label_scores", {})

            # Calculate average score for labels
            scores = [label_scores.get(label, 0.5) for label in label_names]
            avg_score = sum(scores) / len(scores) if scores else 0.5

            logger.debug(
                f"Label score for {issue.get('identifier', 'unknown')}: "
                f"labels={label_names}, score={avg_score:.2f}"
            )

            return avg_score

        except Exception as e:
            logger.error(f"Error calculating label score: {e}", exc_info=True)
            return 0.5  # Neutral score on error

    async def get_engagement_score(self, issue: dict[str, Any]) -> float:
        """
        Get engagement score for this issue.

        Loads engagement data from EngagementTracker to see how often
        the user has interacted with this specific issue.

        Args:
            issue: Issue dictionary with identifier

        Returns:
            Engagement score (0.0 to 1.0), 0.0 if no engagement
        """
        try:
            issue_id = issue.get("identifier")
            if not issue_id:
                return 0.0

            # Lazy load engagement tracker
            if not self.engagement_tracker:
                from .engagement_tracker import EngagementTracker

                self.engagement_tracker = EngagementTracker()

            # Get engagement score
            score = await self.engagement_tracker.calculate_engagement_score(
                user_id=self.user_id, issue_id=issue_id
            )

            logger.debug(f"Engagement score for {issue_id}: {score:.2f}")

            return score

        except Exception as e:
            logger.error(f"Error getting engagement score: {e}", exc_info=True)
            return 0.0  # No engagement on error

    async def rank_issues(
        self,
        issues: list[dict[str, Any]],
        base_priorities: dict[str, float] | None = None,
    ) -> list[tuple[dict[str, Any], float]]:
        """
        Rank list of issues with personalized priorities.

        Args:
            issues: List of issue dictionaries
            base_priorities: Optional pre-calculated base priorities (issue_id -> priority)

        Returns:
            List of (issue, personalized_priority) tuples sorted by priority desc

        Example:
            ranked = await ranker.rank_issues(issues, {"PROJ-1": 8.0, "PROJ-2": 5.0})
            for issue, priority in ranked:
                print(f"{issue['identifier']}: {priority:.2f}")
        """
        try:
            logger.info(f"Ranking {len(issues)} issues with personalized priorities")

            ranked = []

            for issue in issues:
                issue_id = issue.get("identifier")

                # Get base priority
                if base_priorities and issue_id:
                    base_priority = base_priorities.get(issue_id, 5.0)
                else:
                    # Extract from _analysis if available
                    base_priority = issue.get("_analysis", {}).get("priority", 5.0)

                # Calculate personalized priority
                personalized_priority = await self.calculate_personalized_priority(
                    issue=issue,
                    base_priority=float(base_priority),
                )

                ranked.append((issue, personalized_priority))

            # Sort by priority (highest first)
            ranked.sort(key=lambda x: x[1], reverse=True)

            logger.info(
                f"Ranked {len(ranked)} issues. Top issue: "
                f"{ranked[0][0].get('identifier', 'unknown')} "
                f"(priority: {ranked[0][1]:.2f})"
            )

            return ranked

        except Exception as e:
            logger.error(f"Error ranking issues: {e}", exc_info=True)
            # Return issues with base priorities on error
            return [(issue, issue.get("_analysis", {}).get("priority", 5.0)) for issue in issues]

    async def get_preference_context(self) -> dict[str, Any]:
        """
        Get current preference context for debugging/display.

        Returns:
            {
                "user_id": "...",
                "topic_preferences": {"backend": 0.9, "frontend": 0.3},
                "team_preferences": {"Engineering": 0.85},
                "label_preferences": {"bug": 0.92, "feature": 0.45},
                "last_updated": "2025-11-05T16:30:00Z"
            }
        """
        try:
            if not self._cached_preferences:
                await self._load_preferences()

            context = {
                "user_id": self.user_id,
                "topic_preferences": self._cached_preferences.get("topic_scores", {}),
                "team_preferences": self._cached_preferences.get("team_scores", {}),
                "label_preferences": self._cached_preferences.get("label_scores", {}),
                "last_updated": self._cached_preferences.get("analysis_date", None),
            }

            return context

        except Exception as e:
            logger.error(f"Error getting preference context: {e}", exc_info=True)
            return {
                "user_id": self.user_id,
                "topic_preferences": {},
                "team_preferences": {},
                "label_preferences": {},
                "last_updated": None,
            }

    async def _load_preferences(self) -> None:
        """
        Load user preferences from PreferenceLearner.

        Lazy loads PreferenceLearner and caches preferences for performance.
        """
        try:
            # Lazy load preference learner
            if not self.preference_learner:
                from .preference_learner import PreferenceLearner

                self.preference_learner = PreferenceLearner(user_id=self.user_id)

            # Load preferences
            self._cached_preferences = await self.preference_learner.get_preferences()

            logger.info(
                f"Loaded preferences for user {self.user_id}: "
                f"{len(self._cached_preferences.get('topic_scores', {}))} topics, "
                f"{len(self._cached_preferences.get('team_scores', {}))} teams, "
                f"{len(self._cached_preferences.get('label_scores', {}))} labels"
            )

        except Exception as e:
            logger.error(f"Error loading preferences: {e}", exc_info=True)
            # Use empty preferences on error
            self._cached_preferences = {
                "topic_scores": {},
                "team_scores": {},
                "label_scores": {},
            }
