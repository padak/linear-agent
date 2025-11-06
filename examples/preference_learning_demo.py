"""
Demonstration script for the Preference Learning Engine.

Shows how to use PreferenceLearner to analyze user feedback and learn preferences.

Usage:
    python examples/preference_learning_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from linear_chief.intelligence.preference_learner import PreferenceLearner
from linear_chief.storage import (
    init_db,
    get_session_maker,
    get_db_session,
    FeedbackRepository,
    IssueHistoryRepository,
    UserPreferenceRepository,
)


async def setup_demo_data():
    """Create sample feedback and issue data for demonstration."""
    print("Setting up demo data...")

    session_maker = get_session_maker()

    for session in get_db_session(session_maker):
        feedback_repo = FeedbackRepository(session)
        issue_repo = IssueHistoryRepository(session)

        # Create some sample issues
        issues = [
            {
                "issue_id": "DEMO-101",
                "linear_id": "uuid-101",
                "title": "Fix backend API authentication bug",
                "state": "In Progress",
                "priority": 1,
                "assignee_id": "user1",
                "assignee_name": "Alice",
                "team_id": "team1",
                "team_name": "Backend Team",
                "labels": ["bug", "urgent", "api"],
            },
            {
                "issue_id": "DEMO-102",
                "linear_id": "uuid-102",
                "title": "Implement GraphQL API for profiles",
                "state": "In Progress",
                "priority": 2,
                "assignee_id": "user2",
                "assignee_name": "Bob",
                "team_id": "team1",
                "team_name": "Backend Team",
                "labels": ["feature", "api"],
            },
            {
                "issue_id": "DEMO-103",
                "linear_id": "uuid-103",
                "title": "Update CSS styles for login page",
                "state": "Todo",
                "priority": 3,
                "assignee_id": "user3",
                "assignee_name": "Charlie",
                "team_id": "team2",
                "team_name": "Frontend Team",
                "labels": ["ui", "css"],
            },
        ]

        for issue_data in issues:
            issue_repo.save_snapshot(**issue_data)

        # Create feedback: positive for backend, negative for frontend
        feedback_entries = [
            {
                "user_id": "demo_user",
                "briefing_id": 1,
                "feedback_type": "positive",
                "extra_metadata": {"issue_id": "DEMO-101"},
            },
            {
                "user_id": "demo_user",
                "briefing_id": 1,
                "feedback_type": "positive",
                "extra_metadata": {"issue_id": "DEMO-102"},
            },
            {
                "user_id": "demo_user",
                "briefing_id": 2,
                "feedback_type": "negative",
                "extra_metadata": {"issue_id": "DEMO-103"},
            },
        ]

        for feedback_data in feedback_entries:
            feedback_repo.save_feedback(**feedback_data)

    print("Demo data created successfully!")


async def demonstrate_preference_learning():
    """Demonstrate the complete preference learning workflow."""
    print("\n" + "=" * 60)
    print("PREFERENCE LEARNING ENGINE DEMONSTRATION")
    print("=" * 60)

    # Step 1: Initialize the learner
    print("\n[1] Initializing PreferenceLearner...")
    learner = PreferenceLearner(user_id="demo_user")
    print("    ✓ PreferenceLearner initialized")

    # Step 2: Analyze feedback patterns
    print("\n[2] Analyzing feedback patterns...")
    preferences = await learner.analyze_feedback_patterns(days=30, min_feedback_count=1)

    print(f"    ✓ Analysis complete!")
    print(f"    - Feedback count: {preferences['feedback_count']}")
    print(f"    - Confidence: {preferences['confidence']:.2f}")
    print(f"    - Engagement score: {preferences['engagement_score']:.2f}")

    # Step 3: Show detected preferences
    print("\n[3] Detected Preferences:")

    if preferences["preferred_topics"]:
        print(f"\n    Preferred Topics:")
        for topic in preferences["preferred_topics"]:
            score = preferences["topic_scores"].get(topic, 0)
            print(f"      • {topic:15s} (score: {score:.2f})")
    else:
        print("    No preferred topics detected")

    if preferences["disliked_topics"]:
        print(f"\n    Disliked Topics:")
        for topic in preferences["disliked_topics"]:
            score = preferences["topic_scores"].get(topic, 0)
            print(f"      • {topic:15s} (score: {score:.2f})")

    if preferences["preferred_teams"]:
        print(f"\n    Preferred Teams:")
        for team in preferences["preferred_teams"]:
            score = preferences["team_scores"].get(team, 0)
            print(f"      • {team:20s} (score: {score:.2f})")

    if preferences["preferred_labels"]:
        print(f"\n    Preferred Labels:")
        for label in preferences["preferred_labels"]:
            score = preferences["label_scores"].get(label, 0)
            print(f"      • {label:15s} (score: {score:.2f})")

    # Step 4: Save to mem0
    print("\n[4] Saving preferences to mem0...")
    await learner.save_to_mem0(preferences)
    print("    ✓ Saved to mem0")

    # Step 5: Save to database
    print("\n[5] Saving preferences to database...")
    await learner.save_to_database(preferences)
    print("    ✓ Saved to database")

    # Step 6: Retrieve and verify
    print("\n[6] Retrieving preferences from mem0...")
    retrieved = await learner.get_preferences()
    print("    ✓ Retrieved successfully")
    print(f"    - Preferred topics: {retrieved['preferred_topics']}")
    print(f"    - Disliked topics: {retrieved['disliked_topics']}")

    # Step 7: Show database statistics
    print("\n[7] Database Statistics:")
    session_maker = get_session_maker()
    for session in get_db_session(session_maker):
        pref_repo = UserPreferenceRepository(session)
        summary = pref_repo.get_preference_summary("demo_user")

        print(f"    - Total preferences: {summary['total_count']}")
        print(f"    - Average score: {summary['avg_score']:.2f}")
        print(f"    - Average confidence: {summary['avg_confidence']:.2f}")
        print(f"\n    By Type:")
        for pref_type, stats in summary["by_type"].items():
            print(
                f"      • {pref_type:10s}: {stats['count']} items, "
                f"avg score {stats['avg_score']:.2f}"
            )

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


async def main():
    """Main entry point."""
    # Initialize database
    print("Initializing database...")
    init_db()

    # Setup demo data
    await setup_demo_data()

    # Run demonstration
    await demonstrate_preference_learning()

    print("\n✓ Demo completed successfully!")
    print("\nTo clean up demo data, delete the database or run:")
    print("  python -m linear_chief init")


if __name__ == "__main__":
    asyncio.run(main())
