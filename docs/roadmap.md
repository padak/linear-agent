# Linear Chief of Staff - Roadmap

## MVP (Week 1-4): Morning Digest with Basic Context

### Core Features
- ✅ Morning briefing (9 AM daily) via Telegram
- ✅ Linear issue tracking (assigned + watched)
- ✅ Issue analysis (blocked, stale, active)
- ✅ Intelligent ranking (top 3-10 issues)
- ✅ **Basic agent context (MVP scope):**
  - Agent context persistence (7-day briefing history in SQLite)
  - NO preference learning, NO semantic search, NO embeddings (Phase 2+)
- ✅ Telegram delivery with Markdown formatting

### Tech Stack (Locked-in for MVP)
- Python 3.11, async/await
- Anthropic Claude Messages API (Agent SDK optional, to be validated in Week 1 spike)
- APScheduler (ONLY scheduling mechanism)
- SQLite + WAL mode (ONLY data store)
- python-telegram-bot

### Out of MVP (Moved to Phase 2+)
- ❌ mem0 / preference learning → Phase 2
- ❌ sentence-transformers / embeddings → Phase 2
- ❌ ChromaDB / vector search → Phase 2
- ❌ Telegram feedback (👍/👎) → Phase 2
- ❌ Web dashboard → Phase 3
- ❌ Multi-user support → Phase 4+
- ❌ Cloud deployment (start local, deploy later)

---

## Post-MVP: Conversational & Interactive

### Phase 2: Learning & Bidirectional Telegram (Week 5-8)
**Goal:** Add preference learning, semantic search, and interactive Telegram

**Features Added:**
1. **Preference Learning (mem0):**
   - Topic preferences (backend vs. frontend)
   - Team/label prioritization
   - Historical engagement patterns
   - Adjusts IssueRanker based on learned prefs

2. **Semantic Search (embeddings):**
   - sentence-transformers for issue embeddings
   - ChromaDB for vector storage
   - "Show me issues similar to ENG-123"
   - Automatic duplicate detection

3. **Bidirectional Telegram:**
   - Conversational queries: "What's blocked?"
   - Inline keyboards: 👍/👎 feedback per issue
   - Natural language commands: "Remind me about ENG-123"
   - Conversation state management

**Implementation:**
- Add mem0 / custom preference store
- Integrate sentence-transformers + ChromaDB
- Update Telegram bot with message handlers
- Implement feedback tracking
- ~40-50 hours (more complex than original Phase 2)

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

## MVP Go/No-Go Criteria

Before proceeding from MVP to Phase 2, validate:

**Must Have (Hard Requirements):**
1. ✅ 7 consecutive days of successful briefings (99% uptime = max 1 miss)
2. ✅ Cost < $20/month for 30 briefings (actual measured, not estimated)
3. ✅ Briefing generation < 30 seconds for 50 issues (instrumented timing)
4. ✅ No critical bugs in Week 1 usage (agent crashes, data loss, API failures)

**Should Have (Quality Indicators):**
5. 📊 Briefing relevance ≥ 70% (manual daily rating in journal)
6. ⏱️ Saves ≥ 10 minutes per morning vs. manual Linear checking
7. 🧠 Agent context continuity works (references previous briefings correctly)

**Decision Gate:**
- **All "Must Have" met → Proceed to Phase 2**
- **≥ 3 "Must Have" met + 2 "Should Have" → Proceed with caution, document gaps**
- **< 3 "Must Have" → Pivot or stop (MVP assumptions invalid)**

**Phase 2 Go/No-Go (after 2-3 weeks):**
- Bidirectional Telegram works reliably (queries answered correctly 80%+ of time)
- Preference learning shows measurable improvement (relevance increases 10%+)
- No cost explosion from added features (< $50/month)

---

## Decision Log

### Why Reduced mem0 Scope for MVP?
**Original Plan:** Full-featured mem0 with preference learning, embeddings, semantic search
**Revised Plan:** Basic context only (SQLite), defer ML features to Phase 2

**Rationale:**
- Embeddings/vectors add significant complexity (ChromaDB, model management)
- Preference learning requires data collection period (no data on Day 1)
- **MVP goal:** Validate core workflow first, add intelligence later

**Trade-off:** Less "intelligent" MVP, but faster to implement and validate. ML features moved to Phase 2 where they have data to learn from.

### Why Telegram First, Web Second?
**Rationale:** Telegram is zero-friction delivery (user already has app). Web dashboard adds visual value but isn't critical for core workflow.

**Trade-off:** Web dashboard deferred to Phase 3, but briefings are usable from Day 1.

### Why APScheduler Instead of Agent SDK Scheduling?
**Rationale:** De-risks MVP. APScheduler is proven, Agent SDK scheduling is unvalidated. Week 1 spike will determine if Agent SDK can replace it.

**Trade-off:** Slightly more code (APScheduler integration), but guaranteed to work.
