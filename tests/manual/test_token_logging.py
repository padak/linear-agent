#!/usr/bin/env python3
"""
Test script to demonstrate visible token usage logging.

This script shows how token counts and costs are now visible in console logs
during conversation and briefing generation.
"""

import asyncio
import logging
from linear_chief.agent import ConversationAgent, BriefingAgent
from linear_chief.config import ANTHROPIC_API_KEY


# Configure logging to show console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


async def test_conversation_agent():
    """Test ConversationAgent with visible token logging."""
    print("\n" + "="*80)
    print("Testing ConversationAgent Token Logging")
    print("="*80 + "\n")

    agent = ConversationAgent(api_key=ANTHROPIC_API_KEY)

    # Simple test query
    response = await agent.generate_response(
        user_message="What is Linear?",
        conversation_history=[],
        context=None,
        max_tokens=200,
    )

    print(f"\nResponse length: {len(response)} chars")
    print("Check the log output above for token usage details!")


async def test_briefing_agent():
    """Test BriefingAgent with visible token logging."""
    print("\n" + "="*80)
    print("Testing BriefingAgent Token Logging")
    print("="*80 + "\n")

    agent = BriefingAgent(api_key=ANTHROPIC_API_KEY)

    # Create sample issues
    sample_issues = [
        {
            "identifier": "TEST-123",
            "title": "Implement user authentication",
            "state": {"name": "In Progress"},
            "priorityLabel": "High",
            "assignee": {"name": "John Doe"},
            "team": {"name": "Engineering"},
            "updatedAt": "2025-11-05T10:30:00Z",
            "description": "Add OAuth2 authentication flow to the application",
            "url": "https://linear.app/test/issue/TEST-123",
            "comments": {"nodes": []},
        },
        {
            "identifier": "TEST-124",
            "title": "Fix database migration bug",
            "state": {"name": "Blocked"},
            "priorityLabel": "Critical",
            "assignee": {"name": "Jane Smith"},
            "team": {"name": "Engineering"},
            "updatedAt": "2025-11-04T15:00:00Z",
            "description": "Database migrations failing on production",
            "url": "https://linear.app/test/issue/TEST-124",
            "comments": {"nodes": [
                {
                    "body": "Waiting for DevOps to review infrastructure changes",
                    "user": {"name": "Jane Smith"}
                }
            ]},
        }
    ]

    briefing = await agent.generate_briefing(
        issues=sample_issues,
        user_context=None,
        max_tokens=500,
    )

    print(f"\nBriefing length: {len(briefing)} chars")
    print("Check the log output above for token usage details!")


async def main():
    """Run both tests."""
    print("\n" + "#"*80)
    print("# Token Usage Logging Test Suite")
    print("#"*80)
    print("\nThis test demonstrates visible token usage in console logs.")
    print("You should see log messages with format:")
    print("  'Response generated (tokens: X in, Y out, Z total, cost: $A.BBBB)'")

    # Test ConversationAgent
    await test_conversation_agent()

    # Test BriefingAgent
    await test_briefing_agent()

    print("\n" + "="*80)
    print("Test Complete!")
    print("="*80)
    print("\nSummary:")
    print("- Token counts (input/output/total) are visible in console")
    print("- Cost estimates (4 decimal places) are shown for each API call")
    print("- Structured metadata is preserved in extra fields for JSON logging")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
