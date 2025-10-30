# Requirements

## Functional Requirements

- **FR1:** System SHALL fetch all Linear issues assigned to the user or explicitly watched by the user via Linear GraphQL API
- **FR2:** System SHALL generate a single daily briefing at 9:00 AM local time
- **FR3:** Briefing SHALL include issues with activity in the last 24 hours (new comments, status changes, assignments)
- **FR4:** Briefing SHALL identify and flag issues marked with "Blocked" label
- **FR5:** Briefing SHALL identify issues that are stale (no updates for 3+ days while in "In Progress" status)
- **FR6:** Briefing SHALL generate a 1-2 sentence summary for each flagged issue using Anthropic Agent SDK
- **FR7:** Briefing SHALL be delivered via Telegram Bot API to the configured user
- **FR8:** System SHALL provide a manual trigger capability (CLI script) to generate on-demand briefings for testing
- **FR9:** System SHALL track issue state changes using Linear's `updatedAt` timestamps
- **FR10:** System SHALL persist briefing history and seen issue states in local SQLite database
- **FR11:** System SHALL log all API calls, token usage, and errors for debugging and learning analysis
- **FR12:** System SHALL handle Linear API failures gracefully with retry logic (exponential backoff)
- **FR13:** System SHALL respect Linear API rate limits (max 100 requests/minute)
- **FR14:** Briefing SHALL limit output to 3-10 most relevant issues to avoid overwhelming the user
- **FR15:** System SHALL authenticate with Linear API using personal API key (OAuth2 for future)
- **FR16:** System SHALL authenticate with Telegram Bot API using bot token
- **FR17:** System SHALL authenticate with Anthropic API using API key

## Non-Functional Requirements

- **NFR1:** Briefing generation SHALL complete in under 30 seconds for up to 50 tracked issues
- **NFR2:** System SHALL stay within $100/month budget for Anthropic API costs
- **NFR3:** System SHALL run on local development machine (macOS/Linux) before cloud deployment
- **NFR4:** System SHALL use Python 3.11+ as primary implementation language
- **NFR5:** System SHALL store API keys securely using environment variables (no hardcoded secrets)
- **NFR6:** Telegram messages SHALL not exceed 4096 character limit (chunk if necessary)
- **NFR7:** System SHALL maintain 99% uptime over 7-day testing period (max 1 missed briefing)
- **NFR8:** System SHALL log structured JSON logs for parsing and analysis
- **NFR9:** System SHALL have no PII (Personally Identifiable Information) in logs beyond issue IDs
- **NFR10:** Code SHALL include docstrings and type hints for maintainability
- **NFR11:** System SHALL be deployable via single configuration file (`.env` or similar)
- **NFR12:** System SHALL track and report token usage per briefing for cost analysis

---
