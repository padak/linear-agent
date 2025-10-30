# Technical Assumptions

## Repository Structure

**Monorepo** - Single repository containing all code, configuration, and documentation for the MVP.

## Service Architecture

**Monolith** - Single Python process with async tasks for API calls. No microservices for MVP. Architecture pattern:
- Main orchestrator script runs on schedule (cron or Agent SDK scheduler)
- Async modules for Linear API, Telegram Bot, Anthropic Agent SDK
- SQLite database for state persistence (file-based, no separate DB server)

**Rationale:** Learning project with single user doesn't justify distributed architecture complexity. Focus is on Agent SDK patterns, not infrastructure.

## Testing Requirements

**Unit + Integration Testing**
- Unit tests for core logic (issue analysis, stagnation detection)
- Integration tests for Linear API client (mocked responses)
- Integration tests for Telegram Bot (mocked sends)
- Manual testing for end-to-end briefing generation
- **No automated E2E or UI tests** (Telegram is third-party interface)

**Testing Philosophy:** Test business logic thoroughly, mock external APIs, accept manual verification for Telegram delivery.

## Additional Technical Assumptions and Requests

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

**Critical Week 1 Validation Items:**
- Confirm Anthropic Agent SDK supports scheduled execution OR design external orchestration
- Validate token usage stays within budget (<$100/month target)
- Research Linear API rate limits and pagination strategies
- Test SQLite performance with 50+ issues and 7+ days of history

---
