"""Telegram bot for delivering briefings."""

import logging
from telegram import Bot
from telegram.error import TelegramError
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramBriefingBot:
    """Simple Telegram bot for sending briefing messages."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram bot.

        Args:
            bot_token: Telegram bot API token
            chat_id: Target chat ID to send messages to
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_briefing(
        self, message: str, parse_mode: Optional[str] = "Markdown"
    ) -> bool:
        """
        Send a briefing message to the configured chat.

        Args:
            message: The briefing message text
            parse_mode: Message parse mode (Markdown, HTML, or None)

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
            )
            logger.info(f"Briefing sent successfully to chat {self.chat_id}")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def test_connection(self) -> bool:
        """
        Test the bot connection by fetching bot information.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Bot connected: @{bot_info.username}")
            return True

        except TelegramError as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False
