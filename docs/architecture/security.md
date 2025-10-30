# Security

## Input Validation

- **Validation Library:** Pydantic (for DTO models)
- **Validation Location:** At API boundary (Linear client, config loading)
- **Required Rules:**
  - All environment variables must be validated on startup (missing API keys → fail fast)
  - Linear issue data must be sanitized (strip HTML, limit description length)
  - Telegram message content must escape Markdown special chars

## Authentication & Authorization

- **Auth Method:** API key-based for all external services (no OAuth for MVP)
- **Session Management:** N/A (no user sessions, agent runs as single user)
- **Required Patterns:**
  - API keys loaded from environment variables only
  - Never log API keys (mask in logs: `LINEAR_API_KEY=sk-***...***`)

## Secrets Management

- **Development:** `.env` file (gitignored) loaded via `python-decouple`
- **Production (Phase 1 - systemd):** Environment variables set in systemd service file (`/etc/systemd/system/linear-chief.service`)
- **Production (Phase 2 - cloud):** Migrate to OS keychain (macOS Keychain, Linux `secret-tool`) or cloud secret manager (AWS Secrets Manager, GCP Secret Manager)
  - **Upgrade Path:** Implement `SecretsProvider` interface with multiple backends (env vars, keychain, cloud)
  - **Migration Timeline:** Before remote deployment (Week 4+)
- **Code Requirements:**
  - NEVER hardcode secrets
  - Access via `config.py` module only (abstracts secret provider)
  - No secrets in logs or error messages

## API Security

- **Rate Limiting:** Respect external API limits (Linear: 100 req/min, Telegram: 30 msg/sec)
- **CORS Policy:** N/A (no web interface)
- **Security Headers:** N/A (no HTTP server)
- **HTTPS Enforcement:** All external API calls use HTTPS (httpx verifies SSL by default)

## Data Protection

- **Encryption at Rest:** SQLite database file permissions set to 0600 (owner read/write only)
- **Encryption in Transit:** All API calls use TLS 1.2+ (httpx default)
- **PII Handling:** No PII stored (issue IDs and titles only, no user emails or names)
- **Logging Restrictions:** Never log issue descriptions (may contain sensitive data)

## Dependency Security

- **Scanning Tool:** `safety` library (checks dependencies for known vulnerabilities)
- **Update Policy:** Update dependencies monthly, security patches immediately
- **Approval Process:** Review changelogs before updating major versions

## Security Testing

- **SAST Tool:** Bandit (Python security linter) in GitHub Actions (future)
- **DAST Tool:** Not applicable (no web interface)
- **Penetration Testing:** Not applicable for MVP (single-user local deployment)

---
