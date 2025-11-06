"""Unit tests for ConversationAgent."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from anthropic.types import Message, Usage, TextBlock

from linear_chief.agent.conversation_agent import ConversationAgent


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return Message(
        id="msg_123",
        type="message",
        role="assistant",
        content=[
            TextBlock(
                type="text",
                text="Here's the status of your issues. You have 3 issues in progress.",
            )
        ],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=150, output_tokens=50),
    )


@pytest.mark.asyncio
async def test_generate_response_simple(mock_anthropic_response):
    """Test generating a simple response without context."""
    agent = ConversationAgent(api_key="test_key")

    with patch.object(
        agent.client.messages, "create", return_value=mock_anthropic_response
    ):
        response = await agent.generate_response(
            user_message="What issues do I have?",
            conversation_history=[],
            context=None,
        )

        assert (
            response
            == "Here's the status of your issues. You have 3 issues in progress."
        )


@pytest.mark.asyncio
async def test_generate_response_with_history(mock_anthropic_response):
    """Test generating response with conversation history."""
    agent = ConversationAgent(api_key="test_key")

    history = [
        {"role": "user", "content": "Hi there"},
        {"role": "assistant", "content": "Hello! How can I help?"},
    ]

    with patch.object(
        agent.client.messages, "create", return_value=mock_anthropic_response
    ) as mock_create:
        response = await agent.generate_response(
            user_message="What issues do I have?",
            conversation_history=history,
            context=None,
        )

        # Verify history was included in the call
        call_args = mock_create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 3  # 2 history + 1 current
        assert messages[0] == history[0]
        assert messages[1] == history[1]


@pytest.mark.asyncio
async def test_generate_response_with_context(mock_anthropic_response):
    """Test generating response with context."""
    agent = ConversationAgent(api_key="test_key")

    context = "Recent Issues:\n- PROJ-123: Bug fix\n- PROJ-124: Feature request"

    with patch.object(
        agent.client.messages, "create", return_value=mock_anthropic_response
    ) as mock_create:
        response = await agent.generate_response(
            user_message="What issues do I have?",
            conversation_history=[],
            context=context,
        )

        # Verify context was included in the message
        call_args = mock_create.call_args
        messages = call_args.kwargs["messages"]
        assert "Context Information:" in messages[0]["content"]
        assert context in messages[0]["content"]


@pytest.mark.asyncio
async def test_generate_response_limits_history():
    """Test that conversation history is limited to CONVERSATION_MAX_HISTORY."""
    from linear_chief.config import CONVERSATION_MAX_HISTORY

    agent = ConversationAgent(api_key="test_key")

    # Create more messages than the limit (100 messages = 50 pairs)
    history = []
    for i in range(100):
        history.append({"role": "user", "content": f"Message {i}"})
        history.append({"role": "assistant", "content": f"Response {i}"})

    mock_response = Message(
        id="msg_123",
        type="message",
        role="assistant",
        content=[TextBlock(type="text", text="Response")],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=100, output_tokens=50),
    )

    with patch.object(
        agent.client.messages, "create", return_value=mock_response
    ) as mock_create:
        await agent.generate_response(
            user_message="Current question",
            conversation_history=history,
            context=None,
        )

        # Verify only last CONVERSATION_MAX_HISTORY messages + current were used
        call_args = mock_create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) <= CONVERSATION_MAX_HISTORY + 1  # history + 1 current


@pytest.mark.asyncio
async def test_generate_response_handles_api_error():
    """Test error handling when API call fails."""
    agent = ConversationAgent(api_key="test_key")

    with patch.object(
        agent.client.messages, "create", side_effect=Exception("API Error")
    ):
        with pytest.raises(Exception, match="API Error"):
            await agent.generate_response(
                user_message="Test",
                conversation_history=[],
                context=None,
            )


def test_estimate_cost():
    """Test cost estimation calculation."""
    agent = ConversationAgent(api_key="test_key")

    # Test with known values
    cost = agent.estimate_cost(input_tokens=1000, output_tokens=500)

    # Input: 1000 tokens * $3 per million = $0.003
    # Output: 500 tokens * $15 per million = $0.0075
    # Total: $0.0105
    assert cost == pytest.approx(0.0105, rel=1e-6)


def test_build_system_prompt():
    """Test system prompt building."""
    agent = ConversationAgent(api_key="test_key")
    prompt = agent._build_system_prompt()

    # Verify key elements are present
    assert "Chief of Staff" in prompt
    assert "Linear" in prompt
    assert "briefings" in prompt.lower()
    assert "capabilities" in prompt.lower()
    assert "guidelines" in prompt.lower()


def test_build_messages_no_context():
    """Test message building without context."""
    agent = ConversationAgent(api_key="test_key")

    messages = agent._build_messages(
        user_message="What's my status?",
        conversation_history=[],
        context=None,
    )

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What's my status?"


def test_build_messages_with_context():
    """Test message building with context."""
    agent = ConversationAgent(api_key="test_key")

    context = "Recent issues: PROJ-123"

    messages = agent._build_messages(
        user_message="What's my status?",
        conversation_history=[],
        context=context,
    )

    assert len(messages) == 1
    assert "Context Information:" in messages[0]["content"]
    assert context in messages[0]["content"]
    assert "What's my status?" in messages[0]["content"]


@pytest.mark.asyncio
async def test_generate_response_with_issue_map(mock_anthropic_response):
    """Test that issue_map adds clickable links to response."""
    # Mock response with plain issue IDs
    mock_response_with_issues = Message(
        id="msg_123",
        type="message",
        role="assistant",
        content=[
            TextBlock(
                type="text",
                text="Here are your issues:\n- PROJ-123: Feature request\n- PROJ-456: Bug fix",
            )
        ],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=150, output_tokens=50),
    )

    agent = ConversationAgent(api_key="test_key")
    issue_map = {
        "PROJ-123": "https://linear.app/org/issue/PROJ-123",
        "PROJ-456": "https://linear.app/org/issue/PROJ-456",
    }

    with patch.object(
        agent.client.messages, "create", return_value=mock_response_with_issues
    ):
        response = await agent.generate_response(
            user_message="What issues do I have?",
            conversation_history=[],
            context=None,
            issue_map=issue_map,
        )

        # Verify issue IDs are now clickable links
        assert "[**PROJ-123**](https://linear.app/org/issue/PROJ-123)" in response
        assert "[**PROJ-456**](https://linear.app/org/issue/PROJ-456)" in response
        # Original plain IDs should not exist
        assert "- PROJ-123:" not in response
        assert "- PROJ-456:" not in response


@pytest.mark.asyncio
async def test_generate_response_without_issue_map(mock_anthropic_response):
    """Test that response works without issue_map (no links added)."""
    # Mock response with plain issue IDs
    mock_response_with_issues = Message(
        id="msg_123",
        type="message",
        role="assistant",
        content=[
            TextBlock(
                type="text",
                text="Issue PROJ-123 is in progress",
            )
        ],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=150, output_tokens=50),
    )

    agent = ConversationAgent(api_key="test_key")

    with patch.object(
        agent.client.messages, "create", return_value=mock_response_with_issues
    ):
        response = await agent.generate_response(
            user_message="What issues do I have?",
            conversation_history=[],
            context=None,
            issue_map=None,  # No issue map provided
        )

        # Response should remain unchanged (no links)
        assert response == "Issue PROJ-123 is in progress"
