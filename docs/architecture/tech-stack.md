# Tech Stack

## Cloud Infrastructure

**Note:** MVP runs locally before cloud deployment. Cloud infrastructure is **future consideration** only.

- **Provider:** None for MVP (local machine). Future: Digital Ocean Droplet or AWS EC2 t3.small
- **Key Services:** Systemd (process management), environment variables (secrets)
- **Deployment Regions:** N/A for MVP. Future: US-East-1 or closest region

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|-----------|---------|---------|-----------|
| **Language** | Python | 3.11+ | Primary development language | Modern type hints, async/await, Agent SDK support |
| **Runtime** | CPython | 3.11+ | Python interpreter | Standard implementation, best compatibility |
| **LLM API** | Anthropic Claude Messages API | Latest | Briefing generation via LLM inference | Primary choice. Agent SDK is optional if Week 1 spike shows value |
| **Linear API Client** | `httpx` + hand-written GraphQL | 0.26.x | GraphQL queries to Linear | Simpler than gql library, easier mocking, fewer dependencies |
| **Telegram Bot** | `python-telegram-bot` | 20.x | Telegram Bot API integration | Mature, well-documented, async support |
| **HTTP Client** | `httpx` | 0.26.x | Async HTTP requests | Modern async client, better than requests for concurrent calls |
| **Database** | SQLite | 3.x | Local state persistence | File-based, no server, perfect for single-user MVP |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction | Type-safe, supports migrations, async support |
| **Scheduler** | APScheduler | 3.10.x | **ONLY** scheduling mechanism for MVP | Proven, well-documented, de-risks MVP. Agent SDK NOT used for scheduling |
| **Config Management** | python-decouple | 3.8+ | Environment variable management | Separates config from code, `.env` support |
| **Logging** | python-json-logger | 2.0.x | Structured JSON logging | Parseable logs for analysis and debugging |
| **Retry Logic** | tenacity | 8.2.x | Exponential backoff retries | Handles transient API failures gracefully |
| **Type Checking** | mypy | 1.8.x | Static type validation | Catch type errors before runtime |
| **Code Formatter** | black | 24.x | Code formatting | Consistent style, zero configuration |
| **Testing Framework** | pytest | 8.x | Unit and integration tests | Most popular Python test framework, great plugins |
| **Test Coverage** | pytest-cov | 4.x | Coverage reporting | Tracks test coverage metrics |
| **Mocking Library** | pytest-mock | 3.12.x | Test mocking | Simplifies mocking in pytest |
| **Async Testing** | pytest-asyncio | 0.23.x | Async test support | Run async tests in pytest |
| **Dependency Management** | poetry | 1.7.x | Reproducible builds | Better than pip, lockfile support, virtual envs |
| **CI/CD** | GitHub Actions | N/A | Automated testing (future) | Free, integrated with GitHub |
| **Deployment** | systemd | System default | Process management (future) | Standard Linux service manager |


## Phase 2+ Dependencies (NOT MVP)

The following dependencies are **explicitly out of MVP scope** and will be added in Phase 2+:

| Category | Technology | Version | Purpose | Phase |
|----------|-----------|---------|---------|-------|
| **Embeddings** | sentence-transformers | 2.x | Generate semantic embeddings for Linear issues | Phase 2 |
| **Memory Layer** | mem0 | Latest | User preference learning and interaction tracking | Phase 2 |
| **Vector Store** | ChromaDB | 0.4.x | Store and search issue embeddings for similarity search | Phase 2 |

**MVP Approach:** Agent context stored in SQLite `briefings.agent_context` JSON column. No ML, no embeddings, no preference learning until Phase 2.

---
