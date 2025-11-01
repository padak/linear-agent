"""Agent SDK wrapper for generating Linear issue briefings."""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from anthropic.types import TextBlock

from linear_chief.utils.logging import get_logger

logger = get_logger(__name__)


class BriefingAgent:
    """Agent for generating intelligent briefings from Linear issues using Claude."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the briefing agent.

        Args:
            api_key: Anthropic API key
            model: Claude model to use for generation
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def _format_issue(self, issue: Dict[str, Any]) -> str:
        """
        Format a single issue for the prompt.

        Args:
            issue: Issue dictionary from Linear API

        Returns:
            Formatted issue string
        """
        parts = [
            f"**{issue.get('identifier', 'N/A')}**: {issue.get('title', 'Untitled')}",
            f"Status: {issue.get('state', {}).get('name', 'Unknown')}",
            f"Priority: {issue.get('priorityLabel', 'None')}",
        ]

        assignee = issue.get("assignee")
        if assignee:
            parts.append(f"Assignee: {assignee.get('name', 'Unknown')}")

        team = issue.get("team")
        if team:
            parts.append(f"Team: {team.get('name', 'Unknown')}")

        updated_at = issue.get("updatedAt", "")
        if updated_at:
            parts.append(f"Last updated: {updated_at[:10]}")

        description = issue.get("description", "")
        if description:
            # Truncate long descriptions
            description = (
                description[:300] + "..." if len(description) > 300 else description
            )
            parts.append(f"Description: {description}")

        # Add recent comments
        comments = issue.get("comments", {}).get("nodes", [])
        if comments:
            latest_comment = comments[-1]
            comment_text = latest_comment.get("body", "")[:150]
            comment_author = latest_comment.get("user", {}).get("name", "Unknown")
            parts.append(f"Latest comment ({comment_author}): {comment_text}")

        return "\n".join(parts)

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the agent.

        Returns:
            System prompt string
        """
        return """You are an AI Chief of Staff assistant analyzing Linear issues to provide actionable daily briefings.

Your role is to:
1. Identify issues that need immediate attention (blocked, stale, high priority)
2. Provide concise summaries focusing on status and next actions
3. Highlight potential risks and dependencies
4. Be direct and action-oriented

Guidelines:
- Keep summaries to 1-2 sentences per issue
- Focus on what needs to happen next, not history
- Flag blockers and delays explicitly
- Use clear, professional language
- Prioritize by impact, not just priority labels"""

    def _build_user_prompt(
        self, issues: List[Dict[str, Any]], user_context: Optional[str] = None
    ) -> str:
        """
        Build the user prompt with issues.

        Args:
            issues: List of issue dictionaries
            user_context: Optional user preferences/context

        Returns:
            User prompt string
        """
        formatted_issues = "\n\n---\n\n".join(
            [self._format_issue(issue) for issue in issues]
        )

        prompt = f"""Analyze these {len(issues)} Linear issues and create a morning briefing.

{formatted_issues}

Please provide:
1. **Key Issues Requiring Attention** (3-5 most critical)
2. **Status Summary** (brief overview of progress)
3. **Blockers & Risks** (anything preventing progress)
4. **Quick Wins** (easy tasks that can be completed today)

Keep it concise and actionable. Focus on what I need to know and do today."""

        if user_context:
            prompt = f"User context: {user_context}\n\n{prompt}"

        return prompt

    async def generate_briefing(
        self,
        issues: List[Dict[str, Any]],
        user_context: Optional[str] = None,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate a briefing from Linear issues.

        Args:
            issues: List of issue dictionaries from Linear API
            user_context: Optional user context/preferences
            max_tokens: Maximum tokens for the response

        Returns:
            Generated briefing text
        """
        if not issues:
            return "No issues to report today. All clear!"

        logger.info(
            "Generating briefing",
            extra={
                "service": "Anthropic",
                "model": self.model,
                "issue_count": len(issues),
                "max_tokens": max_tokens,
            },
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self._build_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": self._build_user_prompt(issues, user_context),
                    }
                ],
            )

            # Type guard: ensure we have a TextBlock with text content
            content_block = response.content[0]
            if isinstance(content_block, TextBlock):
                briefing = content_block.text
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

            logger.info(
                "Briefing generated successfully",
                extra={
                    "service": "Anthropic",
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens
                    + response.usage.output_tokens,
                    "model": self.model,
                },
            )

            return briefing

        except Exception as e:
            logger.error(
                "Failed to generate briefing",
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
