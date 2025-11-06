"""Agent SDK wrapper for generating Linear issue briefings."""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from anthropic.types import TextBlock

from linear_chief.utils.logging import get_logger
from linear_chief.utils.markdown import add_clickable_issue_links

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
        # Format issue header WITHOUT links (Claude would remove them anyway)
        # Links will be added in post-processing after briefing generation
        identifier = issue.get("identifier", "N/A")
        title = issue.get("title", "Untitled")

        parts = [
            f"**{identifier}**: {title}",
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
        self,
        issues: List[Dict[str, Any]],
        user_context: Optional[str] = None,
        related_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> str:
        """
        Build the user prompt with issues.

        Args:
            issues: List of issue dictionaries
            user_context: Optional user preferences/context
            related_map: Optional mapping of issue_id -> related_issues

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

        # Add related issues context if provided
        if related_map:
            related_section = "\n\n**RELATED ISSUES DATA:**\n"
            related_section += "Some issues have related work that may be relevant:\n\n"

            for issue_id, related in related_map.items():
                if related:
                    related_section += f"{issue_id} is related to:\n"
                    for rel in related:
                        rel_id = rel.get("issue_id", "Unknown")
                        rel_title = rel.get("title", "")
                        similarity = rel.get("similarity", 0.0)
                        related_section += (
                            f"  - {rel_id}: {rel_title} ({similarity:.0%} similar)\n"
                        )
                    related_section += "\n"

            related_section += (
                "Please mention related issues where relevant in the briefing.\n"
            )
            prompt += related_section

        if user_context:
            prompt = f"User context: {user_context}\n\n{prompt}"

        return prompt

    def _add_clickable_links(self, briefing: str, issues: List[Dict[str, Any]]) -> str:
        """
        Post-process briefing to add clickable links for issue identifiers.

        This is done AFTER Claude generates the briefing because Claude tends
        to remove/modify Markdown links during generation.

        Args:
            briefing: Generated briefing text
            issues: List of issues with URLs

        Returns:
            Briefing with clickable links
        """
        # Build mapping of identifier -> URL
        issue_map = {}
        for issue in issues:
            identifier = issue.get("identifier")
            url = issue.get("url")
            if identifier and url:
                issue_map[identifier] = url

        # Use shared utility to add links
        return add_clickable_issue_links(briefing, issue_map)

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

        # Find related issues for briefing context
        related_map: Dict[str, List[Dict[str, Any]]] = {}
        try:
            from linear_chief.intelligence.related_suggester import (
                RelatedIssuesSuggester,
            )

            suggester = RelatedIssuesSuggester()
            # Find related issues for top 5 issues (avoid overwhelming the prompt)
            related_map = await suggester.add_to_briefing_context(
                issues=issues[:5],
                max_related_per_issue=2,
            )

            logger.info(
                f"Found related issues for {len(related_map)} briefing issues",
                extra={"related_issues_count": len(related_map)},
            )

        except Exception as e:
            logger.error(
                "Failed to find related issues for briefing",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            # Don't fail briefing generation if related issues fails
            related_map = {}

        # Check for duplicates in the issues being briefed
        duplicate_warnings = []
        try:
            from linear_chief.intelligence.duplicate_detector import DuplicateDetector

            detector = DuplicateDetector()
            issue_ids = [
                issue.get("identifier") for issue in issues if issue.get("identifier")
            ]

            # Check each issue for duplicates
            for issue_id in issue_ids:
                dups = await detector.check_issue_for_duplicates(
                    issue_id, min_similarity=0.85
                )
                if dups:
                    duplicate_warnings.extend(dups)

            # Remove duplicate entries (same pair might appear multiple times)
            if duplicate_warnings:
                seen_pairs = set()
                unique_warnings = []
                for dup in duplicate_warnings:
                    pair = tuple(sorted([dup["issue_a"], dup["issue_b"]]))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        unique_warnings.append(dup)
                duplicate_warnings = unique_warnings

            logger.info(
                f"Duplicate detection found {len(duplicate_warnings)} potential duplicates",
                extra={"duplicate_count": len(duplicate_warnings)},
            )

        except Exception as e:
            logger.error(
                "Failed to check for duplicates during briefing generation",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            # Don't fail briefing generation if duplicate detection fails
            duplicate_warnings = []

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self._build_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": self._build_user_prompt(
                            issues, user_context, related_map
                        ),
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

            # Calculate cost
            cost_usd = self.estimate_cost(
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            logger.info(
                f"Briefing generated successfully "
                f"(tokens: {response.usage.input_tokens} in, "
                f"{response.usage.output_tokens} out, "
                f"{response.usage.input_tokens + response.usage.output_tokens} total, "
                f"cost: ${cost_usd:.4f})",
                extra={
                    "service": "Anthropic",
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens
                    + response.usage.output_tokens,
                    "cost_usd": cost_usd,
                    "model": self.model,
                },
            )

            # Post-process: Add clickable links for issue identifiers
            briefing_with_links = self._add_clickable_links(briefing, issues)

            # Append duplicate warnings if any were found
            if duplicate_warnings:
                from linear_chief.intelligence.duplicate_detector import (
                    DuplicateDetector,
                )

                detector = DuplicateDetector()
                duplicate_section = "\n\n---\n\n" + detector.format_duplicate_report(
                    duplicate_warnings
                )

                # Replace emoji placeholders with actual emojis
                duplicate_section = duplicate_section.replace("Warning", "\u26a0\ufe0f")
                duplicate_section = duplicate_section.replace(
                    "Double-arrows", "\u2194\ufe0f"
                )
                duplicate_section = duplicate_section.replace("Bullet", "\u2022")
                duplicate_section = duplicate_section.replace(
                    "Right-arrow", "\u27a1\ufe0f"
                )

                briefing_with_links += duplicate_section

                logger.info(
                    f"Added {len(duplicate_warnings)} duplicate warnings to briefing",
                )

            return briefing_with_links

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
