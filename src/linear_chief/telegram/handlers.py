"""Telegram bot message handlers for bidirectional communication.

This module implements command handlers and message processors for the Linear Chief
of Staff Telegram bot, enabling user interactions and queries.

Handlers:
- /start - Welcome message with bot capabilities
- /help - List of available commands
- /status - Current briefing status (issues count, last briefing time)
- Text messages - User queries (placeholder for future conversation)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict

from telegram import Update
from telegram.ext import ContextTypes

from linear_chief.storage import get_session_maker, get_db_session
from linear_chief.storage.repositories import BriefingRepository, IssueHistoryRepository
from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command - Welcome message with bot capabilities.

    Sends a welcome message introducing the bot and its primary function of
    delivering daily Linear issue briefings.

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If message sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat:
            logger.warning("Received /start command without effective_chat")
            return

        welcome_message = (
            "👋 *Welcome to Linear Chief of Staff!*\n\n"
            "I'm your autonomous AI assistant for Linear issue management. "
            "I monitor your Linear workspace and generate intelligent briefings "
            "to keep you informed about what matters most.\n\n"
            "*What I can do:*\n"
            "• 📊 Daily briefings on your Linear issues\n"
            "• 🔍 Track issue changes, stagnation, and priorities\n"
            "• 📈 Provide status updates on demand\n"
            "• 💬 Answer questions (coming soon)\n\n"
            "Use /help to see available commands."
        )

        await update.effective_chat.send_message(
            text=welcome_message,
            parse_mode="Markdown",
        )

        logger.info(
            "Sent welcome message",
            extra={
                "chat_id": update.effective_chat.id,
                "user_id": update.effective_user.id if update.effective_user else None,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to handle /start command",
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


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command - List available commands.

    Provides comprehensive help documentation listing all available commands
    and their descriptions.

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If message sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat:
            logger.warning("Received /help command without effective_chat")
            return

        # Import config for briefing time
        from linear_chief.config import BRIEFING_TIME, LOCAL_TIMEZONE

        help_message = (
            "🤖 *Linear Chief of Staff Bot*\n\n"
            "*Available Commands:*\n"
            "• /start - Welcome message and introduction\n"
            "• /help - Show this help message\n"
            "• /status - View current briefing status and statistics\n"
            "• /briefing - Get the latest briefing\n\n"
            "*Ask Questions:*\n"
            "You can also ask me questions in natural language:\n"
            '• "Show me today\'s briefing"\n'
            '• "What blocked issues do I have?"\n'
            '• "Summarize the last briefing"\n'
            '• "What\'s my priority for today?"\n\n'
            f"*Daily Briefings:*\n"
            f"I automatically send daily briefings at {BRIEFING_TIME} ({LOCAL_TIMEZONE}).\n\n"
            "*Feedback:*\n"
            "Use 👍/👎 buttons on briefings to help me improve!"
        )

        await update.effective_chat.send_message(
            text=help_message,
            parse_mode="Markdown",
        )

        logger.info(
            "Sent help message",
            extra={
                "chat_id": update.effective_chat.id,
                "user_id": update.effective_user.id if update.effective_user else None,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to handle /help command",
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


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command - Show current briefing status.

    Retrieves and displays:
    - Total tracked issues count
    - Recent briefings count (last 7 days)
    - Last briefing timestamp
    - Briefing statistics

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If database query or message sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat:
            logger.warning("Received /status command without effective_chat")
            return

        # Get database session
        session_maker = get_session_maker()

        # Query briefing and issue data
        for session in get_db_session(session_maker):
            briefing_repo = BriefingRepository(session)
            issue_repo = IssueHistoryRepository(session)

            # Get recent briefings (last 7 days)
            recent_briefings = briefing_repo.get_recent_briefings(days=7)

            # Get tracked issues (last 30 days)
            tracked_issues = issue_repo.get_all_latest_snapshots(days=30)

            # Calculate statistics
            total_briefings = len(recent_briefings)
            total_issues = len(tracked_issues)

            # Get last briefing info
            last_briefing: Optional[datetime] = None
            last_briefing_status: Optional[str] = None
            if recent_briefings:
                # SQLAlchemy ORM: Column access at runtime returns actual type
                last_briefing = recent_briefings[0].generated_at  # type: ignore[assignment]
                last_briefing_status = recent_briefings[0].delivery_status  # type: ignore[assignment]

            # Calculate total cost (last 7 days)
            total_cost = briefing_repo.get_total_cost(days=7)

            # Count issues by state (while still in session!)
            state_counts: dict[str, int] = {}
            if tracked_issues:
                for issue in tracked_issues:
                    # SQLAlchemy ORM: Column access at runtime returns actual type
                    state: str = issue.state  # type: ignore[assignment]
                    state_counts[state] = state_counts.get(state, 0) + 1

        # Format last briefing time
        if last_briefing:
            time_ago = _format_time_ago(last_briefing)
            status_emoji = "✅" if last_briefing_status == "sent" else "⚠️"
            last_briefing_text = (
                f"{status_emoji} {time_ago}\n"
                f"Status: {last_briefing_status or 'unknown'}"
            )
        else:
            last_briefing_text = "No briefings generated yet"

        # Build status message
        status_message = (
            "📊 *Briefing Status*\n\n"
            f"*Tracked Issues:* {total_issues}\n"
            f"*Recent Briefings (7d):* {total_briefings}\n"
            f"*Last Briefing:* {last_briefing_text}\n"
            f"*Total Cost (7d):* ${total_cost:.4f}\n\n"
        )

        # Add issue breakdown if available
        if state_counts:
            status_message += "*Issue Breakdown:*\n"
            for state, count in sorted(state_counts.items(), key=lambda x: -x[1]):
                status_message += f"• {state}: {count}\n"

        status_message += "\n_Use /help to see available commands_"

        await update.effective_chat.send_message(
            text=status_message,
            parse_mode="Markdown",
        )

        logger.info(
            "Sent status message",
            extra={
                "chat_id": update.effective_chat.id,
                "user_id": update.effective_user.id if update.effective_user else None,
                "total_briefings": total_briefings,
                "total_issues": total_issues,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to handle /status command",
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
                    text="⚠️ Sorry, I encountered an error retrieving status information. "
                    "Please try again later.",
                )
            except Exception:
                pass  # Silently fail if error message can't be sent
        raise


async def briefing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /briefing command - Show the most recent briefing.

    Fetches the latest briefing from database and sends it with feedback keyboard.

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If briefing retrieval or sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat:
            logger.warning("Received /briefing command without effective_chat")
            return

        logger.info(
            "Handling /briefing command",
            extra={
                "chat_id": update.effective_chat.id,
                "user_id": update.effective_user.id if update.effective_user else None,
            },
        )

        # Get database session
        session_maker = get_session_maker()

        # Query latest briefing
        for session in get_db_session(session_maker):
            briefing_repo = BriefingRepository(session)

            # Get most recent briefing (last 7 days)
            recent_briefings = briefing_repo.get_recent_briefings(days=7)

            # Handle no briefings case
            if not recent_briefings:
                await update.effective_chat.send_message(
                    text="No briefings generated yet. Use /status to see when the next one will be generated.",
                )
                logger.info(
                    "No briefings available",
                    extra={
                        "chat_id": update.effective_chat.id,
                    },
                )
                return

            # Extract briefing content
            latest_briefing = recent_briefings[0]
            # SQLAlchemy ORM: Column access at runtime returns actual type
            briefing_content: str = latest_briefing.content  # type: ignore[assignment]
            generated_at: datetime = latest_briefing.generated_at  # type: ignore[assignment]
            delivery_status: str = latest_briefing.delivery_status  # type: ignore[assignment]

        # Format timestamp
        timestamp_str = generated_at.strftime("%Y-%m-%d %H:%M")

        # Build message with header
        full_message = (
            f"📊 *Latest Briefing*\n"
            f"Generated: {timestamp_str}\n\n"
            f"{briefing_content}"
        )

        # Import keyboard utility
        from linear_chief.telegram.keyboards import get_briefing_feedback_keyboard

        # Send briefing with feedback keyboard
        await update.effective_chat.send_message(
            text=full_message,
            parse_mode="Markdown",
            reply_markup=get_briefing_feedback_keyboard(),
        )

        logger.info(
            "Sent latest briefing",
            extra={
                "chat_id": update.effective_chat.id,
                "user_id": update.effective_user.id if update.effective_user else None,
                "briefing_timestamp": timestamp_str,
                "delivery_status": delivery_status,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to handle /briefing command",
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
                    text="⚠️ Sorry, I encountered an error retrieving the briefing. "
                    "Please try again later.",
                )
            except Exception:
                pass  # Silently fail if error message can't be sent
        raise


async def text_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle text messages - Process user queries with intelligent responses.

    Uses Claude API to generate intelligent responses based on:
    - User's question
    - Conversation history
    - Recent issues and briefings context

    Args:
        update: Telegram update object containing message info
        context: Telegram context for bot state and API calls

    Raises:
        Exception: If message sending fails (logged and re-raised)
    """
    try:
        if not update.effective_chat or not update.message:
            logger.warning("Received text message without effective_chat or message")
            return

        # Check if conversation is enabled
        from linear_chief.config import (
            CONVERSATION_ENABLED,
            ANTHROPIC_API_KEY,
            CONVERSATION_MAX_HISTORY,
        )

        if not CONVERSATION_ENABLED:
            await update.effective_chat.send_message(
                text="💬 Conversation mode is currently disabled. Use /help to see available commands.",
            )
            return

        user_message = update.message.text or ""
        user_id = str(update.effective_user.id) if update.effective_user else "unknown"
        chat_id = str(update.effective_chat.id)

        # Log the message
        logger.info(
            "Received user query",
            extra={
                "chat_id": chat_id,
                "user_id": user_id,
                "message_length": len(user_message),
                "message_preview": user_message[:100],  # First 100 chars
            },
        )

        # Send "typing" action while processing
        await update.effective_chat.send_action(action="typing")

        # Get database session
        session_maker = get_session_maker()

        # Import conversation components
        from linear_chief.agent import ConversationAgent, build_conversation_context
        from linear_chief.agent.context_builder import check_issue_query
        from linear_chief.storage.repositories import ConversationRepository

        # Load conversation history
        conversation_history = []
        for session in get_db_session(session_maker):
            conv_repo = ConversationRepository(session)

            # Save user message to database
            conv_repo.save_message(
                user_id=user_id,
                chat_id=chat_id,
                message=user_message,
                role="user",
                extra_metadata={"message_id": str(update.message.message_id)},
            )

            # Get recent conversation history (configurable via CONVERSATION_MAX_HISTORY)
            recent_conversations = conv_repo.get_conversation_history(
                user_id=user_id, limit=CONVERSATION_MAX_HISTORY
            )

            # Convert to Claude API format
            for conv in recent_conversations[:-1]:  # Exclude the message we just saved
                # Type guard for SQLAlchemy ORM attributes
                role: str = conv.role  # type: ignore[assignment]
                message: str = conv.message  # type: ignore[assignment]
                conversation_history.append({"role": role, "content": message})

        # Build context (issues, briefings, etc.)
        # Also build issue_map for clickable links
        issue_map: Dict[str, str] = {}
        try:
            # Check if we should use vector search for issue-specific queries
            use_vector_search = check_issue_query(user_message)

            # Always pass query for issue ID extraction and optional vector search
            conversation_context = await build_conversation_context(
                user_id=user_id,
                include_vector_search=use_vector_search,
                query=user_message,  # Always pass for issue ID extraction
            )

            # Build issue_map from fetched issues and DB issues
            # 1. Extract issue IDs from query
            from linear_chief.agent.context_builder import (
                extract_issue_ids,
                fetch_issue_details,
            )

            issue_ids = extract_issue_ids(user_message)
            if issue_ids:
                # Fetch real-time issue details
                fetched_issues = await fetch_issue_details(issue_ids)
                for issue in fetched_issues:
                    identifier = issue.get("identifier")
                    url = issue.get("url")
                    if identifier and url:
                        issue_map[identifier] = url

            # 2. Get URLs from recent issues in DB (from extra_metadata)
            for session in get_db_session(session_maker):
                issue_repo = IssueHistoryRepository(session)
                recent_issues = issue_repo.get_all_latest_snapshots(days=30)

                for issue in recent_issues:
                    issue_id: str = issue.issue_id  # type: ignore[assignment]
                    extra_metadata = getattr(issue, "extra_metadata", None)

                    # Extract URL from JSON metadata if available
                    if extra_metadata and isinstance(extra_metadata, dict):
                        url = extra_metadata.get("url")
                        if url and issue_id not in issue_map:
                            issue_map[issue_id] = url

        except Exception as e:
            logger.error(
                "Failed to build context, using minimal context",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            conversation_context = (
                f"Current Date: {datetime.utcnow().strftime('%Y-%m-%d')}"
            )

        # Generate response using ConversationAgent
        try:
            agent = ConversationAgent(api_key=ANTHROPIC_API_KEY)
            response_text = await agent.generate_response(
                user_message=user_message,
                conversation_history=conversation_history,
                context=conversation_context,
                max_tokens=1000,  # Keep responses concise
                issue_map=issue_map,  # Add clickable links to response
            )

            # Truncate if too long for Telegram (max 4096 chars)
            if len(response_text) > 4000:
                response_text = response_text[:3997] + "..."

            # Send response
            await update.effective_chat.send_message(
                text=response_text,
                parse_mode="Markdown",
            )

            # Save assistant response to database
            for session in get_db_session(session_maker):
                conv_repo = ConversationRepository(session)
                conv_repo.save_message(
                    user_id=user_id,
                    chat_id=chat_id,
                    message=response_text,
                    role="assistant",
                )

            logger.info(
                "Sent intelligent response to user query",
                extra={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "response_length": len(response_text),
                },
            )

        except Exception as e:
            logger.error(
                "Failed to generate response, sending fallback",
                extra={
                    "chat_id": chat_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

            # Fallback response
            fallback_response = (
                "⚠️ I'm having trouble generating a response right now. "
                "Please try again in a moment.\n\n"
                "In the meantime, you can use:\n"
                "• /status - View current briefing status\n"
                "• /help - See available commands"
            )

            await update.effective_chat.send_message(
                text=fallback_response,
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error(
            "Failed to handle text message",
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
                    text="⚠️ Sorry, I encountered an error processing your message. "
                    "Please try again later.",
                )
            except Exception:
                pass  # Silently fail if error message can't be sent
        raise


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
