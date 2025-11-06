"""Repository pattern implementations for data access."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import logging

from linear_chief.storage.models import (
    IssueHistory,
    Briefing,
    Metrics,
    Conversation,
    Feedback,
)

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

    def get_issue_snapshot_by_identifier(
        self, issue_id: str, max_age_hours: int = 1
    ) -> Optional[IssueHistory]:
        """
        Get issue snapshot by identifier if it exists and is fresh.

        Used for intelligent caching - returns cached data if recent enough,
        otherwise returns None to trigger fresh API fetch.

        Args:
            issue_id: Issue identifier (e.g., "PROJ-123")
            max_age_hours: Maximum age of snapshot in hours (default: 1 hour)

        Returns:
            Latest IssueHistory if found and fresh, None if not found or stale
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        return (
            self.session.query(IssueHistory)
            .filter(
                IssueHistory.issue_id == issue_id,
                IssueHistory.snapshot_at >= cutoff,
            )
            .order_by(desc(IssueHistory.snapshot_at))
            .first()
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


class ConversationRepository:
    """Repository for Conversation model operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def save_message(
        self,
        user_id: str,
        chat_id: str,
        message: str,
        role: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Conversation:
        """
        Save a conversation message (user or assistant).

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            message: Message content
            role: Message role ('user' or 'assistant')
            extra_metadata: Additional fields (message_id, reply_to, etc.)

        Returns:
            Created Conversation instance

        Raises:
            ValueError: If role is not 'user' or 'assistant'
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        conversation = Conversation(
            user_id=user_id,
            chat_id=chat_id,
            message=message,
            role=role,
            extra_metadata=extra_metadata,
        )

        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)

        logger.debug(f"Saved {role} message for user {user_id}")
        return conversation

    def get_conversation_history(
        self,
        user_id: str,
        limit: int = 20,
        since_hours: Optional[int] = None,
    ) -> List[Conversation]:
        """
        Get recent conversation history for a user.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to return
            since_hours: Optional filter to only get messages from last N hours

        Returns:
            List of Conversation instances, ordered chronologically (oldest first)
        """
        query = self.session.query(Conversation).filter(Conversation.user_id == user_id)

        if since_hours is not None:
            cutoff = datetime.utcnow() - timedelta(hours=since_hours)
            query = query.filter(Conversation.timestamp >= cutoff)

        # Order by timestamp descending, then by ID descending (most recent first)
        # This ensures we get the most recent N messages
        conversations = (
            query.order_by(desc(Conversation.timestamp), desc(Conversation.id))
            .limit(limit)
            .all()
        )

        # Reverse to get chronological order (oldest first)
        return list(reversed(conversations))

    def get_user_context(self, user_id: str, limit: int = 10) -> str:
        """
        Get formatted conversation context for agent prompt.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of recent messages to include

        Returns:
            Formatted conversation history as string
        """
        conversations = self.get_conversation_history(user_id, limit=limit)

        if not conversations:
            return "No previous conversation history."

        context_lines = []
        for conv in conversations:
            # Format: "User: message" or "Assistant: message"
            role_label = "User" if conv.role == "user" else "Assistant"
            context_lines.append(f"{role_label}: {conv.message}")

        return "\n".join(context_lines)

    def clear_old_conversations(self, days: int = 30) -> int:
        """
        Delete conversations older than N days for data retention.

        Args:
            days: Number of days to retain

        Returns:
            Number of conversations deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        count = (
            self.session.query(Conversation)
            .filter(Conversation.timestamp < cutoff)
            .delete()
        )

        self.session.commit()
        logger.info(f"Deleted {count} conversations older than {days} days")
        return count

    def get_active_users(self, since_days: int = 7) -> List[str]:
        """
        Get list of user IDs who have had conversations in the last N days.

        Args:
            since_days: Number of days to look back

        Returns:
            List of unique user IDs
        """
        cutoff = datetime.utcnow() - timedelta(days=since_days)

        results = (
            self.session.query(Conversation.user_id)
            .filter(Conversation.timestamp >= cutoff)
            .distinct()
            .all()
        )

        return [row[0] for row in results]

    def get_conversation_stats(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get conversation statistics for a user.

        Args:
            user_id: Telegram user ID
            days: Number of days to analyze

        Returns:
            Dict with total_messages, user_messages, assistant_messages, first_message, last_message
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total messages
        total = (
            self.session.query(func.count(Conversation.id))
            .filter(
                Conversation.user_id == user_id,
                Conversation.timestamp >= cutoff,
            )
            .scalar()
        )

        # User messages
        user_count = (
            self.session.query(func.count(Conversation.id))
            .filter(
                Conversation.user_id == user_id,
                Conversation.role == "user",
                Conversation.timestamp >= cutoff,
            )
            .scalar()
        )

        # Assistant messages
        assistant_count = (
            self.session.query(func.count(Conversation.id))
            .filter(
                Conversation.user_id == user_id,
                Conversation.role == "assistant",
                Conversation.timestamp >= cutoff,
            )
            .scalar()
        )

        # First and last message timestamps
        first_msg = (
            self.session.query(Conversation.timestamp)
            .filter(
                Conversation.user_id == user_id,
                Conversation.timestamp >= cutoff,
            )
            .order_by(Conversation.timestamp)
            .first()
        )

        last_msg = (
            self.session.query(Conversation.timestamp)
            .filter(
                Conversation.user_id == user_id,
                Conversation.timestamp >= cutoff,
            )
            .order_by(desc(Conversation.timestamp))
            .first()
        )

        return {
            "total_messages": total or 0,
            "user_messages": user_count or 0,
            "assistant_messages": assistant_count or 0,
            "first_message": first_msg[0] if first_msg else None,
            "last_message": last_msg[0] if last_msg else None,
        }


class FeedbackRepository:
    """Repository for Feedback model operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def save_feedback(
        self,
        user_id: str,
        briefing_id: Optional[int],
        feedback_type: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Feedback:
        """
        Save user feedback on briefings or issue actions.

        Args:
            user_id: Telegram user ID
            briefing_id: Briefing ID (optional, can be None for issue actions)
            feedback_type: Type of feedback ('positive', 'negative', 'issue_action')
            extra_metadata: Additional context (telegram_message_id, action details, etc.)

        Returns:
            Created Feedback instance

        Raises:
            ValueError: If feedback_type is invalid
        """
        valid_types = ("positive", "negative", "issue_action")
        if feedback_type not in valid_types:
            raise ValueError(
                f"Invalid feedback_type: {feedback_type}. "
                f"Must be one of {valid_types}"
            )

        feedback = Feedback(
            user_id=user_id,
            briefing_id=briefing_id,
            feedback_type=feedback_type,
            extra_metadata=extra_metadata,
        )

        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)

        logger.debug(f"Saved {feedback_type} feedback from user {user_id}")
        return feedback

    def get_user_feedback_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get feedback statistics for a specific user.

        Args:
            user_id: Telegram user ID
            days: Number of days to analyze

        Returns:
            Dict with positive_count, negative_count, issue_action_count, total_count
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Count by feedback type
        positive_count = (
            self.session.query(func.count(Feedback.id))
            .filter(
                Feedback.user_id == user_id,
                Feedback.feedback_type == "positive",
                Feedback.timestamp >= cutoff,
            )
            .scalar()
        )

        negative_count = (
            self.session.query(func.count(Feedback.id))
            .filter(
                Feedback.user_id == user_id,
                Feedback.feedback_type == "negative",
                Feedback.timestamp >= cutoff,
            )
            .scalar()
        )

        issue_action_count = (
            self.session.query(func.count(Feedback.id))
            .filter(
                Feedback.user_id == user_id,
                Feedback.feedback_type == "issue_action",
                Feedback.timestamp >= cutoff,
            )
            .scalar()
        )

        total_count = (
            (positive_count or 0) + (negative_count or 0) + (issue_action_count or 0)
        )

        return {
            "positive_count": positive_count or 0,
            "negative_count": negative_count or 0,
            "issue_action_count": issue_action_count or 0,
            "total_count": total_count,
            "satisfaction_rate": (
                round((positive_count or 0) / total_count * 100, 1)
                if total_count > 0
                else 0.0
            ),
        }

    def get_recent_feedback(
        self,
        days: int = 7,
        limit: int = 100,
        feedback_type: Optional[str] = None,
    ) -> List[Feedback]:
        """
        Get recent feedback entries.

        Args:
            days: Number of days to look back
            limit: Maximum number of entries to return
            feedback_type: Optional filter by feedback type

        Returns:
            List of Feedback instances, ordered by timestamp descending
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(Feedback).filter(Feedback.timestamp >= cutoff)

        if feedback_type:
            query = query.filter(Feedback.feedback_type == feedback_type)

        return query.order_by(desc(Feedback.timestamp)).limit(limit).all()

    def get_briefing_feedback(self, briefing_id: int) -> List[Feedback]:
        """
        Get all feedback for a specific briefing.

        Args:
            briefing_id: Briefing ID

        Returns:
            List of Feedback instances for the briefing
        """
        return (
            self.session.query(Feedback)
            .filter(Feedback.briefing_id == briefing_id)
            .order_by(desc(Feedback.timestamp))
            .all()
        )

    def get_overall_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get overall feedback statistics across all users.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with aggregated feedback statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Count by feedback type
        positive_count = (
            self.session.query(func.count(Feedback.id))
            .filter(
                Feedback.feedback_type == "positive",
                Feedback.timestamp >= cutoff,
            )
            .scalar()
        )

        negative_count = (
            self.session.query(func.count(Feedback.id))
            .filter(
                Feedback.feedback_type == "negative",
                Feedback.timestamp >= cutoff,
            )
            .scalar()
        )

        issue_action_count = (
            self.session.query(func.count(Feedback.id))
            .filter(
                Feedback.feedback_type == "issue_action",
                Feedback.timestamp >= cutoff,
            )
            .scalar()
        )

        # Count unique users
        unique_users = (
            self.session.query(func.count(func.distinct(Feedback.user_id)))
            .filter(Feedback.timestamp >= cutoff)
            .scalar()
        )

        total_count = (
            (positive_count or 0) + (negative_count or 0) + (issue_action_count or 0)
        )

        return {
            "positive_count": positive_count or 0,
            "negative_count": negative_count or 0,
            "issue_action_count": issue_action_count or 0,
            "total_count": total_count,
            "unique_users": unique_users or 0,
            "satisfaction_rate": (
                round((positive_count or 0) / total_count * 100, 1)
                if total_count > 0
                else 0.0
            ),
        }
