# Database Schema

**SQLite Configuration:**
```sql
-- Enable WAL mode for concurrency (prevents locking issues with APScheduler + manual CLI)
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
```

```sql
-- Issues table
CREATE TABLE issues (
    linear_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    assignee_id TEXT,
    labels TEXT,  -- JSON array
    updated_at DATETIME NOT NULL,
    last_seen_at DATETIME NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_updated_at (updated_at),
    INDEX idx_last_seen_at (last_seen_at)
);

-- Briefings table
CREATE TABLE briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at DATETIME NOT NULL,
    issue_count INTEGER NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost_usd DECIMAL(10, 4) NOT NULL,
    telegram_message_id TEXT,
    delivery_status TEXT NOT NULL CHECK(delivery_status IN ('pending', 'sent', 'failed', 'permanently_failed')),
    error_message TEXT,
    agent_context TEXT,  -- JSON: {narrative, follow_up_flags, notes}
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_generated_at (generated_at)
);

-- Briefing-Issue junction table (many-to-many)
CREATE TABLE briefing_issues (
    briefing_id INTEGER NOT NULL,
    issue_linear_id TEXT NOT NULL,
    PRIMARY KEY (briefing_id, issue_linear_id),
    FOREIGN KEY (briefing_id) REFERENCES briefings(id) ON DELETE CASCADE,
    FOREIGN KEY (issue_linear_id) REFERENCES issues(linear_id) ON DELETE CASCADE
);
```

---
