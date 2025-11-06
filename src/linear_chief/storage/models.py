"""SQLAlchemy ORM models for persistent storage."""

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, Index
from sqlalchemy.sql import func

from linear_chief.storage.database import Base


class IssueHistory(Base):
    """
    Track Linear issue snapshots over time.

    Stores issue state at specific points in time to detect changes,
    stagnation, and trends.
    """

    __tablename__ = "issue_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(String(50), nullable=False, index=True)  # e.g., "PROJ-123"
    linear_id = Column(String(100), nullable=False)  # Linear UUID
    title = Column(Text, nullable=False)
    state = Column(String(50), nullable=False)  # e.g., "In Progress", "Done"
    priority = Column(
        Integer, nullable=True
    )  # 0=None, 1=Urgent, 2=High, 3=Normal, 4=Low
    assignee_id = Column(String(100), nullable=True)
    assignee_name = Column(String(200), nullable=True)
    team_id = Column(String(100), nullable=True)
    team_name = Column(String(200), nullable=True)
    labels = Column(JSON, nullable=True)  # List of label names
    extra_metadata = Column(
        JSON, nullable=True
    )  # Additional fields (project, cycle, etc.)
    snapshot_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (Index("ix_issue_snapshot", "issue_id", "snapshot_at"),)

    def __repr__(self) -> str:
        return f"<IssueHistory(issue_id={self.issue_id}, state={self.state}, snapshot_at={self.snapshot_at})>"


class Briefing(Base):
    """
    Archive of generated briefings with metadata.

    Stores briefings for historical reference, cost tracking,
    and context building for mem0.
    """

    __tablename__ = "briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)  # Full briefing text (markdown)
    issue_count = Column(Integer, nullable=False, default=0)
    agent_context = Column(JSON, nullable=True)  # Context used by Agent SDK
    cost_usd = Column(Float, nullable=True)  # Estimated cost in USD
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    model_name = Column(String(100), nullable=True)  # e.g., "claude-sonnet-4-20250514"
    delivery_status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, sent, failed
    telegram_message_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column(
        JSON, nullable=True
    )  # Additional fields (timezone, user prefs, etc.)
    generated_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    sent_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Briefing(id={self.id}, issue_count={self.issue_count}, generated_at={self.generated_at}, status={self.delivery_status})>"


class Metrics(Base):
    """
    Track operational metrics for monitoring and cost control.

    Records API usage, costs, success rates, and performance metrics.
    """

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_type = Column(
        String(50), nullable=False, index=True
    )  # e.g., "api_call", "briefing_generated"
    metric_name = Column(
        String(100), nullable=False
    )  # e.g., "linear_fetch_issues", "anthropic_generate"
    value = Column(Float, nullable=False)  # Numeric value (count, duration, cost, etc.)
    unit = Column(
        String(50), nullable=False
    )  # e.g., "count", "seconds", "usd", "tokens"
    extra_metadata = Column(
        JSON, nullable=True
    )  # Additional context (issue count, model, etc.)
    recorded_at = Column(DateTime, nullable=False, default=func.now(), index=True)

    __table_args__ = (
        Index("ix_metrics_type_name", "metric_type", "metric_name", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<Metrics(type={self.metric_type}, name={self.metric_name}, value={self.value}, unit={self.unit})>"


class Conversation(Base):
    """
    Store user conversation history for bidirectional Telegram bot.

    Tracks all user and assistant messages to maintain conversation context
    and enable natural dialogue with the Linear Chief of Staff agent.
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False)  # Telegram user_id
    chat_id = Column(String(100), nullable=False)  # Telegram chat_id
    message = Column(Text, nullable=False)  # Message content
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    timestamp = Column(DateTime, nullable=False, default=func.now())
    extra_metadata = Column(
        JSON, nullable=True
    )  # Additional fields (message_id, reply_to, etc.)

    __table_args__ = (
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_chat_id", "chat_id"),
        Index("ix_conversations_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(user_id={self.user_id}, role={self.role}, timestamp={self.timestamp})>"


class Feedback(Base):
    """
    Store user feedback on briefings and issue interactions.

    Tracks positive/negative feedback on briefings and user actions
    on specific issues to improve future briefings.
    """

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)  # Telegram user ID
    briefing_id = Column(Integer, nullable=True)  # FK to briefings table
    feedback_type = Column(
        String(20), nullable=False, index=True
    )  # 'positive', 'negative', 'issue_action'
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    extra_metadata = Column(
        JSON, nullable=True
    )  # Additional context (telegram_message_id, action details, etc.)

    __table_args__ = (Index("ix_feedback_user_time", "user_id", "timestamp"),)

    def __repr__(self) -> str:
        return f"<Feedback(user_id={self.user_id}, type={self.feedback_type}, timestamp={self.timestamp})>"


class IssueEngagement(Base):
    """
    Track user engagement with specific Linear issues.

    Records when users interact with issues (queries, views, mentions) to learn
    engagement patterns and improve personalized issue ranking in briefings.

    Engagement score (0.0 to 1.0) combines:
    - Frequency: How often user interacts with this issue
    - Recency: How recently user interacted (exponential decay)
    """

    __tablename__ = "issue_engagements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False)  # Telegram user ID
    issue_id = Column(String(50), nullable=False)  # e.g., "AI-1799", "DMD-480"
    linear_id = Column(String(100), nullable=False)  # Linear UUID
    interaction_type = Column(String(20), nullable=False)  # 'query', 'view', 'mention'
    interaction_count = Column(Integer, nullable=False, default=1)
    engagement_score = Column(Float, nullable=False, default=0.5)
    last_interaction = Column(DateTime, nullable=False, default=func.now())
    first_interaction = Column(DateTime, nullable=False, default=func.now())
    context = Column(Text, nullable=True)  # What user said (first 200 chars)
    extra_metadata = Column(JSON, nullable=True)  # Additional fields for future use

    __table_args__ = (
        Index("ix_issue_engagements_user_id", "user_id"),
        Index("ix_issue_engagements_issue_id", "issue_id"),
        Index("ix_issue_engagements_score", "engagement_score"),
        Index("ix_issue_engagements_last_interaction", "last_interaction"),
        Index("ix_issue_engagements_user_issue", "user_id", "issue_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<IssueEngagement(user_id={self.user_id}, issue_id={self.issue_id}, score={self.engagement_score}, count={self.interaction_count})>"


class UserPreference(Base):
    """
    Store learned user preferences from feedback analysis.

    Tracks user preferences for topics, teams, labels, and other
    issue characteristics learned from feedback patterns. Used for
    intelligent briefing personalization.
    """

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False)
    preference_type = Column(String(50), nullable=False)  # "topic", "team", "label"
    preference_key = Column(
        String(100), nullable=False
    )  # e.g., "backend", "engineering"
    score = Column(Float, nullable=False)  # 0.0 to 1.0 (preference strength)
    confidence = Column(Float, nullable=False, default=0.5)  # How certain are we
    feedback_count = Column(Integer, nullable=False, default=0)  # Data points used
    last_updated = Column(DateTime, nullable=False, default=func.now())
    extra_metadata = Column(JSON, nullable=True)  # Additional context

    __table_args__ = (
        Index("ix_user_preferences_user_id", "user_id"),
        Index("ix_user_preferences_type", "preference_type"),
        Index(
            "ix_user_preferences_user_type_key",
            "user_id",
            "preference_type",
            "preference_key",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<UserPreference(user_id={self.user_id}, type={self.preference_type}, key={self.preference_key}, score={self.score})>"
