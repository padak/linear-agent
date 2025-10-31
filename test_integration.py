#!/usr/bin/env python3
"""Quick integration test to verify all components work together."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from linear_chief.config import (
    LINEAR_API_KEY,
    ANTHROPIC_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ensure_directories,
)
from linear_chief.linear import LinearClient
from linear_chief.agent import BriefingAgent
from linear_chief.telegram import TelegramBriefingBot


async def test_integration():
    """Test end-to-end integration."""
    print("🚀 Linear Chief of Staff - Integration Test\n")

    # Ensure directories exist
    ensure_directories()
    print("✓ Directories created")

    # Check environment variables
    if not LINEAR_API_KEY:
        print("❌ LINEAR_API_KEY not set in environment")
        return False

    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set in environment")
        return False

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        return False

    print("✓ Environment variables loaded\n")

    # Test Linear API
    print("1️⃣ Testing Linear API connection...")
    try:
        async with LinearClient(LINEAR_API_KEY) as linear:
            viewer = await linear.get_viewer()
            print(f"   ✓ Connected as: {viewer.get('name')} ({viewer.get('email')})")

            issues = await linear.get_issues(limit=5)
            print(f"   ✓ Fetched {len(issues)} issues")

            if not issues:
                print("   ⚠️  No issues found. You might want to create some test issues.")
                # Create a mock issue for testing
                issues = [
                    {
                        "id": "test-1",
                        "identifier": "TEST-1",
                        "title": "Test issue for briefing",
                        "state": {"name": "In Progress"},
                        "priorityLabel": "High",
                        "assignee": {"name": "Test User"},
                        "team": {"name": "Test Team"},
                        "updatedAt": "2024-11-01T10:00:00Z",
                        "description": "This is a test issue to verify the briefing generation works.",
                        "comments": {"nodes": []},
                    }
                ]
                print("   ✓ Using mock issue for testing")

    except Exception as e:
        print(f"   ❌ Linear API error: {e}")
        return False

    # Test Agent SDK
    print("\n2️⃣ Testing Agent SDK briefing generation...")
    try:
        agent = BriefingAgent(ANTHROPIC_API_KEY)
        briefing = await agent.generate_briefing(issues, user_context="Test user context")
        print(f"   ✓ Generated briefing ({len(briefing)} characters)")
        print(f"\n--- BRIEFING PREVIEW ---")
        print(briefing[:500] + ("..." if len(briefing) > 500 else ""))
        print("--- END PREVIEW ---\n")

    except Exception as e:
        print(f"   ❌ Agent SDK error: {e}")
        return False

    # Test Telegram Bot
    print("3️⃣ Testing Telegram bot connection...")
    try:
        bot = TelegramBriefingBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

        if not await bot.test_connection():
            print("   ❌ Telegram connection failed")
            return False

        print("   ✓ Telegram bot connected")

        # Optionally send the briefing (commented out to avoid spam)
        # success = await bot.send_briefing(briefing)
        # if success:
        #     print("   ✓ Briefing sent to Telegram")
        # else:
        #     print("   ❌ Failed to send briefing")

        print("   ⚠️  Skipping actual send (uncomment to test sending)")

    except Exception as e:
        print(f"   ❌ Telegram error: {e}")
        return False

    print("\n✅ All integration tests passed!")
    print("\nNext steps:")
    print("1. Create .env file from .env.example")
    print("2. Add your API keys")
    print("3. Run: python test_integration.py")
    print("4. Implement scheduling for daily briefings")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
