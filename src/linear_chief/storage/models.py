"""SQLAlchemy ORM models for persistent storage."""

from datetime import datetime
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
    priority = Column(Integer, nullable=True)  # 0=None, 1=Urgent, 2=High, 3=Normal, 4=Low
    assignee_id = Column(String(100), nullable=True)
    assignee_name = Column(String(200), nullable=True)
    team_id = Column(String(100), nullable=True)
    team_name = Column(String(200), nullable=True)
    labels = Column(JSON, nullable=True)  # List of label names
    extra_metadata = Column(JSON, nullable=True)  # Additional fields (project, cycle, etc.)
    snapshot_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        Index("ix_issue_snapshot", "issue_id", "snapshot_at"),
    )

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
    delivery_status = Column(String(50), nullable=False, default="pending")  # pending, sent, failed
    telegram_message_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)  # Additional fields (timezone, user prefs, etc.)
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
    metric_type = Column(String(50), nullable=False, index=True)  # e.g., "api_call", "briefing_generated"
    metric_name = Column(String(100), nullable=False)  # e.g., "linear_fetch_issues", "anthropic_generate"
    value = Column(Float, nullable=False)  # Numeric value (count, duration, cost, etc.)
    unit = Column(String(50), nullable=False)  # e.g., "count", "seconds", "usd", "tokens"
    extra_metadata = Column(JSON, nullable=True)  # Additional context (issue count, model, etc.)
    recorded_at = Column(DateTime, nullable=False, default=func.now(), index=True)

    __table_args__ = (
        Index("ix_metrics_type_name", "metric_type", "metric_name", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<Metrics(type={self.metric_type}, name={self.metric_name}, value={self.value}, unit={self.unit})>"
