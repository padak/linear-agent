# Linear Chief of Staff - Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Learn how to build autonomous AI agents using Anthropic's Agent SDK
- Understand agent patterns: scheduling, persistent memory, tool integration
- Model and optimize LLM costs for production workloads
- Reduce time spent manually checking Linear by 10+ minutes per morning
- Build confidence in deploying autonomous agents to production
- Create a working morning digest that surfaces 3-10 relevant Linear issues (blocked, stale, active)
- Validate that the agent runs reliably for 7+ consecutive days without crashes

### Background Context

This is a personal learning project to explore Anthropic's Agent SDK by solving a real problem: maintaining awareness across Linear issues without spending 1-2 hours daily on manual checking. The problem involves tracking 10-30 active issues across multiple teams, catching blocked or stale items before they impact timelines, and reducing the cognitive load of constant context-switching.

The timing is ideal because Anthropic's Agent SDK (2024-2025) represents a significant shift in autonomous AI system architecture. Building a real monitoring agent provides hands-on experience with critical agent patterns while creating immediate personal utility. This is NOT a commercial product—success means deeply understanding Agent SDK capabilities AND building something useful, even if briefings are imperfect.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-30 | 0.1 | Initial PRD creation from Project Brief | John (PM Agent) |

---

## Requirements

### Functional Requirements

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

### Non-Functional Requirements

- **NFR1:** Briefing generation SHALL complete in under 30 seconds for up to 50 tracked issues
- **NFR2:** System SHALL stay within $20/month budget for Anthropic API costs (realistic target based on 30 briefings × ~2K tokens)
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

## User Interface Design Goals

**Note:** This is primarily a backend/agent system. The only user-facing interface is Telegram messages.

### Overall UX Vision

The user receives a concise, actionable morning briefing via Telegram that feels like a human chief of staff providing a situational update. The tone is professional yet conversational, highlighting what needs attention without overwhelming detail.

### Key Interaction Paradigms

- **Push notification model:** Agent proactively delivers briefings at scheduled time
- **Read-only for MVP:** No interactive responses or queries (v2 feature)
- **Structured message format:** Briefing uses Telegram markdown for readability (headers, bullet points, bold for issue IDs)

### Core Screens and Views

1. **Telegram Briefing Message** (primary interface)
   - Header: "🌅 Morning Briefing - [Date]"
   - Section 1: Active Issues (updated in last 24h)
   - Section 2: Blocked Issues (needs attention)
   - Section 3: Stale Issues (no activity 3+ days)
   - Footer: Summary count and timestamp

2. **CLI Manual Trigger** (testing only)
   - Command: `python -m linear_chief.cli generate-briefing`
   - Output: Same briefing sent to Telegram + token usage stats

### Accessibility

None - Telegram is the interface, inherits Telegram's accessibility features.

### Branding

Minimal. Use emoji sparingly (🌅 for morning, ⚠️ for blocked, 🕐 for stale). Keep professional tone suitable for work context.

### Target Device and Platforms

- **Primary:** Telegram mobile app (iOS/Android)
- **Secondary:** Telegram desktop/web clients
- Device-agnostic: Telegram handles rendering

---

## Technical Assumptions

### Repository Structure

**Monorepo** - Single repository containing all code, configuration, and documentation for the MVP.

### Service Architecture

**Monolith** - Single Python process with async tasks for API calls. No microservices for MVP. Architecture pattern:
- Main orchestrator script runs on schedule (cron or Agent SDK scheduler)
- Async modules for Linear API, Telegram Bot, Anthropic Agent SDK
- SQLite database for state persistence (file-based, no separate DB server)

**Rationale:** Learning project with single user doesn't justify distributed architecture complexity. Focus is on Agent SDK patterns, not infrastructure.

### Testing Requirements

**Unit + Integration Testing**
- Unit tests for core logic (issue analysis, stagnation detection)
- Integration tests for Linear API client (mocked responses)
- Integration tests for Telegram Bot (mocked sends)
- Manual testing for end-to-end briefing generation
- **No automated E2E or UI tests** (Telegram is third-party interface)

**Testing Philosophy:** Test business logic thoroughly, mock external APIs, accept manual verification for Telegram delivery.

### Additional Technical Assumptions and Requests

- **Python 3.11+** with type hints (PEP 484) and async/await (asyncio)
- **Anthropic Agent SDK** as primary dependency (validate in Week 1 spike)
- **Linear API:** Use official Linear Python SDK OR `gql` library for GraphQL queries (decide based on SDK quality research)
- **Telegram:** Use `python-telegram-bot` library (mature, well-documented)
- **Scheduling:** Prefer Agent SDK native scheduling if available; fallback to `APScheduler` or system cron
- **State Management:** SQLite with `SQLAlchemy` ORM for simplicity
- **Logging:** Use Python `logging` module with JSON formatter (`python-json-logger`)
- **Configuration:** Use `python-decouple` for environment variable management
- **Secrets:** Store in `.env` file (local) or environment variables (production)
- **Deployment (future):** Systemd service on Ubuntu 22.04 LTS (Digital Ocean Droplet or EC2)
- **Code Quality:** Use `black` for formatting, `mypy` for type checking, `pytest` for testing
- **Dependency Management:** Use `poetry` or `pip-tools` for reproducible builds
- **NO Docker for MVP:** Local Python environment is sufficient for learning and testing
- **Cost Tracking:** Monitor token usage to validate <$20/month target during implementation

---

## Epic List

### Epic 1: Foundation & Core Setup

**Goal:** Establish project foundation with locked-in technology stack (Agent SDK + mem0 + ChromaDB) and implement core data pipelines. Deliver working integration of Linear API, Agent SDK, and memory layer.

### Epic 2: Production-Ready Morning Digest

**Goal:** Transform the validated prototype into a reliable, scheduled production system that runs autonomously and delivers daily briefings via Telegram with robust error handling and logging.

### Epic 3: Intelligence & Optimization

**Goal:** Enhance the briefing quality with better issue analysis, optimize costs through prompt engineering, and add instrumentation for learning analysis.

---

## Epic 1: Foundation & Core Setup

**Expanded Goal:**

Set up the development environment with locked-in technology stack (Agent SDK, mem0, ChromaDB, sentence-transformers). Integrate Linear API, implement memory layer, and create working briefing generation pipeline. Deliverable is end-to-end data flow: Linear issues → Intelligence analysis → Agent SDK + mem0 → Briefing output.

### Story 1.1: Project Setup and Development Environment

**As a** developer learning Anthropic Agent SDK,
**I want** a properly configured Python project with all necessary dependencies,
**so that** I can begin prototyping without environment issues.

**Acceptance Criteria:**
1. Python 3.11+ virtual environment created using `poetry`
2. `pyproject.toml` includes: `anthropic`, `mem0ai`, `chromadb`, `sentence-transformers`, `httpx`, `python-telegram-bot`, `sqlalchemy`, `python-decouple`, `apscheduler`, `pytest`
3. `.env.example` file documents required environment variables: `ANTHROPIC_API_KEY`, `LINEAR_API_KEY`, `TELEGRAM_BOT_TOKEN`
4. `.gitignore` configured to exclude `.env`, `__pycache__`, `.pytest_cache`, `*.db`
5. Project structure created with directories: `src/linear_chief/`, `tests/`, `docs/`, `config/`
6. README.md includes setup instructions and environment variable documentation
7. All dependencies install successfully via `pip install` or `poetry install`

### Story 1.2: Linear API Integration - Fetch User's Issues

**As a** developer,
**I want** to fetch all Linear issues assigned to or watched by the authenticated user,
**so that** I have real data to feed into the Agent SDK for briefing generation.

**Acceptance Criteria:**
1. `src/linear_chief/linear_client.py` module created with `LinearClient` class
2. `LinearClient.authenticate()` method validates API key and retrieves user info
3. `LinearClient.fetch_my_issues()` method retrieves issues using GraphQL query filtering on `assignee.id` or `subscriber.id`
4. Issues include fields: `id`, `title`, `state.name`, `updatedAt`, `labels.name`, `description`, `comments.nodes.body`
5. Method handles pagination if user has 50+ issues (uses `after` cursor)
6. Rate limiting handled: exponential backoff on 429 responses, max 100 req/min tracking
7. Unit tests mock GraphQL responses and verify parsing logic
8. Integration test (with real API key in CI or manual) confirms data structure

### Story 1.3: Anthropic Agent SDK - Generate Basic Briefing

**As a** developer,
**I want** to pass Linear issues to Anthropic Agent SDK and receive a structured briefing,
**so that** I can validate the SDK can reason about issue data and produce useful output.

**Acceptance Criteria:**
1. `src/linear_chief/agent.py` module created with `BriefingAgent` class
2. `BriefingAgent.generate_briefing(issues: List[Issue])` method sends issues to Agent SDK
3. Prompt instructs agent to identify: blocked issues (labeled "Blocked"), stale issues (no update 3+ days, status "In Progress"), recently active issues (updated <24h)
4. Agent returns structured response with sections: Active, Blocked, Stale (JSON or Markdown)
5. Token usage logged and returned from method call
6. Method handles API errors gracefully (retry on 5xx, fail-fast on 4xx)
7. Unit tests mock Agent SDK responses
8. Manual test with 10+ real Linear issues produces sensible briefing and logs token count
9. Cost tracking automatically logs token usage (included in BriefingAgent, not separate story)

---

## Epic 2: Production-Ready Morning Digest

**Expanded Goal:**

Build production-grade infrastructure around the validated prototype: scheduling, Telegram delivery, state persistence, error handling, and logging. The system should run autonomously for 7+ days without intervention and deliver reliable morning briefings.

### Story 2.1: SQLite State Persistence

**As a** system,
**I want** to persist issue state and briefing history in SQLite,
**so that** I can track changes over time and avoid re-processing identical issues.

**Acceptance Criteria:**
1. `src/linear_chief/storage/models.py` defines SQLAlchemy models: `Issue`, `Briefing`
2. `Issue` table tracks: `linear_id`, `title`, `state`, `last_updated`, `last_seen_at`, `labels_json`
3. `Briefing` table tracks: `id`, `generated_at`, `issue_count`, `tokens_used`, `telegram_message_id`
4. `src/linear_chief/storage/db.py` provides `Database` class with methods: `save_issues()`, `get_last_briefing()`, `mark_issue_seen()`
5. Database file created at `~/.linear_chief/state.db` or configurable path
6. Schema migrations handled (for MVP: drop/recreate on schema change is acceptable)
7. Unit tests verify CRUD operations
8. Integration test persists 50 issues, retrieves them, verifies data integrity

### Story 2.2: Telegram Bot Integration

**As a** user,
**I want** to receive briefings via Telegram,
**so that** I can read them on mobile without opening Linear or checking email.

**Acceptance Criteria:**
1. `src/linear_chief/telegram_bot.py` module created with `TelegramNotifier` class
2. `TelegramNotifier.send_briefing(briefing_text: str)` sends formatted message via Bot API
3. Briefing uses Telegram Markdown formatting: **bold** for issue IDs, headers (###), bullet points
4. Messages exceeding 4096 chars are chunked into multiple messages
5. Bot token and chat ID configured via environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
6. Error handling: retry on network failures, log and skip on 4xx errors
7. Unit tests mock Bot API responses
8. Manual test sends sample briefing to actual Telegram account and verifies formatting

### Story 2.3: Scheduled Briefing Generation

**As a** user,
**I want** the system to automatically generate and send a briefing at 9:00 AM daily,
**so that** I receive updates without manual triggering.

**Acceptance Criteria:**
1. `src/linear_chief/scheduler.py` implements scheduling using `APScheduler` (if Agent SDK doesn't support native scheduling)
2. OR if Agent SDK supports scheduling: document and use native scheduler
3. Scheduler triggers `generate_and_send_briefing()` daily at 9:00 AM local time
4. Orchestrator workflow: fetch issues → generate briefing → persist state → send to Telegram → log metrics
5. Scheduler runs as long-running process (not cron job for MVP simplicity)
6. Graceful shutdown: catches SIGTERM/SIGINT and completes in-flight briefing
7. Logging includes: start time, issue count, tokens used, Telegram delivery status, errors
8. Manual test: set schedule to "next minute", verify briefing arrives on time (±1 min acceptable)

### Story 2.4: Robust Error Handling and Retry Logic

**As a** system operator,
**I want** the system to handle transient failures gracefully,
**so that** a single API error doesn't crash the entire agent.

**Acceptance Criteria:**
1. All API clients (Linear, Anthropic, Telegram) implement exponential backoff retry (use `tenacity` library)
2. Linear API: retry on 5xx (max 3 retries), fail after exhaustion
3. Anthropic API: retry on 5xx and rate limit (max 3 retries)
4. Telegram API: retry on network errors (max 3 retries)
5. If briefing generation fails after retries, log error and skip that day's briefing (don't crash scheduler)
6. Structured error logging includes: timestamp, error type, request payload, response status
7. Unit tests simulate network failures and verify retry behavior
8. Integration test: mock API to return 500, verify system retries and eventually logs failure

### Story 2.5: Comprehensive Logging and Observability

**As a** developer/operator,
**I want** structured JSON logs for all system events,
**so that** I can debug issues and analyze agent performance.

**Acceptance Criteria:**
1. Logging configured in `src/linear_chief/logging_config.py` using `python-json-logger`
2. All modules use logger: `logger = logging.getLogger(__name__)`
3. Log levels: DEBUG for API requests/responses, INFO for briefing generation, WARNING for retries, ERROR for failures
4. JSON log format includes: `timestamp`, `level`, `module`, `message`, `extra` (context fields)
5. Logs written to `~/.linear_chief/logs/agent.log` (rotated daily, keep 7 days)
6. Token usage logged after each Anthropic call: `{"event": "token_usage", "tokens": 1234, "cost_usd": 0.05}`
7. No PII logged (no issue descriptions, only IDs and metadata)
8. Manual review: generate 3 briefings, verify logs are parseable JSON and contain all required fields

---

## Epic 3: Intelligence & Optimization

**Expanded Goal:**

Refine the briefing quality by improving issue analysis logic, optimize costs through prompt engineering and caching, and add instrumentation to track learning goals (token usage trends, API patterns, briefing effectiveness).

### Story 3.1: Enhanced Issue Analysis - Stagnation Detection

**As a** user,
**I want** the agent to accurately identify truly stale issues,
**so that** I'm not spammed with false positives for issues that are intentionally paused.

**Acceptance Criteria:**
1. `src/linear_chief/intelligence/analyzers.py` module created with `StagnationAnalyzer` class
2. Stale issue criteria refined: no updates for 3+ days AND status is "In Progress" AND not labeled "On Hold" or "Waiting"
3. Analyzer checks issue comments for keywords: "paused", "blocked on external", "waiting for" → exclude from stale list
4. Unit tests verify edge cases: issue updated 72 hours ago (stale), issue with "On Hold" label (not stale)
5. Integration test with 20 real issues verifies <10% false positive rate (manually review flagged issues)

### Story 3.2: Prompt Engineering for Concise Summaries

**As a** user,
**I want** issue summaries to be concise (1-2 sentences) and action-oriented,
**so that** I can quickly understand what needs attention without reading full descriptions.

**Acceptance Criteria:**
1. Prompt template updated to emphasize: "Summarize in 1-2 sentences focusing on current status and next action needed"
2. Prompt includes few-shot examples of good summaries
3. Agent instructed to avoid regurgitating issue description verbatim
4. Unit tests verify summary length: <200 characters per issue
5. Manual review: 10 generated summaries are concise and actionable (subjective but documentable)

### Story 3.3: Cost Optimization - Issue Data Caching

**As a** project owner,
**I want** to reduce Anthropic API costs by sending only changed issues,
**so that** monthly costs stay well below $20 budget target.

**Acceptance Criteria:**
1. `Database.get_issues_changed_since(timestamp)` method queries SQLite for issues updated since last briefing
2. Orchestrator sends only changed issues to Agent SDK (not full 50-issue list daily)
3. Agent prompt adjusted: "Here are issues that changed since yesterday. Summarize changes and flag concerns."
4. Token usage logged before/after optimization for comparison
5. Test: generate briefing on Day 1 (50 issues, baseline tokens), Day 2 (5 changed issues, reduced tokens)
6. Document token reduction: target 50% reduction on days with <10 changed issues

### Story 3.4: Learning Metrics Dashboard (CLI)

**As a** learner,
**I want** a CLI command to view token usage trends and system health,
**so that** I can track learning goals and optimize costs.

**Acceptance Criteria:**
1. CLI command: `python -m linear_chief.cli metrics` displays summary table
2. Metrics shown: total briefings generated, avg tokens per briefing, total cost, uptime %, missed briefings
3. Data pulled from `Briefing` table in SQLite
4. Graph (ASCII art or simple) showing token usage over last 7 days
5. Warnings: flag if any day exceeded $5 cost or briefing failed
6. Manual test: run for 7 days, review metrics, verify accuracy

---

## Checklist Results Report

_(This section will be populated after running pm-checklist.md)_

**Status:** Pending - checklist execution will validate:
- All requirements are testable and unambiguous
- Stories are properly sequenced and sized for AI agent execution
- Technical assumptions are documented and validated
- Epic dependencies are correct
- Acceptance criteria are complete and verifiable

---

## Next Steps

### UX Expert Prompt

Not applicable for this project - primary interface is Telegram messages (no custom UI design needed).

### Architect Prompt

**Winston (Architect),**

Please review this PRD and create a detailed technical architecture for the Linear Chief of Staff agent system. Focus on:

1. **Agent SDK Integration Patterns:** How to structure the Anthropic Agent SDK integration for scheduled briefing generation. Document whether the SDK supports native scheduling or if we need external orchestration (APScheduler/cron).

2. **Data Flow Architecture:** Design the data flow from Linear API → Issue Analysis → Agent SDK → Telegram delivery, with emphasis on state management and caching strategies.

3. **Module Structure:** Define the Python package structure (agents, storage, telegram, linear, intelligence modules) with clear interfaces and dependency injection patterns.

4. **Cost Optimization Strategy:** Architecture decisions that minimize token usage (caching, incremental updates, prompt templates).

5. **Deployment Model:** Local development architecture and path to production (systemd service, monitoring, log aggregation).

Use the PRD's technical assumptions (Python, SQLite, monolith) as constraints. Output should be `docs/architecture.md` following BMad architecture template.

