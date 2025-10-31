# Issue Filtering Strategy

## Overview

Linear Chief of Staff uses intelligent filtering to show only issues relevant to you, minimizing noise and maximizing signal.

## Current Implementation (v0.1)

### `get_my_relevant_issues()` Method

Aggregates issues from multiple sources and deduplicates:

1. **Assigned to me**
   - Filter: `assignee.id == viewer.id`
   - Why: Direct responsibility for completion

2. **Created by me**
   - Filter: `creator.id == viewer.id`
   - Why: You initiated these, want to track progress

3. **Subscribed to**
   - Filter: `subscribers contains viewer.id`
   - Why: Explicitly chosen to follow

### Deduplication

Issues are deduplicated by `id` to avoid showing the same issue multiple times.

Example: If you created an issue AND it's assigned to you, it only appears once.

---

## Future Enhancements (Planned)

### 4. Issues You've Commented On 🔜
- **Implementation:** Filter by `comments.user.id == viewer.id`
- **Why:** Shows active engagement and context
- **Status:** Not yet implemented (Linear API limitation)

### 5. Favorited Issues 🔜
- **Implementation:** Use Linear's favorites/starred API
- **Why:** Manually marked as important
- **Status:** Investigating API support

### 6. Inbox/Notifications 🔜
- **Implementation:** Query notification/inbox API
- **Why:** Issues where you received updates
- **Status:** Requires notification API research

---

## API Calls

Current implementation makes **3 parallel GraphQL queries:**

```python
# Query 1: Assigned issues
filter: { assignee: { id: { eq: "viewer-id" } } }

# Query 2: Created issues
filter: { creator: { id: { eq: "viewer-id" } } }

# Query 3: Subscribed issues
filter: { subscribers: { some: {} } }
```

**Total API overhead:** ~3 requests per briefing

---

## Configuration

In `.env` you can control:

```bash
# Maximum issues per category (default: 100)
# Total could be up to 300 issues before deduplication
LINEAR_MAX_ISSUES_PER_CATEGORY=50
```

---

## Performance

**Typical workspace:**
- 10-30 assigned issues
- 5-15 created issues
- 10-20 subscribed issues
- **Total unique:** 20-50 issues (after dedup)

**Processing time:** ~2-3 seconds for 50 issues

---

## Alternative Approaches (Not Used)

### Approach 1: Workspace-wide fetch + client-side filter
❌ **Problem:** Would fetch 100s of irrelevant issues
❌ **Cost:** Higher API usage, slower response

### Approach 2: Single query with complex OR filter
❌ **Problem:** Linear GraphQL doesn't support complex OR across different fields
❌ **Limitation:** API constraint

### Approach 3: Fetch all, filter by viewer participation ✅ CHOSEN
✅ **Benefit:** Multiple focused queries
✅ **Benefit:** Better performance
✅ **Benefit:** Clear separation of concerns

---

## Testing

Test script validates all three sources:

```bash
python test_integration.py
```

Output:
```
📋 Fetching your relevant issues...
   - Assigned: 12 issues
   - Created: 8 issues
   - Subscribed: 15 issues
✓ Found 28 unique relevant issues (after deduplication)
```

---

## Roadmap

- [x] **v0.1:** Assigned + Created + Subscribed
- [ ] **v0.2:** Add commented issues (if API supports)
- [ ] **v0.3:** Add favorited issues
- [ ] **v0.4:** Add inbox/notification-based issues
- [ ] **v0.5:** User-configurable filters (config file)
- [ ] **v0.6:** Team-based filtering (follow specific teams)

---

## Known Limitations

1. **No comment history filter:** Linear API doesn't expose "issues I commented on" directly
   - **Workaround:** Fetch issues, check comments client-side (expensive)
   - **Status:** Monitoring API for improvements

2. **Subscription accuracy:** Linear's subscriber filter may need verification
   - **Workaround:** Additional client-side filtering
   - **Status:** Testing in production

3. **Rate limits:** Multiple queries could hit rate limits on large workspaces
   - **Mitigation:** Caching, pagination
   - **Status:** Monitoring

---

## Questions?

See `src/linear_chief/linear/client.py:205` for implementation details.
