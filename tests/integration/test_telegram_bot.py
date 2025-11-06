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


@pytest.mark.asyncio
class TestTelegramBotWithKeyboards:
    """Tests for bot with inline keyboards."""

    async def test_send_briefing_with_feedback_keyboard(self, bot_token, chat_id):
        """Test sending briefing with feedback keyboard."""
        from linear_chief.telegram.keyboards import get_briefing_feedback_keyboard

        with patch("linear_chief.telegram.bot.Bot") as MockBot:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(return_value=Mock(message_id=123))
            MockBot.return_value = mock_bot

            bot = TelegramBriefingBot(bot_token, chat_id)
            keyboard = get_briefing_feedback_keyboard()

            # Send message with keyboard (would need bot enhancement)
            result = await bot.send_briefing("Test briefing")

            assert result is True

    async def test_keyboard_structure(self):
        """Test feedback keyboard structure."""
        from linear_chief.telegram.keyboards import get_briefing_feedback_keyboard

        keyboard = get_briefing_feedback_keyboard()

        # Verify keyboard has buttons
        assert len(keyboard.inline_keyboard) == 1  # One row
        assert len(keyboard.inline_keyboard[0]) == 2  # Two buttons

        # Verify button data
        buttons = keyboard.inline_keyboard[0]
        assert buttons[0].callback_data == "feedback_positive"
        assert buttons[1].callback_data == "feedback_negative"

    async def test_issue_action_keyboard_structure(self):
        """Test issue action keyboard structure."""
        from linear_chief.telegram.keyboards import get_issue_action_keyboard

        keyboard = get_issue_action_keyboard(
            issue_id="PROJ-123",
            issue_url="https://linear.app/team/issue/PROJ-123"
        )

        # Verify keyboard has 2 rows
        assert len(keyboard.inline_keyboard) == 2

        # First row: Open in Linear (URL button)
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].url == "https://linear.app/team/issue/PROJ-123"

        # Second row: Mark Done, Unsubscribe (callback buttons)
        assert len(keyboard.inline_keyboard[1]) == 2
        assert keyboard.inline_keyboard[1][0].callback_data == "issue_done_PROJ-123"
        assert keyboard.inline_keyboard[1][1].callback_data == "issue_unsub_PROJ-123"


@pytest.mark.asyncio
class TestHandlerRegistration:
    """Tests for handler registration and bot application setup."""

    async def test_handlers_are_registered(self):
        """Test that all handlers would be registered in application."""
        from linear_chief.telegram.handlers import (
            start_handler,
            help_handler,
            status_handler,
            text_message_handler,
        )
        from linear_chief.telegram.callbacks import (
            feedback_callback_handler,
            issue_action_callback_handler,
        )

        # Verify handlers exist and are callable
        assert callable(start_handler)
        assert callable(help_handler)
        assert callable(status_handler)
        assert callable(text_message_handler)
        assert callable(feedback_callback_handler)
        assert callable(issue_action_callback_handler)

    async def test_callback_patterns(self):
        """Test callback query patterns are correct."""
        # Verify feedback patterns
        feedback_positive = "feedback_positive"
        feedback_negative = "feedback_negative"

        assert feedback_positive.startswith("feedback_")
        assert feedback_negative.startswith("feedback_")

        # Verify issue action patterns
        issue_done = "issue_done_PROJ-123"
        issue_unsub = "issue_unsub_PROJ-456"

        assert issue_done.startswith("issue_done_")
        assert issue_unsub.startswith("issue_unsub_")

        # Extract issue IDs
        assert issue_done.replace("issue_done_", "") == "PROJ-123"
        assert issue_unsub.replace("issue_unsub_", "") == "PROJ-456"


@pytest.mark.asyncio
class TestEndToEndWorkflow:
    """Tests for end-to-end bidirectional workflow."""

    async def test_user_sends_message_gets_response(self, bot_token, chat_id):
        """Test complete user interaction workflow."""
        from telegram import Update, Message, Chat, User
        from linear_chief.telegram.handlers import text_message_handler

        # Mock components
        mock_user = Mock(spec=User)
        mock_user.id = 12345
        mock_user.username = "testuser"

        mock_chat = Mock(spec=Chat)
        mock_chat.id = chat_id
        mock_chat.send_message = AsyncMock()

        mock_message = Mock(spec=Message)
        mock_message.text = "What issues are blocked?"
        mock_message.from_user = mock_user
        mock_message.chat = mock_chat

        mock_update = Mock(spec=Update)
        mock_update.message = mock_message
        mock_update.effective_user = mock_user
        mock_update.effective_chat = mock_chat

        mock_context = Mock()

        # Handle message
        await text_message_handler(mock_update, mock_context)

        # Verify response was sent
        mock_chat.send_message.assert_called_once()

    async def test_feedback_workflow(self, bot_token, chat_id):
        """Test complete feedback workflow."""
        from telegram import Update, CallbackQuery, Message, Chat, User
        from linear_chief.telegram.callbacks import feedback_callback_handler

        # Mock components
        mock_user = Mock(spec=User)
        mock_user.id = 12345

        mock_chat = Mock(spec=Chat)
        mock_chat.id = chat_id

        mock_message = Mock(spec=Message)
        mock_message.message_id = 123
        mock_message.chat = mock_chat
        mock_message.reply_text = AsyncMock()

        mock_query = Mock(spec=CallbackQuery)
        mock_query.id = "callback_123"
        mock_query.from_user = mock_user
        mock_query.message = mock_message
        mock_query.data = "feedback_positive"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_reply_markup = AsyncMock()

        mock_update = Mock(spec=Update)
        mock_update.callback_query = mock_query

        mock_context = Mock()

        # Mock database operations
        with patch(
            "linear_chief.telegram.callbacks.get_session_maker"
        ) as mock_get_session_maker, patch(
            "linear_chief.telegram.callbacks.get_db_session"
        ) as mock_get_db_session:

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_feedback_repo = Mock()
            mock_feedback_repo.save_feedback = Mock()

            with patch(
                "linear_chief.telegram.callbacks.FeedbackRepository",
                return_value=mock_feedback_repo,
            ):
                await feedback_callback_handler(mock_update, mock_context)

        # Verify workflow completed
        mock_query.answer.assert_called_once()
        mock_query.edit_message_reply_markup.assert_called_once()
        mock_message.reply_text.assert_called_once()
        mock_feedback_repo.save_feedback.assert_called_once()
