"""Repository pattern implementations for data access."""

from collections import defaultdict
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
    IssueEngagement,
    UserPreference,
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

    def record_feedback(
        self,
        user_id: str,
        briefing_id: Optional[int],
        feedback_type: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Feedback:
        """
        Record user feedback on briefings or issue actions.

        Alias for save_feedback() to support both naming conventions.

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
        return self.save_feedback(user_id, briefing_id, feedback_type, extra_metadata)

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


class IssueEngagementRepository:
    """Repository for IssueEngagement model operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def record_interaction(
        self,
        user_id: str,
        issue_id: str,
        linear_id: str,
        interaction_type: str = "mention",
        context: Optional[str] = None,
    ) -> IssueEngagement:
        """
        Record user interaction with issue (upsert pattern).

        If record exists: increments interaction_count and updates last_interaction.
        If record doesn't exist: creates new record.

        Args:
            user_id: Telegram user ID
            issue_id: Issue identifier (e.g., "AI-1799")
            linear_id: Linear UUID
            interaction_type: Type of interaction ("query", "view", "mention")
            context: User's message or context (optional)

        Returns:
            Created or updated IssueEngagement instance

        Raises:
            ValueError: If interaction_type is invalid
        """
        valid_types = ("query", "view", "mention")
        if interaction_type not in valid_types:
            raise ValueError(
                f"Invalid interaction_type: {interaction_type}. "
                f"Must be one of {valid_types}"
            )

        # Check if record exists (user_id + issue_id unique constraint)
        engagement = (
            self.session.query(IssueEngagement)
            .filter(
                IssueEngagement.user_id == user_id,
                IssueEngagement.issue_id == issue_id,
            )
            .first()
        )

        if engagement:
            # Update existing record
            # SQLAlchemy ORM: Column assignments at runtime work despite type hints
            engagement.interaction_count += 1  # type: ignore[attr-defined]
            engagement.last_interaction = datetime.utcnow()  # type: ignore[assignment]
            engagement.interaction_type = interaction_type  # type: ignore[assignment]
            if context:
                engagement.context = context  # type: ignore[assignment]

            logger.debug(
                f"Updated engagement for {user_id} on {issue_id} "
                f"(count: {engagement.interaction_count})"  # type: ignore[attr-defined]
            )
        else:
            # Create new record
            engagement = IssueEngagement(
                user_id=user_id,
                issue_id=issue_id,
                linear_id=linear_id,
                interaction_type=interaction_type,
                interaction_count=1,
                engagement_score=0.5,  # Default score
                context=context,
            )
            self.session.add(engagement)
            logger.debug(f"Created new engagement for {user_id} on {issue_id}")

        self.session.commit()
        self.session.refresh(engagement)

        return engagement

    def get_engagement(self, user_id: str, issue_id: str) -> Optional[IssueEngagement]:
        """
        Get engagement record for specific issue.

        Args:
            user_id: Telegram user ID
            issue_id: Issue identifier

        Returns:
            IssueEngagement instance or None if not found
        """
        return (
            self.session.query(IssueEngagement)
            .filter(
                IssueEngagement.user_id == user_id,
                IssueEngagement.issue_id == issue_id,
            )
            .first()
        )

    def get_all_engagements(
        self, user_id: str, min_score: float = 0.0
    ) -> List[IssueEngagement]:
        """
        Get all engagement records for user.

        Args:
            user_id: Telegram user ID
            min_score: Minimum engagement score to filter (default: 0.0)

        Returns:
            List of IssueEngagement instances
        """
        return (
            self.session.query(IssueEngagement)
            .filter(
                IssueEngagement.user_id == user_id,
                IssueEngagement.engagement_score >= min_score,
            )
            .order_by(desc(IssueEngagement.engagement_score))
            .all()
        )

    def get_top_engaged(self, user_id: str, limit: int = 10) -> List[IssueEngagement]:
        """
        Get top engaged issues sorted by engagement score.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of issues to return

        Returns:
            List of IssueEngagement instances, sorted by score descending
        """
        return (
            self.session.query(IssueEngagement)
            .filter(IssueEngagement.user_id == user_id)
            .order_by(desc(IssueEngagement.engagement_score))
            .limit(limit)
            .all()
        )

    def get_top_engaged_issues(self, user_id: str, limit: int = 10) -> List[IssueEngagement]:
        """
        Get top engaged issues sorted by engagement score.

        Alias for get_top_engaged() for backwards compatibility.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of issues to return

        Returns:
            List of IssueEngagement instances, sorted by score descending
        """
        return self.get_top_engaged(user_id, limit)

    def update_score(self, user_id: str, issue_id: str, new_score: float) -> None:
        """
        Update engagement score for issue.

        Args:
            user_id: Telegram user ID
            issue_id: Issue identifier
            new_score: New engagement score (0.0 to 1.0)

        Raises:
            ValueError: If new_score is outside [0.0, 1.0] range
        """
        if not (0.0 <= new_score <= 1.0):
            raise ValueError(f"Score must be between 0.0 and 1.0, got {new_score}")

        engagement = self.get_engagement(user_id, issue_id)
        if engagement:
            # SQLAlchemy ORM: Column assignments at runtime work despite type hints
            engagement.engagement_score = new_score  # type: ignore[assignment]
            self.session.commit()
            logger.debug(f"Updated score for {user_id} on {issue_id}: {new_score:.2f}")
        else:
            logger.warning(
                f"Cannot update score: No engagement found for {user_id} on {issue_id}"
            )

    def decay_old_engagements(
        self, user_id: str, days_threshold: int = 30, decay_factor: float = 0.1
    ) -> int:
        """
        Apply decay to old engagement scores.

        Reduces scores for interactions older than days_threshold.
        This ensures engagement reflects recent user interest.

        Args:
            user_id: Telegram user ID
            days_threshold: Age threshold in days
            decay_factor: Factor to reduce score by (0.1 = 10% reduction)

        Returns:
            Number of engagement records decayed

        Raises:
            ValueError: If decay_factor is outside [0.0, 1.0] range
        """
        if not (0.0 <= decay_factor <= 1.0):
            raise ValueError(
                f"Decay factor must be between 0.0 and 1.0, got {decay_factor}"
            )

        cutoff = datetime.utcnow() - timedelta(days=days_threshold)

        # Find old engagements
        old_engagements = (
            self.session.query(IssueEngagement)
            .filter(
                IssueEngagement.user_id == user_id,
                IssueEngagement.last_interaction < cutoff,
                IssueEngagement.engagement_score
                > 0.0,  # Don't decay already-zero scores
            )
            .all()
        )

        count = 0
        for engagement in old_engagements:
            # Apply decay
            current_score: float = engagement.engagement_score  # type: ignore[attr-defined]
            new_score = max(0.0, current_score * (1.0 - decay_factor))

            # SQLAlchemy ORM: Column assignments at runtime work despite type hints
            engagement.engagement_score = new_score  # type: ignore[assignment]
            count += 1

        if count > 0:
            self.session.commit()
            logger.info(f"Decayed {count} engagement scores for user {user_id}")

        return count

    def delete_all_engagements(self, user_id: str) -> int:
        """
        Delete all engagement records for a user.

        Used when user wants to reset all preferences and engagement data.

        Args:
            user_id: Telegram user ID

        Returns:
            Number of engagement records deleted
        """
        count = (
            self.session.query(IssueEngagement)
            .filter(IssueEngagement.user_id == user_id)
            .delete()
        )

        self.session.commit()
        logger.info(f"Deleted {count} engagement records for user {user_id}")
        return count


class UserPreferenceRepository:
    """Repository for UserPreference model operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def save_preference(
        self,
        user_id: str,
        preference_type: str,
        preference_key: str,
        score: float,
        confidence: float = 0.5,
        feedback_count: int = 0,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> UserPreference:
        """
        Save or update user preference.

        Uses upsert logic: if preference exists, updates it; otherwise creates new.

        Args:
            user_id: User identifier
            preference_type: Type of preference ("topic", "team", "label")
            preference_key: Specific preference key (e.g., "backend", "engineering")
            score: Preference score (0.0 to 1.0)
            confidence: Confidence level (0.0 to 1.0)
            feedback_count: Number of feedback data points used
            extra_metadata: Additional context

        Returns:
            Created or updated UserPreference instance

        Raises:
            ValueError: If preference_type is invalid or score out of range
        """
        # Validate inputs
        valid_types = ("topic", "team", "label")
        if preference_type not in valid_types:
            raise ValueError(
                f"Invalid preference_type: {preference_type}. "
                f"Must be one of {valid_types}"
            )

        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {confidence}"
            )

        # Try to find existing preference
        existing = (
            self.session.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == preference_type,
                UserPreference.preference_key == preference_key,
            )
            .first()
        )

        if existing:
            # Update existing preference
            # SQLAlchemy ORM: Column assignments at runtime work despite type hints
            existing.score = score  # type: ignore[assignment]
            existing.confidence = confidence  # type: ignore[assignment]
            existing.feedback_count = feedback_count  # type: ignore[assignment]
            existing.last_updated = datetime.utcnow()  # type: ignore[assignment]
            if extra_metadata:
                existing.extra_metadata = extra_metadata  # type: ignore[assignment]

            self.session.commit()
            self.session.refresh(existing)

            logger.debug(
                f"Updated preference: {user_id}/{preference_type}/{preference_key} "
                f"(score={score}, confidence={confidence})"
            )
            return existing
        else:
            # Create new preference
            preference = UserPreference(
                user_id=user_id,
                preference_type=preference_type,
                preference_key=preference_key,
                score=score,
                confidence=confidence,
                feedback_count=feedback_count,
                extra_metadata=extra_metadata,
            )

            self.session.add(preference)
            self.session.commit()
            self.session.refresh(preference)

            logger.debug(
                f"Created preference: {user_id}/{preference_type}/{preference_key} "
                f"(score={score}, confidence={confidence})"
            )
            return preference

    def get_preferences_by_type(
        self, user_id: str, preference_type: str
    ) -> List[UserPreference]:
        """
        Get all preferences of specific type for a user.

        Args:
            user_id: User identifier
            preference_type: Type of preference ("topic", "team", "label")

        Returns:
            List of UserPreference instances, ordered by score descending
        """
        return (
            self.session.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == preference_type,
            )
            .order_by(desc(UserPreference.score))
            .all()
        )

    def get_all_preferences(self, user_id: str) -> List[UserPreference]:
        """
        Get all preferences for a user across all types.

        Args:
            user_id: User identifier

        Returns:
            List of UserPreference instances, ordered by type then score
        """
        return (
            self.session.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .order_by(UserPreference.preference_type, desc(UserPreference.score))
            .all()
        )

    def get_preference(
        self, user_id: str, preference_type: str, preference_key: str
    ) -> Optional[UserPreference]:
        """
        Get a specific preference.

        Args:
            user_id: User identifier
            preference_type: Type of preference
            preference_key: Specific preference key

        Returns:
            UserPreference instance if found, None otherwise
        """
        return (
            self.session.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == preference_type,
                UserPreference.preference_key == preference_key,
            )
            .first()
        )

    def get_top_preferences(
        self,
        user_id: str,
        preference_type: str,
        limit: int = 5,
        min_score: float = 0.6,
    ) -> List[UserPreference]:
        """
        Get top N preferences of a type above minimum score.

        Args:
            user_id: User identifier
            preference_type: Type of preference
            limit: Maximum number to return
            min_score: Minimum score threshold (default 0.6)

        Returns:
            List of top UserPreference instances
        """
        return (
            self.session.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == preference_type,
                UserPreference.score >= min_score,
            )
            .order_by(desc(UserPreference.score))
            .limit(limit)
            .all()
        )

    def delete_preference(
        self, user_id: str, preference_type: str, preference_key: str
    ) -> bool:
        """
        Delete a specific preference.

        Args:
            user_id: User identifier
            preference_type: Type of preference
            preference_key: Specific preference key

        Returns:
            True if deleted, False if not found
        """
        count = (
            self.session.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == preference_type,
                UserPreference.preference_key == preference_key,
            )
            .delete()
        )
        self.session.commit()

        logger.info(
            f"Deleted preference for user {user_id}: {preference_type}/{preference_key}"
        )
        return count > 0

    def delete_preferences(
        self, user_id: str, preference_type: Optional[str] = None
    ) -> int:
        """
        Delete preferences for a user.

        Args:
            user_id: User identifier
            preference_type: Optional type filter (if None, deletes all types)

        Returns:
            Number of preferences deleted
        """
        query = self.session.query(UserPreference).filter(
            UserPreference.user_id == user_id
        )

        if preference_type:
            query = query.filter(UserPreference.preference_type == preference_type)

        count = query.delete()
        self.session.commit()

        logger.info(
            f"Deleted {count} preferences for user {user_id}"
            + (f" (type={preference_type})" if preference_type else " (all types)")
        )
        return count

    def get_preference_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary statistics of user preferences.

        Args:
            user_id: User identifier

        Returns:
            Dict with counts by type, average scores, etc.
        """
        all_prefs = self.get_all_preferences(user_id)

        if not all_prefs:
            return {
                "total_count": 0,
                "by_type": {},
                "avg_score": 0.0,
                "avg_confidence": 0.0,
            }

        by_type = defaultdict(lambda: {"count": 0, "avg_score": 0.0})
        total_score = 0.0
        total_confidence = 0.0

        for pref in all_prefs:
            by_type[pref.preference_type]["count"] += 1
            by_type[pref.preference_type]["avg_score"] += pref.score
            total_score += pref.score
            total_confidence += pref.confidence

        # Calculate averages
        for pref_type in by_type:
            count = by_type[pref_type]["count"]
            by_type[pref_type]["avg_score"] = round(
                by_type[pref_type]["avg_score"] / count, 2
            )

        return {
            "total_count": len(all_prefs),
            "by_type": dict(by_type),
            "avg_score": round(total_score / len(all_prefs), 2),
            "avg_confidence": round(total_confidence / len(all_prefs), 2),
        }
