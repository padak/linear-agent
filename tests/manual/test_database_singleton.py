"""Test database engine singleton behavior."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from linear_chief.storage import get_engine, get_session_maker, reset_engine

# Configure logging to see the singleton messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def test_engine_singleton():
    """Test that engine is created only once."""
    logger.info("=" * 80)
    logger.info("TEST 1: Engine Singleton Pattern")
    logger.info("=" * 80)

    # Reset to clean state
    reset_engine()

    logger.info("\n1. First call to get_engine() - should create engine")
    engine1 = get_engine()

    logger.info("\n2. Second call to get_engine() - should reuse engine")
    engine2 = get_engine()

    logger.info("\n3. Third call to get_engine() - should reuse engine")
    engine3 = get_engine()

    # Verify same object
    assert engine1 is engine2, "Engine 1 and 2 should be the same object"
    assert engine2 is engine3, "Engine 2 and 3 should be the same object"

    logger.info("\n✓ All three calls returned the same engine instance")


def test_session_maker_singleton():
    """Test that session maker is created only once."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Session Maker Singleton Pattern")
    logger.info("=" * 80)

    # Reset to clean state
    reset_engine()

    logger.info("\n1. First call to get_session_maker() - should create engine and session maker")
    sm1 = get_session_maker()

    logger.info("\n2. Second call to get_session_maker() - should reuse both")
    sm2 = get_session_maker()

    logger.info("\n3. Third call to get_session_maker() - should reuse both")
    sm3 = get_session_maker()

    # Verify same object
    assert sm1 is sm2, "Session maker 1 and 2 should be the same object"
    assert sm2 is sm3, "Session maker 2 and 3 should be the same object"

    logger.info("\n✓ All three calls returned the same session maker instance")


def test_multiple_sessions():
    """Test that multiple session creations don't recreate engine."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Multiple Session Usage Pattern")
    logger.info("=" * 80)

    # Reset to clean state
    reset_engine()

    logger.info("\n1. Creating session maker (should create engine)")
    sm = get_session_maker()

    logger.info("\n2. Creating multiple sessions (should NOT create new engines)")
    session1 = sm()
    session2 = sm()
    session3 = sm()

    # Close sessions
    session1.close()
    session2.close()
    session3.close()

    logger.info("\n✓ Multiple sessions created without recreating engine")


def test_reset_functionality():
    """Test that reset_engine() properly clears singletons."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Reset Engine Functionality")
    logger.info("=" * 80)

    # Reset to clean state
    reset_engine()

    logger.info("\n1. Creating initial engine and session maker")
    engine1 = get_engine()
    sm1 = get_session_maker()

    logger.info("\n2. Resetting singletons")
    reset_engine()

    logger.info("\n3. Creating new engine and session maker after reset")
    engine2 = get_engine()
    sm2 = get_session_maker()

    # Verify different objects (new instances created)
    assert engine1 is not engine2, "Engine should be recreated after reset"
    assert sm1 is not sm2, "Session maker should be recreated after reset"

    logger.info("\n✓ Reset properly cleared and recreated singletons")


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("DATABASE SINGLETON TESTS")
    logger.info("=" * 80)

    try:
        test_engine_singleton()
        test_session_maker_singleton()
        test_multiple_sessions()
        test_reset_functionality()

        logger.info("\n" + "=" * 80)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 80)
        logger.info(
            "\nKey observations:"
            "\n- Engine created only ONCE per lifecycle"
            "\n- Session maker created only ONCE per lifecycle"
            "\n- Multiple sessions don't recreate engine"
            "\n- Reset properly clears and recreates singletons"
        )

    except AssertionError as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ UNEXPECTED ERROR: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
