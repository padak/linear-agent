"""Database engine setup and session management."""

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path
from typing import Generator, Union, Optional, Any
import logging

from linear_chief.config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Base class for all ORM models
Base = declarative_base()

# Module-level singletons for engine and session maker
_engine: Optional[Engine] = None
_session_maker: Optional[sessionmaker] = None
_current_db_path: Optional[Union[Path, str]] = None


def get_engine(database_path: Union[Path, str] = DATABASE_PATH) -> Engine:
    """
    Get SQLAlchemy engine for SQLite database (singleton pattern).

    Args:
        database_path: Path to SQLite database file or ":memory:" for in-memory DB

    Returns:
        SQLAlchemy Engine instance (reused across calls for same path)

    Note:
        Uses check_same_thread=False for SQLite to allow multi-threaded access.
        StaticPool ensures connection reuse in development/testing.
        Engine is created once and reused for the same database path.
    """
    global _engine, _current_db_path

    # Check if we need to create a new engine (different path or first call)
    if _engine is None or _current_db_path != database_path:
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

        _engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,  # Set to True for SQL debugging
        )

        # Enable WAL mode for better concurrency (only for file-based DBs)
        if database_path != ":memory:":
            with _engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()

        _current_db_path = database_path
        logger.info(f"Database engine created: {database_path}")
    else:
        logger.debug(f"Reusing existing database engine: {database_path}")

    return _engine


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
    Get session factory for database operations (singleton pattern).

    Args:
        engine: SQLAlchemy engine (if None, uses default engine singleton)

    Returns:
        SessionMaker instance (reused across calls)

    Note:
        Session maker is created once and reused for efficiency.
    """
    global _session_maker

    # If custom engine provided, create a new session maker for it
    if engine is not None:
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Otherwise use singleton pattern for default engine
    if _session_maker is None:
        default_engine = get_engine()
        _session_maker = sessionmaker(autocommit=False, autoflush=False, bind=default_engine)
        logger.debug("Session maker created")
    else:
        logger.debug("Reusing existing session maker")

    return _session_maker


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


def reset_engine() -> None:
    """
    Reset engine and session maker singletons.

    This is primarily useful for testing when you need to switch between
    different database instances or clean up connections.

    Warning:
        This will dispose of the existing engine and close all connections.
        Use with caution in production code.
    """
    global _engine, _session_maker, _current_db_path

    if _engine is not None:
        _engine.dispose()
        logger.debug("Database engine disposed")

    _engine = None
    _session_maker = None
    _current_db_path = None
    logger.debug("Database singletons reset")
