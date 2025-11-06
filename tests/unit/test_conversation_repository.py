"""Unit tests for ConversationRepository."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from linear_chief.storage import Base, Conversation, ConversationRepository


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    yield session
    session.close()


@pytest.fixture
def conversation_repo(session):
    """Create ConversationRepository instance."""
    return ConversationRepository(session)


@pytest.fixture
def sample_conversations(conversation_repo):
    """Create sample conversation data."""
    conversations = []

    # User 123 - Recent conversation
    for i in range(5):
        conv = conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message=f"User message {i}",
            role="user",
        )
        conversations.append(conv)

        conv = conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message=f"Assistant response {i}",
            role="assistant",
        )
        conversations.append(conv)

    # User 789 - Different user
    conv = conversation_repo.save_message(
        user_id="789",
        chat_id="999",
        message="Another user's message",
        role="user",
    )
    conversations.append(conv)

    return conversations


class TestSaveMessage:
    """Tests for save_message method."""

    def test_save_user_message(self, conversation_repo):
        """Test saving user message."""
        conversation = conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="Hello, what's my status?",
            role="user",
        )

        assert conversation.id is not None
        assert conversation.user_id == "123"
        assert conversation.chat_id == "456"
        assert conversation.message == "Hello, what's my status?"
        assert conversation.role == "user"
        assert conversation.timestamp is not None

    def test_save_assistant_message(self, conversation_repo):
        """Test saving assistant message."""
        conversation = conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="You have 5 issues in progress.",
            role="assistant",
        )

        assert conversation.role == "assistant"
        assert conversation.message == "You have 5 issues in progress."

    def test_save_message_with_metadata(self, conversation_repo):
        """Test saving message with extra metadata."""
        metadata = {
            "message_id": "12345",
            "reply_to_message_id": "54321",
            "from_username": "testuser",
        }

        conversation = conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="Test message",
            role="user",
            extra_metadata=metadata,
        )

        assert conversation.extra_metadata == metadata
        assert conversation.extra_metadata["message_id"] == "12345"

    def test_save_message_invalid_role(self, conversation_repo):
        """Test saving message with invalid role raises error."""
        with pytest.raises(ValueError) as exc_info:
            conversation_repo.save_message(
                user_id="123",
                chat_id="456",
                message="Test",
                role="invalid_role",
            )

        assert "Invalid role" in str(exc_info.value)
        assert "user" in str(exc_info.value)
        assert "assistant" in str(exc_info.value)

    def test_save_message_empty_message(self, conversation_repo):
        """Test saving empty message."""
        conversation = conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="",
            role="user",
        )

        assert conversation.message == ""
        assert conversation.id is not None

    def test_save_message_long_message(self, conversation_repo):
        """Test saving very long message."""
        long_message = "A" * 10000
        conversation = conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message=long_message,
            role="user",
        )

        assert conversation.message == long_message
        assert len(conversation.message) == 10000


class TestGetConversationHistory:
    """Tests for get_conversation_history method."""

    def test_get_conversation_history(self, conversation_repo, sample_conversations):
        """Test retrieving conversation history."""
        history = conversation_repo.get_conversation_history(user_id="123", limit=10)

        assert len(history) == 10
        # Should be in chronological order (oldest first)
        assert history[0].message == "User message 0"
        assert history[-1].message == "Assistant response 4"

    def test_get_conversation_history_with_limit(
        self, conversation_repo, sample_conversations
    ):
        """Test conversation history with limit."""
        history = conversation_repo.get_conversation_history(user_id="123", limit=5)

        assert len(history) == 5
        # Should return most recent 5, in chronological order
        assert history[-1].message == "Assistant response 4"

    def test_get_conversation_history_time_filter(
        self, conversation_repo, session
    ):
        """Test conversation history with time filter."""
        # Create old conversation
        old_conv = Conversation(
            user_id="123",
            chat_id="456",
            message="Old message",
            role="user",
            timestamp=datetime.utcnow() - timedelta(hours=48),
        )
        session.add(old_conv)
        session.commit()

        # Create recent conversation
        conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="Recent message",
            role="user",
        )

        # Get only recent messages (last 24 hours)
        history = conversation_repo.get_conversation_history(
            user_id="123", limit=10, since_hours=24
        )

        assert len(history) == 1
        assert history[0].message == "Recent message"

    def test_get_conversation_history_different_users(
        self, conversation_repo, sample_conversations
    ):
        """Test conversation history filters by user."""
        user_123_history = conversation_repo.get_conversation_history(
            user_id="123", limit=20
        )
        user_789_history = conversation_repo.get_conversation_history(
            user_id="789", limit=20
        )

        assert len(user_123_history) == 10
        assert len(user_789_history) == 1
        assert user_789_history[0].message == "Another user's message"

    def test_get_conversation_history_empty(self, conversation_repo):
        """Test conversation history for user with no messages."""
        history = conversation_repo.get_conversation_history(user_id="999", limit=10)

        assert len(history) == 0

    def test_get_conversation_history_order(self, conversation_repo):
        """Test conversation history maintains chronological order."""
        # Add messages with delays
        conversation_repo.save_message(
            user_id="123", chat_id="456", message="First", role="user"
        )
        conversation_repo.save_message(
            user_id="123", chat_id="456", message="Second", role="assistant"
        )
        conversation_repo.save_message(
            user_id="123", chat_id="456", message="Third", role="user"
        )

        history = conversation_repo.get_conversation_history(user_id="123", limit=10)

        assert history[0].message == "First"
        assert history[1].message == "Second"
        assert history[2].message == "Third"


class TestGetUserContext:
    """Tests for get_user_context method."""

    def test_get_user_context(self, conversation_repo, sample_conversations):
        """Test getting formatted user context."""
        context = conversation_repo.get_user_context(user_id="123", limit=6)

        assert "User: User message 2" in context
        assert "Assistant: Assistant response 2" in context
        assert "User: User message 4" in context

        # Should have 6 messages formatted
        lines = context.split("\n")
        assert len(lines) == 6

    def test_get_user_context_formatting(self, conversation_repo):
        """Test user context formatting."""
        conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="What issues are blocked?",
            role="user",
        )
        conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="You have 2 blocked issues.",
            role="assistant",
        )

        context = conversation_repo.get_user_context(user_id="123", limit=10)

        assert context == (
            "User: What issues are blocked?\n"
            "Assistant: You have 2 blocked issues."
        )

    def test_get_user_context_empty_history(self, conversation_repo):
        """Test user context with no history."""
        context = conversation_repo.get_user_context(user_id="999", limit=10)

        assert context == "No previous conversation history."

    def test_get_user_context_limit(self, conversation_repo, sample_conversations):
        """Test user context respects limit."""
        context = conversation_repo.get_user_context(user_id="123", limit=3)

        lines = context.split("\n")
        assert len(lines) == 3


class TestClearOldConversations:
    """Tests for clear_old_conversations method."""

    def test_clear_old_conversations(self, conversation_repo, session):
        """Test clearing old conversations."""
        # Create old conversation (35 days ago)
        old_conv = Conversation(
            user_id="123",
            chat_id="456",
            message="Old message",
            role="user",
            timestamp=datetime.utcnow() - timedelta(days=35),
        )
        session.add(old_conv)
        session.commit()

        # Create recent conversation
        conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="Recent message",
            role="user",
        )

        # Clear conversations older than 30 days
        deleted_count = conversation_repo.clear_old_conversations(days=30)

        assert deleted_count == 1

        # Verify recent message still exists
        history = conversation_repo.get_conversation_history(user_id="123")
        assert len(history) == 1
        assert history[0].message == "Recent message"

    def test_clear_old_conversations_none_to_delete(self, conversation_repo, session):
        """Test clearing when no old conversations exist."""
        # Create recent conversation
        conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="Recent message",
            role="user",
        )

        deleted_count = conversation_repo.clear_old_conversations(days=30)

        assert deleted_count == 0

    def test_clear_old_conversations_custom_retention(
        self, conversation_repo, session
    ):
        """Test clearing with custom retention period."""
        # Create conversation 8 days ago
        old_conv = Conversation(
            user_id="123",
            chat_id="456",
            message="8 days old",
            role="user",
            timestamp=datetime.utcnow() - timedelta(days=8),
        )
        session.add(old_conv)
        session.commit()

        # Clear with 7-day retention
        deleted_count = conversation_repo.clear_old_conversations(days=7)

        assert deleted_count == 1


class TestGetActiveUsers:
    """Tests for get_active_users method."""

    def test_get_active_users(self, conversation_repo, sample_conversations):
        """Test getting list of active users."""
        active_users = conversation_repo.get_active_users(since_days=7)

        assert "123" in active_users
        assert "789" in active_users
        assert len(active_users) == 2

    def test_get_active_users_time_filter(self, conversation_repo, session):
        """Test active users with time filter."""
        # Create old conversation (10 days ago)
        old_conv = Conversation(
            user_id="old_user",
            chat_id="999",
            message="Old message",
            role="user",
            timestamp=datetime.utcnow() - timedelta(days=10),
        )
        session.add(old_conv)
        session.commit()

        # Create recent conversation
        conversation_repo.save_message(
            user_id="recent_user",
            chat_id="888",
            message="Recent message",
            role="user",
        )

        # Get users active in last 7 days
        active_users = conversation_repo.get_active_users(since_days=7)

        assert "recent_user" in active_users
        assert "old_user" not in active_users

    def test_get_active_users_empty(self, conversation_repo):
        """Test active users when no conversations exist."""
        active_users = conversation_repo.get_active_users(since_days=7)

        assert len(active_users) == 0

    def test_get_active_users_unique(self, conversation_repo):
        """Test active users returns unique user IDs."""
        # Create multiple messages from same user
        for i in range(5):
            conversation_repo.save_message(
                user_id="123",
                chat_id="456",
                message=f"Message {i}",
                role="user",
            )

        active_users = conversation_repo.get_active_users(since_days=7)

        assert len(active_users) == 1
        assert active_users[0] == "123"


class TestGetConversationStats:
    """Tests for get_conversation_stats method."""

    def test_get_conversation_stats(self, conversation_repo, sample_conversations):
        """Test getting conversation statistics."""
        stats = conversation_repo.get_conversation_stats(user_id="123", days=7)

        assert stats["total_messages"] == 10
        assert stats["user_messages"] == 5
        assert stats["assistant_messages"] == 5
        assert stats["first_message"] is not None
        assert stats["last_message"] is not None

    def test_get_conversation_stats_empty(self, conversation_repo):
        """Test conversation stats for user with no messages."""
        stats = conversation_repo.get_conversation_stats(user_id="999", days=7)

        assert stats["total_messages"] == 0
        assert stats["user_messages"] == 0
        assert stats["assistant_messages"] == 0
        assert stats["first_message"] is None
        assert stats["last_message"] is None

    def test_get_conversation_stats_time_filter(self, conversation_repo, session):
        """Test conversation stats with time filter."""
        # Create old conversation (10 days ago)
        old_conv = Conversation(
            user_id="123",
            chat_id="456",
            message="Old message",
            role="user",
            timestamp=datetime.utcnow() - timedelta(days=10),
        )
        session.add(old_conv)
        session.commit()

        # Create recent conversation
        conversation_repo.save_message(
            user_id="123",
            chat_id="456",
            message="Recent message",
            role="user",
        )

        # Get stats for last 7 days only
        stats = conversation_repo.get_conversation_stats(user_id="123", days=7)

        # Should only count recent message
        assert stats["total_messages"] == 1
        assert stats["user_messages"] == 1

    def test_get_conversation_stats_timestamps(self, conversation_repo):
        """Test conversation stats includes correct timestamps."""
        # Create messages with delays
        first_time = datetime.utcnow()
        conversation_repo.save_message(
            user_id="123", chat_id="456", message="First", role="user"
        )

        conversation_repo.save_message(
            user_id="123", chat_id="456", message="Second", role="user"
        )

        stats = conversation_repo.get_conversation_stats(user_id="123", days=7)

        assert stats["first_message"] is not None
        assert stats["last_message"] is not None
        assert stats["first_message"] <= stats["last_message"]

    def test_get_conversation_stats_different_users(
        self, conversation_repo, sample_conversations
    ):
        """Test conversation stats for different users."""
        stats_123 = conversation_repo.get_conversation_stats(user_id="123", days=7)
        stats_789 = conversation_repo.get_conversation_stats(user_id="789", days=7)

        assert stats_123["total_messages"] == 10
        assert stats_789["total_messages"] == 1
