"""Conversation agent for handling user queries using Claude API."""

from typing import List, Dict, Optional
from anthropic import Anthropic
from anthropic.types import TextBlock

from linear_chief.config import CONVERSATION_MAX_HISTORY
from linear_chief.utils.logging import get_logger
from linear_chief.utils.markdown import add_clickable_issue_links

logger = get_logger(__name__)


class ConversationAgent:
    """Agent for handling conversational queries using Claude.

    This agent provides intelligent responses to user questions about their
    Linear issues, briefings, and work progress. It maintains conversation
    context and uses Claude's language understanding to provide helpful,
    action-oriented responses.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the conversation agent.

        Args:
            api_key: Anthropic API key
            model: Claude model to use for generation
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for conversation agent.

        Returns:
            System prompt string
        """
        from linear_chief.config import LINEAR_USER_NAME, LINEAR_USER_EMAIL

        # Add user identity info to system prompt
        user_context = ""
        if LINEAR_USER_NAME:
            user_context = f"\n\n**User Identity:**\nYou are assisting {LINEAR_USER_NAME}"
            if LINEAR_USER_EMAIL:
                user_context += f" ({LINEAR_USER_EMAIL})"
            user_context += ".\nWhen the user says 'my issues', 'assigned to me', or similar, filter for this user."

        return f"""You are an AI Chief of Staff assistant for Linear project management.{user_context}

Your role:
- Answer questions about Linear issues, status, and progress
- Provide information from recent briefings
- Help users understand their work priorities
- Be direct and professional

Capabilities:
- Access to recent issue updates (last 30 days)
- Access to recent briefings (last 7 days)
- Can search for specific issues by ID or keywords
- Can answer questions about issue status, priorities, blockers

Guidelines:
- Keep responses under 3 paragraphs
- Reference specific issues when relevant (use issue IDs)
- When asked about briefings, provide the most recent one or summarize multiple
- If you don't have enough context, ask clarifying questions
- Focus on what's most helpful for the user right now

Common queries you should handle:
- "Show me today's briefing" -> Return the latest briefing content
- "What was in the last briefing?" -> Summarize recent briefing
- "Summarize briefings from this week" -> Aggregate multiple briefings
- "What are the blocked issues?" -> Extract from briefing context"""

    def _build_messages(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build messages array for Claude API.

        Args:
            user_message: User's current question
            conversation_history: Previous messages [{"role": "user", "content": "..."}, ...]
            context: Optional context about issues, briefings, etc.

        Returns:
            Messages array for Claude API
        """
        messages = []

        # Add conversation history (configurable limit via CONVERSATION_MAX_HISTORY)
        # History should already be in chronological order (oldest first)
        for msg in conversation_history[-CONVERSATION_MAX_HISTORY:]:
            messages.append(msg)

        # Build current message with context
        current_content = user_message
        if context:
            current_content = f"""Context Information:
{context}

---

User Question: {user_message}"""

        messages.append({"role": "user", "content": current_content})

        return messages

    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context: Optional[str] = None,
        max_tokens: int = 1000,
        issue_map: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate intelligent response to user query.

        Args:
            user_message: User's question/query
            conversation_history: List of previous messages
            context: Optional context (recent issues, briefings, etc.)
            max_tokens: Maximum tokens for response (default: 1000 for concise answers)
            issue_map: Optional mapping of issue identifier -> URL for clickable links

        Returns:
            Generated response text with clickable issue links

        Raises:
            Exception: If API call fails
        """
        logger.info(
            "Generating conversation response",
            extra={
                "service": "Anthropic",
                "model": self.model,
                "message_length": len(user_message),
                "history_length": len(conversation_history),
                "has_context": context is not None,
            },
        )

        try:
            messages = self._build_messages(user_message, conversation_history, context)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self._build_system_prompt(),
                messages=messages,
            )

            # Type guard: ensure we have a TextBlock with text content
            content_block = response.content[0]
            if isinstance(content_block, TextBlock):
                response_text = content_block.text
            else:
                logger.error(
                    "Unexpected content type from Anthropic API",
                    extra={
                        "service": "Anthropic",
                        "expected_type": "TextBlock",
                        "actual_type": type(content_block).__name__,
                    },
                )
                raise ValueError(f"Expected TextBlock, got {type(content_block)}")

            # Calculate cost
            cost_usd = self.estimate_cost(
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            logger.info(
                f"Conversation response generated successfully "
                f"(tokens: {response.usage.input_tokens} in, "
                f"{response.usage.output_tokens} out, "
                f"{response.usage.input_tokens + response.usage.output_tokens} total, "
                f"cost: ${cost_usd:.4f})",
                extra={
                    "service": "Anthropic",
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                    "cost_usd": cost_usd,
                    "model": self.model,
                    "response_length": len(response_text),
                },
            )

            # Post-process: Add clickable links for issue identifiers
            if issue_map:
                response_text = add_clickable_issue_links(response_text, issue_map)

            return response_text

        except Exception as e:
            logger.error(
                "Failed to generate conversation response",
                extra={
                    "service": "Anthropic",
                    "error_type": type(e).__name__,
                    "model": self.model,
                },
                exc_info=True,
            )
            raise

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost of API call.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD

        Note: Pricing for Claude Sonnet 4 (as of Nov 2024):
            - Input: $3.00 per million tokens
            - Output: $15.00 per million tokens
        """
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost
