"""mem0 wrapper for persistent agent memory and user preference learning."""

import logging
from datetime import datetime, timedelta
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import MEM0_API_KEY

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages persistent agent memory using mem0.

    Handles agent context (previous briefings, conversation history) and
    user preferences (topics of interest, team preferences). Falls back to
    in-memory storage if mem0 API key is not configured.
    """

    def __init__(self) -> None:
        """Initialize MemoryManager with mem0 client or in-memory fallback."""
        self._use_mem0 = bool(MEM0_API_KEY)
        self._memory_store: list[dict[str, Any]] = []  # In-memory fallback

        if self._use_mem0:
            try:
                import os
                from mem0 import Memory
                from mem0.configs.base import MemoryConfig
                from ..config import OPENAI_API_KEY, MEM0_PATH

                # Set OpenAI API key for embeddings
                if OPENAI_API_KEY and "OPENAI_API_KEY" not in os.environ:
                    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

                # Configure mem0 to use custom storage path from .env
                memory_config = MemoryConfig(
                    vector_store={
                        "provider": "qdrant",
                        "config": {
                            "collection_name": "mem0",
                            "path": str(MEM0_PATH),
                        },
                    },
                    history_db_path=str(MEM0_PATH / "history.db"),  # Use .env path
                )

                self._client = Memory(config=memory_config)
                logger.info(f"mem0 initialized with local storage at {MEM0_PATH}")
            except ImportError:
                logger.warning("mem0 library not installed, using in-memory fallback")
                self._use_mem0 = False
            except Exception as e:
                logger.error(f"Failed to initialize mem0 client: {e}", exc_info=True)
                logger.info("Falling back to in-memory storage")
                self._use_mem0 = False
        else:
            logger.info("MEM0_API_KEY not set, using in-memory storage")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def add_briefing_context(
        self, briefing: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Add a briefing to agent memory for future context.

        Args:
            briefing: The briefing text content.
            metadata: Optional metadata (timestamp, issue count, etc.).

        Raises:
            Exception: If mem0 API call fails after retries.
        """
        metadata = metadata or {}
        metadata["type"] = "briefing"
        metadata["timestamp"] = datetime.utcnow().isoformat()

        if self._use_mem0:
            try:
                self._client.add(
                    messages=[{"role": "assistant", "content": briefing}],
                    user_id="linear_chief_agent",
                    metadata=metadata,
                )
                logger.info("Briefing context added to mem0")
            except Exception as e:
                logger.error(f"Failed to add briefing to mem0: {e}", exc_info=True)
                raise
        else:
            # In-memory fallback
            self._memory_store.append(
                {"content": briefing, "metadata": metadata, "type": "briefing"}
            )
            logger.debug("Briefing context added to in-memory store")

    async def get_agent_context(self, days: int = 7) -> list[dict[str, Any]]:
        """Retrieve agent context from the last N days.

        Args:
            days: Number of days of history to retrieve.

        Returns:
            List of context items (briefings, interactions) with metadata.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        if self._use_mem0:
            try:
                memories = self._client.get_all(user_id="linear_chief_agent")
                # mem0 0.1.19+ returns list directly, not dict with "results"
                memory_list = (
                    memories
                    if isinstance(memories, list)
                    else memories.get("results", [])
                )

                # Filter by date and type
                filtered = [
                    mem
                    for mem in memory_list
                    if datetime.fromisoformat(
                        mem.get("metadata", {}).get("timestamp", "1970-01-01")
                    )
                    > cutoff_date
                    and mem.get("metadata", {}).get("type") == "briefing"
                ]
                logger.info(f"Retrieved {len(filtered)} context items from mem0")
                return filtered
            except Exception as e:
                logger.error(
                    f"Failed to retrieve context from mem0: {e}", exc_info=True
                )
                return []
        else:
            # In-memory fallback
            filtered = [
                item
                for item in self._memory_store
                if datetime.fromisoformat(item["metadata"]["timestamp"]) > cutoff_date
                and item["type"] == "briefing"
            ]
            logger.debug(
                f"Retrieved {len(filtered)} context items from in-memory store"
            )
            return filtered

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def add_user_preference(
        self, preference: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Add a user preference to memory.

        Args:
            preference: Preference description (e.g., "Focus on blocking issues").
            metadata: Optional metadata (category, priority, etc.).

        Raises:
            Exception: If mem0 API call fails after retries.
        """
        metadata = metadata or {}
        metadata["type"] = "preference"
        metadata["timestamp"] = datetime.utcnow().isoformat()

        if self._use_mem0:
            try:
                self._client.add(
                    messages=[{"role": "user", "content": preference}],
                    user_id="linear_chief_user",
                    metadata=metadata,
                )
                logger.info("User preference added to mem0")
            except Exception as e:
                logger.error(f"Failed to add preference to mem0: {e}", exc_info=True)
                raise
        else:
            # In-memory fallback
            self._memory_store.append(
                {"content": preference, "metadata": metadata, "type": "preference"}
            )
            logger.debug("User preference added to in-memory store")

    async def get_user_preferences(self) -> list[dict[str, Any]]:
        """Retrieve all user preferences.

        Returns:
            List of user preferences with metadata.
        """
        if self._use_mem0:
            try:
                memories = self._client.get_all(user_id="linear_chief_user")
                # mem0 0.1.19+ returns list directly, not dict with "results"
                memory_list = (
                    memories
                    if isinstance(memories, list)
                    else memories.get("results", [])
                )

                preferences = [
                    mem
                    for mem in memory_list
                    if mem.get("metadata", {}).get("type") == "preference"
                ]
                logger.info(f"Retrieved {len(preferences)} preferences from mem0")
                return preferences
            except Exception as e:
                logger.error(
                    f"Failed to retrieve preferences from mem0: {e}", exc_info=True
                )
                return []
        else:
            # In-memory fallback
            preferences = [
                item for item in self._memory_store if item["type"] == "preference"
            ]
            logger.debug(
                f"Retrieved {len(preferences)} preferences from in-memory store"
            )
            return preferences
