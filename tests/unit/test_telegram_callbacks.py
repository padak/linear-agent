"""Unit tests for Telegram callback query handlers."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, CallbackQuery, Message, Chat, User

from linear_chief.telegram.callbacks import (
    feedback_callback_handler,
    issue_action_callback_handler,
)


@pytest.fixture
def mock_user():
    """Create mock Telegram user."""
    user = Mock(spec=User)
    user.id = 12345
    user.first_name = "Test"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_chat():
    """Create mock Telegram chat."""
    chat = Mock(spec=Chat)
    chat.id = 67890
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message(mock_chat):
    """Create mock Telegram message."""
    message = Mock(spec=Message)
    message.message_id = 123
    message.chat = mock_chat
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query(mock_user, mock_message):
    """Create mock CallbackQuery."""
    query = Mock(spec=CallbackQuery)
    query.id = "callback_123"
    query.from_user = mock_user
    query.message = mock_message
    query.data = None
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    return query


@pytest.fixture
def mock_update(mock_callback_query):
    """Create mock Update with CallbackQuery."""
    update = Mock(spec=Update)
    update.callback_query = mock_callback_query
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    return Mock()


class TestFeedbackCallbackHandler:
    """Tests for feedback callback handler (thumbs up/down)."""

    @pytest.mark.asyncio
    async def test_feedback_positive(
        self, mock_update, mock_context, mock_callback_query, mock_message
    ):
        """Test positive feedback callback."""
        mock_callback_query.data = "feedback_positive"

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

        # Verify answer was called
        mock_callback_query.answer.assert_called_once()

        # Verify feedback was saved
        mock_feedback_repo.save_feedback.assert_called_once()
        call_args = mock_feedback_repo.save_feedback.call_args
        assert call_args[1]["user_id"] == "12345"
        assert call_args[1]["feedback_type"] == "positive"

        # Verify buttons were removed
        mock_callback_query.edit_message_reply_markup.assert_called_once()

        # Verify acknowledgment message
        mock_message.reply_text.assert_called_once()
        ack_text = mock_message.reply_text.call_args[0][0]
        assert "Thanks for your feedback" in ack_text
        assert "helpful" in ack_text

    @pytest.mark.asyncio
    async def test_feedback_negative(
        self, mock_update, mock_context, mock_callback_query, mock_message
    ):
        """Test negative feedback callback."""
        mock_callback_query.data = "feedback_negative"

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

        # Verify answer was called
        mock_callback_query.answer.assert_called_once()

        # Verify feedback was saved with correct type
        mock_feedback_repo.save_feedback.assert_called_once()
        call_args = mock_feedback_repo.save_feedback.call_args
        assert call_args[1]["feedback_type"] == "negative"

        # Verify acknowledgment message
        mock_message.reply_text.assert_called_once()
        ack_text = mock_message.reply_text.call_args[0][0]
        assert "improving" in ack_text

    @pytest.mark.asyncio
    async def test_feedback_callback_no_query(self, mock_update, mock_context):
        """Test feedback callback when query is None."""
        mock_update.callback_query = None

        # Should not raise error
        await feedback_callback_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_feedback_callback_no_data(
        self, mock_update, mock_context, mock_callback_query
    ):
        """Test feedback callback when callback_data is None."""
        mock_callback_query.data = None

        await feedback_callback_handler(mock_update, mock_context)

        # Should answer and not proceed
        mock_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_feedback_callback_unknown_data(
        self, mock_update, mock_context, mock_callback_query
    ):
        """Test feedback callback with unknown callback data."""
        mock_callback_query.data = "unknown_action"

        await feedback_callback_handler(mock_update, mock_context)

        # Should remove buttons
        mock_callback_query.edit_message_reply_markup.assert_called_once()
        call_args = mock_callback_query.edit_message_reply_markup.call_args
        assert call_args[1]["reply_markup"] is None

    @pytest.mark.asyncio
    async def test_feedback_callback_saves_message_id(
        self, mock_update, mock_context, mock_callback_query, mock_message
    ):
        """Test feedback callback saves telegram_message_id in metadata."""
        mock_callback_query.data = "feedback_positive"
        mock_message.message_id = 456

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

        # Verify metadata includes message_id
        call_args = mock_feedback_repo.save_feedback.call_args
        assert call_args[1]["extra_metadata"]["telegram_message_id"] == "456"

    @pytest.mark.asyncio
    async def test_feedback_callback_error_handling(
        self, mock_update, mock_context, mock_callback_query
    ):
        """Test feedback callback error handling."""
        mock_callback_query.data = "feedback_positive"

        with patch(
            "linear_chief.telegram.callbacks.get_session_maker"
        ) as mock_get_session_maker:
            mock_get_session_maker.side_effect = Exception("Database error")

            await feedback_callback_handler(mock_update, mock_context)

            # Should answer with error message
            mock_callback_query.answer.assert_called()


class TestIssueActionCallbackHandler:
    """Tests for issue action callback handler (mark done, unsubscribe)."""

    @pytest.mark.asyncio
    async def test_issue_action_done(
        self, mock_update, mock_context, mock_callback_query, mock_message
    ):
        """Test mark issue as done callback."""
        mock_callback_query.data = "issue_done_PROJ-123"

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
                await issue_action_callback_handler(mock_update, mock_context)

        # Verify answer was called
        mock_callback_query.answer.assert_called_once()

        # Verify feedback was saved with action metadata
        mock_feedback_repo.save_feedback.assert_called_once()
        call_args = mock_feedback_repo.save_feedback.call_args
        assert call_args[1]["feedback_type"] == "issue_action"
        assert call_args[1]["extra_metadata"]["action"] == "done"
        assert call_args[1]["extra_metadata"]["issue_id"] == "PROJ-123"

        # Verify acknowledgment message
        mock_message.reply_text.assert_called_once()
        ack_text = mock_message.reply_text.call_args[0][0]
        assert "PROJ-123" in ack_text
        assert "marked as done" in ack_text

    @pytest.mark.asyncio
    async def test_issue_action_unsubscribe(
        self, mock_update, mock_context, mock_callback_query, mock_message
    ):
        """Test unsubscribe from issue callback."""
        mock_callback_query.data = "issue_unsub_PROJ-456"

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
                await issue_action_callback_handler(mock_update, mock_context)

        # Verify feedback was saved with correct action
        mock_feedback_repo.save_feedback.assert_called_once()
        call_args = mock_feedback_repo.save_feedback.call_args
        assert call_args[1]["extra_metadata"]["action"] == "unsubscribe"
        assert call_args[1]["extra_metadata"]["issue_id"] == "PROJ-456"

        # Verify acknowledgment message
        mock_message.reply_text.assert_called_once()
        ack_text = mock_message.reply_text.call_args[0][0]
        assert "PROJ-456" in ack_text
        assert "unsubscribed" in ack_text

    @pytest.mark.asyncio
    async def test_issue_action_callback_no_query(self, mock_update, mock_context):
        """Test issue action callback when query is None."""
        mock_update.callback_query = None

        # Should not raise error
        await issue_action_callback_handler(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_issue_action_callback_no_data(
        self, mock_update, mock_context, mock_callback_query
    ):
        """Test issue action callback when callback_data is None."""
        mock_callback_query.data = None

        await issue_action_callback_handler(mock_update, mock_context)

        # Should answer and not proceed
        mock_callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_action_callback_unknown_action(
        self, mock_update, mock_context, mock_callback_query
    ):
        """Test issue action callback with unknown action."""
        mock_callback_query.data = "issue_unknown_PROJ-123"

        await issue_action_callback_handler(mock_update, mock_context)

        # Should remove buttons
        mock_callback_query.edit_message_reply_markup.assert_called_once()
        call_args = mock_callback_query.edit_message_reply_markup.call_args
        assert call_args[1]["reply_markup"] is None

    @pytest.mark.asyncio
    async def test_issue_action_callback_removes_buttons(
        self, mock_update, mock_context, mock_callback_query
    ):
        """Test issue action callback removes buttons after action."""
        mock_callback_query.data = "issue_done_PROJ-123"

        with patch(
            "linear_chief.telegram.callbacks.get_session_maker"
        ) as mock_get_session_maker, patch(
            "linear_chief.telegram.callbacks.get_db_session"
        ) as mock_get_db_session:

            mock_session = Mock()
            mock_get_db_session.return_value = [mock_session]

            mock_feedback_repo = Mock()
            with patch(
                "linear_chief.telegram.callbacks.FeedbackRepository",
                return_value=mock_feedback_repo,
            ):
                await issue_action_callback_handler(mock_update, mock_context)

        # Verify buttons removed
        mock_callback_query.edit_message_reply_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_action_callback_error_handling(
        self, mock_update, mock_context, mock_callback_query
    ):
        """Test issue action callback error handling."""
        mock_callback_query.data = "issue_done_PROJ-123"

        with patch(
            "linear_chief.telegram.callbacks.get_session_maker"
        ) as mock_get_session_maker:
            mock_get_session_maker.side_effect = Exception("Database error")

            await issue_action_callback_handler(mock_update, mock_context)

            # Should answer with error message
            mock_callback_query.answer.assert_called()

    @pytest.mark.asyncio
    async def test_issue_action_multiple_issues(
        self, mock_update, mock_context, mock_callback_query, mock_message
    ):
        """Test issue action with different issue IDs."""
        issue_ids = ["PROJ-123", "ENG-456", "DESIGN-789"]

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
                for issue_id in issue_ids:
                    mock_callback_query.data = f"issue_done_{issue_id}"
                    await issue_action_callback_handler(mock_update, mock_context)

        # Verify all issues were processed
        assert mock_feedback_repo.save_feedback.call_count == 3
