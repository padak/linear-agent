# Epic 1: Foundation & Agent SDK Validation Spike

**Expanded Goal:**

Set up the development environment, integrate Anthropic Agent SDK, and validate the core hypothesis: can the SDK reason about Linear issues to generate a useful briefing? This epic focuses on learning and de-risking technical unknowns before investing in production-ready infrastructure. Deliverable is a working Python script that fetches real Linear issues and produces a briefing using the Agent SDK.

## Story 1.1: Project Setup and Development Environment

**As a** developer learning Anthropic Agent SDK,
**I want** a properly configured Python project with all necessary dependencies,
**so that** I can begin prototyping without environment issues.

**Acceptance Criteria:**
1. Python 3.11+ virtual environment created using `venv` or `poetry`
2. `pyproject.toml` or `requirements.txt` includes: `anthropic`, `gql` (or Linear SDK), `python-decouple`, `pytest`
3. `.env.example` file documents required environment variables: `ANTHROPIC_API_KEY`, `LINEAR_API_KEY`, `TELEGRAM_BOT_TOKEN`
4. `.gitignore` configured to exclude `.env`, `__pycache__`, `.pytest_cache`, `*.db`
5. Project structure created with directories: `src/linear_chief/`, `tests/`, `docs/`, `config/`
6. README.md includes setup instructions and environment variable documentation
7. All dependencies install successfully via `pip install` or `poetry install`

## Story 1.2: Linear API Integration - Fetch User's Issues

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

## Story 1.3: Anthropic Agent SDK - Generate Basic Briefing

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

## Story 1.4: Cost and Feasibility Analysis

**As a** project owner,
**I want** to measure actual token usage and cost for briefing generation,
**so that** I can validate the project stays within $100/month budget before proceeding.

**Acceptance Criteria:**
1. `src/linear_chief/cost_tracker.py` module logs token usage per API call
2. Test script generates 30 briefings with 50 issues each to simulate full month
3. Cost calculation using Claude Sonnet 3.5 pricing:
   - Input: $3 per 1M tokens
   - Output: $15 per 1M tokens
   - Formula: (input_tokens × $3/1M) + (output_tokens × $15/1M)
4. Expected token usage per briefing:
   - Input: ~10K tokens (50 issues × 200 tokens/issue average)
   - Output: ~2K tokens (briefing summary)
   - Cost per briefing: (10K × $3/1M) + (2K × $15/1M) = $0.03 + $0.03 = $0.06
5. Monthly cost projection:
   - 30 briefings × $0.06 = $1.80/month
   - Buffer for experimentation (5x): $9/month
   - Target budget: <$20/month (well under original $100 estimate)
6. If actual cost exceeds $20/month, implement optimizations:
   - Reduce issue count (top 30 instead of 50)
   - Use prompt caching (reuse issue data across briefings)
   - Switch to Claude Haiku for less critical summaries ($0.25/$1.25 per 1M)
7. Results documented in `docs/week1-spike-results.md` with decision: proceed, optimize, or pivot
8. Linear API rate limits researched and documented (confirm polling strategy is viable)

---
