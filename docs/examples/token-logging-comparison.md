# Token Logging: Before vs After

## Before: Hidden Token Usage

Token usage was logged in structured metadata but **NOT visible** in console:

```
2025-11-05 16:30:18 | INFO     | linear_chief.agent.conversation_agent | Generating conversation response
2025-11-05 16:30:21 | INFO     | linear_chief.agent.conversation_agent | Conversation response generated successfully
```

**Problem**: User has no idea how many tokens were used or what it cost!

The token data existed in the `extra` field but wasn't displayed:
```python
extra={
    "input_tokens": 1234,
    "output_tokens": 567,
    "total_tokens": 1801,
    # No cost field!
}
```

## After: Visible Token Usage

Token usage is **now visible** in every log message:

```
2025-11-05 16:30:18 | INFO     | linear_chief.agent.conversation_agent | Generating conversation response
2025-11-05 16:30:21 | INFO     | linear_chief.agent.conversation_agent | Conversation response generated successfully (tokens: 1234 in, 567 out, 1801 total, cost: $0.0122)
```

**Benefits**:
- See exact token counts (input/output/total)
- See cost immediately ($0.0122)
- Track costs in real-time
- Debug expensive queries

The token data is also preserved in structured metadata:
```python
extra={
    "input_tokens": 1234,
    "output_tokens": 567,
    "total_tokens": 1801,
    "cost_usd": 0.0122,  # Now included!
    "model": "claude-sonnet-4-20250514",
}
```

## Real-World Examples

### Example 1: Short Conversation

**Before**:
```
2025-11-05 09:15:23 | INFO | linear_chief.agent.conversation_agent | Conversation response generated successfully
```

**After**:
```
2025-11-05 09:15:23 | INFO | linear_chief.agent.conversation_agent | Conversation response generated successfully (tokens: 345 in, 78 out, 423 total, cost: $0.0022)
```

**Analysis**: Small query, only $0.0022 - very cheap!

---

### Example 2: Daily Briefing

**Before**:
```
2025-11-05 09:00:12 | INFO | linear_chief.agent.briefing_agent | Briefing generated successfully
```

**After**:
```
2025-11-05 09:00:12 | INFO | linear_chief.agent.briefing_agent | Briefing generated successfully (tokens: 3500 in, 1200 out, 4700 total, cost: $0.0285)
```

**Analysis**: Typical briefing costs $0.0285 - within budget!

---

### Example 3: Complex Query with Context

**Before**:
```
2025-11-05 14:22:10 | INFO | linear_chief.agent.conversation_agent | Conversation response generated successfully
```

**After**:
```
2025-11-05 14:22:10 | INFO | linear_chief.agent.conversation_agent | Conversation response generated successfully (tokens: 2100 in, 450 out, 2550 total, cost: $0.0138)
```

**Analysis**: Longer context = more input tokens = higher cost

---

### Example 4: Telegram Conversation Flow

**Complete interaction showing token tracking**:

```
2025-11-05 16:30:18 | INFO | linear_chief.telegram.handlers | Received user query
2025-11-05 16:30:18 | INFO | linear_chief.agent.context_builder | Building conversation context
2025-11-05 16:30:19 | INFO | linear_chief.agent.conversation_agent | Generating conversation response
2025-11-05 16:30:21 | INFO | linear_chief.agent.conversation_agent | Conversation response generated successfully (tokens: 1234 in, 567 out, 1801 total, cost: $0.0122)
2025-11-05 16:30:21 | INFO | linear_chief.telegram.handlers | Sent intelligent response to user query
```

**User can see**: This conversation cost $0.0122

---

## Budget Tracking Example

With visible logging, track daily costs:

```bash
# Morning briefing
09:00:12 | Briefing generated (tokens: 3500 in, 1200 out, 4700 total, cost: $0.0285)

# User queries throughout the day
10:15:23 | Conversation response (tokens: 345 in, 78 out, 423 total, cost: $0.0022)
11:30:45 | Conversation response (tokens: 890 in, 234 out, 1124 total, cost: $0.0062)
14:22:10 | Conversation response (tokens: 2100 in, 450 out, 2550 total, cost: $0.0138)
16:45:32 | Conversation response (tokens: 567 in, 123 out, 690 total, cost: $0.0035)

# Daily total: ~$0.0542 (well under $0.67/day budget for <$20/month)
```

## Cost Formula (Visible in Code)

```python
def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
    """
    Estimate cost of API call.

    Pricing for Claude Sonnet 4 (as of Nov 2024):
        - Input: $3.00 per million tokens
        - Output: $15.00 per million tokens
    """
    input_cost = (input_tokens / 1_000_000) * 3.00
    output_cost = (output_tokens / 1_000_000) * 15.00
    return input_cost + output_cost
```

**Example calculation**:
- 1234 input tokens: (1234 / 1,000,000) × $3.00 = $0.0037
- 567 output tokens: (567 / 1,000,000) × $15.00 = $0.0085
- **Total**: $0.0037 + $0.0085 = **$0.0122**

## Impact on User Experience

### Before
- User has no visibility into costs
- Can't debug expensive queries
- No way to track budget in real-time
- Must wait for monthly bill

### After
- Immediate cost visibility
- Can identify expensive patterns
- Track budget daily
- Optimize queries based on token usage
- Feel confident about staying under budget

## Implementation Details

### Changed Files

1. **`src/linear_chief/agent/conversation_agent.py`**
   - Added `cost_usd` calculation before logging
   - Updated log message to include token counts and cost
   - Preserved structured metadata in `extra` field

2. **`src/linear_chief/agent/briefing_agent.py`**
   - Same changes as conversation_agent.py
   - Ensures consistent format across all agents

### Code Pattern

```python
# Calculate cost
cost_usd = self.estimate_cost(
    response.usage.input_tokens,
    response.usage.output_tokens,
)

# Log with visible token usage
logger.info(
    f"Response generated successfully "
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

### Benefits of This Pattern

1. **Visible in console**: Token counts and cost in log message text
2. **Structured data**: All data preserved in `extra` for JSON logging
3. **Consistent format**: Same format across all agents
4. **Cost-aware**: Shows cost immediately, not just tokens
5. **Debugging**: Easy to spot expensive queries
6. **Budget tracking**: Know if you're staying under $20/month

## Testing

Run the test script to see example output:

```bash
python test_token_logging.py
```

Expected output:
```
================================================================================
Testing ConversationAgent Token Logging
================================================================================

2025-11-05 16:30:18 | INFO | linear_chief.agent.conversation_agent | Generating conversation response
2025-11-05 16:30:21 | INFO | linear_chief.agent.conversation_agent | Conversation response generated successfully (tokens: 345 in, 78 out, 423 total, cost: $0.0022)

Response length: 234 chars
Check the log output above for token usage details!

================================================================================
Testing BriefingAgent Token Logging
================================================================================

2025-11-05 16:32:05 | INFO | linear_chief.agent.briefing_agent | Generating briefing
2025-11-05 16:32:12 | INFO | linear_chief.agent.briefing_agent | Briefing generated successfully (tokens: 3500 in, 1200 out, 4700 total, cost: $0.0285)

Briefing length: 1456 chars
Check the log output above for token usage details!
```
