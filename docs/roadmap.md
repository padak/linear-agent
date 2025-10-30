# Linear Chief of Staff - Roadmap

## MVP (Week 1-4): Morning Digest with Full-Featured mem0

### Core Features
- ✅ Morning briefing (9 AM daily) via Telegram
- ✅ Linear issue tracking (assigned + watched)
- ✅ Issue analysis (blocked, stale, active)
- ✅ Intelligent ranking (top 3-10 issues)
- ✅ **Full-featured mem0 integration:**
  - Agent context persistence (briefing history)
  - User preference learning (topics, teams, labels)
  - Interaction tracking (Telegram queries, feedback)
  - Semantic search (embeddings for similar issues)
- ✅ Telegram delivery with Markdown formatting

### Tech Stack (Locked-in)
- Python 3.11, async/await
- Anthropic Agent SDK / Messages API
- APScheduler (primary scheduling)
- SQLite + WAL mode
- mem0 (persistent memory)
- sentence-transformers (embeddings)
- ChromaDB (vector search)
- python-telegram-bot

### Out of MVP
- ❌ Web dashboard
- ❌ Multi-user support
- ❌ Cloud deployment (start local)

---

## Post-MVP: Conversational & Interactive

### Phase 2: Telegram Bidirectional (Week 5-6)
**Goal:** Transform Telegram into interactive interface

**Features:**
- **Conversational queries:**
  - "What's blocked?"
  - "Show me stale issues"
  - "What did I miss today?"
- **Inline keyboards:**
  - 👍/👎 feedback per issue
  - "Show details" button → expanded view
  - "Mark as reviewed" action
- **Natural language commands:**
  - "Remind me about ENG-123 tomorrow"
  - "Set priority high on ENG-456"
  - "Summarize last week's progress"

**mem0 Integration:**
- Track which queries user asks most
- Learn from 👍/👎 feedback
- Personalize future briefings based on engagement

**Implementation:**
- Update Telegram bot with message handlers
- Add conversation state management
- Integrate mem0 feedback loop
- ~20-30 hours

---

## Phase 3: Web Dashboard (Week 7-10)
**Goal:** Visualize trends and preferences

**Features:**
- **Issue Dashboard:**
  - All tracked issues (filterable by state, label, team)
  - Trend charts (blocked over time, stale count)
  - Historical briefings archive
- **Preference Heatmap:**
  - Topics you engage with most (backend 40%, API 30%, etc.)
  - Team focus areas (visual breakdown)
  - Label cloud (sized by frequency)
- **Memory Inspector:**
  - View what mem0 knows about you
  - Edit preferences manually
  - Export/import memory snapshots

**Tech Stack:**
- FastAPI or Flask (backend)
- React or Svelte (frontend)
- TailwindCSS (styling)
- Hosted on same server as agent

**Implementation:**
- Build API endpoints for data access
- Create simple SPA dashboard
- Integrate with existing mem0 data
- ~40-60 hours

---

## Phase 4: Advanced Intelligence (Week 11-14)
**Goal:** Predictive analytics and proactive suggestions

**Features:**
- **Velocity tracking:**
  - "Issue ENG-123 has been 'In Progress' for 2 weeks, typical completion time is 5 days → flag as at-risk"
- **Dependency detection:**
  - Parse issue descriptions for mentions of other issues
  - Build dependency graph
  - Alert when blocking issue is resolved
- **Team collaboration insights:**
  - "You and @teammate are both working on authentication → suggest sync meeting"
- **Automated triage:**
  - Suggest labels based on issue content (using embeddings)
  - Recommend assignees based on historical patterns

**mem0 Integration:**
- Store historical velocity data
- Track collaboration patterns
- Learn from past triage decisions

**Implementation:**
- NLP for dependency extraction
- Graph database for dependencies (Neo4j or networkx)
- Advanced embeddings (fine-tuned on Linear data)
- ~60-80 hours

---

## Future Considerations

### Multi-User (Phase 5)
- Team-level briefings
- Role-based perspectives (manager vs. IC)
- Shared mem0 memory (team preferences)

### Integrations (Phase 6)
- GitHub (cross-reference PRs with Linear issues)
- Slack (post briefings to channel)
- Jira/Asana (multi-tool monitoring)

### Mobile App (Phase 7)
- Native iOS/Android app
- Push notifications
- Offline briefing cache

---

## Timeline Summary

| Phase | Duration | Effort | Status |
|-------|----------|--------|--------|
| MVP | 4 weeks | 40-60h | 🚧 Planning |
| Phase 2: Conversational | 2 weeks | 20-30h | ⏳ Planned |
| Phase 3: Web Dashboard | 4 weeks | 40-60h | ⏳ Planned |
| Phase 4: Advanced Intelligence | 4 weeks | 60-80h | ⏳ Planned |

**Total to Phase 4:** ~14 weeks, 160-230 hours

---

## Success Metrics

### MVP Success Criteria
1. ✅ Saves 10+ minutes per morning vs manual Linear checking
2. ✅ Agent runs 7+ consecutive days without crashes
3. ✅ Briefing quality: 70%+ relevance (subjective, daily journal)
4. ✅ Cost: <$20/month Anthropic API usage
5. ✅ Learning: Deep understanding of Agent SDK + mem0 patterns

### Post-MVP Metrics
- **Phase 2:** 80%+ user queries answered correctly
- **Phase 3:** Dashboard used 3+ times per week
- **Phase 4:** Predictive alerts reduce missed blockers by 50%

---

## Decision Log

### Why Full-Featured mem0 in MVP?
**Rationale:** AI agent can implement complex features as easily as simple ones. No reason to artificially limit scope when the architecture is already designed for it.

**Trade-off:** Slightly higher Week 1 complexity, but we learn mem0 patterns immediately instead of retrofitting later.

### Why Telegram First, Web Second?
**Rationale:** Telegram is zero-friction delivery (user already has app). Web dashboard adds visual value but isn't critical for core workflow.

**Trade-off:** Web dashboard deferred to Phase 3, but briefings are usable from Day 1.

### Why APScheduler Instead of Agent SDK Scheduling?
**Rationale:** De-risks MVP. APScheduler is proven, Agent SDK scheduling is unvalidated. Week 1 spike will determine if Agent SDK can replace it.

**Trade-off:** Slightly more code (APScheduler integration), but guaranteed to work.
