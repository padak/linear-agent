"""Preference management handlers for Telegram bot.

This module implements preference-related command handlers including:
- /preferences - View learned preferences
- /prefer - Manually boost preference
- /ignore - Manually lower preference
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)


async def preferences_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /preferences command.

    Shows learned user preferences from feedback and engagement data.

    Usage:
        /preferences                    # Show all preferences
        /preferences topics             # Show topic preferences only
        /preferences teams              # Show team preferences only
        /preferences labels             # Show label preferences only
        /preferences stats              # Show engagement statistics
        /preferences reset              # Reset all preferences (with confirmation)

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If preference retrieval or message sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat:
            logger.warning("Received /preferences command without effective_chat")
            return

        from linear_chief.intelligence.preference_learner import PreferenceLearner
        from linear_chief.intelligence.engagement_tracker import EngagementTracker
        from linear_chief.config import LINEAR_USER_EMAIL

        if not LINEAR_USER_EMAIL:
            await update.effective_chat.send_message(
                text="⚠️ User email not configured.\n\n"
                "Set LINEAR_USER_EMAIL in .env to use preferences.",
                parse_mode="Markdown",
            )
            return

        args = context.args or []
        user_id = LINEAR_USER_EMAIL

        # Handle reset subcommand with confirmation
        if args and args[0] == "reset":
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Yes, reset", callback_data="prefs_reset_confirm"
                        ),
                        InlineKeyboardButton(
                            "❌ Cancel", callback_data="prefs_reset_cancel"
                        ),
                    ]
                ]
            )

            await update.effective_chat.send_message(
                text="⚠️ **Reset All Preferences?**\n\n"
                "This will delete all learned preferences and engagement data.\n"
                "This action cannot be undone.\n\n"
                "Are you sure?",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            logger.info(
                "Showed preference reset confirmation",
                extra={"user_id": user_id, "chat_id": update.effective_chat.id},
            )
            return

        await update.effective_chat.send_action(action="typing")

        try:
            learner = PreferenceLearner(user_id=user_id)
            tracker = EngagementTracker()

            # Get preferences from database
            from linear_chief.storage import get_session_maker, get_db_session
            from linear_chief.storage.repositories import UserPreferenceRepository

            session_maker = get_session_maker()
            all_prefs: list[Any] = []
            for session in get_db_session(session_maker):
                pref_repo = UserPreferenceRepository(session)
                all_prefs = pref_repo.get_all_preferences(user_id)

            # Convert to dict format
            preferences = _convert_db_prefs_to_dict(all_prefs)

            # Get engagement stats
            engagement_stats = await tracker.get_engagement_stats(user_id=user_id)

            # Format based on subcommand
            if not args or args[0] == "all":
                # Show everything
                formatted = format_full_preferences(preferences, engagement_stats)
            elif args[0] == "topics":
                formatted = format_topic_preferences(preferences)
            elif args[0] == "teams":
                formatted = format_team_preferences(preferences)
            elif args[0] == "labels":
                formatted = format_label_preferences(preferences)
            elif args[0] == "stats":
                formatted = format_engagement_stats(engagement_stats)
            else:
                await update.effective_chat.send_message(
                    text="Unknown subcommand. Use:\n"
                    "• `/preferences` - Show all\n"
                    "• `/preferences topics`\n"
                    "• `/preferences teams`\n"
                    "• `/preferences labels`\n"
                    "• `/preferences stats`\n"
                    "• `/preferences reset`",
                    parse_mode="Markdown",
                )
                return

            await update.effective_chat.send_message(
                text=formatted,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

            logger.info(
                "Displayed preferences",
                extra={
                    "user_id": user_id,
                    "chat_id": update.effective_chat.id,
                    "subcommand": args[0] if args else "all",
                },
            )

        except Exception as e:
            logger.error(
                "Error in preferences_handler",
                extra={
                    "chat_id": update.effective_chat.id,
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            await update.effective_chat.send_message(
                text=f"⚠️ Error loading preferences: {str(e)}",
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error(
            "Failed to handle /preferences command",
            extra={
                "chat_id": update.effective_chat.id if update.effective_chat else None,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        # Try to send error message to user
        if update.effective_chat:
            try:
                await update.effective_chat.send_message(
                    text="⚠️ Sorry, I encountered an error processing your request. "
                    "Please try again later.",
                )
            except Exception:
                pass  # Silently fail if error message can't be sent
        raise


async def prefer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /prefer command.

    Manually boost preference for topic/team/label.

    Usage:
        /prefer backend
        /prefer "Backend Team"
        /prefer bug

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If preference saving or message sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat:
            logger.warning("Received /prefer command without effective_chat")
            return

        from linear_chief.storage.repositories import UserPreferenceRepository
        from linear_chief.storage.database import get_session_maker, get_db_session
        from linear_chief.config import LINEAR_USER_EMAIL
        from linear_chief.intelligence.preference_learner import TOPIC_KEYWORDS

        if not context.args:
            await update.effective_chat.send_message(
                text="**Usage:** `/prefer <topic/team/label>`\n\n"
                "**Examples:**\n"
                "• `/prefer backend`\n"
                '• `/prefer "Backend Team"`\n'
                "• `/prefer bug`",
                parse_mode="Markdown",
            )
            return

        preference_key = " ".join(context.args)
        user_id = LINEAR_USER_EMAIL

        if not user_id:
            await update.effective_chat.send_message(
                text="⚠️ User email not configured.\n\n"
                "Set LINEAR_USER_EMAIL in .env to use preferences.",
                parse_mode="Markdown",
            )
            return

        # Detect type (topic, team, or label)
        if preference_key.lower() in TOPIC_KEYWORDS:
            preference_type = "topic"
        elif preference_key.endswith("Team") or preference_key.endswith("team"):
            preference_type = "team"
        else:
            preference_type = "label"

        # Save preference with high score (0.9)
        session_maker = get_session_maker()
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.save_preference(
                user_id=user_id,
                preference_type=preference_type,
                preference_key=preference_key.lower(),
                score=0.9,
                confidence=1.0,
                feedback_count=1,
            )

        await update.effective_chat.send_message(
            text=f"✅ **Preference saved!**\n\n"
            f"You now **prefer** {preference_type}: **{preference_key}**\n"
            f"Score: 90%\n\n"
            f"This will boost priority for related issues in future briefings.",
            parse_mode="Markdown",
        )

        logger.info(
            "User manually set preference",
            extra={
                "user_id": user_id,
                "preference_type": preference_type,
                "preference_key": preference_key,
                "chat_id": update.effective_chat.id,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to handle /prefer command",
            extra={
                "chat_id": update.effective_chat.id if update.effective_chat else None,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        # Try to send error message to user
        if update.effective_chat:
            try:
                await update.effective_chat.send_message(
                    text="⚠️ Sorry, I encountered an error processing your request. "
                    "Please try again later.",
                )
            except Exception:
                pass  # Silently fail if error message can't be sent
        raise


async def ignore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ignore command.

    Manually lower preference for topic/team/label.

    Usage:
        /ignore frontend
        /ignore "Frontend Team"
        /ignore feature

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If preference saving or message sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat:
            logger.warning("Received /ignore command without effective_chat")
            return

        from linear_chief.storage.repositories import UserPreferenceRepository
        from linear_chief.storage.database import get_session_maker, get_db_session
        from linear_chief.config import LINEAR_USER_EMAIL
        from linear_chief.intelligence.preference_learner import TOPIC_KEYWORDS

        if not context.args:
            await update.effective_chat.send_message(
                text="**Usage:** `/ignore <topic/team/label>`\n\n"
                "**Examples:**\n"
                "• `/ignore frontend`\n"
                '• `/ignore "Frontend Team"`\n'
                "• `/ignore feature`",
                parse_mode="Markdown",
            )
            return

        preference_key = " ".join(context.args)
        user_id = LINEAR_USER_EMAIL

        if not user_id:
            await update.effective_chat.send_message(
                text="⚠️ User email not configured.\n\n"
                "Set LINEAR_USER_EMAIL in .env to use preferences.",
                parse_mode="Markdown",
            )
            return

        # Detect type (topic, team, or label)
        if preference_key.lower() in TOPIC_KEYWORDS:
            preference_type = "topic"
        elif preference_key.endswith("Team") or preference_key.endswith("team"):
            preference_type = "team"
        else:
            preference_type = "label"

        # Save preference with low score (0.1)
        session_maker = get_session_maker()
        for session in get_db_session(session_maker):
            repo = UserPreferenceRepository(session)
            repo.save_preference(
                user_id=user_id,
                preference_type=preference_type,
                preference_key=preference_key.lower(),
                score=0.1,
                confidence=1.0,
                feedback_count=1,
            )

        await update.effective_chat.send_message(
            text=f"✅ **Preference saved!**\n\n"
            f"You now **ignore** {preference_type}: **{preference_key}**\n"
            f"Score: 10%\n\n"
            f"This will lower priority for related issues in future briefings.",
            parse_mode="Markdown",
        )

        logger.info(
            "User manually set ignore preference",
            extra={
                "user_id": user_id,
                "preference_type": preference_type,
                "preference_key": preference_key,
                "chat_id": update.effective_chat.id,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to handle /ignore command",
            extra={
                "chat_id": update.effective_chat.id if update.effective_chat else None,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        # Try to send error message to user
        if update.effective_chat:
            try:
                await update.effective_chat.send_message(
                    text="⚠️ Sorry, I encountered an error processing your request. "
                    "Please try again later.",
                )
            except Exception:
                pass  # Silently fail if error message can't be sent
        raise


def format_full_preferences(
    preferences: Dict[str, Any],
    engagement_stats: Dict[str, Any],
) -> str:
    """Format complete preference view."""
    lines = ["**📊 Your Preferences**\n"]

    # Summary
    feedback_count = preferences.get("feedback_count", 0)
    confidence = preferences.get("confidence", 0.0)

    lines.append("**Summary:**")
    lines.append(f"• Feedback samples: {feedback_count}")
    lines.append(f"• Confidence: {confidence:.0%}")
    lines.append(f"• Engaged issues: {engagement_stats.get('unique_issues', 0)}")
    lines.append("")

    # Topics
    topic_scores = preferences.get("topic_scores", {})
    if topic_scores:
        lines.append("**📚 Topic Preferences:**")
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        for topic, score in sorted_topics[:5]:  # Top 5
            emoji = "❤️" if score > 0.7 else "👍" if score > 0.5 else "👎"
            lines.append(f"{emoji} {topic.title()}: {score:.0%}")
        lines.append("")

    # Teams
    team_scores = preferences.get("team_scores", {})
    if team_scores:
        lines.append("**👥 Team Preferences:**")
        sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)
        for team, score in sorted_teams[:5]:
            emoji = "❤️" if score > 0.7 else "👍" if score > 0.5 else "👎"
            lines.append(f"{emoji} {team}: {score:.0%}")
        lines.append("")

    # Labels
    label_scores = preferences.get("label_scores", {})
    if label_scores:
        lines.append("**🏷️ Label Preferences:**")
        sorted_labels = sorted(label_scores.items(), key=lambda x: x[1], reverse=True)
        for label, score in sorted_labels[:5]:
            emoji = "❤️" if score > 0.7 else "👍" if score > 0.5 else "👎"
            lines.append(f"{emoji} {label}: {score:.0%}")
        lines.append("")

    # Most engaged issues
    top_engaged = engagement_stats.get("most_engaged_issues", [])
    if top_engaged:
        lines.append("**🔥 Most Engaged Issues:**")
        for issue_id in top_engaged[:3]:
            lines.append(f"• {issue_id}")
        lines.append("")

    # Footer
    lines.append("_Use `/preferences topics/teams/labels/stats` for details_")
    lines.append("_Use `/preferences reset` to reset all preferences_")

    return "\n".join(lines)


def format_topic_preferences(preferences: Dict[str, Any]) -> str:
    """Format topic preferences only."""
    topic_scores = preferences.get("topic_scores", {})

    if not topic_scores:
        return (
            "**📚 Topic Preferences:**\n\n"
            "No topic preferences learned yet.\n"
            "Give 👍/👎 feedback to help me learn!"
        )

    lines = ["**📚 Topic Preferences:**\n"]

    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)

    for topic, score in sorted_topics:
        # Emoji based on score
        if score > 0.7:
            emoji = "❤️"
            desc = "Love"
        elif score > 0.6:
            emoji = "😊"
            desc = "Like"
        elif score > 0.4:
            emoji = "😐"
            desc = "Neutral"
        else:
            emoji = "👎"
            desc = "Dislike"

        # Progress bar
        bar_length = 10
        filled = int(score * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        lines.append(f"{emoji} **{topic.title()}**: {score:.0%}")
        lines.append(f"   `{bar}` {desc}\n")

    feedback_count = preferences.get("feedback_count", 0)
    lines.append(f"_Based on {feedback_count} feedback samples_")

    return "\n".join(lines)


def format_team_preferences(preferences: Dict[str, Any]) -> str:
    """Format team preferences only."""
    team_scores = preferences.get("team_scores", {})

    if not team_scores:
        return (
            "**👥 Team Preferences:**\n\n"
            "No team preferences learned yet.\n"
            "Give 👍/👎 feedback to help me learn!"
        )

    lines = ["**👥 Team Preferences:**\n"]

    sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)

    for team, score in sorted_teams:
        # Emoji based on score
        if score > 0.7:
            emoji = "❤️"
            desc = "Love"
        elif score > 0.6:
            emoji = "😊"
            desc = "Like"
        elif score > 0.4:
            emoji = "😐"
            desc = "Neutral"
        else:
            emoji = "👎"
            desc = "Dislike"

        # Progress bar
        bar_length = 10
        filled = int(score * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        lines.append(f"{emoji} **{team}**: {score:.0%}")
        lines.append(f"   `{bar}` {desc}\n")

    feedback_count = preferences.get("feedback_count", 0)
    lines.append(f"_Based on {feedback_count} feedback samples_")

    return "\n".join(lines)


def format_label_preferences(preferences: Dict[str, Any]) -> str:
    """Format label preferences only."""
    label_scores = preferences.get("label_scores", {})

    if not label_scores:
        return (
            "**🏷️ Label Preferences:**\n\n"
            "No label preferences learned yet.\n"
            "Give 👍/👎 feedback to help me learn!"
        )

    lines = ["**🏷️ Label Preferences:**\n"]

    sorted_labels = sorted(label_scores.items(), key=lambda x: x[1], reverse=True)

    for label, score in sorted_labels:
        # Emoji based on score
        if score > 0.7:
            emoji = "❤️"
            desc = "Love"
        elif score > 0.6:
            emoji = "😊"
            desc = "Like"
        elif score > 0.4:
            emoji = "😐"
            desc = "Neutral"
        else:
            emoji = "👎"
            desc = "Dislike"

        # Progress bar
        bar_length = 10
        filled = int(score * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        lines.append(f"{emoji} **{label}**: {score:.0%}")
        lines.append(f"   `{bar}` {desc}\n")

    feedback_count = preferences.get("feedback_count", 0)
    lines.append(f"_Based on {feedback_count} feedback samples_")

    return "\n".join(lines)


def format_engagement_stats(engagement_stats: Dict[str, Any]) -> str:
    """Format engagement statistics."""
    lines = ["**📈 Engagement Statistics:**\n"]

    total_interactions = engagement_stats.get("total_interactions", 0)
    unique_issues = engagement_stats.get("unique_issues", 0)
    avg_interactions = engagement_stats.get("avg_interactions_per_issue", 0.0)
    most_engaged = engagement_stats.get("most_engaged_issues", [])
    last_interaction = engagement_stats.get("last_interaction")

    lines.append("**Overall:**")
    lines.append(f"• Total interactions: {total_interactions}")
    lines.append(f"• Unique issues: {unique_issues}")
    lines.append(f"• Avg interactions per issue: {avg_interactions:.1f}")

    if last_interaction:
        try:
            # Parse ISO format
            last_dt = datetime.fromisoformat(last_interaction.replace("Z", "+00:00"))
            time_ago = _format_time_ago(last_dt)
            lines.append(f"• Last interaction: {time_ago}")
        except Exception:
            pass

    if most_engaged:
        lines.append("\n**🔥 Most Engaged Issues:**")
        for issue_id in most_engaged:
            lines.append(f"• {issue_id}")

    return "\n".join(lines)


def _convert_db_prefs_to_dict(db_prefs: list[Any]) -> Dict[str, Any]:
    """Convert database preferences to dict format."""
    topic_scores = {}
    team_scores = {}
    label_scores = {}
    feedback_count = 0
    confidence = 0.0

    for pref in db_prefs:
        pref_type = pref.preference_type
        pref_key = pref.preference_key
        score = pref.score

        if pref_type == "topic":
            topic_scores[pref_key] = score
        elif pref_type == "team":
            team_scores[pref_key] = score
        elif pref_type == "label":
            label_scores[pref_key] = score

        # Get max feedback count and confidence
        if pref.feedback_count > feedback_count:
            feedback_count = pref.feedback_count
        if pref.confidence > confidence:
            confidence = pref.confidence

    return {
        "topic_scores": topic_scores,
        "team_scores": team_scores,
        "label_scores": label_scores,
        "feedback_count": feedback_count,
        "confidence": confidence,
    }


def _format_time_ago(timestamp: datetime) -> str:
    """
    Format datetime as human-readable "time ago" string.

    Args:
        timestamp: Datetime to format

    Returns:
        Human-readable time ago string (e.g., "2 hours ago", "3 days ago")
    """
    now = datetime.utcnow()
    delta = now - timestamp

    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif delta < timedelta(days=30):
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = delta.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
