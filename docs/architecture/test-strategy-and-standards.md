# Test Strategy and Standards

## Testing Philosophy

- **Approach:** Test-after (write tests for each story's acceptance criteria after implementation)
- **Coverage Goals:** 80%+ unit test coverage, 60%+ integration test coverage
- **Performance SLA:** 30s end-to-end briefing generation (instrumented per-stage)
- **Test Pyramid:**
  - 70% unit tests (fast, isolated)
  - 25% integration tests (mocked external APIs)
  - 5% manual end-to-end tests (Telegram delivery)

## Test Types and Organization

### Unit Tests

- **Framework:** pytest 8.x
- **File Convention:** `test_<module_name>.py` (e.g., `test_briefing_agent.py`)
- **Location:** `tests/unit/`
- **Mocking Library:** pytest-mock (fixtures + mocker)
- **Coverage Requirement:** 80%+ for core logic modules (intelligence, agent, repositories)

**AI Agent Requirements:**
- Generate tests for all public methods and classes
- Cover edge cases: empty issue list, no changed issues, API errors
- Follow AAA pattern (Arrange, Act, Assert)
- Mock all external dependencies (Agent SDK, Linear API, Telegram API)

### Integration Tests

- **Scope:** Test interactions between modules with mocked external APIs
- **Location:** `tests/integration/`
- **Test Infrastructure:**
  - **Linear API:** Mock HTTP responses using `pytest-httpx`
  - **Anthropic API:** Mock Agent SDK responses (fixture-based)
  - **Telegram API:** Mock `python-telegram-bot` with pytest-mock
  - **SQLite:** Use in-memory database (`:memory:`) for fast tests

#### SQLite Concurrency Test

**Purpose:** Validate SQLite WAL mode handles concurrent writes from APScheduler scheduler and manual CLI without locking errors.

**Test Scenario:**
```python
async def test_concurrent_writes():
    # Start APScheduler briefing generation
    scheduler_task = asyncio.create_task(generate_scheduled_briefing())

    # Simultaneously trigger manual briefing from CLI
    await asyncio.sleep(0.1)  # Small delay to ensure overlap
    manual_task = asyncio.create_task(generate_manual_briefing())

    # Both should complete without locking errors
    results = await asyncio.gather(scheduler_task, manual_task)
    assert all(r.success for r in results)
```

**Expected Behavior:**
- No `database is locked` errors
- Both briefings written to database successfully
- WAL mode prevents lock contention

**Test Infrastructure:**
- Use pytest-asyncio for async test execution
- SQLite database in WAL mode (configured in test fixtures)
- Mock Linear/Anthropic APIs to focus on database concurrency

### End-to-End Tests

- **Framework:** Manual testing for MVP (no automation)
- **Scope:** Full workflow from scheduler trigger to Telegram delivery
- **Environment:** Local development machine
- **Test Data:** Use separate test Telegram bot and Linear workspace (or mock Linear responses)

### Performance Tests

- **Framework:** pytest with timing fixtures
- **Scope:** End-to-end briefing generation (Linear fetch → Agent SDK → Telegram)
- **SLA Target:** 30 seconds for ≤50 issues (NFR1)
- **Instrumentation:**
  - Measure each stage: Linear API (budget: 5s), Intelligence (budget: 2s), Agent SDK (budget: 20s), Telegram (budget: 3s)
  - Regression tests assert total time < 30s
  - Log timing data to cost_logs table for analysis
- **Test Data:** Use 50-issue fixture with realistic content
- **Run Frequency:** Every commit (GitHub Actions)

## Test Data Management

- **Strategy:** Fixture-based test data (JSON files in `tests/fixtures/`)
- **Fixtures:** `sample_issues.json`, `sample_briefing.json`
- **Factories:** Not needed for MVP (fixtures are sufficient)
- **Cleanup:** pytest fixtures with `yield` for setup/teardown

## Continuous Testing

- **CI Integration:** GitHub Actions (future) - run pytest on every push
- **Performance Tests:** Not implemented for MVP (single user, low volume)
- **Security Tests:** Dependency scanning with `safety` library (future)

---
