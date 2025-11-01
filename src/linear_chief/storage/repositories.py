"""Repository pattern implementations for data access."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import logging

from linear_chief.storage.models import IssueHistory, Briefing, Metrics

logger = logging.getLogger(__name__)


class IssueHistoryRepository:
    """Repository for IssueHistory model operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def save_snapshot(
        self,
        issue_id: str,
        linear_id: str,
        title: str,
        state: str,
        priority: Optional[int] = None,
        assignee_id: Optional[str] = None,
        assignee_name: Optional[str] = None,
        team_id: Optional[str] = None,
        team_name: Optional[str] = None,
        labels: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> IssueHistory:
        """
        Save issue snapshot to history.

        Args:
            issue_id: Issue identifier (e.g., "PROJ-123")
            linear_id: Linear UUID
            title: Issue title
            state: Issue state (e.g., "In Progress")
            priority: Priority level (0-4)
            assignee_id: Assignee UUID
            assignee_name: Assignee display name
            team_id: Team UUID
            team_name: Team name
            labels: List of label names
            metadata: Additional fields

        Returns:
            Created IssueHistory instance
        """
        snapshot = IssueHistory(
            issue_id=issue_id,
            linear_id=linear_id,
            title=title,
            state=state,
            priority=priority,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            team_id=team_id,
            team_name=team_name,
            labels=labels,
            extra_metadata=extra_metadata,
        )

        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)

        logger.debug(f"Saved issue snapshot: {issue_id} - {state}")
        return snapshot

    def get_latest_snapshot(self, issue_id: str) -> Optional[IssueHistory]:
        """
        Get most recent snapshot for an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            Latest IssueHistory or None if not found
        """
        return (
            self.session.query(IssueHistory)
            .filter(IssueHistory.issue_id == issue_id)
            .order_by(desc(IssueHistory.snapshot_at))
            .first()
        )

    def get_snapshots_since(self, issue_id: str, since: datetime) -> List[IssueHistory]:
        """
        Get all snapshots for an issue since a specific time.

        Args:
            issue_id: Issue identifier
            since: Datetime to filter from

        Returns:
            List of IssueHistory snapshots
        """
        return (
            self.session.query(IssueHistory)
            .filter(
                IssueHistory.issue_id == issue_id,
                IssueHistory.snapshot_at >= since,
            )
            .order_by(IssueHistory.snapshot_at)
            .all()
        )

    def get_all_latest_snapshots(self, days: int = 30) -> List[IssueHistory]:
        """
        Get latest snapshot for each unique issue in the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of latest IssueHistory snapshots per issue
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Subquery to find latest snapshot_at for each issue_id
        subquery = (
            self.session.query(
                IssueHistory.issue_id,
                func.max(IssueHistory.snapshot_at).label("max_snapshot"),
            )
            .filter(IssueHistory.snapshot_at >= cutoff)
            .group_by(IssueHistory.issue_id)
            .subquery()
        )

        # Join to get full records
        return (
            self.session.query(IssueHistory)
            .join(
                subquery,
                (IssueHistory.issue_id == subquery.c.issue_id)
                & (IssueHistory.snapshot_at == subquery.c.max_snapshot),
            )
            .all()
        )


class BriefingRepository:
    """Repository for Briefing model operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create_briefing(
        self,
        content: str,
        issue_count: int,
        agent_context: Optional[Dict[str, Any]] = None,
        cost_usd: Optional[float] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Briefing:
        """
        Create new briefing record.

        Args:
            content: Full briefing text (markdown)
            issue_count: Number of issues in briefing
            agent_context: Context used by Agent SDK
            cost_usd: Estimated cost
            input_tokens: Input token count
            output_tokens: Output token count
            model_name: Model identifier
            metadata: Additional fields

        Returns:
            Created Briefing instance
        """
        briefing = Briefing(
            content=content,
            issue_count=issue_count,
            agent_context=agent_context,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
            extra_metadata=extra_metadata,
        )

        self.session.add(briefing)
        self.session.commit()
        self.session.refresh(briefing)

        logger.info(f"Created briefing: {briefing.id} ({issue_count} issues)")
        return briefing

    def mark_as_sent(
        self, briefing_id: int, telegram_message_id: Optional[str] = None
    ) -> None:
        """
        Mark briefing as successfully sent.

        Args:
            briefing_id: Briefing ID
            telegram_message_id: Telegram message ID
        """
        briefing = (
            self.session.query(Briefing).filter(Briefing.id == briefing_id).first()
        )
        if briefing:
            # SQLAlchemy ORM: Column assignments at runtime work despite type hints
            briefing.delivery_status = "sent"  # type: ignore[assignment]
            briefing.sent_at = datetime.utcnow()  # type: ignore[assignment]
            briefing.telegram_message_id = telegram_message_id  # type: ignore[assignment]
            self.session.commit()
            logger.info(f"Marked briefing {briefing_id} as sent")

    def mark_as_failed(self, briefing_id: int, error_message: str) -> None:
        """
        Mark briefing as failed with error message.

        Args:
            briefing_id: Briefing ID
            error_message: Error description
        """
        briefing = (
            self.session.query(Briefing).filter(Briefing.id == briefing_id).first()
        )
        if briefing:
            # SQLAlchemy ORM: Column assignments at runtime work despite type hints
            briefing.delivery_status = "failed"  # type: ignore[assignment]
            briefing.error_message = error_message  # type: ignore[assignment]
            self.session.commit()
            logger.error(f"Marked briefing {briefing_id} as failed: {error_message}")

    def get_recent_briefings(self, days: int = 7) -> List[Briefing]:
        """
        Get briefings from last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of Briefing instances
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            self.session.query(Briefing)
            .filter(Briefing.generated_at >= cutoff)
            .order_by(desc(Briefing.generated_at))
            .all()
        )

    def get_total_cost(self, days: int = 30) -> float:
        """
        Calculate total cost for last N days.

        Args:
            days: Number of days to calculate

        Returns:
            Total cost in USD
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = (
            self.session.query(func.sum(Briefing.cost_usd))
            .filter(
                Briefing.generated_at >= cutoff,
                Briefing.cost_usd.isnot(None),
            )
            .scalar()
        )
        return result or 0.0


class MetricsRepository:
    """Repository for Metrics model operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def record_metric(
        self,
        metric_type: str,
        metric_name: str,
        value: float,
        unit: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Metrics:
        """
        Record a metric.

        Args:
            metric_type: Metric category (e.g., "api_call")
            metric_name: Metric identifier (e.g., "linear_fetch_issues")
            value: Numeric value
            unit: Unit of measurement (e.g., "count", "seconds", "usd")
            metadata: Additional context

        Returns:
            Created Metrics instance
        """
        metric = Metrics(
            metric_type=metric_type,
            metric_name=metric_name,
            value=value,
            unit=unit,
            extra_metadata=extra_metadata,
        )

        self.session.add(metric)
        self.session.commit()
        self.session.refresh(metric)

        logger.debug(f"Recorded metric: {metric_type}.{metric_name} = {value} {unit}")
        return metric

    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        days: int = 7,
    ) -> List[Metrics]:
        """
        Query metrics with optional filters.

        Args:
            metric_type: Filter by metric type
            metric_name: Filter by metric name
            days: Number of days to look back

        Returns:
            List of Metrics instances
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(Metrics).filter(Metrics.recorded_at >= cutoff)

        if metric_type:
            query = query.filter(Metrics.metric_type == metric_type)
        if metric_name:
            query = query.filter(Metrics.metric_name == metric_name)

        return query.order_by(desc(Metrics.recorded_at)).all()

    def get_aggregated_metrics(
        self,
        metric_type: str,
        metric_name: str,
        days: int = 7,
    ) -> Dict[str, float]:
        """
        Get aggregated statistics for a metric.

        Args:
            metric_type: Metric category
            metric_name: Metric identifier
            days: Number of days to aggregate

        Returns:
            Dict with sum, avg, min, max, count
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = (
            self.session.query(
                func.sum(Metrics.value).label("sum"),
                func.avg(Metrics.value).label("avg"),
                func.min(Metrics.value).label("min"),
                func.max(Metrics.value).label("max"),
                func.count(Metrics.value).label("count"),
            )
            .filter(
                Metrics.metric_type == metric_type,
                Metrics.metric_name == metric_name,
                Metrics.recorded_at >= cutoff,
            )
            .first()
        )

        return {
            "sum": result.sum or 0.0,
            "avg": result.avg or 0.0,
            "min": result.min or 0.0,
            "max": result.max or 0.0,
            "count": result.count or 0,
        }
