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

**Purpose:** Tracks generated briefings for cost analysis, debugging, and historical reference.

**Key Attributes:**
- `id`: integer - Primary key
- `generated_at`: datetime - When briefing was created
- `issue_count`: integer - Number of issues included in briefing
- `tokens_used`: integer - Total tokens consumed by Anthropic API
- `cost_usd`: decimal - Estimated cost in USD
- `telegram_message_id`: string (nullable) - Telegram message ID if delivered
- `delivery_status`: enum - "pending", "sent", "failed"
- `error_message`: text (nullable) - Error details if delivery failed

**Relationships:**
- Many-to-many with `Issue` (briefing can include multiple issues, issue can appear in multiple briefings)

---
