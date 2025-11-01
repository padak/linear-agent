"""Integration tests for Briefing Agent (Anthropic Messages API wrapper)."""

import pytest
from unittest.mock import Mock, patch
from anthropic.types import TextBlock

from linear_chief.agent import BriefingAgent


@pytest.fixture
def api_key():
    """Test Anthropic API key."""
    return "sk-ant-test-key-12345"


@pytest.fixture
def sample_issues():
    """Sample Linear issues for testing."""
    return [
        {
            "id": "issue-uuid-1",
            "identifier": "PROJ-123",
            "title": "Fix critical login bug",
            "description": "Users cannot log in after password reset. This is affecting production users.",
            "state": {"name": "In Progress"},
            "priority": 1,
            "priorityLabel": "Urgent",
            "assignee": {"id": "user-1", "name": "John Doe"},
            "team": {"id": "team-1", "name": "Engineering"},
            "updatedAt": "2024-01-15T14:30:00Z",
            "labels": {"nodes": [{"name": "bug"}, {"name": "urgent"}]},
            "comments": {
                "nodes": [
                    {
                        "id": "comment-1",
                        "body": "Working on a fix, will deploy today",
                        "user": {"name": "John Doe"},
                        "createdAt": "2024-01-15T13:00:00Z",
                    }
                ]
            },
        },
        {
            "id": "issue-uuid-2",
            "identifier": "PROJ-124",
            "title": "Add dark mode support",
            "description": "Implement dark mode theme across the application",
            "state": {"name": "Todo"},
            "priority": 3,
            "priorityLabel": "Normal",
            "assignee": None,
            "team": {"id": "team-1", "name": "Engineering"},
            "updatedAt": "2024-01-10T09:00:00Z",
            "labels": {"nodes": [{"name": "feature"}]},
            "comments": {"nodes": []},
        },
        {
            "id": "issue-uuid-3",
            "identifier": "PROJ-125",
            "title": "Update documentation",
            "description": "Update API documentation with new endpoints",
            "state": {"name": "Done"},
            "priority": 4,
            "priorityLabel": "Low",
            "assignee": {"id": "user-2", "name": "Jane Smith"},
            "team": {"id": "team-2", "name": "Docs"},
            "updatedAt": "2024-01-14T16:00:00Z",
            "labels": {"nodes": [{"name": "docs"}]},
            "comments": {"nodes": []},
        },
    ]


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    mock_response = Mock()
    # Create a proper TextBlock mock
    text_content = "**Key Issues Requiring Attention**\n\n1. PROJ-123: Critical login bug needs immediate attention\n\n**Status Summary**\n\nTeam is making progress on critical issues.\n\n**Blockers & Risks**\n\nNone identified.\n\n**Quick Wins**\n\nPROJ-125 documentation is already done."
    mock_text_block = Mock(spec=TextBlock)
    mock_text_block.text = text_content
    mock_text_block.type = "text"

    mock_response.content = [mock_text_block]
    mock_response.usage = Mock(input_tokens=1500, output_tokens=200)
    mock_response.stop_reason = "end_turn"
    return mock_response


@pytest.mark.asyncio
class TestBriefingAgentGeneration:
    """Tests for generate_briefing method."""

    async def test_generate_briefing_success(
        self, api_key, sample_issues, mock_anthropic_response
    ):
        """Test successful briefing generation with issues."""
        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_anthropic_response
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key)
            briefing = await agent.generate_briefing(sample_issues)

            # Verify briefing was generated
            assert "Key Issues Requiring Attention" in briefing
            assert "PROJ-123" in briefing
            assert "Critical login bug" in briefing

            # Verify API was called correctly
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args

            # Check model
            assert call_args[1]["model"] == "claude-sonnet-4-20250514"

            # Check system prompt
            assert "Chief of Staff" in call_args[1]["system"]

            # Check user prompt contains issues
            user_message = call_args[1]["messages"][0]
            assert user_message["role"] == "user"
            assert "PROJ-123" in user_message["content"]
            assert "PROJ-124" in user_message["content"]
            assert "PROJ-125" in user_message["content"]

    async def test_generate_briefing_with_user_context(
        self, api_key, sample_issues, mock_anthropic_response
    ):
        """Test briefing generation with user context."""
        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_anthropic_response
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key)
            user_context = "Focus on urgent items only, I have a meeting at 2pm"
            briefing = await agent.generate_briefing(
                sample_issues, user_context=user_context
            )

            assert briefing is not None

            # Verify user context was included in prompt
            call_args = mock_client.messages.create.call_args
            user_message = call_args[1]["messages"][0]["content"]
            assert "Focus on urgent items only" in user_message
            assert "meeting at 2pm" in user_message

    async def test_generate_briefing_without_user_context(
        self, api_key, sample_issues, mock_anthropic_response
    ):
        """Test briefing generation without user context."""
        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_anthropic_response
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key)
            briefing = await agent.generate_briefing(sample_issues, user_context=None)

            assert briefing is not None

            # Verify no user context in prompt
            call_args = mock_client.messages.create.call_args
            user_message = call_args[1]["messages"][0]["content"]
            # Should not start with "User context:"
            assert not user_message.startswith("User context:")

    async def test_generate_briefing_empty_issues(self, api_key):
        """Test briefing generation with no issues."""
        agent = BriefingAgent(api_key)
        briefing = await agent.generate_briefing([])

        # Should return default message
        assert briefing == "No issues to report today. All clear!"

    async def test_generate_briefing_custom_max_tokens(
        self, api_key, sample_issues, mock_anthropic_response
    ):
        """Test briefing generation with custom max_tokens."""
        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_anthropic_response
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key)
            briefing = await agent.generate_briefing(sample_issues, max_tokens=1000)

            assert briefing is not None

            # Verify max_tokens was passed
            call_args = mock_client.messages.create.call_args
            assert call_args[1]["max_tokens"] == 1000

    async def test_generate_briefing_api_error(self, api_key, sample_issues):
        """Test briefing generation when API returns error."""
        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception(
                "API rate limit exceeded"
            )
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key)

            with pytest.raises(Exception, match="API rate limit exceeded"):
                await agent.generate_briefing(sample_issues)

    async def test_generate_briefing_authentication_error(self, api_key, sample_issues):
        """Test briefing generation with invalid API key."""
        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("Invalid API key")
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key)

            with pytest.raises(Exception, match="Invalid API key"):
                await agent.generate_briefing(sample_issues)

    async def test_generate_briefing_network_error(self, api_key, sample_issues):
        """Test briefing generation with network error."""
        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("Connection timeout")
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key)

            with pytest.raises(Exception, match="Connection timeout"):
                await agent.generate_briefing(sample_issues)


@pytest.mark.asyncio
class TestBriefingAgentPromptBuilding:
    """Tests for prompt building methods."""

    def test_format_issue_complete(self, api_key, sample_issues):
        """Test formatting issue with all fields present."""
        agent = BriefingAgent(api_key)
        formatted = agent._format_issue(sample_issues[0])

        # Verify all key fields are present
        assert "PROJ-123" in formatted
        assert "Fix critical login bug" in formatted
        assert "In Progress" in formatted
        assert "Urgent" in formatted
        assert "John Doe" in formatted
        assert "Engineering" in formatted
        assert "2024-01-15" in formatted
        assert "Users cannot log in" in formatted
        assert "Working on a fix" in formatted

    def test_format_issue_minimal(self, api_key):
        """Test formatting issue with minimal fields."""
        agent = BriefingAgent(api_key)
        minimal_issue = {
            "id": "issue-uuid-99",
            "identifier": "PROJ-999",
            "title": "Minimal issue",
        }
        formatted = agent._format_issue(minimal_issue)

        assert "PROJ-999" in formatted
        assert "Minimal issue" in formatted
        # Should handle missing fields gracefully
        assert "Unknown" in formatted or "None" in formatted

    def test_format_issue_long_description(self, api_key):
        """Test formatting issue with long description (should truncate)."""
        agent = BriefingAgent(api_key)
        long_description = "A" * 400  # 400 characters
        issue = {
            "identifier": "PROJ-200",
            "title": "Long issue",
            "description": long_description,
            "state": {"name": "Todo"},
            "priorityLabel": "Normal",
        }
        formatted = agent._format_issue(issue)

        # Should truncate to 300 chars + "..."
        assert "..." in formatted
        assert (
            len(formatted) < len(long_description) + 200
        )  # Some overhead for other fields

    def test_format_issue_no_assignee(self, api_key, sample_issues):
        """Test formatting issue with no assignee."""
        agent = BriefingAgent(api_key)
        formatted = agent._format_issue(sample_issues[1])  # PROJ-124 has no assignee

        assert "PROJ-124" in formatted
        assert "Add dark mode support" in formatted
        # Should not include "Assignee:" line
        lines = formatted.split("\n")
        assert not any("Assignee:" in line for line in lines)

    def test_format_issue_with_latest_comment(self, api_key, sample_issues):
        """Test formatting issue includes latest comment."""
        agent = BriefingAgent(api_key)
        formatted = agent._format_issue(sample_issues[0])

        assert "Latest comment" in formatted
        assert "John Doe" in formatted
        assert "Working on a fix" in formatted

    def test_format_issue_no_comments(self, api_key, sample_issues):
        """Test formatting issue with no comments."""
        agent = BriefingAgent(api_key)
        formatted = agent._format_issue(sample_issues[1])  # PROJ-124 has no comments

        # Should not include comment section
        assert "Latest comment" not in formatted

    def test_build_system_prompt(self, api_key):
        """Test system prompt construction."""
        agent = BriefingAgent(api_key)
        system_prompt = agent._build_system_prompt()

        # Verify key elements of system prompt
        assert "Chief of Staff" in system_prompt
        assert "Linear issues" in system_prompt
        assert "actionable" in system_prompt
        assert "briefings" in system_prompt
        # Should mention key responsibilities
        assert (
            "immediate attention" in system_prompt
            or "blockers" in system_prompt.lower()
        )

    def test_build_user_prompt_multiple_issues(self, api_key, sample_issues):
        """Test user prompt with multiple issues."""
        agent = BriefingAgent(api_key)
        user_prompt = agent._build_user_prompt(sample_issues)

        # Verify prompt structure
        assert f"Analyze these {len(sample_issues)} Linear issues" in user_prompt
        assert "PROJ-123" in user_prompt
        assert "PROJ-124" in user_prompt
        assert "PROJ-125" in user_prompt

        # Verify sections
        assert "Key Issues Requiring Attention" in user_prompt
        assert "Status Summary" in user_prompt
        assert "Blockers & Risks" in user_prompt
        assert "Quick Wins" in user_prompt

    def test_build_user_prompt_with_context(self, api_key, sample_issues):
        """Test user prompt includes user context."""
        agent = BriefingAgent(api_key)
        context = "I'm focused on bugs today"
        user_prompt = agent._build_user_prompt(sample_issues, user_context=context)

        # Context should appear before issues
        assert user_prompt.startswith("User context: I'm focused on bugs today")

    def test_build_user_prompt_without_context(self, api_key, sample_issues):
        """Test user prompt without user context."""
        agent = BriefingAgent(api_key)
        user_prompt = agent._build_user_prompt(sample_issues, user_context=None)

        # Should not include context line
        assert not user_prompt.startswith("User context:")

    def test_build_user_prompt_single_issue(self, api_key, sample_issues):
        """Test user prompt with single issue."""
        agent = BriefingAgent(api_key)
        user_prompt = agent._build_user_prompt([sample_issues[0]])

        assert "Analyze these 1 Linear issues" in user_prompt
        assert "PROJ-123" in user_prompt


@pytest.mark.asyncio
class TestBriefingAgentCostEstimation:
    """Tests for cost estimation functionality."""

    def test_estimate_cost_typical_briefing(self, api_key):
        """Test cost estimation for typical briefing."""
        agent = BriefingAgent(api_key)

        # Typical briefing: ~1500 input tokens, ~200 output tokens
        cost = agent.estimate_cost(input_tokens=1500, output_tokens=200)

        # Expected: (1500/1M * $3) + (200/1M * $15) = $0.0045 + $0.003 = $0.0075
        expected = 0.0075
        assert abs(cost - expected) < 0.0001  # Allow small floating point difference

    def test_estimate_cost_large_briefing(self, api_key):
        """Test cost estimation for large briefing."""
        agent = BriefingAgent(api_key)

        # Large briefing: 5000 input, 1000 output
        cost = agent.estimate_cost(input_tokens=5000, output_tokens=1000)

        # Expected: (5000/1M * $3) + (1000/1M * $15) = $0.015 + $0.015 = $0.03
        expected = 0.03
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_small_briefing(self, api_key):
        """Test cost estimation for small briefing."""
        agent = BriefingAgent(api_key)

        # Small briefing: 500 input, 100 output
        cost = agent.estimate_cost(input_tokens=500, output_tokens=100)

        # Expected: (500/1M * $3) + (100/1M * $15) = $0.0015 + $0.0015 = $0.003
        expected = 0.003
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_zero_tokens(self, api_key):
        """Test cost estimation with zero tokens."""
        agent = BriefingAgent(api_key)
        cost = agent.estimate_cost(input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_estimate_cost_only_input_tokens(self, api_key):
        """Test cost estimation with only input tokens."""
        agent = BriefingAgent(api_key)
        cost = agent.estimate_cost(input_tokens=1000, output_tokens=0)

        # Expected: (1000/1M * $3) = $0.003
        expected = 0.003
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_only_output_tokens(self, api_key):
        """Test cost estimation with only output tokens."""
        agent = BriefingAgent(api_key)
        cost = agent.estimate_cost(input_tokens=0, output_tokens=500)

        # Expected: (500/1M * $15) = $0.0075
        expected = 0.0075
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_pricing_accuracy(self, api_key):
        """Test that pricing matches documented rates."""
        agent = BriefingAgent(api_key)

        # 1 million input tokens
        input_cost = agent.estimate_cost(input_tokens=1_000_000, output_tokens=0)
        assert abs(input_cost - 3.00) < 0.0001

        # 1 million output tokens
        output_cost = agent.estimate_cost(input_tokens=0, output_tokens=1_000_000)
        assert abs(output_cost - 15.00) < 0.0001


@pytest.mark.asyncio
class TestBriefingAgentCustomModel:
    """Tests for custom model configuration."""

    async def test_custom_model_initialization(self):
        """Test agent initialization with custom model."""
        custom_model = "claude-3-5-sonnet-20241022"
        agent = BriefingAgent(api_key="test-key", model=custom_model)

        assert agent.model == custom_model

    async def test_custom_model_used_in_api_call(
        self, sample_issues, mock_anthropic_response
    ):
        """Test that custom model is used in API calls."""
        custom_model = "claude-3-5-sonnet-20241022"

        with patch("linear_chief.agent.briefing_agent.Anthropic") as MockAnthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_anthropic_response
            MockAnthropic.return_value = mock_client

            agent = BriefingAgent(api_key="test-key", model=custom_model)
            await agent.generate_briefing(sample_issues)

            # Verify custom model was used
            call_args = mock_client.messages.create.call_args
            assert call_args[1]["model"] == custom_model
