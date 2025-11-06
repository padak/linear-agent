#!/usr/bin/env python3
"""
Demo script for testing semantic search functionality.

This script demonstrates the semantic search capabilities by:
1. Adding test issues to ChromaDB
2. Finding similar issues
3. Searching by natural language
4. Formatting results for display

Usage:
    python scripts/test_semantic_search.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from linear_chief.intelligence.semantic_search import SemanticSearchService
from linear_chief.memory.vector_store import IssueVectorStore


async def main():
    """Run semantic search demo."""
    print("=" * 80)
    print("Semantic Search Demo")
    print("=" * 80)

    # Initialize services
    print("\n1. Initializing services...")
    vector_store = IssueVectorStore()
    search_service = SemanticSearchService()

    # Add test issues
    print("\n2. Adding test issues to vector store...")
    test_issues = [
        {
            "issue_id": "DEMO-1",
            "title": "OAuth2 Authentication Implementation",
            "description": "Implement OAuth2 authentication flow with PKCE support for secure login",
            "state": "In Progress",
            "team": "Backend",
        },
        {
            "issue_id": "DEMO-2",
            "title": "OpenID Connect Provider Integration",
            "description": "Add support for OIDC authentication providers including Google and Azure AD",
            "state": "Todo",
            "team": "Backend",
        },
        {
            "issue_id": "DEMO-3",
            "title": "Database Migration Script",
            "description": "Create migration script to move user data from PostgreSQL to MySQL",
            "state": "Done",
            "team": "DevOps",
        },
        {
            "issue_id": "DEMO-4",
            "title": "Login Page UI Redesign",
            "description": "Redesign the login page with modern authentication flow and better UX",
            "state": "In Progress",
            "team": "Frontend",
        },
        {
            "issue_id": "DEMO-5",
            "title": "API Performance Optimization",
            "description": "Optimize slow API endpoints and reduce response times",
            "state": "Todo",
            "team": "Backend",
        },
    ]

    for issue in test_issues:
        await vector_store.add_issue(
            issue_id=issue["issue_id"],
            title=issue["title"],
            description=issue["description"],
            metadata={
                "title": issue["title"],
                "description": issue["description"],
                "state": issue["state"],
                "team_name": issue["team"],
                "url": f"https://demo.linear.app/issue/{issue['issue_id']}",
            },
        )
        print(f"  ✓ Added {issue['issue_id']}: {issue['title'][:50]}...")

    # Wait for indexing
    await asyncio.sleep(0.5)

    # Test 1: Find similar issues
    print("\n3. Finding issues similar to DEMO-1 (OAuth2 Authentication)...")
    print("   Query: Find similar issues to DEMO-1")
    print("   Threshold: 50% similarity\n")

    # Mock get_issue_context for demo
    from unittest.mock import AsyncMock, patch

    with patch.object(
        search_service, "get_issue_context", new_callable=AsyncMock
    ) as mock_context:
        mock_context.return_value = {
            "issue_id": "DEMO-1",
            "title": "OAuth2 Authentication Implementation",
            "description": "Implement OAuth2 authentication flow with PKCE support for secure login",
            "state": "In Progress",
            "team": "Backend",
            "url": "https://demo.linear.app/issue/DEMO-1",
        }

        similar_results = await search_service.find_similar_issues(
            "DEMO-1", limit=3, min_similarity=0.3
        )

        formatted = search_service.format_similarity_results(
            similar_results, include_score=True
        )
        print(formatted)

    # Test 2: Natural language search
    print("\n" + "=" * 80)
    print("\n4. Natural language search...")
    print("   Query: 'authentication and login features'")
    print("   Threshold: 30% similarity\n")

    search_results = await search_service.search_by_text(
        "authentication and login features", limit=3, min_similarity=0.3
    )

    formatted = search_service.format_similarity_results(
        search_results, include_score=True
    )
    print(formatted)

    # Test 3: Different topic search
    print("\n" + "=" * 80)
    print("\n5. Natural language search for different topic...")
    print("   Query: 'performance and optimization'")
    print("   Threshold: 30% similarity\n")

    perf_results = await search_service.search_by_text(
        "performance and optimization", limit=3, min_similarity=0.3
    )

    formatted = search_service.format_similarity_results(
        perf_results, include_score=True
    )
    print(formatted)

    # Cleanup
    print("\n" + "=" * 80)
    print("\n6. Cleaning up test data...")
    for issue in test_issues:
        await vector_store.delete_issue(issue["issue_id"])
        print(f"  ✓ Deleted {issue['issue_id']}")

    print("\n" + "=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
