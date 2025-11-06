"""
Comparison test showing before/after behavior of database engine creation.

This test simulates the old behavior (creating engine on every call) vs the new
singleton pattern to demonstrate the improvement.
"""

import logging
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from linear_chief.config import DATABASE_PATH
from linear_chief.storage import get_engine, get_session_maker, reset_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


def old_behavior_get_engine(database_path=DATABASE_PATH):
    """OLD: Creates new engine on every call (before fix)."""
    db_url = f"sqlite:///{database_path}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    logger.info(f"  [OLD] Database engine created: {database_path}")
    return engine


def old_behavior_simulation():
    """Simulate old behavior - creates engine multiple times."""
    logger.info("\n" + "=" * 80)
    logger.info("BEFORE FIX: Old Behavior (Creating Engine Every Time)")
    logger.info("=" * 80)

    logger.info("\nSimulating 5 calls to get_session_maker()...")
    for i in range(1, 6):
        # Old behavior: get_engine() called every time
        engine = old_behavior_get_engine()
        logger.info(f"  Call {i}: Created new engine (id: {id(engine)})")

    logger.info("\nResult: 5 SEPARATE engine instances created")
    logger.info("Problem: Wasteful, slow, multiple connection setups")


def new_behavior_simulation():
    """Simulate new behavior - reuses singleton engine."""
    logger.info("\n" + "=" * 80)
    logger.info("AFTER FIX: New Behavior (Singleton Pattern)")
    logger.info("=" * 80)

    # Reset to clean state
    reset_engine()

    logger.info("\nSimulating 5 calls to get_session_maker()...")
    engines = []
    for i in range(1, 6):
        # New behavior: get_engine() returns singleton
        engine = get_engine()
        engines.append(engine)
        logger.info(f"  Call {i}: Got engine (id: {id(engine)})")

    # Verify all are the same object
    all_same = all(e is engines[0] for e in engines)

    logger.info(f"\nResult: {'SAME' if all_same else 'DIFFERENT'} engine instance reused")
    logger.info("Benefit: Fast, efficient, single connection setup")


def performance_comparison():
    """Show performance difference."""
    import time

    logger.info("\n" + "=" * 80)
    logger.info("PERFORMANCE COMPARISON")
    logger.info("=" * 80)

    # Old behavior timing
    logger.info("\nOLD: Creating 100 engines...")
    start = time.time()
    for _ in range(100):
        old_behavior_get_engine()
    old_time = time.time() - start
    logger.info(f"  Time: {old_time:.4f} seconds")

    # New behavior timing
    logger.info("\nNEW: Getting singleton engine 100 times...")
    reset_engine()
    start = time.time()
    for _ in range(100):
        get_engine()
    new_time = time.time() - start
    logger.info(f"  Time: {new_time:.4f} seconds")

    # Comparison
    speedup = old_time / new_time if new_time > 0 else float("inf")
    logger.info(f"\nSpeedup: {speedup:.1f}x faster")


def main():
    """Run all comparisons."""
    logger.info("\n" + "=" * 80)
    logger.info("DATABASE ENGINE SINGLETON - BEFORE/AFTER COMPARISON")
    logger.info("=" * 80)

    old_behavior_simulation()
    new_behavior_simulation()
    performance_comparison()

    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(
        "\nBefore Fix:"
        "\n  - New engine created on EVERY call"
        "\n  - Multiple connection setups"
        "\n  - Slower performance"
        "\n  - More log spam"
        "\n"
        "\nAfter Fix:"
        "\n  - Engine created ONCE at startup"
        "\n  - Single connection setup"
        "\n  - Much faster performance"
        "\n  - Cleaner logs"
        "\n  - Same API (no code changes needed)"
    )
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
