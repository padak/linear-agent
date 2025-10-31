# Data Models

## Issue

**Purpose:** Represents a Linear issue being tracked by the agent. Stores metadata needed for stagnation detection and change tracking.

**Key Attributes:**
- `linear_id`: string - Linear's unique issue identifier (e.g., "ENG-123")
- `title`: string - Issue title
- `state`: string - Current state (e.g., "In Progress", "Done", "Blocked")
- `assignee_id`: string (nullable) - Linear user ID of assignee
- `labels`: JSON array - Issue labels (e.g., ["Blocked", "High Priority"])
- `updated_at`: datetime - Last update timestamp from Linear
- `last_seen_at`: datetime - When our agent last processed this issue
- `description`: text (nullable) - Issue description (truncated for token limits)
- `created_at`: datetime - When record was created in our DB

**Relationships:**
- One issue can appear in multiple briefings (one-to-many with `Briefing` via junction table)

## Briefing

**Purpose:** Tracks generated briefings for cost analysis, debugging, and historical reference. Also stores agent context for continuity across briefing cycles.

**Key Attributes:**
- `id`: integer - Primary key
- `generated_at`: datetime - When briefing was created
- `issue_count`: integer - Number of issues included in briefing
- `tokens_used`: integer - Total tokens consumed by Anthropic API
- `cost_usd`: decimal - Estimated cost in USD
- `telegram_message_id`: string (nullable) - Telegram message ID if delivered
- `delivery_status`: enum - "pending", "sent", "failed", "permanently_failed"
- `error_message`: text (nullable) - Error details if delivery failed
- `agent_context`: JSON (nullable) - Agent memory for continuity (last briefing narrative, follow-up flags, notes for next cycle)

**Relationships:**
- Many-to-many with `Issue` (briefing can include multiple issues, issue can appear in multiple briefings)

---

## Data Ownership Table (MVP)

This table defines **source of truth** for all data types in MVP. Eliminates ambiguity about where data lives and who owns it.

| Data Type | Storage | Purpose | Lifecycle | Source of Truth |
|-----------|---------|---------|-----------|-----------------|
| **Linear Issue Metadata** | SQLite `issues` table | Cache of Linear issue data for analysis | Synced every briefing cycle, 30-day retention | Linear API (external) |
| **Briefing History** | SQLite `briefings` table | Record of generated briefings with cost/token data | Permanent retention | Linear Chief of Staff (internal) |
| **Agent Context** | SQLite `briefings.agent_context` JSON | Last 7 days of briefing narratives for continuity | 7-day rolling window | Linear Chief of Staff (internal) |
| **Issue-Briefing Relationships** | SQLite `briefing_issues` junction table | Which issues appeared in which briefings | Permanent retention | Linear Chief of Staff (internal) |

**Key Principles:**
- **Single Source of Truth:** SQLite is the ONLY data store for MVP. No ChromaDB, no mem0, no external databases.
- **Linear API is External Source:** Issue data is fetched from Linear, cached in SQLite, but Linear remains canonical source.
- **No Duplicated Data:** Each piece of data lives in exactly one place.
- **Clear Ownership:** Linear Chief of Staff owns briefings and agent context. Linear owns issue data.

## Data Ownership Table (Phase 2+)

When Phase 2 adds mem0 + ChromaDB, ownership expands:

| Data Type | Storage | Purpose | Source of Truth |
|-----------|---------|---------|-----------------|
| **Issue Embeddings** | ChromaDB | Vector representations of Linear issues | Linear Chief of Staff (generated from Linear data) |
| **User Preferences** | mem0 or SQLite | Learned preferences (topics, teams, labels) | Linear Chief of Staff (learned from user behavior) |
| **Feedback Data** | SQLite `issue_feedback` table | Telegram 👍/👎 ratings per issue | Linear Chief of Staff (user input) |
| **Interaction History** | mem0 | Conversation history, queries, read receipts | Linear Chief of Staff (logged interactions) |

**Phase 2 Principle:** SQLite remains source of truth for transactional data. mem0/ChromaDB are **derived data stores** for ML features.

---

## Data Lifecycle & Cleanup Strategy

### Automated Cleanup (APScheduler Job)

**Cleanup Scheduler:**
- APScheduler job runs daily at 2:00 AM (low-traffic time)
- Separate from briefing scheduler for isolation
- Logs cleanup operations for audit trail

**Cleanup Rules:**

| Data Type | Retention Policy | Cleanup Logic | Rationale |
|-----------|------------------|---------------|-----------|
| **Linear Issue Metadata** | 30 days | Delete issues where `last_seen_at` < 30 days ago | Issue cache, not canonical source. Stale issues unlikely to be relevant. |
| **Briefing History** | Permanent | No deletion | Cost analysis, debugging, learning analysis requires full history. |
| **Agent Context** | 7-day rolling window | Delete `agent_context` from briefings older than 7 days (set JSON field to NULL) | Context only useful for continuity, not historical analysis. Keeps DB size manageable. |
| **Briefing-Issue Relationships** | Permanent | No deletion | Required for historical queries ("which briefings included ENG-123?"). |

**Implementation:**
```python
# Pseudo-code for cleanup job
async def cleanup_stale_data():
    thirty_days_ago = datetime.now() - timedelta(days=30)
    seven_days_ago = datetime.now() - timedelta(days=7)

    # Delete old issue cache
    await db.execute("DELETE FROM issues WHERE last_seen_at < ?", thirty_days_ago)

    # Clear old agent context (keep briefing record, just nullify context)
    await db.execute("UPDATE briefings SET agent_context = NULL WHERE generated_at < ?", seven_days_ago)

    # Log metrics
    logger.info("cleanup_completed", issues_deleted=count1, contexts_cleared=count2)
```

**Configuration:**
- `DATA_RETENTION_DAYS_ISSUES` - Default 30, configurable via .env
- `DATA_RETENTION_DAYS_CONTEXT` - Default 7, configurable via .env
- `CLEANUP_HOUR` - Default 2 (AM), configurable via .env

**Phase 2 Additions:**
When adding ChromaDB/mem0:
- ChromaDB embeddings: 30-day retention (sync with issue cache)
- mem0 preferences: No expiration (learned data should persist)
- Feedback data: 90-day retention (longer for learning purposes)

---
