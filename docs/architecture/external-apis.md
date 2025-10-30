# External APIs

## Linear GraphQL API

- **Purpose:** Fetch issues assigned to or watched by the authenticated user
- **Documentation:** https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- **Base URL(s):** `https://api.linear.app/graphql`
- **Authentication:** Personal API key (header: `Authorization: Bearer <token>`) or OAuth2 (future)
- **Rate Limits:** 100 requests per minute per API key (to be validated in Week 1 spike - Linear API docs were inaccessible during architecture phase)

**Key Endpoints Used:**
- `POST /graphql` - Main query endpoint
  - Query: `viewer { assignedIssues { nodes { id title state updatedAt labels { name } } } }`
  - Query: `issues(filter: { subscribers: { id: { eq: $userId } } })`

**Integration Notes:**
- Use pagination cursors for 50+ issues (`after` parameter)
- Implement request batching where possible to minimize API calls
- Cache responses for 5 minutes to avoid redundant queries
- Exponential backoff on 429 (rate limit) responses

## Anthropic API

- **Purpose:** Generate natural language briefing summaries using Claude via Agent SDK
- **Documentation:** https://docs.anthropic.com/claude/reference
- **Base URL(s):** Handled by Agent SDK (abstracts API details)
- **Authentication:** API key via `ANTHROPIC_API_KEY` environment variable
- **Rate Limits:** TBD (typically tier-based, should be sufficient for single user)

**Key Endpoints Used:**
- Agent SDK abstracts direct API calls
- Underlying: `/v1/messages` (Claude Messages API)

**Integration Notes:**
- Track token usage for cost monitoring (aim for <$100/month)
- Use prompt caching if Agent SDK supports it (reduce costs for repeated issue data)
- Set max_tokens limit to prevent runaway costs (e.g., 1000 tokens per briefing)
- Implement timeout (30s) to prevent hanging requests

## Telegram Bot API

- **Purpose:** Deliver briefing messages to user's Telegram chat
- **Documentation:** https://core.telegram.org/bots/api
- **Base URL(s):** `https://api.telegram.org/bot<token>/`
- **Authentication:** Bot token in URL path
- **Rate Limits:** 30 messages per second (not a concern for single user)

**Key Endpoints Used:**
- `POST /sendMessage` - Send text message to chat
  - Parameters: `chat_id`, `text`, `parse_mode: "Markdown"`

**Integration Notes:**
- Message length limit: 4096 characters (chunk long briefings)
- Use Markdown formatting for readability (**bold**, `code`, etc.)
- Retry on network errors (tenacity with max 3 retries)
- No need for webhooks (we only send, not receive messages)

---
