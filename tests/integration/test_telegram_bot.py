"""Integration tests for Telegram bot."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from telegram.error import TelegramError, NetworkError, BadRequest, InvalidToken

from linear_chief.telegram import TelegramBriefingBot


@pytest.fixture
def bot_token():
    """Test bot token."""
    return "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"


@pytest.fixture
def chat_id():
    """Test chat ID."""
    return "123456789"


@pytest.fixture
def short_message():
    """Short message under 4096 characters."""
    return """**Daily Linear Briefing**

**Key Issues Requiring Attention**

1. PROJ-123: Critical login bug - needs immediate fix
2. PROJ-124: API endpoint timeout - affecting production

**Status Summary**

2 issues in progress, 1 blocked

**Blockers & Risks**

PROJ-124 blocked on infrastructure team

**Quick Wins**

PROJ-125: Documentation update ready to merge"""


@pytest.fixture
def long_message():
    """Long message exceeding 4096 characters."""
    # Create a message > 4096 chars
    base = """**Daily Linear Briefing**

**Key Issues Requiring Attention**

"""
    issues = "\n".join(
        [
            f"{i}. PROJ-{i}: This is a test issue with a longer description that takes up more space in the message"
            for i in range(1, 100)
        ]
    )
    return base + issues


@pytest.mark.asyncio
class TestTelegramBotSendBriefing:
    """Tests for send_briefing method."""

    async def test_send_briefing_short_message_success(
        self, bot_token, chat_id, short_message
    ):
        """Test sending short message successfully."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(short_message)

            assert result is True
            mock_bot.send_message.assert_called_once_with(
                chat_id=chat_id,
                text=short_message,
                parse_mode="Markdown",
            )

    async def test_send_briefing_with_markdown_formatting(self, bot_token, chat_id):
        """Test sending message with Markdown formatting."""
        message = "**Bold text** and *italic text* with `code`"

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(message, parse_mode="Markdown")

            assert result is True
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert call_args[1]["parse_mode"] == "Markdown"

    async def test_send_briefing_with_html_formatting(self, bot_token, chat_id):
        """Test sending message with HTML formatting."""
        message = "<b>Bold text</b> and <i>italic text</i>"

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(message, parse_mode="HTML")

            assert result is True
            call_args = mock_bot.send_message.call_args
            assert call_args[1]["parse_mode"] == "HTML"

    async def test_send_briefing_no_parse_mode(self, bot_token, chat_id, short_message):
        """Test sending message without parse mode."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(short_message, parse_mode=None)

            assert result is True
            call_args = mock_bot.send_message.call_args
            assert call_args[1]["parse_mode"] is None

    async def test_send_briefing_telegram_error(
        self, bot_token, chat_id, short_message
    ):
        """Test sending message when Telegram API returns error."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(
                side_effect=TelegramError("Bad Request: message is too long")
            )
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(short_message)

            assert result is False
            mock_bot.send_message.assert_called_once()

    async def test_send_briefing_network_error(self, bot_token, chat_id, short_message):
        """Test sending message when network error occurs."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(
                side_effect=NetworkError("Connection timeout")
            )
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(short_message)

            assert result is False

    async def test_send_briefing_unauthorized_error(
        self, bot_token, chat_id, short_message
    ):
        """Test sending message with invalid bot token."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(
                side_effect=InvalidToken("Invalid bot token")
            )
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(short_message)

            assert result is False

    async def test_send_briefing_bad_request_error(self, bot_token, chat_id):
        """Test sending message with bad request (e.g., invalid chat_id)."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(side_effect=BadRequest("Chat not found"))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing("Test message")

            assert result is False

    async def test_send_briefing_empty_message(self, bot_token, chat_id):
        """Test sending empty message."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing("")

            # Should still attempt to send
            assert result is True
            mock_bot.send_message.assert_called_once()

    async def test_send_briefing_very_long_message(
        self, bot_token, chat_id, long_message
    ):
        """Test sending message that exceeds 4096 character limit.

        Note: Current implementation sends as-is. If chunking is added later,
        this test should verify chunking behavior.
        """
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            # Telegram would reject this, but our implementation doesn't chunk yet
            mock_bot.send_message = AsyncMock(
                side_effect=BadRequest("Message is too long")
            )
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(long_message)

            # Currently returns False due to error
            assert result is False

    async def test_send_briefing_special_characters(self, bot_token, chat_id):
        """Test sending message with special characters."""
        message = "Test with emoji 🚀 and special chars: <>&[]"

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(message)

            assert result is True
            call_args = mock_bot.send_message.call_args
            assert call_args[1]["text"] == message

    async def test_send_briefing_multiline_message(self, bot_token, chat_id):
        """Test sending multiline message."""
        message = "Line 1\nLine 2\nLine 3\n\nLine 5"

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(message)

            assert result is True
            call_args = mock_bot.send_message.call_args
            assert "\n" in call_args[1]["text"]


@pytest.mark.asyncio
class TestTelegramBotTestConnection:
    """Tests for test_connection method."""

    async def test_test_connection_success(self, bot_token, chat_id):
        """Test successful connection test."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_me = Mock()
            mock_me.username = "test_bot"
            mock_me.first_name = "Test Bot"
            mock_me.id = 123456789
            mock_bot.get_me = AsyncMock(return_value=mock_me)
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.test_connection()

            assert result is True
            mock_bot.get_me.assert_called_once()

    async def test_test_connection_invalid_token(self, bot_token, chat_id):
        """Test connection with invalid token."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.get_me = AsyncMock(side_effect=InvalidToken("Invalid bot token"))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.test_connection()

            assert result is False

    async def test_test_connection_network_error(self, bot_token, chat_id):
        """Test connection with network error."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.get_me = AsyncMock(side_effect=NetworkError("Connection failed"))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.test_connection()

            assert result is False

    async def test_test_connection_telegram_error(self, bot_token, chat_id):
        """Test connection with general Telegram error."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.get_me = AsyncMock(side_effect=TelegramError("Unknown error"))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.test_connection()

            assert result is False

    async def test_test_connection_timeout(self, bot_token, chat_id):
        """Test connection timeout."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.get_me = AsyncMock(side_effect=NetworkError("Request timed out"))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.test_connection()

            assert result is False

    async def test_test_connection_returns_bot_info(self, bot_token, chat_id):
        """Test that connection test retrieves bot information."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_me = Mock()
            mock_me.username = "linear_chief_bot"
            mock_me.first_name = "Linear Chief"
            mock_me.id = 987654321
            mock_me.is_bot = True
            mock_bot.get_me = AsyncMock(return_value=mock_me)
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.test_connection()

            assert result is True
            # Verify get_me was called (which returns bot info)
            mock_bot.get_me.assert_called_once()
            bot_info = await mock_bot.get_me()
            assert bot_info.username == "linear_chief_bot"
            assert bot_info.is_bot is True


@pytest.mark.asyncio
class TestTelegramBotInitialization:
    """Tests for bot initialization."""

    def test_initialization_with_valid_credentials(self, bot_token, chat_id):
        """Test bot initialization with valid credentials."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            bot = TelegramBriefingBot(bot_token, chat_id)

            assert bot.chat_id == chat_id
            MockBot.assert_called_once_with(token=bot_token)

    def test_initialization_stores_chat_id(self, bot_token, chat_id):
        """Test that initialization stores chat_id correctly."""
        with patch("telegram.Bot"):
            bot = TelegramBriefingBot(bot_token, chat_id)

            assert bot.chat_id == chat_id

    def test_initialization_creates_bot_instance(self, bot_token, chat_id):
        """Test that initialization creates bot instance."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            bot = TelegramBriefingBot(bot_token, chat_id)

            assert bot.bot is not None
            MockBot.assert_called_once()


@pytest.mark.asyncio
class TestTelegramBotEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_send_briefing_with_markdown_escape_issues(self, bot_token, chat_id):
        """Test sending message with problematic Markdown characters."""
        # Markdown characters that might need escaping
        message = "Test with _ and * and [ and ] characters"

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(
                side_effect=BadRequest("Can't parse entities")
            )
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(message, parse_mode="Markdown")

            # Should return False due to parse error
            assert result is False

    async def test_send_briefing_retry_behavior(
        self, bot_token, chat_id, short_message
    ):
        """Test that send_briefing doesn't retry automatically.

        Note: Current implementation doesn't have retry logic.
        If retry is added, this test should verify retry behavior.
        """
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(side_effect=NetworkError("Timeout"))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(short_message)

            # Should fail without retry
            assert result is False
            mock_bot.send_message.assert_called_once()

    async def test_multiple_send_operations(self, bot_token, chat_id):
        """Test sending multiple messages sequentially."""
        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(
                side_effect=[
                    Mock(message_id=1),
                    Mock(message_id=2),
                    Mock(message_id=3),
                ]
            )
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)

            result1 = await bot.send_briefing("Message 1")
            result2 = await bot.send_briefing("Message 2")
            result3 = await bot.send_briefing("Message 3")

            assert result1 is True
            assert result2 is True
            assert result3 is True
            assert mock_bot.send_message.call_count == 3

    async def test_send_briefing_with_unicode(self, bot_token, chat_id):
        """Test sending message with Unicode characters."""
        message = "Test with Unicode: 你好 مرحبا Привет 🌍"

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            result = await bot.send_briefing(message)

            assert result is True
            call_args = mock_bot.send_message.call_args
            assert "你好" in call_args[1]["text"]
            assert "🌍" in call_args[1]["text"]

    async def test_concurrent_connection_tests(self, bot_token, chat_id):
        """Test running multiple connection tests concurrently."""
        import asyncio

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_me = Mock(username="test_bot", id=123)
            mock_bot.get_me = AsyncMock(return_value=mock_me)
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)

            # Run 5 connection tests concurrently
            results = await asyncio.gather(*[bot.test_connection() for _ in range(5)])

            assert all(results)
            assert mock_bot.get_me.call_count == 5
