"""Database engine setup and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path
from typing import Generator, Union, Optional, Any
import logging

from linear_chief.config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Base class for all ORM models
Base = declarative_base()


def get_engine(database_path: Union[Path, str] = DATABASE_PATH):
    """
    Create SQLAlchemy engine for SQLite database.

    Args:
        database_path: Path to SQLite database file or ":memory:" for in-memory DB

    Returns:
        SQLAlchemy Engine instance

    Note:
        Uses check_same_thread=False for SQLite to allow multi-threaded access.
        StaticPool ensures connection reuse in development/testing.
    """
    # Handle in-memory database
    if database_path == ":memory:":
        db_url = "sqlite:///:memory:"
    else:
        # Convert to Path if string
        if isinstance(database_path, str):
            database_path = Path(database_path)

        # Create parent directories
        database_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{database_path}"

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
    )

    logger.info(f"Database engine created: {database_path}")
    return engine


def init_db(engine=None) -> None:
    """
    Initialize database schema by creating all tables.

    Args:
        engine: SQLAlchemy engine (if None, creates default engine)
    """
    if engine is None:
        engine = get_engine()

    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized")


def get_session_maker(engine=None) -> sessionmaker:
    """
    Create session factory for database operations.

    Args:
        engine: SQLAlchemy engine (if None, creates default engine)

    Returns:
        SessionMaker instance
    """
    if engine is None:
        engine = get_engine()

    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session(
    session_maker: Optional[sessionmaker[Any]] = None,
) -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup.

    Args:
        session_maker: SessionMaker instance (if None, creates default)

    Yields:
        SQLAlchemy Session

    Example:
        >>> session_maker = get_session_maker()
        >>> for session in get_db_session(session_maker):
        >>>     issue = session.query(IssueHistory).first()
    """
    if session_maker is None:
        session_maker = get_session_maker()

    session = session_maker()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        session.close()
