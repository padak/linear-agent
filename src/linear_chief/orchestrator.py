"""Main orchestrator for briefing generation workflow."""

from typing import Dict, Any
from datetime import datetime
import uuid

from linear_chief.utils.logging import get_logger, LogContext
from linear_chief.linear import LinearClient
from linear_chief.agent import BriefingAgent
from linear_chief.telegram.bot import TelegramBriefingBot
from linear_chief.telegram.application import TelegramApplication
from linear_chief.intelligence import IssueAnalyzer
from linear_chief.memory import MemoryManager, IssueVectorStore
from linear_chief.storage import (
    get_session_maker,
    get_db_session,
    IssueHistoryRepository,
    BriefingRepository,
    MetricsRepository,
)
from linear_chief.config import (
    LINEAR_API_KEY,
    ANTHROPIC_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_MODE,
)

logger = get_logger(__name__)


class BriefingOrchestrator:
    """
    Main orchestrator for daily briefing workflow.

    Coordinates Linear API, Intelligence, Agent SDK, Memory, Storage, and Telegram.
    """

    def __init__(
        self,
        linear_api_key: str = LINEAR_API_KEY,
        anthropic_api_key: str = ANTHROPIC_API_KEY,
        telegram_bot_token: str = TELEGRAM_BOT_TOKEN,
        telegram_chat_id: str = TELEGRAM_CHAT_ID,
        telegram_mode: str = TELEGRAM_MODE,
    ):
        """
        Initialize orchestrator with API credentials.

        Args:
            linear_api_key: Linear API key
            anthropic_api_key: Anthropic API key
            telegram_bot_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            telegram_mode: Telegram mode ("send_only" or "interactive")
        """
        # Initialize clients
        self.linear_client = LinearClient(api_key=linear_api_key)
        self.agent = BriefingAgent(api_key=anthropic_api_key)

        # Initialize Telegram bot based on mode
        self.telegram_mode = telegram_mode
        if telegram_mode == "interactive":
            # Use new bidirectional application
            self.telegram_bot = TelegramApplication(
                bot_token=telegram_bot_token,
                chat_id=telegram_chat_id,
                polling=False,  # Don't start polling in orchestrator
            )
            logger.info("Using interactive Telegram mode (TelegramApplication)")
        else:
            # Use original send-only bot (backward compatible)
            self.telegram_bot = TelegramBriefingBot(
                bot_token=telegram_bot_token,
                chat_id=telegram_chat_id,
            )
            logger.info("Using send-only Telegram mode (TelegramBriefingBot)")

        # Initialize intelligence and memory layers
        self.analyzer = IssueAnalyzer()
        self.memory_manager = MemoryManager()
        self.vector_store = IssueVectorStore()

        # Database session maker
        self.session_maker = get_session_maker()

        logger.info(
            "Orchestrator initialized",
            extra={
                "component": "orchestrator",
                "telegram_mode": telegram_mode,
            },
        )

    async def generate_and_send_briefing(self) -> Dict[str, Any]:
        """
        Execute full briefing workflow.

        Workflow:
        1. Fetch issues from Linear
        2. Analyze issues (priority, stagnation, blocking)
        3. Save issue snapshots to database
        4. Add issues to vector store
        5. Get agent context from memory
        6. Generate briefing via Agent SDK
        7. Send briefing via Telegram (with feedback keyboard if interactive mode)
        8. Archive briefing and metrics to database

        Note on Telegram modes:
        - send_only: Uses TelegramBriefingBot for simple message delivery
        - interactive: Uses TelegramApplication with feedback keyboards and handlers

        Returns:
            Dict with workflow results (success, briefing_id, metrics, error)

        Raises:
            Exception: If critical workflow step fails
        """
        start_time = datetime.utcnow()
        result: Dict[str, Any] = {
            "success": False,
            "briefing_id": None,
            "issue_count": 0,
            "cost_usd": None,
            "duration_seconds": None,
            "error": None,
        }

        # Generate unique request ID for tracking
        request_id = f"briefing-{uuid.uuid4().hex[:8]}"

        with LogContext(request_id=request_id):
            try:
                # Step 1: Fetch issues from Linear
                logger.info(
                    "Step 1/8: Fetching issues from Linear",
                    extra={"step": 1, "total_steps": 8, "operation": "fetch_issues"},
                )
                issues = await self.linear_client.get_my_relevant_issues()
                result["issue_count"] = len(issues)
                logger.info(
                    "Fetched issues from Linear",
                    extra={"issue_count": len(issues), "step": 1},
                )

                if not issues:
                    logger.info("No issues to report")
                    result["success"] = True
                    result["duration_seconds"] = (
                        datetime.utcnow() - start_time
                    ).total_seconds()
                    return result

                # Step 2: Analyze issues
                logger.info("Step 2/8: Analyzing issues with intelligence layer")
                analyzed_issues = []
                for issue in issues:
                    analysis = self.analyzer.analyze_issue(issue)
                    # Attach analysis to issue for context
                    issue["_analysis"] = {
                        "priority": analysis.priority,
                        "is_stagnant": analysis.is_stagnant,
                        "is_blocked": analysis.is_blocked,
                        "insights": analysis.insights,
                    }
                    analyzed_issues.append(issue)

                # Sort by priority (descending)
                analyzed_issues.sort(
                    key=lambda x: x.get("_analysis", {}).get("priority", 0),
                    reverse=True,
                )

                # Step 3: Save issue snapshots to database
                logger.info("Step 3/8: Saving issue snapshots to database")
                for session in get_db_session(self.session_maker):
                    issue_repo = IssueHistoryRepository(session)
                    for issue in analyzed_issues:
                        issue_repo.save_snapshot(
                            issue_id=issue.get("identifier", ""),
                            linear_id=issue.get("id", ""),
                            title=issue.get("title", ""),
                            state=issue.get("state", {}).get("name", ""),
                            priority=issue.get("priority"),
                            assignee_id=(
                                issue.get("assignee", {}).get("id")
                                if issue.get("assignee")
                                else None
                            ),
                            assignee_name=(
                                issue.get("assignee", {}).get("name")
                                if issue.get("assignee")
                                else None
                            ),
                            team_id=(
                                issue.get("team", {}).get("id")
                                if issue.get("team")
                                else None
                            ),
                            team_name=(
                                issue.get("team", {}).get("name")
                                if issue.get("team")
                                else None
                            ),
                            labels=[
                                label.get("name", "")
                                for label in issue.get("labels", {}).get("nodes", [])
                            ],
                            extra_metadata={"analysis": issue.get("_analysis")},
                        )

                # Step 4: Add issues to vector store
                logger.info("Step 4/8: Adding issues to vector store")
                for issue in analyzed_issues:
                    await self.vector_store.add_issue(
                        issue_id=issue.get("identifier", ""),
                        title=issue.get("title", ""),
                        description=issue.get("description", ""),
                        metadata={
                            "state": issue.get("state", {}).get("name", ""),
                            "priority": issue.get("_analysis", {}).get("priority", 0),
                        },
                    )

                # Step 5: Get agent context from memory
                logger.info("Step 5/8: Retrieving agent context from memory")
                memory_context = await self.memory_manager.get_agent_context(days=7)

                # Convert list of context items to string for agent prompt
                agent_context_str = None
                if memory_context:
                    context_parts = []
                    for item in memory_context:
                        if "memory" in item:
                            context_parts.append(item["memory"])
                    agent_context_str = (
                        "\n\n".join(context_parts) if context_parts else None
                    )

                # Step 6: Generate briefing via Agent SDK
                logger.info("Step 6/8: Generating briefing via Agent SDK")
                briefing_content = await self.agent.generate_briefing(
                    issues=analyzed_issues,
                    user_context=agent_context_str,
                )

                # Extract token usage from last API call (approximate)
                # Note: Would need to modify BriefingAgent to return usage stats
                input_tokens = 3000  # Placeholder - should get from agent
                output_tokens = 1000  # Placeholder - should get from agent
                cost_usd = self.agent.estimate_cost(input_tokens, output_tokens)
                result["cost_usd"] = cost_usd

                # Step 7: Send briefing via Telegram
                logger.info("Step 7/8: Sending briefing via Telegram")

                # Note: briefing_id not available yet - will be created in Step 8
                # For interactive mode, we'll update the briefing record after creation
                telegram_success = await self.telegram_bot.send_briefing(
                    briefing_content
                )

                # Step 8: Archive briefing and metrics to database
                logger.info("Step 8/8: Archiving briefing and metrics to database")
                for session in get_db_session(self.session_maker):
                    briefing_repo = BriefingRepository(session)
                    metrics_repo = MetricsRepository(session)

                    # Create briefing record
                    briefing = briefing_repo.create_briefing(
                        content=briefing_content,
                        issue_count=len(issues),
                        agent_context=(
                            {"context": agent_context_str}
                            if agent_context_str
                            else None
                        ),
                        cost_usd=cost_usd,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        model_name=self.agent.model,
                        extra_metadata={
                            "analyzed_issues_count": len(analyzed_issues),
                            "high_priority_count": sum(
                                1
                                for i in analyzed_issues
                                if i.get("_analysis", {}).get("priority", 0) >= 8
                            ),
                        },
                    )

                    result["briefing_id"] = int(briefing.id)

                    # Mark delivery status
                    if telegram_success:
                        # Cast Column[int] to int for type checker
                        briefing_repo.mark_as_sent(int(briefing.id))
                    else:
                        briefing_repo.mark_as_failed(
                            int(briefing.id), "Telegram delivery failed"
                        )

                    # Record metrics
                    metrics_repo.record_metric(
                        metric_type="briefing_generated",
                        metric_name="daily_briefing",
                        value=1,
                        unit="count",
                        extra_metadata={
                            "issue_count": len(issues),
                            "cost_usd": cost_usd,
                            "telegram_success": telegram_success,
                        },
                    )

                    metrics_repo.record_metric(
                        metric_type="api_cost",
                        metric_name="anthropic_briefing",
                        value=cost_usd,
                        unit="usd",
                        extra_metadata={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "model": self.agent.model,
                        },
                    )

                # Add briefing to memory for future context
                await self.memory_manager.add_briefing_context(
                    briefing_content,
                    metadata={
                        "timestamp": datetime.utcnow().isoformat(),
                        "issue_count": len(issues),
                    },
                )

                # Success!
                result["success"] = True
                result["duration_seconds"] = (
                    datetime.utcnow() - start_time
                ).total_seconds()

                logger.info(
                    f"Briefing workflow completed successfully. "
                    f"ID: {result['briefing_id']}, Issues: {len(issues)}, "
                    f"Cost: ${cost_usd:.4f}, Duration: {result['duration_seconds']:.2f}s"
                )

                return result

            except Exception as e:
                error_msg = f"Briefing workflow failed: {e}"
                logger.error(error_msg, exc_info=True)
                result["error"] = str(e)

                # Try to record failure in database
                try:
                    for session in get_db_session(self.session_maker):
                        metrics_repo = MetricsRepository(session)
                        metrics_repo.record_metric(
                            metric_type="briefing_error",
                            metric_name="workflow_failure",
                            value=1,
                            unit="count",
                            extra_metadata={"error": str(e)},
                        )
                except Exception as db_error:
                    logger.error(f"Failed to record error metric: {db_error}")

                raise

    async def test_connections(self) -> Dict[str, bool]:
        """
        Test all external service connections.

        Returns:
            Dict with service names and connection status
        """
        results = {}

        # Test Linear connection
        try:
            viewer = await self.linear_client.get_viewer()
            results["linear"] = viewer is not None
            logger.info(f"Linear connection: {'OK' if results['linear'] else 'FAILED'}")
        except Exception as e:
            logger.error(f"Linear connection failed: {e}")
            results["linear"] = False

        # Test Telegram connection
        try:
            results["telegram"] = await self.telegram_bot.test_connection()
            logger.info(
                f"Telegram connection: {'OK' if results['telegram'] else 'FAILED'}"
            )
        except Exception as e:
            logger.error(f"Telegram connection failed: {e}")
            results["telegram"] = False

        return results
