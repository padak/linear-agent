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
| **Agent Framework** | Anthropic Agent SDK | Latest | Core intelligence and briefing generation | Primary learning objective, handles LLM reasoning |
| **Linear API Client** | `gql` or Linear Python SDK | TBD (Week 1) | GraphQL queries to Linear | Decision pending SDK quality research |
| **Telegram Bot** | `python-telegram-bot` | 20.x | Telegram Bot API integration | Mature, well-documented, async support |
| **HTTP Client** | `httpx` | 0.26.x | Async HTTP requests | Modern async client, better than requests for concurrent calls |
| **Database** | SQLite | 3.x | Local state persistence | File-based, no server, perfect for single-user MVP |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction | Type-safe, supports migrations, async support |
| **Scheduler** | APScheduler | 3.10.x | Scheduled task execution | Fallback if Agent SDK lacks native scheduling |
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
| **Embeddings** | sentence-transformers | 2.x | Generate semantic embeddings for Linear issues | Enables semantic search and preference learning (all-MiniLM-L6-v2 model) |
| **Memory Layer** | mem0 | Latest | Persistent agent memory and user preference learning | Replaces custom DB-based context, provides memory graph for tracking user interactions and preferences |
| **Vector Store** | ChromaDB | 0.4.x | Store and search issue embeddings | Lightweight vector DB for similarity search (alternative: pgvector if migrating to PostgreSQL) |

---
