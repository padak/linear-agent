"""Bidirectional Telegram bot application using python-telegram-bot.

This module implements the main Telegram bot application with full bidirectional
communication capabilities, including:
- Command handlers (/start, /help, /status)
- Text message handling
- Callback query handling (feedback, issue actions)
- Briefing delivery with interactive keyboards

Architecture:
- Uses python-telegram-bot's Application framework
- Supports both polling and webhook modes
- Integrates with storage layer for feedback and conversation tracking
- Backward compatible with original TelegramBriefingBot
"""

import asyncio
from typing import Optional
from telegram import Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import TelegramError

from linear_chief.utils.logging import get_logger
from linear_chief.telegram.handlers import (
    start_handler,
    help_handler,
    status_handler,
    briefing_handler,
    duplicates_handler,
    similar_handler,
    related_handler,
    text_message_handler,
)
from linear_chief.telegram.handlers_preferences import (
    preferences_handler,
    prefer_handler,
    ignore_handler,
)
from linear_chief.telegram.callbacks import (
    feedback_callback_handler,
    issue_action_callback_handler,
    preferences_reset_callback,
)
from linear_chief.telegram.keyboards import get_briefing_feedback_keyboard

logger = get_logger(__name__)


class TelegramApplication:
    """
    Bidirectional Telegram bot application.

    Provides full interactive capabilities including command handling,
    message processing, and callback query handling. Supports briefing
    delivery with feedback keyboards.

    Example:
        >>> app = TelegramApplication(bot_token="...", chat_id="...")
        >>> await app.start()  # Start polling
        >>> await app.send_briefing("Daily briefing...", briefing_id=123)
        >>> await app.stop()  # Graceful shutdown
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        polling: bool = True,
    ):
        """
        Initialize Telegram application.

        Args:
            bot_token: Telegram bot API token
            chat_id: Target chat ID for briefing delivery
            polling: Use polling mode (True) or webhook mode (False)

        Raises:
            ValueError: If bot_token or chat_id is empty
        """
        if not bot_token:
            raise ValueError("bot_token cannot be empty")
        if not chat_id:
            raise ValueError("chat_id cannot be empty")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.polling = polling

        # Build application
        self.application: Application = ApplicationBuilder().token(bot_token).build()

        # Register all handlers
        self._register_handlers()

        # Track if application is running
        self._running = False

        logger.info(
            "Telegram application initialized",
            extra={
                "chat_id": chat_id,
                "mode": "polling" if polling else "webhook",
            },
        )

    def _register_handlers(self) -> None:
        """
        Register all command, message, and callback handlers.

        Handlers are registered in order of priority:
        1. Command handlers (specific commands)
        2. Callback query handlers (button interactions)
        3. Message handlers (general text messages)
        """
        # Command handlers
        self.application.add_handler(
            CommandHandler("start", start_handler),
        )
        self.application.add_handler(
            CommandHandler("help", help_handler),
        )
        self.application.add_handler(
            CommandHandler("status", status_handler),
        )
        self.application.add_handler(
            CommandHandler("briefing", briefing_handler),
        )
        self.application.add_handler(
            CommandHandler("duplicates", duplicates_handler),
        )
        self.application.add_handler(
            CommandHandler("similar", similar_handler),
        )
        self.application.add_handler(
            CommandHandler("related", related_handler),
        )
        self.application.add_handler(
            CommandHandler("preferences", preferences_handler),
        )
        self.application.add_handler(
            CommandHandler("prefer", prefer_handler),
        )
        self.application.add_handler(
            CommandHandler("ignore", ignore_handler),
        )

        # Callback query handlers (inline keyboard buttons)
        self.application.add_handler(
            CallbackQueryHandler(
                feedback_callback_handler,
                pattern="^feedback_",
            )
        )
        self.application.add_handler(
            CallbackQueryHandler(
                issue_action_callback_handler,
                pattern="^issue_(done|unsub)_",
            )
        )
        self.application.add_handler(
            CallbackQueryHandler(
                preferences_reset_callback,
                pattern="^prefs_reset_",
            )
        )

        # Text message handler (must be last to avoid catching commands)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                text_message_handler,
            )
        )

        logger.info(
            "Registered handlers",
            extra={
                "command_handlers": 10,
                "callback_handlers": 3,
                "message_handlers": 1,
            },
        )

    async def start(self) -> None:
        """
        Start the Telegram bot application.

        Initializes the bot and starts polling for updates (if polling mode).
        This is a blocking call that runs until stop() is called.

        Raises:
            TelegramError: If bot fails to start
        """
        if self._running:
            logger.warning("Application already running")
            return

        try:
            logger.info("Starting Telegram application")

            # Initialize the application
            await self.application.initialize()
            await self.application.start()

            if self.polling:
                # Start polling for updates
                logger.info("Starting polling mode")
                await self.application.updater.start_polling(
                    drop_pending_updates=True,
                )
                self._running = True
                logger.info("Telegram application started successfully (polling)")
            else:
                # Webhook mode - just mark as running
                # Actual webhook setup would be done externally
                self._running = True
                logger.info("Telegram application started successfully (webhook)")

        except Exception as e:
            logger.error(
                "Failed to start Telegram application",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            raise

    async def stop(self) -> None:
        """
        Stop the Telegram bot application gracefully.

        Stops polling, shuts down the application, and cleans up resources.

        Raises:
            Exception: If shutdown fails (logged and suppressed)
        """
        if not self._running:
            logger.warning("Application not running")
            return

        try:
            logger.info("Stopping Telegram application")

            if self.polling:
                # Stop polling
                await self.application.updater.stop()
                logger.info("Polling stopped")

            # Stop and shutdown application
            await self.application.stop()
            await self.application.shutdown()

            self._running = False
            logger.info("Telegram application stopped successfully")

        except Exception as e:
            logger.error(
                "Error during Telegram application shutdown",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            # Don't re-raise - allow graceful shutdown even if there are errors

    async def send_briefing(
        self,
        message: str,
        briefing_id: Optional[int] = None,
        parse_mode: Optional[str] = "Markdown",
    ) -> bool:
        """
        Send briefing message with feedback keyboard.

        Sends a briefing to the configured chat with inline keyboard for
        user feedback (thumbs up/down). Handles message chunking if the
        message exceeds Telegram's 4096 character limit.

        Args:
            message: Briefing message text
            briefing_id: Optional briefing ID for feedback tracking
            parse_mode: Message parse mode (Markdown, HTML, or None)

        Returns:
            True if message was sent successfully, False otherwise

        Raises:
            TelegramError: If message sending fails (logged and returns False)
        """
        try:
            # Get bot instance
            bot: Bot = self.application.bot

            # Handle message chunking if needed (Telegram limit: 4096 chars)
            max_length = 4096
            if len(message) <= max_length:
                # Single message - send with feedback keyboard
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=parse_mode,
                    reply_markup=get_briefing_feedback_keyboard(),
                )
                logger.info(
                    "Briefing sent successfully",
                    extra={
                        "chat_id": self.chat_id,
                        "briefing_id": briefing_id,
                        "message_length": len(message),
                    },
                )
            else:
                # Multiple chunks - split message
                chunks = self._split_message(message, max_length)
                logger.info(
                    "Sending briefing in chunks",
                    extra={
                        "chat_id": self.chat_id,
                        "briefing_id": briefing_id,
                        "total_chunks": len(chunks),
                    },
                )

                # Send all chunks except last without keyboard
                for i, chunk in enumerate(chunks[:-1]):
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=chunk,
                        parse_mode=parse_mode,
                    )
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)

                # Send last chunk with feedback keyboard
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=chunks[-1],
                    parse_mode=parse_mode,
                    reply_markup=get_briefing_feedback_keyboard(),
                )

                logger.info(
                    "Briefing chunks sent successfully",
                    extra={
                        "chat_id": self.chat_id,
                        "briefing_id": briefing_id,
                        "chunks_sent": len(chunks),
                    },
                )

            return True

        except TelegramError as e:
            logger.error(
                "Failed to send briefing",
                extra={
                    "chat_id": self.chat_id,
                    "briefing_id": briefing_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error sending briefing",
                extra={
                    "chat_id": self.chat_id,
                    "briefing_id": briefing_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return False

    def _split_message(self, message: str, max_length: int) -> list[str]:
        """
        Split long message into chunks respecting Telegram's character limit.

        Tries to split at paragraph boundaries first, then sentence boundaries,
        then word boundaries to maintain readability.

        Args:
            message: Message text to split
            max_length: Maximum characters per chunk

        Returns:
            List of message chunks, each <= max_length characters
        """
        if len(message) <= max_length:
            return [message]

        chunks = []
        remaining = message

        while remaining:
            if len(remaining) <= max_length:
                chunks.append(remaining)
                break

            # Try to split at paragraph boundary
            chunk = remaining[:max_length]
            split_idx = chunk.rfind("\n\n")

            if split_idx == -1:
                # Try to split at sentence boundary
                split_idx = max(
                    chunk.rfind(". "),
                    chunk.rfind("! "),
                    chunk.rfind("? "),
                )

            if split_idx == -1:
                # Try to split at word boundary
                split_idx = chunk.rfind(" ")

            if split_idx == -1:
                # No good split point - hard cut
                split_idx = max_length

            chunks.append(remaining[:split_idx].strip())
            remaining = remaining[split_idx:].strip()

        return chunks

    async def test_connection(self) -> bool:
        """
        Test the bot connection by fetching bot information.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            bot: Bot = self.application.bot
            bot_info = await bot.get_me()
            logger.info(
                "Bot connection test successful",
                extra={
                    "bot_username": bot_info.username,
                    "bot_id": bot_info.id,
                },
            )
            return True

        except TelegramError as e:
            logger.error(
                "Bot connection test failed",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            return False

    @property
    def is_running(self) -> bool:
        """Check if application is currently running."""
        return self._running
