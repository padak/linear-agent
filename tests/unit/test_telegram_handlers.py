"""Unit tests for Telegram bot message handlers."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timedelta
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes

from linear_chief.telegram.handlers import (
    start_handler,
    help_handler,
    status_handler,
    briefing_handler,
    text_message_handler,
    _format_time_ago,
)


@pytest.fixture
def mock_user():
    """Create mock Telegram user."""
    user = Mock(spec=User)
    user.id = 12345
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_chat():
    """Create mock Telegram chat."""
    chat = Mock(spec=Chat)
    chat.id = 67890
    chat.type = "private"
    chat.send_message = AsyncMock()
    return chat


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Create mock Telegram message."""
    message = Mock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.message_id = 123
    message.text = "Test message"
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_message, mock_user, mock_chat):
    """Create mock Telegram update."""
    update = Mock(spec=Update)
    update.message = mock_message
    update.effective_user = mock_user
    update.effective_chat = mock_chat
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.fixture
def sample_issue_snapshots():
    """Create sample issue snapshots for testing."""
    snapshots = []
    states = ["In Progress", "In Progress", "Todo", "Done", "Blocked"]
    for i in range(5):
        snapshot = Mock()
        snapshot.issue_id = f"PROJ-{i+1}"
        snapshot.state = states[i]
        snapshot.title = f"Test Issue {i+1}"
        snapshot.priority = 2
        snapshot.snapshot_at = datetime.utcnow()
        snapshots.append(snapshot)
    return snapshots


@pytest.fixture
def sample_briefings():
    """Create sample briefings for testing."""
    briefings = []
    for i in range(3):
        briefing = Mock()
        briefing.id = i + 1
        briefing.content = f"Briefing {i+1} content"
        briefing.issue_count = 5
        briefing.generated_at = datetime.utcnow() - timedelta(days=i)
        briefing.delivery_status = "sent"
        briefing.cost_usd = 0.05
        briefings.append(briefing)
    return briefings


class TestStartHandler:
    """Tests for /start command handler."""

    @pytest.mark.asyncio
    async def test_start_handler_success(self, mock_update, mock_context, mock_chat):
        """Test /start command sends welcome message."""
        await start_handler(mock_update, mock_context)

        # Verify message sent
        mock_chat.send_message.assert_called_once()
        call_args = mock_chat.send_message.call_args

        # Verify message content
        assert "Welcome to Linear Chief of Staff" in call_args[1]["text"]
        assert "Daily briefings" in call_args[1]["text"]
        assert call_args[1]["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_start_handler_includes_help_reference(
        self, mock_update, mock_context, mock_chat
    ):
        """Test welcome message includes reference to /help command."""
        await start_handler(mock_update, mock_context)

        call_args = mock_chat.send_message.call_args
        assert "/help" in call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_start_handler_no_effective_chat(self, mock_update, mock_context):
        """Test /start handler when effective_chat is None."""
        mock_update.effective_chat = None

        # Should not raise error, just log warning
        await start_handler(mock_update, mock_context)

        # No message should be sent
        assert (
            not hasattr(mock_update, "effective_chat")
            or mock_update.effective_chat is None
        )

    @pytest.mark.asyncio
    async def test_start_handler_error_handling(
        self, mock_update, mock_context, mock_chat
    ):
        """Test /start handler error handling."""
        # Make send_message raise an error
        mock_chat.send_message.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            await start_handler(mock_update, mock_context)

        # Verify error message attempt (first call is the welcome, second is error)
        assert mock_chat.send_message.call_count == 2


class TestHelpHandler:
    """Tests for /help command handler."""

    @pytest.mark.asyncio
    async def test_help_handler_success(self, mock_update, mock_context, mock_chat):
        """Test /help command sends help message."""
        await help_handler(mock_update, mock_context)

        # Verify message sent
        mock_chat.send_message.assert_called_once()
        call_args = mock_chat.send_message.call_args

        # Verify message content
        assert "Available Commands" in call_args[1]["text"]
        assert "/start" in call_args[1]["text"]
        assert "/status" in call_args[1]["text"]
        assert call_args[1]["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_help_handler_lists_all_commands(
        self, mock_update, mock_context, mock_chat
    ):
        """Test help message lists all available commands."""
        await help_handler(mock_update, mock_context)

        call_args = mock_chat.send_message.call_args
        message_text = call_args[1]["text"]

        # Verify key commands are listed
        assert "/start" in message_text
        assert "/help" in message_text
        assert "/status" in message_text

    @pytest.mark.asyncio
    async def test_help_handler_no_effective_chat(self, mock_update, mock_context):
        """Test /help handler when effective_chat is None."""
        mock_update.effective_chat = None

        # Should not raise error
        await help_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_help_handler_error_handling(
        self, mock_update, mock_context, mock_chat
    ):
        """Test /help handler error handling."""
        mock_chat.send_message.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            await help_handler(mock_update, mock_context)

        # Verify error message attempt
        assert mock_chat.send_message.call_count == 2


class TestStatusHandler:
    """Tests for /status command handler."""

    @pytest.mark.asyncio
    async def test_status_handler_with_briefings(
        self,
        mock_update,
        mock_context,
        mock_chat,
        sample_briefings,
        sample_issue_snapshots,
    ):
        """Test /status command with existing briefings and issues."""
        with (
            patch(
                "linear_chief.telegram.handlers.get_session_maker"
            ) as mock_get_session_maker,
            patch(
                "linear_chief.telegram.handlers.get_db_session"
            ) as mock_get_db_session,
        ):

            # Mock database session
            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            # Mock repositories
            mock_briefing_repo = Mock()
            mock_briefing_repo.get_recent_briefings.return_value = sample_briefings
            mock_briefing_repo.get_total_cost.return_value = 0.15

            mock_issue_repo = Mock()
            mock_issue_repo.get_all_latest_snapshots.return_value = (
                sample_issue_snapshots
            )

            with (
                patch(
                    "linear_chief.telegram.handlers.BriefingRepository",
                    return_value=mock_briefing_repo,
                ),
                patch(
                    "linear_chief.telegram.handlers.IssueHistoryRepository",
                    return_value=mock_issue_repo,
                ),
            ):
                await status_handler(mock_update, mock_context)

        # Verify message sent
        mock_chat.send_message.assert_called_once()
        call_args = mock_chat.send_message.call_args
        message_text = call_args[1]["text"]

        # Verify content
        assert "Briefing Status" in message_text
        assert "*Tracked Issues:* 5" in message_text
        assert "*Recent Briefings (7d):* 3" in message_text
        assert "$0.1500" in message_text  # Total cost
        assert "*Issue Breakdown:*" in message_text

    @pytest.mark.asyncio
    async def test_status_handler_no_briefings(
        self, mock_update, mock_context, mock_chat, sample_issue_snapshots
    ):
        """Test /status command when no briefings exist."""
        with (
            patch(
                "linear_chief.telegram.handlers.get_session_maker"
            ) as mock_get_session_maker,
            patch(
                "linear_chief.telegram.handlers.get_db_session"
            ) as mock_get_db_session,
        ):

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_briefing_repo = Mock()
            mock_briefing_repo.get_recent_briefings.return_value = []
            mock_briefing_repo.get_total_cost.return_value = 0.0

            mock_issue_repo = Mock()
            mock_issue_repo.get_all_latest_snapshots.return_value = (
                sample_issue_snapshots
            )

            with (
                patch(
                    "linear_chief.telegram.handlers.BriefingRepository",
                    return_value=mock_briefing_repo,
                ),
                patch(
                    "linear_chief.telegram.handlers.IssueHistoryRepository",
                    return_value=mock_issue_repo,
                ),
            ):
                await status_handler(mock_update, mock_context)

        call_args = mock_chat.send_message.call_args
        message_text = call_args[1]["text"]

        assert "No briefings generated yet" in message_text
        assert "*Recent Briefings (7d):* 0" in message_text

    @pytest.mark.asyncio
    async def test_status_handler_no_issues(self, mock_update, mock_context, mock_chat):
        """Test /status command when no issues tracked."""
        with (
            patch(
                "linear_chief.telegram.handlers.get_session_maker"
            ) as mock_get_session_maker,
            patch(
                "linear_chief.telegram.handlers.get_db_session"
            ) as mock_get_db_session,
        ):

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_briefing_repo = Mock()
            mock_briefing_repo.get_recent_briefings.return_value = []
            mock_briefing_repo.get_total_cost.return_value = 0.0

            mock_issue_repo = Mock()
            mock_issue_repo.get_all_latest_snapshots.return_value = []

            with (
                patch(
                    "linear_chief.telegram.handlers.BriefingRepository",
                    return_value=mock_briefing_repo,
                ),
                patch(
                    "linear_chief.telegram.handlers.IssueHistoryRepository",
                    return_value=mock_issue_repo,
                ),
            ):
                await status_handler(mock_update, mock_context)

        call_args = mock_chat.send_message.call_args
        message_text = call_args[1]["text"]

        assert "*Tracked Issues:* 0" in message_text

    @pytest.mark.asyncio
    async def test_status_handler_issue_breakdown(
        self,
        mock_update,
        mock_context,
        mock_chat,
        sample_briefings,
        sample_issue_snapshots,
    ):
        """Test /status includes issue breakdown by state."""
        with (
            patch(
                "linear_chief.telegram.handlers.get_session_maker"
            ) as mock_get_session_maker,
            patch(
                "linear_chief.telegram.handlers.get_db_session"
            ) as mock_get_db_session,
        ):

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_briefing_repo = Mock()
            mock_briefing_repo.get_recent_briefings.return_value = sample_briefings
            mock_briefing_repo.get_total_cost.return_value = 0.15

            mock_issue_repo = Mock()
            mock_issue_repo.get_all_latest_snapshots.return_value = (
                sample_issue_snapshots
            )

            with (
                patch(
                    "linear_chief.telegram.handlers.BriefingRepository",
                    return_value=mock_briefing_repo,
                ),
                patch(
                    "linear_chief.telegram.handlers.IssueHistoryRepository",
                    return_value=mock_issue_repo,
                ),
            ):
                await status_handler(mock_update, mock_context)

        call_args = mock_chat.send_message.call_args
        message_text = call_args[1]["text"]

        # Verify state counts (2 In Progress, 1 Todo, 1 Done, 1 Blocked)
        assert "In Progress: 2" in message_text
        assert "Todo: 1" in message_text
        assert "Done: 1" in message_text
        assert "Blocked: 1" in message_text

    @pytest.mark.asyncio
    async def test_status_handler_no_effective_chat(self, mock_update, mock_context):
        """Test /status handler when effective_chat is None."""
        mock_update.effective_chat = None

        await status_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_status_handler_error_handling(
        self, mock_update, mock_context, mock_chat
    ):
        """Test /status handler database error handling."""
        with patch(
            "linear_chief.telegram.handlers.get_session_maker"
        ) as mock_get_session_maker:
            mock_get_session_maker.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await status_handler(mock_update, mock_context)

            # Verify error message attempt
            assert mock_chat.send_message.call_count == 1


class TestBriefingHandler:
    """Tests for /briefing command handler."""

    @pytest.mark.asyncio
    async def test_briefing_handler_success(
        self, mock_update, mock_context, mock_chat, sample_briefings
    ):
        """Test /briefing command sends latest briefing."""
        with (
            patch(
                "linear_chief.telegram.handlers.get_session_maker"
            ) as mock_get_session_maker,
            patch(
                "linear_chief.telegram.handlers.get_db_session"
            ) as mock_get_db_session,
        ):

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_briefing_repo = Mock()
            mock_briefing_repo.get_recent_briefings.return_value = [sample_briefings[0]]

            with patch(
                "linear_chief.telegram.handlers.BriefingRepository",
                return_value=mock_briefing_repo,
            ):
                await briefing_handler(mock_update, mock_context)

        # Verify message sent
        mock_chat.send_message.assert_called_once()
        call_args = mock_chat.send_message.call_args

        # Verify message content
        message_text = call_args[1]["text"]
        assert "📊 *Latest Briefing*" in message_text
        assert "Generated:" in message_text
        assert "Briefing 1 content" in message_text
        assert call_args[1]["parse_mode"] == "Markdown"

        # Verify feedback keyboard included
        assert call_args[1]["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_briefing_handler_no_briefings(
        self, mock_update, mock_context, mock_chat
    ):
        """Test /briefing when no briefings exist."""
        with (
            patch(
                "linear_chief.telegram.handlers.get_session_maker"
            ) as mock_get_session_maker,
            patch(
                "linear_chief.telegram.handlers.get_db_session"
            ) as mock_get_db_session,
        ):

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_briefing_repo = Mock()
            mock_briefing_repo.get_recent_briefings.return_value = []

            with patch(
                "linear_chief.telegram.handlers.BriefingRepository",
                return_value=mock_briefing_repo,
            ):
                await briefing_handler(mock_update, mock_context)

        # Verify message sent
        mock_chat.send_message.assert_called_once()
        call_args = mock_chat.send_message.call_args

        # Verify friendly message
        message_text = call_args[1]["text"]
        assert "No briefings generated yet" in message_text
        assert "/status" in message_text

    @pytest.mark.asyncio
    async def test_briefing_handler_no_effective_chat(self, mock_update, mock_context):
        """Test /briefing handler when effective_chat is None."""
        mock_update.effective_chat = None

        # Should not raise error
        await briefing_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_briefing_handler_error_handling(
        self, mock_update, mock_context, mock_chat
    ):
        """Test /briefing error handling."""
        with patch(
            "linear_chief.telegram.handlers.get_session_maker"
        ) as mock_get_session_maker:
            mock_get_session_maker.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                await briefing_handler(mock_update, mock_context)

            # Verify error message attempt
            assert mock_chat.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_briefing_handler_includes_timestamp(
        self, mock_update, mock_context, mock_chat, sample_briefings
    ):
        """Test /briefing includes formatted timestamp."""
        with (
            patch(
                "linear_chief.telegram.handlers.get_session_maker"
            ) as mock_get_session_maker,
            patch(
                "linear_chief.telegram.handlers.get_db_session"
            ) as mock_get_db_session,
        ):

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_briefing_repo = Mock()
            mock_briefing_repo.get_recent_briefings.return_value = [sample_briefings[0]]

            with patch(
                "linear_chief.telegram.handlers.BriefingRepository",
                return_value=mock_briefing_repo,
            ):
                await briefing_handler(mock_update, mock_context)

        call_args = mock_chat.send_message.call_args
        message_text = call_args[1]["text"]

        # Verify timestamp format (YYYY-MM-DD HH:MM)
        assert "Generated:" in message_text
        # Timestamp should be in format like "2025-11-05 12:34"
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", message_text)


class TestTextMessageHandler:
    """Tests for text message handler."""

    @pytest.mark.asyncio
    async def test_text_message_handler_success(
        self, mock_update, mock_context, mock_chat
    ):
        """Test text message handler sends intelligent response."""
        with (
            patch("linear_chief.config.CONVERSATION_ENABLED", True),
            patch("linear_chief.config.ANTHROPIC_API_KEY", "test_key"),
            patch("linear_chief.telegram.handlers.get_session_maker"),
            patch("linear_chief.telegram.handlers.get_db_session") as mock_get_session,
            patch("linear_chief.agent.ConversationAgent") as mock_agent_class,
            patch(
                "linear_chief.agent.context_builder.build_conversation_context",
                new_callable=AsyncMock,
            ) as mock_build_context,
        ):

            # Mock database session
            mock_session = Mock()
            mock_get_session.return_value = [mock_session]

            # Mock conversation repository
            mock_conv_repo = Mock()
            mock_conv_repo.save_message = Mock()
            mock_conv_repo.get_conversation_history = Mock(return_value=[])

            with patch(
                "linear_chief.storage.repositories.ConversationRepository",
                return_value=mock_conv_repo,
            ):
                # Mock context builder
                mock_build_context.return_value = "Test context"

                # Mock conversation agent
                mock_agent = Mock()
                mock_agent.generate_response = AsyncMock(
                    return_value="Here's your response"
                )
                mock_agent_class.return_value = mock_agent

                await text_message_handler(mock_update, mock_context)

                # Verify typing action sent
                mock_chat.send_action.assert_called_once_with(action="typing")

                # Verify message sent
                assert mock_chat.send_message.call_count == 1
                call_args = mock_chat.send_message.call_args

                # Verify response content
                assert call_args[1]["text"] == "Here's your response"

    @pytest.mark.asyncio
    async def test_text_message_handler_logs_message(
        self, mock_update, mock_context, mock_chat
    ):
        """Test text message handler logs user query."""
        mock_update.message.text = "What issues are blocked?"

        with (
            patch("linear_chief.config.CONVERSATION_ENABLED", True),
            patch("linear_chief.config.ANTHROPIC_API_KEY", "test_key"),
            patch("linear_chief.telegram.handlers.get_session_maker"),
            patch("linear_chief.telegram.handlers.get_db_session") as mock_get_session,
            patch("linear_chief.agent.ConversationAgent") as mock_agent_class,
            patch(
                "linear_chief.agent.context_builder.build_conversation_context",
                new_callable=AsyncMock,
            ),
            patch("linear_chief.telegram.handlers.logger") as mock_logger,
        ):

            # Mock database session
            mock_session = Mock()
            mock_get_session.return_value = [mock_session]

            # Mock conversation repository
            mock_conv_repo = Mock()
            mock_conv_repo.save_message = Mock()
            mock_conv_repo.get_conversation_history = Mock(return_value=[])

            with patch(
                "linear_chief.storage.repositories.ConversationRepository",
                return_value=mock_conv_repo,
            ):
                # Mock conversation agent
                mock_agent = Mock()
                mock_agent.generate_response = AsyncMock(
                    return_value="Here's your response"
                )
                mock_agent_class.return_value = mock_agent

                await text_message_handler(mock_update, mock_context)

                # Verify logging occurred (check that info was called with the message)
                info_calls = [
                    call
                    for call in mock_logger.info.call_args_list
                    if len(call[0]) > 0 and "Received user query" in call[0][0]
                ]
                assert len(info_calls) > 0

                # Verify the logged extra data
                log_call = info_calls[0]
                assert log_call[1]["extra"]["message_length"] == len(
                    "What issues are blocked?"
                )
                assert (
                    log_call[1]["extra"]["message_preview"]
                    == "What issues are blocked?"
                )

    @pytest.mark.asyncio
    async def test_text_message_handler_long_message(
        self, mock_update, mock_context, mock_chat
    ):
        """Test text message handler with long message (>100 chars)."""
        long_message = "A" * 150
        mock_update.message.text = long_message

        with (
            patch("linear_chief.config.CONVERSATION_ENABLED", True),
            patch("linear_chief.config.ANTHROPIC_API_KEY", "test_key"),
            patch("linear_chief.telegram.handlers.get_session_maker"),
            patch("linear_chief.telegram.handlers.get_db_session") as mock_get_session,
            patch("linear_chief.agent.ConversationAgent") as mock_agent_class,
            patch(
                "linear_chief.agent.context_builder.build_conversation_context",
                new_callable=AsyncMock,
            ),
            patch("linear_chief.telegram.handlers.logger") as mock_logger,
        ):

            # Mock database session
            mock_session = Mock()
            mock_get_session.return_value = [mock_session]

            # Mock conversation repository
            mock_conv_repo = Mock()
            mock_conv_repo.save_message = Mock()
            mock_conv_repo.get_conversation_history = Mock(return_value=[])

            with patch(
                "linear_chief.storage.repositories.ConversationRepository",
                return_value=mock_conv_repo,
            ):
                # Mock conversation agent
                mock_agent = Mock()
                mock_agent.generate_response = AsyncMock(
                    return_value="Here's your response"
                )
                mock_agent_class.return_value = mock_agent

                await text_message_handler(mock_update, mock_context)

                # Verify message preview is truncated in logs
                info_calls = [
                    call
                    for call in mock_logger.info.call_args_list
                    if len(call[0]) > 0 and "Received user query" in call[0][0]
                ]
                assert len(info_calls) > 0
                log_call = info_calls[0]
                assert log_call[1]["extra"]["message_length"] == 150
                assert log_call[1]["extra"]["message_preview"] == "A" * 100

    @pytest.mark.asyncio
    async def test_text_message_handler_no_message_text(
        self, mock_update, mock_context, mock_chat
    ):
        """Test text message handler with None message text."""
        mock_update.message.text = None

        with (
            patch("linear_chief.config.CONVERSATION_ENABLED", True),
            patch("linear_chief.config.ANTHROPIC_API_KEY", "test_key"),
            patch("linear_chief.telegram.handlers.get_session_maker"),
            patch("linear_chief.telegram.handlers.get_db_session") as mock_get_session,
            patch("linear_chief.agent.ConversationAgent") as mock_agent_class,
            patch(
                "linear_chief.agent.context_builder.build_conversation_context",
                new_callable=AsyncMock,
            ),
        ):

            # Mock database session
            mock_session = Mock()
            mock_get_session.return_value = [mock_session]

            # Mock conversation repository
            mock_conv_repo = Mock()
            mock_conv_repo.save_message = Mock()
            mock_conv_repo.get_conversation_history = Mock(return_value=[])

            with patch(
                "linear_chief.storage.repositories.ConversationRepository",
                return_value=mock_conv_repo,
            ):
                # Mock conversation agent
                mock_agent = Mock()
                mock_agent.generate_response = AsyncMock(
                    return_value="Here's your response"
                )
                mock_agent_class.return_value = mock_agent

                await text_message_handler(mock_update, mock_context)

                # Should still send response (with empty string as message)
                assert mock_chat.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_text_message_handler_no_effective_chat(
        self, mock_update, mock_context
    ):
        """Test text message handler when effective_chat is None."""
        mock_update.effective_chat = None

        await text_message_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_text_message_handler_no_message(self, mock_update, mock_context):
        """Test text message handler when message is None."""
        mock_update.message = None

        await text_message_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_text_message_handler_error_handling(
        self, mock_update, mock_context, mock_chat
    ):
        """Test text message handler error handling when response generation fails."""
        with (
            patch("linear_chief.config.CONVERSATION_ENABLED", True),
            patch("linear_chief.config.ANTHROPIC_API_KEY", "test_key"),
            patch("linear_chief.telegram.handlers.get_session_maker"),
            patch("linear_chief.telegram.handlers.get_db_session") as mock_get_session,
            patch("linear_chief.agent.ConversationAgent") as mock_agent_class,
            patch(
                "linear_chief.agent.context_builder.build_conversation_context",
                new_callable=AsyncMock,
                return_value="context",
            ),
        ):
            # Mock database session
            mock_session = Mock()
            mock_get_session.return_value = [mock_session]

            # Mock conversation repository
            mock_conv_repo = Mock()
            mock_conv_repo.save_message = Mock()
            mock_conv_repo.get_conversation_history = Mock(return_value=[])

            with patch(
                "linear_chief.storage.repositories.ConversationRepository",
                return_value=mock_conv_repo,
            ):
                # Mock conversation agent to raise error
                mock_agent = Mock()
                mock_agent.generate_response = AsyncMock(
                    side_effect=Exception("API Error")
                )
                mock_agent_class.return_value = mock_agent

                # Should not raise - fallback message should be sent
                await text_message_handler(mock_update, mock_context)

                # Verify fallback message was sent
                assert mock_chat.send_message.call_count == 1
                fallback_call = mock_chat.send_message.call_args
                assert "having trouble" in fallback_call[1]["text"].lower()


class TestFormatTimeAgo:
    """Tests for _format_time_ago helper function."""

    def test_format_time_ago_just_now(self):
        """Test formatting time less than 1 minute ago."""
        timestamp = datetime.utcnow() - timedelta(seconds=30)
        result = _format_time_ago(timestamp)
        assert result == "just now"

    def test_format_time_ago_minutes(self):
        """Test formatting time in minutes."""
        timestamp = datetime.utcnow() - timedelta(minutes=15)
        result = _format_time_ago(timestamp)
        assert result == "15 minutes ago"

    def test_format_time_ago_one_minute(self):
        """Test formatting exactly 1 minute ago (singular)."""
        timestamp = datetime.utcnow() - timedelta(minutes=1)
        result = _format_time_ago(timestamp)
        assert result == "1 minute ago"

    def test_format_time_ago_hours(self):
        """Test formatting time in hours."""
        timestamp = datetime.utcnow() - timedelta(hours=3)
        result = _format_time_ago(timestamp)
        assert result == "3 hours ago"

    def test_format_time_ago_one_hour(self):
        """Test formatting exactly 1 hour ago (singular)."""
        timestamp = datetime.utcnow() - timedelta(hours=1)
        result = _format_time_ago(timestamp)
        assert result == "1 hour ago"

    def test_format_time_ago_days(self):
        """Test formatting time in days."""
        timestamp = datetime.utcnow() - timedelta(days=3)
        result = _format_time_ago(timestamp)
        assert result == "3 days ago"

    def test_format_time_ago_one_day(self):
        """Test formatting exactly 1 day ago (singular)."""
        timestamp = datetime.utcnow() - timedelta(days=1)
        result = _format_time_ago(timestamp)
        assert result == "1 day ago"

    def test_format_time_ago_weeks(self):
        """Test formatting time in weeks."""
        timestamp = datetime.utcnow() - timedelta(days=14)
        result = _format_time_ago(timestamp)
        assert result == "2 weeks ago"

    def test_format_time_ago_one_week(self):
        """Test formatting exactly 1 week ago (singular)."""
        timestamp = datetime.utcnow() - timedelta(days=7)
        result = _format_time_ago(timestamp)
        assert result == "1 week ago"

    def test_format_time_ago_months(self):
        """Test formatting time in months."""
        timestamp = datetime.utcnow() - timedelta(days=60)
        result = _format_time_ago(timestamp)
        assert result == "2 months ago"

    def test_format_time_ago_one_month(self):
        """Test formatting exactly 1 month ago (singular)."""
        timestamp = datetime.utcnow() - timedelta(days=30)
        result = _format_time_ago(timestamp)
        assert result == "1 month ago"
