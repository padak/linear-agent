# Prompt Templates

This directory contains prompt templates for the Linear Chief of Staff agent.

## Templates

### `briefing_v1.txt`
**Purpose:** Generate morning intelligence briefing from Linear issues

**Variables:**
- `{user_context}` - mem0 context (previous briefings, user preferences, historical interactions)
- `{issue_list}` - JSON formatted list of Linear issues with fields:
  - `id`, `title`, `state`, `labels`, `updated_at`, `description`, `comments`

**Output:** Telegram Markdown formatted briefing (<4096 chars)

**Sections:**
1. 🚨 Blocked Issues
2. 🕐 Stale Issues
3. 🔥 Recent Activity
4. 🎯 Top Priority (Ranked)

**Constraints:**
- Max 200 chars per issue summary
- Total <4096 chars (Telegram limit)
- Use Telegram Markdown formatting

## Usage Example

```python
from linear_chief.agent.briefing_agent import BriefingAgent

agent = BriefingAgent()
issues = linear_client.fetch_my_issues()
user_context = mem0_client.get_user_context()

briefing = await agent.generate_briefing(
    issues=issues,
    user_context=user_context,
    template="briefing_v1"
)
```

## Prompt Versioning

When modifying prompts, create new versions (v2, v3, ...) instead of editing existing ones. This allows A/B testing and rollback.

Track which prompt version generated each briefing via `briefings.prompt_version` column.

## Testing Prompts

Use `scripts/test_prompt.py` to test prompts with sample data:

```bash
python scripts/test_prompt.py --template briefing_v1 --issues test_data/50_issues.json
```

This validates:
- Output length (<4096 chars)
- Issue summary length (<200 chars each)
- Markdown formatting
- Token usage
