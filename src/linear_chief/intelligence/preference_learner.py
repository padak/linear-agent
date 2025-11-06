"""Preference Learning Engine for user preference extraction and personalization.

Analyzes user feedback data (thumbs up/down) and conversation patterns to learn
preferences about topics, teams, labels, and issue characteristics. Stores preferences
in both mem0 (for fast retrieval) and SQLite database (for persistence).

Example Usage:

    from linear_chief.intelligence.preference_learner import PreferenceLearner

    learner = PreferenceLearner()

    # Analyze feedback and learn preferences
    preferences = await learner.analyze_feedback_patterns()

    # Save to mem0 and DB
    await learner.save_to_mem0(preferences)

    # Later, retrieve preferences
    prefs = await learner.get_preferences()
    print(prefs["preferred_topics"])  # ["backend", "api"]
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict

from tenacity import retry, stop_after_attempt, wait_exponential

from ..memory.mem0_wrapper import MemoryManager
from ..storage.database import get_session_maker, get_db_session
from ..storage.repositories import FeedbackRepository, IssueHistoryRepository
from ..storage.repositories import UserPreferenceRepository
from ..config import LINEAR_USER_EMAIL

logger = logging.getLogger(__name__)


# Topic detection keywords
TOPIC_KEYWORDS = {
    "backend": ["backend", "api", "server", "database", "sql", "graphql", "rest"],
    "frontend": ["frontend", "ui", "react", "vue", "angular", "css", "html"],
    "infrastructure": [
        "infra",
        "docker",
        "k8s",
        "kubernetes",
        "deploy",
        "ci/cd",
        "cicd",
    ],
    "testing": ["test", "qa", "automation", "playwright", "pytest", "jest"],
    "documentation": ["docs", "documentation", "readme", "guide"],
    "performance": ["performance", "optimize", "slow", "latency", "cache"],
    "security": ["security", "auth", "permission", "vulnerability", "xss", "csrf"],
}


class PreferenceLearner:
    """Learns user preferences from feedback and engagement data.

    Analyzes positive vs negative feedback patterns to extract preferences about:
    - Topics (backend, frontend, infrastructure, etc.)
    - Teams (engineering, platform, etc.)
    - Labels (bug, urgent, enhancement, etc.)
    - Issue characteristics (priority, status, age, etc.)

    Stores learned preferences in both mem0 (for agent context) and
    database (for persistence and analytics).
    """

    def __init__(self, user_id: str | None = None) -> None:
        """Initialize PreferenceLearner.

        Args:
            user_id: User identifier (defaults to LINEAR_USER_EMAIL from config)
        """
        self.user_id = user_id or LINEAR_USER_EMAIL or "default_user"
        self.memory_manager = MemoryManager()
        self.session_maker = get_session_maker()

    async def analyze_feedback_patterns(
        self, days: int = 30, min_feedback_count: int = 3
    ) -> dict[str, Any]:
        """Analyze feedback data to extract preference patterns.

        Queries Feedback and IssueHistory tables to find patterns in
        positive vs negative feedback. Extracts preferences for topics,
        teams, labels, and calculates confidence scores.

        Args:
            days: Number of days of feedback history to analyze
            min_feedback_count: Minimum feedback count to establish preference

        Returns:
            Dict with preference insights:
            {
                "preferred_topics": ["backend", "api", "infrastructure"],
                "preferred_teams": ["engineering", "platform"],
                "preferred_labels": ["bug", "urgent"],
                "disliked_topics": ["frontend", "css"],
                "disliked_teams": [],
                "disliked_labels": ["documentation"],
                "engagement_score": 0.85,
                "confidence": 0.92,
                "feedback_count": 25,
                "analysis_date": "2025-11-05T10:30:00"
            }

        Raises:
            Exception: If database query fails
        """
        logger.info(
            f"Analyzing feedback patterns for user {self.user_id} over last {days} days"
        )

        for session in get_db_session(self.session_maker):
            feedback_repo = FeedbackRepository(session)
            issue_repo = IssueHistoryRepository(session)

            # Get all feedback from the time period
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            all_feedback = feedback_repo.get_recent_feedback(
                days=days, limit=1000
            )  # Generous limit

            if not all_feedback:
                logger.warning(f"No feedback data found for user {self.user_id}")
                return self._empty_preferences()

            # Separate positive and negative feedback
            positive_feedback = [
                f for f in all_feedback if f.feedback_type == "positive"
            ]
            negative_feedback = [
                f for f in all_feedback if f.feedback_type == "negative"
            ]

            logger.info(
                f"Found {len(positive_feedback)} positive, "
                f"{len(negative_feedback)} negative feedback entries"
            )

            # Get issue details for all feedback entries
            positive_issues = await self._get_issues_for_feedback(
                positive_feedback, issue_repo
            )
            negative_issues = await self._get_issues_for_feedback(
                negative_feedback, issue_repo
            )

            # Extract preferences
            topic_prefs = await self.extract_topic_preferences(
                positive_issues, negative_issues
            )
            team_prefs = await self.extract_team_preferences(
                positive_issues, negative_issues
            )
            label_prefs = await self.extract_label_preferences(
                positive_issues, negative_issues
            )

            # Calculate overall engagement and confidence
            total_feedback = len(all_feedback)
            engagement_score = min(
                total_feedback / 30.0, 1.0
            )  # 30+ feedback = full engagement
            confidence = min(
                total_feedback / 20.0, 1.0
            )  # 20+ feedback = full confidence

            # Build preference summary
            preferred_topics = [
                topic for topic, score in topic_prefs.items() if score >= 0.6
            ]
            disliked_topics = [
                topic for topic, score in topic_prefs.items() if score <= 0.4
            ]

            preferred_teams = [
                team for team, score in team_prefs.items() if score >= 0.6
            ]
            disliked_teams = [
                team for team, score in team_prefs.items() if score <= 0.4
            ]

            preferred_labels = [
                label for label, score in label_prefs.items() if score >= 0.6
            ]
            disliked_labels = [
                label for label, score in label_prefs.items() if score <= 0.4
            ]

            preferences = {
                "preferred_topics": preferred_topics,
                "preferred_teams": preferred_teams,
                "preferred_labels": preferred_labels,
                "disliked_topics": disliked_topics,
                "disliked_teams": disliked_teams,
                "disliked_labels": disliked_labels,
                "engagement_score": round(engagement_score, 2),
                "confidence": round(confidence, 2),
                "feedback_count": total_feedback,
                "analysis_date": datetime.utcnow().isoformat(),
                "topic_scores": topic_prefs,
                "team_scores": team_prefs,
                "label_scores": label_prefs,
            }

            logger.info(
                f"Preferences analyzed: {len(preferred_topics)} preferred topics, "
                f"{len(preferred_teams)} preferred teams, "
                f"{len(preferred_labels)} preferred labels"
            )

            return preferences

    async def extract_topic_preferences(
        self, positive_issues: list[dict], negative_issues: list[dict]
    ) -> dict[str, float]:
        """Extract topic preferences from issues.

        Uses keyword matching to identify topics in issue titles and descriptions.
        Calculates preference score based on positive vs negative feedback ratio.

        Args:
            positive_issues: Issues with positive feedback
            negative_issues: Issues with negative feedback

        Returns:
            Dict mapping topic -> preference_score (0.0 to 1.0)
            Example: {"backend": 0.9, "api": 0.8, "frontend": 0.3}
        """
        topic_counts = defaultdict(lambda: {"positive": 0, "negative": 0})

        # Count positive topic mentions
        for issue in positive_issues:
            topics = self._detect_topics(issue)
            for topic in topics:
                topic_counts[topic]["positive"] += 1

        # Count negative topic mentions
        for issue in negative_issues:
            topics = self._detect_topics(issue)
            for topic in topics:
                topic_counts[topic]["negative"] += 1

        # Calculate preference scores
        topic_prefs = {}
        for topic, counts in topic_counts.items():
            total = counts["positive"] + counts["negative"]
            if total > 0:
                # Score = positive_ratio with smoothing
                score = (counts["positive"] + 1) / (total + 2)  # Laplace smoothing
                topic_prefs[topic] = round(score, 2)

        logger.debug(f"Topic preferences: {topic_prefs}")
        return topic_prefs

    async def extract_team_preferences(
        self, positive_issues: list[dict], negative_issues: list[dict]
    ) -> dict[str, float]:
        """Extract team preferences from feedback data.

        Args:
            positive_issues: Issues with positive feedback
            negative_issues: Issues with negative feedback

        Returns:
            Dict mapping team -> preference_score (0.0 to 1.0)
        """
        team_counts = defaultdict(lambda: {"positive": 0, "negative": 0})

        # Count positive team mentions
        for issue in positive_issues:
            team = issue.get("team_name")
            if team:
                team_counts[team]["positive"] += 1

        # Count negative team mentions
        for issue in negative_issues:
            team = issue.get("team_name")
            if team:
                team_counts[team]["negative"] += 1

        # Calculate preference scores
        team_prefs = {}
        for team, counts in team_counts.items():
            total = counts["positive"] + counts["negative"]
            if total > 0:
                score = (counts["positive"] + 1) / (total + 2)  # Laplace smoothing
                team_prefs[team] = round(score, 2)

        logger.debug(f"Team preferences: {team_prefs}")
        return team_prefs

    async def extract_label_preferences(
        self, positive_issues: list[dict], negative_issues: list[dict]
    ) -> dict[str, float]:
        """Extract label preferences from feedback data.

        Args:
            positive_issues: Issues with positive feedback
            negative_issues: Issues with negative feedback

        Returns:
            Dict mapping label -> preference_score (0.0 to 1.0)
        """
        label_counts = defaultdict(lambda: {"positive": 0, "negative": 0})

        # Count positive label mentions
        for issue in positive_issues:
            labels = issue.get("labels", [])
            if isinstance(labels, list):
                for label in labels:
                    label_counts[label]["positive"] += 1

        # Count negative label mentions
        for issue in negative_issues:
            labels = issue.get("labels", [])
            if isinstance(labels, list):
                for label in labels:
                    label_counts[label]["negative"] += 1

        # Calculate preference scores
        label_prefs = {}
        for label, counts in label_counts.items():
            total = counts["positive"] + counts["negative"]
            if total > 0:
                score = (counts["positive"] + 1) / (total + 2)  # Laplace smoothing
                label_prefs[label] = round(score, 2)

        logger.debug(f"Label preferences: {label_prefs}")
        return label_prefs

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def save_to_mem0(self, preferences: dict[str, Any]) -> None:
        """Save learned preferences to mem0 for persistent storage.

        Stores preferences as structured memories with metadata for fast
        retrieval by the agent. Each preference type (topic, team, label)
        is stored separately.

        Args:
            preferences: Preference dict from analyze_feedback_patterns()

        Raises:
            Exception: If mem0 storage fails after retries
        """
        logger.info(f"Saving preferences to mem0 for user {self.user_id}")

        # Save topic preferences
        for topic in preferences["preferred_topics"]:
            score = preferences["topic_scores"].get(topic, 0.5)
            preference_text = f"User prefers {topic} topics (score: {score})"
            await self.memory_manager.add_user_preference(
                preference_text,
                metadata={
                    "preference_type": "topic",
                    "preference_key": topic,
                    "score": score,
                    "confidence": preferences["confidence"],
                    "timestamp": preferences["analysis_date"],
                },
            )

        # Save disliked topics
        for topic in preferences["disliked_topics"]:
            score = preferences["topic_scores"].get(topic, 0.5)
            preference_text = f"User dislikes {topic} topics (score: {score})"
            await self.memory_manager.add_user_preference(
                preference_text,
                metadata={
                    "preference_type": "topic",
                    "preference_key": topic,
                    "score": score,
                    "confidence": preferences["confidence"],
                    "timestamp": preferences["analysis_date"],
                },
            )

        # Save team preferences
        for team in preferences["preferred_teams"]:
            score = preferences["team_scores"].get(team, 0.5)
            preference_text = f"User prefers {team} team (score: {score})"
            await self.memory_manager.add_user_preference(
                preference_text,
                metadata={
                    "preference_type": "team",
                    "preference_key": team,
                    "score": score,
                    "confidence": preferences["confidence"],
                    "timestamp": preferences["analysis_date"],
                },
            )

        # Save label preferences
        for label in preferences["preferred_labels"]:
            score = preferences["label_scores"].get(label, 0.5)
            preference_text = f"User prefers {label} labels (score: {score})"
            await self.memory_manager.add_user_preference(
                preference_text,
                metadata={
                    "preference_type": "label",
                    "preference_key": label,
                    "score": score,
                    "confidence": preferences["confidence"],
                    "timestamp": preferences["analysis_date"],
                },
            )

        logger.info("Preferences saved to mem0 successfully")

    async def save_to_database(self, preferences: dict[str, Any]) -> None:
        """Save preferences to database for persistence.

        Args:
            preferences: Preference dict from analyze_feedback_patterns()
        """
        logger.info(f"Saving preferences to database for user {self.user_id}")

        for session in get_db_session(self.session_maker):
            pref_repo = UserPreferenceRepository(session)

            # Save topic preferences
            for topic, score in preferences["topic_scores"].items():
                feedback_count = preferences["feedback_count"]
                pref_repo.save_preference(
                    user_id=self.user_id,
                    preference_type="topic",
                    preference_key=topic,
                    score=score,
                    confidence=preferences["confidence"],
                    feedback_count=feedback_count,
                )

            # Save team preferences
            for team, score in preferences["team_scores"].items():
                feedback_count = preferences["feedback_count"]
                pref_repo.save_preference(
                    user_id=self.user_id,
                    preference_type="team",
                    preference_key=team,
                    score=score,
                    confidence=preferences["confidence"],
                    feedback_count=feedback_count,
                )

            # Save label preferences
            for label, score in preferences["label_scores"].items():
                feedback_count = preferences["feedback_count"]
                pref_repo.save_preference(
                    user_id=self.user_id,
                    preference_type="label",
                    preference_key=label,
                    score=score,
                    confidence=preferences["confidence"],
                    feedback_count=feedback_count,
                )

        logger.info("Preferences saved to database successfully")

    async def get_preferences(self) -> dict[str, Any]:
        """Retrieve current preferences from mem0.

        Returns:
            Dict with current preferences in same format as analyze_feedback_patterns()
        """
        logger.info(f"Retrieving preferences for user {self.user_id}")

        # Get all user preferences from mem0
        preferences = await self.memory_manager.get_user_preferences()

        # Parse and structure
        preferred_topics = []
        disliked_topics = []
        preferred_teams = []
        preferred_labels = []
        topic_scores = {}
        team_scores = {}
        label_scores = {}

        for pref in preferences:
            metadata = pref.get("metadata", {})
            pref_type = metadata.get("preference_type")
            pref_key = metadata.get("preference_key")
            score = metadata.get("score", 0.5)

            if pref_type == "topic":
                topic_scores[pref_key] = score
                if score >= 0.6:
                    preferred_topics.append(pref_key)
                elif score <= 0.4:
                    disliked_topics.append(pref_key)
            elif pref_type == "team":
                team_scores[pref_key] = score
                if score >= 0.6:
                    preferred_teams.append(pref_key)
            elif pref_type == "label":
                label_scores[pref_key] = score
                if score >= 0.6:
                    preferred_labels.append(pref_key)

        result = {
            "preferred_topics": preferred_topics,
            "disliked_topics": disliked_topics,
            "preferred_teams": preferred_teams,
            "preferred_labels": preferred_labels,
            "topic_scores": topic_scores,
            "team_scores": team_scores,
            "label_scores": label_scores,
        }

        logger.info(
            f"Retrieved preferences: {len(preferred_topics)} preferred topics, "
            f"{len(preferred_teams)} preferred teams"
        )

        return result

    def _detect_topics(self, issue: dict) -> list[str]:
        """Detect topics in issue using keyword matching.

        Args:
            issue: Issue dict with title, description fields

        Returns:
            List of detected topic names
        """
        detected = []
        text = f"{issue.get('title', '')} {issue.get('description', '')}".lower()

        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                detected.append(topic)

        return detected

    async def _get_issues_for_feedback(
        self, feedback_list: list, issue_repo: IssueHistoryRepository
    ) -> list[dict]:
        """Get issue details for feedback entries.

        Args:
            feedback_list: List of Feedback objects
            issue_repo: IssueHistoryRepository instance

        Returns:
            List of issue dicts with title, description, labels, team_name
        """
        issues = []
        for feedback in feedback_list:
            metadata = feedback.extra_metadata or {}
            issue_id = metadata.get("issue_id")

            if not issue_id:
                continue

            # Get latest snapshot for this issue
            snapshot = issue_repo.get_latest_snapshot(issue_id)
            if snapshot:
                issues.append(
                    {
                        "issue_id": snapshot.issue_id,
                        "title": snapshot.title,
                        "description": "",  # Not stored in IssueHistory
                        "labels": snapshot.labels or [],
                        "team_name": snapshot.team_name,
                        "state": snapshot.state,
                    }
                )

        return issues

    def _empty_preferences(self) -> dict[str, Any]:
        """Return empty preferences structure when no data available.

        Returns:
            Empty preferences dict with default values
        """
        return {
            "preferred_topics": [],
            "preferred_teams": [],
            "preferred_labels": [],
            "disliked_topics": [],
            "disliked_teams": [],
            "disliked_labels": [],
            "engagement_score": 0.0,
            "confidence": 0.0,
            "feedback_count": 0,
            "analysis_date": datetime.utcnow().isoformat(),
            "topic_scores": {},
            "team_scores": {},
            "label_scores": {},
        }
