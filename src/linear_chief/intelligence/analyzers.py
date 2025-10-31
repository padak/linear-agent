"""Issue analysis logic for stagnation detection, blocking detection, and priority calculation."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .types import AnalysisResult

logger = logging.getLogger(__name__)


class IssueAnalyzer:
    """Analyzes Linear issues for stagnation, blocking, and priority.

    Provides intelligent insights about issue status, urgency, and
    recommended actions based on issue metadata and history.
    """

    # Keywords indicating an issue is intentionally paused
    PAUSED_KEYWORDS = [
        "paused",
        "on hold",
        "waiting for",
        "blocked on external",
        "pending approval",
    ]

    # Keywords indicating an issue is blocked
    BLOCKED_KEYWORDS = [
        "blocked",
        "blocker",
        "dependency",
        "waiting on",
        "needs",
        "requires",
    ]

    def analyze_issue(self, issue: dict[str, Any]) -> AnalysisResult:
        """Perform complete analysis of an issue.

        Args:
            issue: Issue dictionary with fields (id, title, description, status, etc.).

        Returns:
            AnalysisResult with priority, stagnation, blocking status, and insights.
        """
        is_stagnant = self.detect_stagnation(issue)
        is_blocked = self.detect_blocking(issue)
        priority = self.calculate_priority(issue)
        insights = self._generate_insights(issue, is_stagnant, is_blocked, priority)

        logger.debug(
            f"Analyzed issue {issue.get('id', 'unknown')}: "
            f"priority={priority}, stagnant={is_stagnant}, blocked={is_blocked}"
        )

        return AnalysisResult(
            priority=priority,
            is_stagnant=is_stagnant,
            is_blocked=is_blocked,
            insights=insights,
        )

    def detect_stagnation(self, issue: dict[str, Any]) -> bool:
        """Detect if issue is stagnant (inactive for 3+ days).

        An issue is considered stagnant if:
        - No updates for 3+ days AND
        - Status is "In Progress" AND
        - NOT labeled "On Hold" or "Waiting" AND
        - No paused keywords in recent comments

        Args:
            issue: Issue dictionary.

        Returns:
            True if issue is stagnant, False otherwise.
        """
        try:
            # Check status
            status = issue.get("state", {}).get("name", "").lower()
            if status not in ["in progress", "started", "active"]:
                return False

            # Check labels for "On Hold" or "Waiting"
            labels = [label.get("name", "").lower() for label in issue.get("labels", {}).get("nodes", [])]
            if any(keyword in label for label in labels for keyword in ["on hold", "waiting", "paused"]):
                return False

            # Check updated timestamp
            updated_at_str = issue.get("updatedAt")
            if not updated_at_str:
                logger.warning(f"Issue {issue.get('id')} missing updatedAt field")
                return False

            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days

            if days_since_update < 3:
                return False

            # Check for paused keywords in description or title
            title = issue.get("title", "").lower()
            description = issue.get("description", "").lower()
            combined_text = f"{title} {description}"

            if any(keyword in combined_text for keyword in self.PAUSED_KEYWORDS):
                return False

            logger.info(
                f"Issue {issue.get('id')} is stagnant: {days_since_update} days since update"
            )
            return True

        except Exception as e:
            logger.error(f"Error detecting stagnation for issue {issue.get('id')}: {e}", exc_info=True)
            return False

    def detect_blocking(self, issue: dict[str, Any]) -> bool:
        """Detect if issue is blocked by external dependencies.

        Checks for:
        - Blocked relationship to other issues
        - "blocked" keywords in title/description/comments
        - Special blocked labels

        Args:
            issue: Issue dictionary.

        Returns:
            True if issue is blocked, False otherwise.
        """
        try:
            # Check labels for "Blocked"
            labels = [label.get("name", "").lower() for label in issue.get("labels", {}).get("nodes", [])]
            if any("blocked" in label for label in labels):
                return True

            # Check title and description for blocking keywords
            title = issue.get("title", "").lower()
            description = issue.get("description", "").lower()
            combined_text = f"{title} {description}"

            if any(keyword in combined_text for keyword in self.BLOCKED_KEYWORDS):
                logger.info(f"Issue {issue.get('id')} appears blocked (keyword match)")
                return True

            # Check for blocking relationships (if available in API response)
            relations = issue.get("relations", {}).get("nodes", [])
            for relation in relations:
                if relation.get("type") == "blocks":
                    logger.info(f"Issue {issue.get('id')} is blocked by relationship")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error detecting blocking for issue {issue.get('id')}: {e}", exc_info=True)
            return False

    def calculate_priority(self, issue: dict[str, Any]) -> int:
        """Calculate priority score (1-10) based on multiple factors.

        Priority factors:
        - Priority label (P0=10, P1=8, P2=5, P3=3, P4=1)
        - Age (older = higher priority)
        - Stagnation (stagnant = +2 points)
        - Blocking (blocked = +3 points)
        - Status (In Progress = +1 point)

        Args:
            issue: Issue dictionary.

        Returns:
            Priority score from 1-10 (10 = highest).
        """
        try:
            priority = 5  # Base priority

            # Check priority labels
            labels = [label.get("name", "") for label in issue.get("labels", {}).get("nodes", [])]
            for label in labels:
                if "P0" in label or "Critical" in label:
                    priority = max(priority, 10)
                elif "P1" in label or "High" in label:
                    priority = max(priority, 8)
                elif "P2" in label or "Medium" in label:
                    priority = max(priority, 5)
                elif "P3" in label or "Low" in label:
                    priority = min(priority, 3)

            # Age factor (issues older than 7 days get +1 point)
            created_at_str = issue.get("createdAt")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                age_days = (datetime.now(created_at.tzinfo) - created_at).days
                if age_days > 7:
                    priority = min(priority + 1, 10)

            # Stagnation factor
            if self.detect_stagnation(issue):
                priority = min(priority + 2, 10)

            # Blocking factor
            if self.detect_blocking(issue):
                priority = min(priority + 3, 10)

            # Status factor (In Progress gets slight boost)
            status = issue.get("state", {}).get("name", "").lower()
            if status in ["in progress", "started"]:
                priority = min(priority + 1, 10)

            logger.debug(f"Issue {issue.get('id')} calculated priority: {priority}")
            return max(1, min(priority, 10))  # Clamp to 1-10

        except Exception as e:
            logger.error(f"Error calculating priority for issue {issue.get('id')}: {e}", exc_info=True)
            return 5  # Default priority on error

    def _generate_insights(
        self, issue: dict[str, Any], is_stagnant: bool, is_blocked: bool, priority: int
    ) -> list[str]:
        """Generate actionable insights based on analysis.

        Args:
            issue: Issue dictionary.
            is_stagnant: Whether issue is stagnant.
            is_blocked: Whether issue is blocked.
            priority: Calculated priority score.

        Returns:
            List of insight strings.
        """
        insights = []

        if is_stagnant:
            # Parse updatedAt and ensure both datetimes are timezone-aware
            updated_at_str = issue.get("updatedAt", "")
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))

            # If the parsed datetime is naive, assume it's UTC
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            days_since_update = (now - updated_at).days
            insights.append(f"No activity for {days_since_update} days - needs attention")

        if is_blocked:
            insights.append("Issue is blocked - investigate dependencies")

        if priority >= 8:
            insights.append("High priority - recommend immediate action")

        status = issue.get("state", {}).get("name", "")
        if status.lower() in ["todo", "backlog"] and priority >= 7:
            insights.append("High priority but not started - consider moving to In Progress")

        if not insights:
            insights.append("No immediate concerns detected")

        return insights
