#!/usr/bin/env python3
"""
Manual test script for real-time issue fetching feature.

This script demonstrates the new capability to extract issue IDs from user queries
and fetch full, real-time details from Linear API.

Usage:
    python test_real_time_fetch.py
"""

import asyncio
from linear_chief.agent.context_builder import (
    extract_issue_ids,
    fetch_issue_details,
    format_fetched_issues,
)
from linear_chief.utils.logging import setup_logging, get_logger
from linear_chief.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE

# Initialize logging to see cache hit/miss messages
setup_logging(
    level=LOG_LEVEL,
    format_type=LOG_FORMAT,
    log_file=LOG_FILE,
)
logger = get_logger(__name__)


async def main():
    """Test the real-time issue fetching feature."""
    logger.info("Starting real-time issue fetching test")
    print("=" * 80)
    print("Real-Time Issue Fetching Test")
    print("=" * 80)
    print()

    # Test 1: Extract issue IDs from queries
    print("Test 1: Issue ID Extraction")
    print("-" * 80)

    test_queries = [
        "dej mi detail CSM-93",
        "co je s DMD-480 a AI-1799?",
        "žádné issue ID zde",
        "PROJ-123: needs review and DMD-501 is blocked",
    ]

    for query in test_queries:
        issue_ids = extract_issue_ids(query)
        print(f"Query: '{query}'")
        print(f"Found IDs: {issue_ids}")
        print()

    # Test 2: Fetch real issues (requires valid LINEAR_API_KEY)
    print("\nTest 2: Real-Time Issue Fetching")
    print("-" * 80)

    from linear_chief.config import LINEAR_API_KEY

    if not LINEAR_API_KEY:
        print("⚠️  LINEAR_API_KEY not configured. Skipping real API test.")
        print("Set LINEAR_API_KEY in .env to test real fetching.")
        return

    # Extract IDs from a sample query
    sample_query = "dej mi detail CSM-93"
    issue_ids = extract_issue_ids(sample_query)

    if not issue_ids:
        print("No issue IDs found in sample query. Try a different query.")
        return

    print(f"Fetching details for: {issue_ids}")
    print()

    try:
        issues = await fetch_issue_details(issue_ids)

        if not issues:
            print("⚠️  No issues found. They may not exist or you may not have access.")
            print("Try using issue IDs from your own Linear workspace.")
            return

        print(f"Successfully fetched {len(issues)} issue(s)!")
        print()

        # Format and display
        formatted = format_fetched_issues(issues)
        print("Formatted Output:")
        print("=" * 80)
        print(formatted)
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error fetching issues: {e}")
        print("This is expected if the issue IDs don't exist in your workspace.")


if __name__ == "__main__":
    asyncio.run(main())
