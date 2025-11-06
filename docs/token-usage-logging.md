# Token Usage Logging

## Overview

Token usage and cost information is now visible in console logs during all AI interactions. This helps you track API costs in real-time and debug expensive queries.

## Features

- **Visible Token Counts**: See input/output/total tokens for every API call
- **Cost Estimates**: Real-time cost calculation with 4 decimal precision
- **Structured Logging**: Metadata preserved in `extra` fields for JSON logging
- **Consistent Format**: Same format across all agents (Conversation, Briefing)

## Example Output

### Conversation Agent

When a user sends a message via Telegram:

```
2025-11-05 16:30:18 | INFO | Generating conversation response
2025-11-05 16:30:21 | INFO | Conversation response generated successfully (tokens: 1234 in, 567 out, 1801 total, cost: $0.0122)
```

### Briefing Agent

When generating a daily briefing:

```
2025-11-05 09:00:05 | INFO | Generating briefing
2025-11-05 09:00:12 | INFO | Briefing generated successfully (tokens: 3500 in, 1200 out, 4700 total, cost: $0.0285)
```

## Cost Calculation

Token costs are calculated based on Claude Sonnet 4 pricing (as of Nov 2024):

- **Input tokens**: $3.00 per million tokens
- **Output tokens**: $15.00 per million tokens

Formula:
```python
cost_usd = (input_tokens / 1_000_000) * 3.00 + (output_tokens / 1_000_000) * 15.00
```

## Budget Tracking

With visible token logging, you can easily track if you're within budget:

**Target Budget**: <$20/month

**Example Daily Usage**:
- 1 daily briefing: ~4,700 tokens = $0.0285
- 10 user queries: ~1,800 tokens each = $0.122 total
- **Daily cost**: ~$0.15
- **Monthly estimate**: ~$4.50

## Testing

Run the token logging test script to see example output:

```bash
python test_token_logging.py
```

This will demonstrate:
1. ConversationAgent token logging
2. BriefingAgent token logging
3. Example output format

## Implementation Details

### Code Changes

**ConversationAgent** (`src/linear_chief/agent/conversation_agent.py`):

```python
# Calculate cost
cost_usd = self.estimate_cost(
    response.usage.input_tokens,
    response.usage.output_tokens,
)

logger.info(
    f"Conversation response generated successfully "
    f"(tokens: {response.usage.input_tokens} in, "
    f"{response.usage.output_tokens} out, "
    f"{response.usage.input_tokens + response.usage.output_tokens} total, "
    f"cost: ${cost_usd:.4f})",
    extra={
        "service": "Anthropic",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        "cost_usd": cost_usd,
        "model": self.model,
    },
)
```

**BriefingAgent** (`src/linear_chief/agent/briefing_agent.py`):
- Same pattern as ConversationAgent
- Consistent format across all agents

### Structured Metadata

All token usage data is preserved in the `extra` field for structured logging:

```python
{
    "service": "Anthropic",
    "input_tokens": 1234,
    "output_tokens": 567,
    "total_tokens": 1801,
    "cost_usd": 0.0122,
    "model": "claude-sonnet-4-20250514"
}
```

This allows:
- JSON logging backends to capture structured data
- Cost aggregation and analysis tools
- Future monitoring/alerting systems

## Benefits

1. **Immediate Visibility**: See costs as they happen, no waiting for monthly bills
2. **Debug Expensive Queries**: Identify and optimize high-token interactions
3. **Budget Monitoring**: Track if you're staying within the <$20/month target
4. **User Transparency**: Users can see exactly what each interaction costs
5. **Cost Optimization**: Compare token usage across different query patterns

## Future Enhancements

Potential improvements:
- Cumulative session cost tracking
- Per-user cost summaries
- Cost alerts when exceeding thresholds
- Daily/weekly cost reports
- Token usage analytics dashboard
