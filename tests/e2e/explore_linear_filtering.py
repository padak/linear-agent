#!/usr/bin/env python3
"""
Interactive Linear API exploration script for enhanced filtering.

This script tests various filtering strategies to find all issues
a user has interacted with (commented, mentioned, reacted, etc.).

Usage:
    python tests/e2e/test_linear_filtering_exploration.py
"""

import asyncio
import json
from typing import Dict, List, Any
from linear_chief.linear.client import LinearClient
from linear_chief import config


async def explore_comment_structure(client: LinearClient) -> Dict[str, Any]:
    """Explore the structure of comments in Linear API."""
    print("\n🔍 Exploring Comment Structure...")
    print("=" * 80)

    # Get viewer info first
    viewer = await client.get_viewer()
    print(f"\n✓ Authenticated as: {viewer.get('name')} ({viewer.get('email')})")
    viewer_id = viewer.get("id")

    # Test 1: Get recent comments globally
    print("\n📝 Test 1: Fetching recent comments (no filter)...")
    query = """
    query {
      comments(first: 5) {
        nodes {
          id
          body
          createdAt
          user {
            id
            name
            email
          }
          issue {
            id
            identifier
            title
          }
        }
      }
    }
    """
    result = await client.query(query)
    comments = result.get("comments", {}).get("nodes", [])
    print(f"  Found {len(comments)} recent comments")
    if comments:
        print(f"  Sample comment: {comments[0].get('body', '')[:100]}...")
        print(f"  By: {comments[0].get('user', {}).get('name')}")
        print(
            f"  On issue: {comments[0].get('issue', {}).get('identifier')} - {comments[0].get('issue', {}).get('title')}"
        )

    # Test 2: Try filtering comments by user
    print(f"\n📝 Test 2: Fetching comments by user ID: {viewer_id}")
    query_with_user_filter = f"""
    query {{
      comments(first: 10, filter: {{user: {{id: {{eq: "{viewer_id}"}}}}}}) {{
        nodes {{
          id
          body
          createdAt
          issue {{
            id
            identifier
            title
          }}
        }}
      }}
    }}
    """
    try:
        result = await client.query(query_with_user_filter)
        my_comments = result.get("comments", {}).get("nodes", [])
        print(f"  ✓ Found {len(my_comments)} comments by me")
        if my_comments:
            print(f"  Sample: {my_comments[0].get('body', '')[:100]}...")
            print(
                f"  On issue: {my_comments[0].get('issue', {}).get('identifier')}"
            )

        # Extract unique issue IDs from my comments
        issue_ids = set()
        for comment in my_comments:
            issue = comment.get("issue")
            if issue:
                issue_ids.add(issue.get("id"))
        print(f"\n  📊 Issues I commented on: {len(issue_ids)} unique issues")

        return {
            "success": True,
            "my_comments_count": len(my_comments),
            "unique_issues": len(issue_ids),
            "issue_ids": list(issue_ids),
        }

    except Exception as e:
        print(f"  ❌ Error with user filter: {e}")
        return {"success": False, "error": str(e)}


async def test_issue_comment_filter(
    client: LinearClient, test_issue_id: str = None
) -> Dict[str, Any]:
    """Test filtering issues by comments."""
    print("\n🔍 Testing Issue Filtering by Comments...")
    print("=" * 80)

    viewer = await client.get_viewer()
    viewer_id = viewer.get("id")

    # Strategy 1: Get all my comments, extract issue IDs
    print("\n📝 Strategy 1: Get issues via comments query...")
    query = f"""
    query {{
      comments(first: 100, filter: {{user: {{id: {{eq: "{viewer_id}"}}}}}}) {{
        nodes {{
          issue {{
            id
            identifier
            title
            state {{
              name
            }}
          }}
        }}
      }}
    }}
    """

    try:
        result = await client.query(query)
        comments = result.get("comments", {}).get("nodes", [])

        # Deduplicate issues
        issues_map = {}
        for comment in comments:
            issue = comment.get("issue")
            if issue:
                issue_id = issue.get("id")
                if issue_id and issue_id not in issues_map:
                    issues_map[issue_id] = issue

        print(f"  ✓ Found {len(issues_map)} unique issues I commented on")
        if issues_map:
            for issue_id, issue in list(issues_map.items())[:5]:
                print(
                    f"    - {issue.get('identifier')}: {issue.get('title')[:60]}..."
                )

        return {
            "strategy": "comments_query",
            "success": True,
            "issues_count": len(issues_map),
            "issues": list(issues_map.values()),
        }

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"strategy": "comments_query", "success": False, "error": str(e)}


async def test_advanced_filters(client: LinearClient) -> Dict[str, Any]:
    """Test advanced filtering strategies."""
    print("\n🔍 Testing Advanced Filtering Strategies...")
    print("=" * 80)

    viewer = await client.get_viewer()
    viewer_id = viewer.get("id")
    viewer_email = viewer.get("email")

    results = {}

    # Strategy: Issues with my comments (using IssueFilter)
    print("\n📝 Testing: Issues with comments filter...")
    query = f"""
    query {{
      issues(
        first: 50
        filter: {{
          comments: {{
            some: {{
              user: {{
                id: {{eq: "{viewer_id}"}}
              }}
            }}
          }}
        }}
      ) {{
        nodes {{
          id
          identifier
          title
          state {{
            name
          }}
          comments {{
            nodes {{
              id
              user {{
                name
              }}
            }}
          }}
        }}
      }}
    }}
    """

    try:
        result = await client.query(query)
        issues = result.get("issues", {}).get("nodes", [])
        print(f"  ✓ Found {len(issues)} issues with my comments")
        if issues:
            for issue in issues[:3]:
                my_comments = [
                    c
                    for c in issue.get("comments", {}).get("nodes", [])
                    if c.get("user", {}).get("name") == viewer.get("name")
                ]
                print(
                    f"    - {issue.get('identifier')}: {issue.get('title')[:50]}... ({len(my_comments)} comments)"
                )

        results["comments_filter"] = {
            "success": True,
            "issues_count": len(issues),
            "issues": issues,
        }

    except Exception as e:
        print(f"  ❌ Error: {e}")
        results["comments_filter"] = {"success": False, "error": str(e)}

    return results


async def compare_all_strategies(client: LinearClient) -> None:
    """Compare all filtering strategies and show comprehensive results."""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE LINEAR FILTERING ANALYSIS")
    print("=" * 80)

    viewer = await client.get_viewer()
    print(f"\n👤 User: {viewer.get('name')} ({viewer.get('email')})")

    # Get current implementation
    print("\n🔧 Current Implementation: get_my_relevant_issues()")
    current_issues = await client.get_my_relevant_issues(limit=100)
    print(f"  ✓ Found {len(current_issues)} issues")

    # Test comment exploration
    comment_data = await explore_comment_structure(client)

    # Test issue filtering
    issue_comment_data = await test_issue_comment_filter(client)

    # Test advanced filters
    advanced_data = await test_advanced_filters(client)

    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"\nCurrent implementation:        {len(current_issues)} issues")

    if comment_data.get("success"):
        print(
            f"Issues from my comments:       {comment_data.get('unique_issues', 0)} issues"
        )

    if issue_comment_data.get("success"):
        print(
            f"Issues via comments query:     {issue_comment_data.get('issues_count', 0)} issues"
        )

    if advanced_data.get("comments_filter", {}).get("success"):
        print(
            f"Issues with comments filter:   {advanced_data['comments_filter']['issues_count']} issues"
        )

    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("=" * 80)

    if advanced_data.get("comments_filter", {}).get("success"):
        print(
            "\n✅ BEST APPROACH: Use IssueFilter with comments.some.user filter"
        )
        print("   This is the most efficient and native Linear API approach.")
        print("\n   GraphQL filter:")
        print(
            """   filter: {
     comments: {
       some: {
         user: { id: { eq: "user-id" } }
       }
     }
   }"""
        )
    else:
        print(
            "\n⚠️  FALLBACK: Use comments query and extract issue IDs"
        )
        print("   Less efficient but reliable approach.")


async def main():
    """Main exploration script."""
    print("\n🚀 Linear API Filtering Exploration")
    print("=" * 80)

    # Initialize client
    api_key = config.LINEAR_API_KEY
    if not api_key:
        print("❌ Error: LINEAR_API_KEY not found in environment")
        print("Please set it in your .env file")
        return

    async with LinearClient(api_key) as client:
        # Test connection
        print("\n🔌 Testing connection...")
        viewer = await client.get_viewer()
        print(f"✓ Connected as: {viewer.get('name')} ({viewer.get('email')})")

        # Run comprehensive analysis
        await compare_all_strategies(client)

        print("\n" + "=" * 80)
        print("✅ Exploration complete!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
