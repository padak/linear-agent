"""Type definitions for intelligence layer."""

from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """Result of issue analysis containing priority and insights.

    Attributes:
        priority: Priority score from 1-10 (10 = highest urgency).
        is_stagnant: True if issue has been inactive for too long.
        is_blocked: True if issue is blocked by external dependencies.
        insights: List of actionable insights about the issue.
    """

    priority: int
    is_stagnant: bool
    is_blocked: bool
    insights: list[str]

    def __post_init__(self) -> None:
        """Validate priority is in range 1-10."""
        if not 1 <= self.priority <= 10:
            raise ValueError(f"Priority must be 1-10, got {self.priority}")
