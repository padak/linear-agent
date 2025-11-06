"""Inline keyboard builders for Telegram bot interactions."""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_briefing_feedback_keyboard() -> InlineKeyboardMarkup:
    """
    Create feedback keyboard with thumbs up/down buttons.

    Returns:
        InlineKeyboardMarkup with positive/negative feedback buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("👍 Helpful", callback_data="feedback_positive"),
            InlineKeyboardButton("👎 Not helpful", callback_data="feedback_negative"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_issue_action_keyboard(issue_id: str, issue_url: str) -> InlineKeyboardMarkup:
    """
    Create action keyboard for specific issue.

    Args:
        issue_id: Issue identifier (e.g., "PROJ-123")
        issue_url: URL to open issue in Linear

    Returns:
        InlineKeyboardMarkup with issue action buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("🔗 Open in Linear", url=issue_url),
        ],
        [
            InlineKeyboardButton(
                "✅ Mark Done", callback_data=f"issue_done_{issue_id}"
            ),
            InlineKeyboardButton(
                "🔕 Unsubscribe", callback_data=f"issue_unsub_{issue_id}"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_acknowledgment_keyboard_removed() -> InlineKeyboardMarkup:
    """
    Create empty keyboard to remove buttons after action.

    Returns:
        Empty InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup([])
