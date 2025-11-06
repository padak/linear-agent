"""Example: Running the bidirectional Telegram bot in interactive mode.

This example demonstrates how to start the TelegramApplication in interactive mode
for bidirectional communication with users.

Usage:
    1. Set TELEGRAM_MODE=interactive in .env
    2. Run: python examples/interactive_bot_example.py

The bot will:
- Listen for commands (/start, /help, /status)
- Respond to user messages
- Handle feedback on briefings (thumbs up/down)
- Process issue actions (mark done, unsubscribe)
"""

import asyncio
from linear_chief.telegram import TelegramApplication
from linear_chief.config import (
    ensure_directories,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_FILE,
)
from linear_chief.utils.logging import setup_logging, get_logger

# Initialize logging system (enables cache hit/miss logs and other info)
setup_logging(
    level=LOG_LEVEL,
    format_type=LOG_FORMAT,
    log_file=LOG_FILE,
)
logger = get_logger(__name__)


async def main():
    """Run the interactive Telegram bot."""
    # Ensure directories exist
    ensure_directories()

    # Create application instance
    app = TelegramApplication(
        bot_token=TELEGRAM_BOT_TOKEN,
        chat_id=TELEGRAM_CHAT_ID,
        polling=True,  # Enable polling mode
    )

    try:
        # Start the bot (blocking call)
        logger.info("Starting Telegram bot in interactive mode...")
        print("Starting Telegram bot in interactive mode...")
        print("Press Ctrl+C to stop")
        await app.start()

        # Keep running until interrupted
        # The bot will handle all incoming messages and callbacks
        while app.is_running:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down bot...")
        print("\nStopping bot...")
    finally:
        # Graceful shutdown
        await app.stop()
        logger.info("Bot stopped")
        print("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Already handled in main()
