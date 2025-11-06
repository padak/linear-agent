"""Callback query handlers for inline keyboard interactions."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from linear_chief.storage import get_session_maker, get_db_session
from linear_chief.storage.repositories import FeedbackRepository
from linear_chief.telegram.keyboards import get_acknowledgment_keyboard_removed

logger = logging.getLogger(__name__)


async def feedback_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle thumbs up/down feedback on briefings.

    Args:
        update: Telegram Update object
        context: Callback context

    Callback data format:
        - "feedback_positive" - User found briefing helpful
        - "feedback_negative" - User did not find briefing helpful
    """
    query = update.callback_query
    if not query:
        logger.warning("Received feedback callback without query")
        return

    await query.answer()

    try:
        # Extract callback data
        callback_data = query.data
        if not callback_data:
            logger.warning("Received feedback callback without data")
            return

        # Determine feedback type
        if callback_data == "feedback_positive":
            feedback_type = "positive"
            acknowledgment = "✅ Thanks for your feedback! Glad it was helpful."
        elif callback_data == "feedback_negative":
            feedback_type = "negative"
            acknowledgment = (
                "📝 Thanks for your feedback! We'll work on improving the briefings."
            )
        else:
            logger.warning(f"Unknown feedback callback data: {callback_data}")
            await query.edit_message_reply_markup(reply_markup=None)
            return

        # Get user and message info
        user_id = str(query.from_user.id)
        message_id = str(query.message.message_id) if query.message else None

        # Save feedback to database
        session_maker = get_session_maker()
        for session in get_db_session(session_maker):
            feedback_repo = FeedbackRepository(session)

            # Store briefing_id in metadata if available
            metadata = {"telegram_message_id": message_id} if message_id else None

            feedback_repo.save_feedback(
                user_id=user_id,
                briefing_id=None,  # Will be linked via telegram_message_id if needed
                feedback_type=feedback_type,
                extra_metadata=metadata,
            )

        logger.info(f"Recorded {feedback_type} feedback from user {user_id}")

        # Remove buttons and show acknowledgment
        await query.edit_message_reply_markup(
            reply_markup=get_acknowledgment_keyboard_removed()
        )

        # Send acknowledgment as separate message
        if query.message and hasattr(query.message, "reply_text"):
            await query.message.reply_text(acknowledgment)

    except Exception as e:
        logger.error(f"Error handling feedback callback: {e}", exc_info=True)
        await query.answer("❌ Sorry, something went wrong. Please try again.")


async def issue_action_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle actions on specific issues (mark done, unsubscribe).

    Args:
        update: Telegram Update object
        context: Callback context

    Callback data format:
        - "issue_done_{issue_id}" - Mark issue as done
        - "issue_unsub_{issue_id}" - Unsubscribe from issue updates
    """
    query = update.callback_query
    if not query:
        logger.warning("Received issue action callback without query")
        return

    await query.answer()

    try:
        # Parse callback data
        callback_data = query.data
        if not callback_data:
            logger.warning("Received issue action callback without data")
            return

        # Extract action and issue_id
        if callback_data.startswith("issue_done_"):
            action = "done"
            issue_id = callback_data.replace("issue_done_", "")
        elif callback_data.startswith("issue_unsub_"):
            action = "unsubscribe"
            issue_id = callback_data.replace("issue_unsub_", "")
        else:
            logger.warning(f"Unknown issue action callback data: {callback_data}")
            await query.edit_message_reply_markup(reply_markup=None)
            return

        user_id = str(query.from_user.id)

        # Handle action
        if action == "done":
            acknowledgment = (
                f"✅ Issue {issue_id} marked as done!\n\n"
                "Note: This is tracked locally. To update in Linear, "
                "please use the 🔗 Open in Linear button."
            )
            logger.info(f"User {user_id} marked issue {issue_id} as done")

            # Store action in database as feedback
            session_maker = get_session_maker()
            for session in get_db_session(session_maker):
                feedback_repo = FeedbackRepository(session)
                feedback_repo.save_feedback(
                    user_id=user_id,
                    briefing_id=None,
                    feedback_type="issue_action",
                    extra_metadata={"action": "done", "issue_id": issue_id},
                )

        elif action == "unsubscribe":
            acknowledgment = (
                f"🔕 You've unsubscribed from issue {issue_id} updates.\n\n"
                "Note: This only affects briefings. To fully unsubscribe in Linear, "
                "please use the 🔗 Open in Linear button."
            )
            logger.info(f"User {user_id} unsubscribed from issue {issue_id}")

            # Store action in database as feedback
            session_maker = get_session_maker()
            for session in get_db_session(session_maker):
                feedback_repo = FeedbackRepository(session)
                feedback_repo.save_feedback(
                    user_id=user_id,
                    briefing_id=None,
                    feedback_type="issue_action",
                    extra_metadata={"action": "unsubscribe", "issue_id": issue_id},
                )

        # Remove buttons
        await query.edit_message_reply_markup(
            reply_markup=get_acknowledgment_keyboard_removed()
        )

        # Send acknowledgment
        if query.message and hasattr(query.message, "reply_text"):
            await query.message.reply_text(acknowledgment)

    except Exception as e:
        logger.error(f"Error handling issue action callback: {e}", exc_info=True)
        await query.answer("❌ Sorry, something went wrong. Please try again.")
