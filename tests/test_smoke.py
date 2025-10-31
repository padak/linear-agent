"""Smoke tests to verify basic project setup."""

import pytest
from linear_chief import __version__
from linear_chief import config


def test_version() -> None:
    """Verify package version is defined."""
    assert __version__ == "0.1.0"


def test_config_loaded() -> None:
    """Verify configuration module can be imported."""
    assert hasattr(config, "LINEAR_API_KEY")
    assert hasattr(config, "ANTHROPIC_API_KEY")
    assert hasattr(config, "TELEGRAM_BOT_TOKEN")


def test_ensure_directories() -> None:
    """Verify directory creation function works."""
    config.ensure_directories()
    assert config.DATABASE_PATH.parent.exists()
    assert config.CHROMADB_PATH.exists()
    assert config.LOGS_PATH.exists()


@pytest.mark.parametrize(
    "setting,expected_type",
    [
        ("LOCAL_TIMEZONE", str),
        ("BRIEFING_TIME", str),
        ("EMBEDDING_MODEL", str),
        ("MONTHLY_BUDGET_USD", float),
    ],
)
def test_config_types(setting: str, expected_type: type) -> None:
    """Verify configuration values have correct types."""
    value = getattr(config, setting)
    assert isinstance(value, expected_type)
