# Project Brief: Linear Chief of Staff

## Executive Summary

**Linear Chief of Staff** is a personal learning project to explore Anthropic's Agent SDK through building an intelligent monitoring agent for Linear. It will autonomously track issues you care about, analyze their momentum, and deliver proactive intelligence briefings via Telegram.

**Primary Goal:** Learn how to build autonomous AI agents using Anthropic's Agent SDK by solving a real personal problem—maintaining awareness across Linear issues without manual checking.

**Personal Problem:** You spend 1-2 hours daily manually checking Linear for updates across multiple issues, teams, and projects. Linear's native notifications create noise fatigue while still missing the bigger picture of what truly needs attention.

**Learning Focus:** This is not a commercial product. The goal is to gain hands-on experience with:
- Anthropic Agent SDK architecture and capabilities
- Autonomous agent patterns (scheduling, persistent memory, tool use)
- Real-world LLM cost modeling and optimization
- Building an AI system that runs 24/7 with minimal supervision

**Success Definition:** Successfully build a working agent that saves you time AND teaches you how to architect autonomous AI systems using modern agent frameworks.

---

## Problem Statement

### Your Current Pain Points

You face a persistent challenge in maintaining awareness across your Linear workspace:

**Manual Context Gathering:** Every morning (and throughout the day), you open Linear and manually check:
- Issues assigned to you across multiple projects
- Issues you're mentioned in or watching
- Team members' progress on dependencies
- Blocked issues requiring escalation
- Stale issues that haven't moved in days

This routine consumes **15-30 minutes per check, 2-3 times daily** = ~1-2 hours of pure overhead.

**Information Fragmentation:** Critical information is scattered:
- Linear notifications (too noisy, miss patterns)
- Slack threads (context lost)
- Direct messages (ad-hoc, unsystematic)
- Standup meetings (once daily, often outdated)

**Reactive vs. Proactive:** You discover problems *after* they've impacted timelines—blocked issues sit for days, dependencies slip unnoticed, and you're always playing catch-up rather than staying ahead.

### Why This is a Good Learning Vehicle

This problem is ideal for exploring agent architectures because it requires:
- **Autonomous operation:** Agent must run continuously without manual intervention
- **Intelligent reasoning:** Determining what's "important" vs "noise" requires LLM reasoning, not just rules
- **Persistent memory:** Tracking changes over time ("what's new since last briefing")
- **Tool integration:** Combining Linear API, Telegram, and AI in a cohesive system
- **Cost optimization:** Real-world constraints force smart prompt engineering and caching strategies

**Note:** Time estimates (1-2 hours/day) are personal observations, not validated research. The key is that the problem is *real enough* to be motivating and *complex enough* to teach agent SDK patterns.

### Why Build This (vs. Use Existing Tools)

**Linear's Native Notifications:**
- Too granular → notification fatigue
- No intelligent prioritization or pattern recognition

**This is primarily a learning project, not because existing tools are inadequate, but because building it teaches:**
- How to architect autonomous agents that run 24/7
- Real-world trade-offs in LLM-based systems (cost, latency, accuracy)
- Integrating multiple APIs (Linear, Telegram, Anthropic) into cohesive workflows

**Why Now:**
- **Anthropic Agent SDK** (2024-2025) is new and represents a significant shift in how to build autonomous AI systems
- Best way to learn new technology is by building something real
- The problem is personal and immediate, providing fast feedback loops for learning

---

## Learning Objectives

### Primary: Master Anthropic Agent SDK

**Critical questions to answer through this project:**
1. **Scheduling & Autonomy:** How does the Agent SDK handle long-running processes? Does it support cron-like scheduling, or do we need external orchestration?
2. **Persistent Memory:** How to maintain state across agent invocations (briefing history, user preferences, issue tracking)?
3. **Tool Integration:** Best practices for integrating external APIs (Linear, Telegram) as agent "tools"
4. **Cost Modeling:** Real-world token usage patterns—how much does continuous monitoring actually cost?
5. **Error Handling:** How to build resilient agents that handle API failures, rate limits, and edge cases gracefully?

### Secondary: Real-World AI System Design

- **Prompt Engineering:** Crafting prompts that reliably produce structured intelligence briefings
- **Context Management:** Strategies for staying within context windows while tracking many issues
- **Evaluation:** How to measure and improve "briefing quality" without labeled datasets
- **Observability:** Logging, monitoring, and debugging autonomous agents in production

### Validation Before Full Build

**Codex identified critical unknowns—validate these FIRST:**
- [ ] Agent SDK supports scheduled execution OR identify orchestration approach
- [ ] Agent SDK persistent memory patterns OR design custom state management
- [ ] Cost modeling: estimate tokens per briefing (aim for <$100/month)
- [ ] Linear API rate limits: confirm polling strategy won't hit limits

**Week 1 spike goal:** Prototype minimal agent that can reason about Linear issues and generate a single briefing. This validates core SDK assumptions before investing in full build.

---

## Proposed Solution

### Core Concept and Approach

**Linear Chief of Staff** is an autonomous AI agent that acts as your intelligent monitoring layer between you and Linear. Built on Anthropic's Agent SDK, it:

1. **Continuously monitors** your Linear workspace for activity on issues you care about
2. **Reasons intelligently** about what's important, what's changing, and what needs attention
3. **Delivers proactive briefings** twice daily via Telegram with actionable insights
4. **Responds conversationally** to ad-hoc queries when you need immediate information

**The "Chief of Staff" Mental Model:**
Like a human chief of staff, the agent:
- Knows what you care about (learns your interests and priorities)
- Monitors the situation continuously (tracks Linear activity 24/7)
- Filters noise intelligently (only surfaces what matters)
- Provides context and recommendations (not just raw data)
- Responds to your questions proactively (conversational interface)

### Key Differentiators from Existing Solutions

**1. True Intelligence vs. Rule-Based Filtering**
- Uses Anthropic's Agent SDK for reasoning and decision-making
- Understands context: "This issue has been 'In Progress' for 5 days with no comments" → signals stagnation
- Adapts to your patterns: learns which issues you engage with most

**2. Proactive Intelligence Briefings vs. Reactive Notifications**
- Scheduled digests (2x daily) with synthesized insights
- Trend analysis: "3 backend issues are blocked on the same infrastructure dependency"
- Momentum tracking: "Frontend work is progressing well, but API integration has stalled"

**3. Conversational Interface vs. Static Dashboards**
- Natural language queries: "What's blocked on my team?", "Show me stale issues"
- Context-aware responses using Linear data and conversation history
- Telegram delivery for friction-free access (no need to open Linear)

**4. Autonomous Operation vs. Manual Monitoring**
- Runs continuously on cloud infrastructure (EC2/Digital Ocean)
- Works while you're offline, sleeping, or focused on other tasks
- Zero configuration after initial setup—just works

### Why This Solution Will Succeed Where Others Haven't

**Timing is Right:**
- **Anthropic Agent SDK** provides the reasoning capabilities that simple webhook automation lacks
- **LLM context windows** (100K+ tokens) can hold entire project histories for intelligent analysis
- **Agent architectures** (tool use, memory, planning) enable truly autonomous operation

**Technical Feasibility:**
- Linear's GraphQL API provides comprehensive data access
- Telegram Bot API is mature, reliable, and developer-friendly
- Cloud infrastructure (EC2/DO) offers always-on reliability at low cost
- Anthropic's infrastructure handles the AI heavy lifting

**User Experience Advantage:**
- Meets users where they are (Telegram) vs. requiring new tool adoption
- Balances push (briefings) and pull (queries) interaction models
- Provides immediate value without lengthy configuration

### High-Level Vision for the Product

**Phase 1 (MVP):** Personal Chief of Staff
- Monitors issues assigned to you or that you're watching
- Delivers 2x daily briefings with momentum analysis
- Supports basic conversational queries
- Single-user deployment

**Phase 2:** Team Intelligence Layer
- Multi-user support with role-based perspectives
- Team-level insights: "Your team has 5 blocked issues"
- Escalation routing: automatically notifies relevant people
- Shared agent memory across team members

**Phase 3:** Strategic Intelligence Platform
- Cross-project pattern recognition
- Predictive analytics: "This epic is likely to miss deadline based on current velocity"
- Integration with other tools (GitHub, Slack, Jira)
- Enterprise deployment model

---

## Target User

**Primary User: You**

This is a personal project. You are the only user for MVP.

**Your Context:**
- Engineering leader/senior contributor managing multiple concurrent initiatives
- Opens Linear 5-15 times per day to check status across projects
- Maintains mental map of 10-30 active issues across teams
- Spends 15-30 minutes each morning "getting context"

**Your Specific Needs:**
- **Situational Awareness:** Know what's happening without manual checking
- **Early Warning System:** Catch blockers before they impact timelines
- **Cognitive Load:** Reduce mental burden of tracking many issues
- **Time Efficiency:** Can't afford 1-2 hours daily on status gathering

**Why This Makes a Good Learning Project:**
- Problem is real and immediate (personal pain)
- Fast feedback loops (you use it daily)
- Complexity is appropriate for learning Agent SDK
- Can iterate based on your own needs without external stakeholder management

---

## Goals & Success Metrics

### Primary Goal: Learning

**Successfully learn how to build autonomous AI agents using Anthropic Agent SDK.**

Success means you can confidently:
- Architect agent systems with scheduling, memory, and tool integration
- Model and optimize LLM costs for production workloads
- Debug and monitor autonomous agents in the wild
- Make informed design decisions about agent architectures

### Secondary Goal: Personal Utility

**Build a working tool that saves you time and reduces cognitive load.**

Success metrics:
- Saves 10+ minutes per morning vs manual Linear checking
- Reduces anxiety about "missing something important"
- Runs reliably for 7+ consecutive days
- Briefings are good enough that you actually read them

### Learning Metrics (Track These)

- **Token usage per briefing:** Actual cost in tokens/$ (target: <$100/month)
- **API call patterns:** How many Linear API calls per briefing? Are we hitting rate limits?
- **Agent SDK limitations discovered:** What features are missing? What workarounds were needed?
- **Time spent debugging:** Where did complexity hide? What was harder than expected?
- **Architectural decisions:** What patterns emerged? What would you do differently next time?

### Personal Utility Metrics

- **Time saved:** Estimate minutes saved per day vs manual checking
- **Briefing quality:** Subjective assessment of relevance (daily journal)
- **Reliability:** Days of consecutive operation without intervention
- **Trust:** Are you checking Linear less? Do you trust the briefings?

---

## MVP Scope

### Simplified Scope (Based on Codex Feedback)

**Codex Warning:** Original scope (tracking + analytics + briefings + conversation + autonomous hosting) in 40-80 hours is unrealistic. **Focus on ONE success workflow first.**

**MVP v1: Morning Digest Only**

- **Linear Issue Tracking:** Fetch all issues assigned to you or explicitly watched
- **Single Daily Briefing:** One morning briefing (9:00 AM) delivered via Telegram with:
  - Issues with activity in last 24 hours (comments, status changes)
  - Issues marked as "Blocked" (explicit label detection)
  - Issues stale for 3+ days (simple heuristic: no updates, still "In Progress")
  - Brief 1-2 sentence summary per flagged issue
  - **Ranking by relevance:** Top 3-10 issues ranked using IssueRanker scoring
- **Preference Learning (mem0):** Agent tracks which issues you engage with and learns your interests:
  - Topic preferences (backend vs. frontend, features vs. bugs)
  - Team/project focus areas
  - Historical briefing quality feedback
  - Semantic search using embeddings to find similar issues
- **Simple Scheduling:** APScheduler (locked-in decision, not Agent SDK native)
- **Local Development First:** Run on local machine before deploying to cloud
- **Manual trigger capability:** Script to generate on-demand briefing for testing

**Explicitly OUT of MVP v1:**
- ❌ Conversational queries (add in v2 after briefings work)
- ❌ Twice-daily briefings (start with morning only)
- ❌ Cloud deployment (validate locally first)
- ❌ Advanced momentum analysis (use rule-based heuristics + semantic similarity)

### Out of Scope for MVP

- Multi-user support (single user only for MVP)
- Team-level analytics or rollups
- Predictive modeling or ML-based prioritization
- Integration with GitHub, Slack, or other tools beyond Linear/Telegram
- Mobile app (Telegram is the interface)
- Advanced NLP or deep semantic understanding of issue content
- Customizable briefing schedules (fixed 2x daily for MVP)
- Historical trend analysis or reporting dashboards
- Webhook-based real-time push (periodic polling is acceptable for MVP)

### MVP Success Criteria

**The MVP is successful if it achieves BOTH learning AND functional goals:**

**Learning Goals (Primary):**
1. ✅ Understand Agent SDK architecture: scheduling, memory, tool use patterns
2. ✅ Validate cost model: actual token usage for briefing generation
3. ✅ Identify Agent SDK limitations and workarounds needed
4. ✅ Build confidence in deploying autonomous agents to production

**Functional Goals (Secondary):**
1. Agent correctly fetches all watched/assigned issues from Linear
2. Morning briefing surfaces 3-10 relevant items (blocked, active, stale)
3. Briefing saves at least 10 minutes vs manual Linear checking
4. Agent runs for 7+ consecutive days without crashes
5. Telegram delivery is reliable (±5 minutes of scheduled time)

**Success means:** You learned how to architect agent systems AND built something personally useful. If briefings are mediocre but you deeply understand Agent SDK capabilities/limits, that's still a win.

---

## Post-MVP Vision (If This Goes Well)

**This section is speculative—focus is on learning, not building a product.**

If the MVP is successful (both as learning tool and personal utility), potential v2 features:

**Enhanced Agent Capabilities:**
- Conversational queries via Telegram ("What's blocked?")
- Twice-daily briefings (morning + evening)
- More sophisticated momentum analysis (not just "stale" heuristics)

**Potential Expansion (Learning Opportunities):**
- Multi-user deployment (learn about user management, RBAC)
- Team-level insights (aggregation, different perspectives)
- Integration with other tools (GitHub, Slack) to learn multi-API orchestration

**Commercial Possibility:**
If this proves valuable, could explore:
- Open-sourcing the framework for others to learn from
- Offering as SaaS for engineering teams
- Building generalized "monitoring agent framework" for any tool

**But for now:** Focus is 100% on learning Agent SDK through building a working MVP.

---

## Technical Considerations

### Platform Requirements

- **Target Platforms:** Cloud-hosted agent (EC2 or Digital Ocean VPS)
- **Operating Environment:** Linux server (Ubuntu 22.04 LTS or similar)
- **External Dependencies:**
  - Linear API access (GraphQL)
  - Telegram Bot API access
  - Anthropic API access (Claude + Agent SDK)
  - Persistent storage (SQLite or PostgreSQL for agent state/memory)
- **Performance Requirements:**
  - Briefing generation: <30 seconds for 50 tracked issues
  - Query response: <10 seconds end-to-end
  - Polling interval: Check Linear every 5-15 minutes for updates
  - Memory footprint: <512MB RAM for single-user deployment

### Technology Preferences

**Language & Framework:**
- **Primary Choice: Python** (best Anthropic SDK support, mature Linear/Telegram libraries)
  - Alternative: TypeScript/Node.js (if Linear SDK is significantly better)
  - Decision criteria: Choose based on SDK quality and async operation support

**Key Libraries:**
- **Anthropic Agent SDK:** Core intelligence and reasoning engine
- **Linear Python SDK or GraphQL client:** Issue tracking and querying (locked-in: httpx with hand-written GraphQL)
- **python-telegram-bot or equivalent:** Telegram bot interface
- **APScheduler:** Scheduled briefing delivery (locked-in: primary scheduler, not Agent SDK native)
- **SQLAlchemy + SQLite:** State persistence and issue history (WAL mode enabled for concurrency)
- **mem0:** Persistent agent memory and user preference learning
- **sentence-transformers:** Generate semantic embeddings for Linear issues (all-MiniLM-L6-v2 model)
- **ChromaDB:** Vector database for similarity search and preference-based ranking

**Infrastructure:**
- **Hosting:** Digital Ocean Droplet ($12-24/mo) or AWS EC2 t3.small
- **Orchestration:** systemd service for process management
- **Monitoring:** Basic logging + health check endpoint
- **Secrets Management:** Environment variables or AWS Secrets Manager

### Architecture Considerations

**Repository Structure:**
```
linear-chief-of-staff/
├── src/
│   ├── agent/           # Anthropic Agent SDK integration
│   ├── linear/          # Linear API client and issue tracking
│   ├── telegram/        # Telegram bot interface
│   ├── intelligence/    # Analysis logic (momentum, stagnation detection)
│   ├── scheduling/      # Briefing scheduler
│   └── storage/         # Database models and persistence
├── config/              # Configuration templates
├── tests/               # Unit and integration tests
├── docs/                # Documentation
└── deploy/              # Deployment scripts and configs
```

**Service Architecture:**
- **Monolithic for MVP:** Single Python process with multiple async tasks
- **Future consideration:** Microservices if scaling to multi-user requires separation

**Integration Requirements:**
- **Linear API:** OAuth2 authentication, GraphQL queries for issues, webhooks (future)
- **Telegram Bot API:** Bot token authentication, long-polling for messages, message formatting
- **Anthropic API:** API key authentication, streaming responses for real-time query handling

**Security/Compliance:**
- **Data storage:** Issue metadata only (no sensitive code/customer data)
- **Secrets management:** Secure storage of API keys (Linear, Telegram, Anthropic)
- **Access control:** Single-user for MVP (no user authentication needed initially)
- **Logging:** No PII in logs, structured logging for debugging
- **Rate limiting:** Respect Linear API limits (no more than 100 requests/minute)

---

## Constraints & Assumptions

### Constraints

**Budget:**
- **Infrastructure:** ~$25-50/month (Digital Ocean/EC2 + storage)
- **Anthropic API costs:** $50-200/month estimated (depends on usage patterns and context size)
- **Total MVP budget:** <$300/month operational costs
- **Development time:** Solo project, evenings/weekends (~40-80 hours total for MVP)

**Timeline:**
- **MVP target:** 4-6 weeks from start to first working version
- **Phase 1 refinement:** Additional 2-4 weeks for polish and iteration
- **Phase 2 (multi-user):** 3-6 months post-MVP

**Resources:**
- **Team:** Solo developer (you) for MVP
- **Expertise:** Need to learn Anthropic Agent SDK, familiarize with Linear API
- **Support:** Community support only (no enterprise Anthropic/Linear support)

**Technical:**
- **Linear API rate limits:** Must stay within documented limits (exact limits TBD during research)
- **Anthropic context window:** 200K tokens with Claude Sonnet 3.5 (sufficient for MVP)
- **Telegram message limits:** 4096 characters per message (need to chunk long briefings)
- **Network reliability:** Agent must handle transient API failures gracefully
- **No real-time webhooks for MVP:** Polling-based is acceptable, webhooks can come later

### Key Assumptions

- **Anthropic Agent SDK is production-ready** for autonomous monitoring use cases (needs validation)
- **Linear API provides sufficient access** to issue metadata, activity history, and user context
- **Polling every 5-15 minutes is adequate** for detecting issues and changes (not real-time critical)
- **Telegram is acceptable channel** for work-related notifications (security/compliance approved)
- **Single Linear workspace** (no multi-workspace support needed for MVP)
- **English language only** for MVP (Linear issue content and bot responses)
- **User maintains consistent Linear usage patterns** (assigned issues, watch patterns)
- **Stagnation = no activity for 3+ days** is a reasonable heuristic (may need tuning)
- **API costs remain predictable** and within budget constraints
- **No specialized infrastructure required** (standard Linux VPS is sufficient)

---

## Risks & Open Questions

### Critical Technical Risks (From Codex Analysis)

**🔴 HIGH RISK: Agent SDK Capabilities Unknown**
- **Issue:** SDK is treated as turnkey orchestrator, but scheduling, persistent memory, and low-latency responses are "open questions" in the brief
- **Impact:** High - may require significant custom infrastructure, invalidating architecture assumptions
- **Mitigation:**
  - Week 1 spike: Build minimal agent that generates one briefing
  - Validate: Can SDK schedule tasks? How does memory work across invocations?
  - Fallback: External orchestration (cron) + custom state management (SQLite)

**🔴 HIGH RISK: Cost Model Unvalidated**
- **Issue:** No prompt-size modeling exists; single verbose briefing could blow context window and exceed budget
- **Impact:** Could make project economically non-viable (target: <$100/month)
- **Mitigation:**
  - Instrument token usage from Day 1
  - Test with realistic issue counts (50+ issues)
  - Set hard budget alerts ($50, $75, $100)
  - Optimize: Use caching, prompt compression, delta queries

**🟡 MEDIUM RISK: Linear API Rate Limits**
- **Issue:** Polling 50+ issues every 5-15 minutes may exceed rate limits
- **Impact:** Could force less frequent polling or complex caching
- **Mitigation:**
  - Research Linear API limits in Week 1
  - Use delta queries (only fetch changed issues)
  - Start with 15-minute polling, optimize later

**🟡 MEDIUM RISK: Briefing Quality**
- **Issue:** Agent may surface irrelevant issues or miss important ones; no feedback loop planned
- **Impact:** Low personal cost (you'll just ignore bad briefings), but limits learning
- **Mitigation:**
  - Start with simple heuristics (blocked, stale, active)
  - Manually review first 2 weeks of briefings
  - Add explicit feedback mechanism in v2

**🟢 LOW RISK: State Management**
- **Issue:** Tracking "what's changed since last briefing" may be complex
- **Impact:** Manageable with simple approaches
- **Mitigation:** Use Linear's `updatedAt` timestamps + SQLite log of seen states

### Open Questions (To Answer Through Building)

**Agent SDK Architecture:**
- Does SDK support scheduled/cron-like execution, or only request-response?
- How does persistent memory work across invocations?
- What's the best pattern for long-running agents vs. triggered agents?
- How to structure "tools" for Linear API and Telegram?

**Cost & Performance:**
- Actual token usage per briefing generation? (estimate: 5K-20K tokens?)
- How to optimize context: summarize old issues, prune irrelevant data?
- Can we cache issue data to reduce API calls?

**Technical Implementation:**
- Linear GraphQL API directly or official Python SDK?
- How to handle pagination for 100+ watched issues?
- SQLite vs. PostgreSQL for state? (SQLite for MVP simplicity)
- Deployment: Local script, systemd service, or cloud function?

**Briefing UX:**
- Optimal length: 5 issues? 15 issues? Variable?
- Include "no activity" sections or only highlight changes?
- One-line summaries vs. multi-paragraph context?

**Note:** These questions will be answered iteratively through building, not upfront research. The goal is to learn by doing.

### Areas Needing Further Research

**Anthropic Agent SDK Deep Dive:**
- Architecture patterns for autonomous agents (long-running processes, scheduled tasks)
- State management and memory persistence
- Tool integration best practices (Linear API as "tool")
- Error handling and retry strategies
- Cost optimization techniques (prompt engineering, context pruning)

**Linear API Research:**
- Comprehensive endpoint documentation (issues, users, teams, projects, comments)
- Rate limiting policies and best practices
- Webhook availability and reliability (for post-MVP real-time updates)
- OAuth setup and user authentication flow
- GraphQL query optimization (minimize over-fetching)

**Telegram Bot Best Practices:**
- Message formatting (markdown, HTML) for structured briefings
- Conversation state management
- Long-polling vs. webhooks for message receiving
- Security considerations (bot token management, user verification)
- Rich UI elements (inline keyboards, reply buttons)

**Learning from Others:**
- How do existing monitoring tools (GitHub, Jira) architect their agents?
- What can we learn from personal assistant AI products (Motion, Reclaim.ai) about UX patterns?
- Review open-source agent projects for implementation patterns

---

## Next Steps

### Week 1: Validation Spike (Critical)

**Goal:** Validate core Agent SDK assumptions before committing to full build.

**Tasks:**
1. **Agent SDK Deep Dive** (2-3 hours)
   - Read documentation cover-to-cover
   - Find examples of scheduling/long-running agents
   - Understand memory/state management patterns
   - Identify cost optimization strategies

2. **Minimal Prototype** (3-4 hours)
   - Set up Python environment with Anthropic SDK
   - Fetch issues from Linear API (use your personal API key)
   - Build single-prompt agent: "Analyze these Linear issues and generate a brief"
   - Measure token usage

3. **Cost & Feasibility Check** (1 hour)
   - Calculate actual token cost for 50 issues
   - Validate: Can we stay under $100/month?
   - Research Linear API rate limits
   - Document findings and blockers

**Decision Point:** If spike reveals showstoppers (SDK can't schedule, costs are 10x budget, etc.), pivot approach or simplify scope further.

### Week 2-3: MVP Build (If Spike Succeeds)

1. **Core System** (Week 2)
   - Linear API integration (fetch watched/assigned issues)
   - Telegram bot setup (send briefings)
   - Simple scheduling (cron or Agent SDK if supported)
   - SQLite for state tracking

2. **Intelligence Layer** (Week 3)
   - Implement stagnation detection (3+ days no updates)
   - Blocked issue detection (label-based)
   - Briefing generation with Agent SDK
   - Manual testing and iteration

### Week 4: Production & Learning

- Deploy to cloud (EC2/Digital Ocean) or run locally
- Use daily for 1 week
- Document learnings: what worked, what didn't, SDK limitations
- Measure: token costs, API usage, time saved

### Decision Point: Continue or Pivot?

After 4 weeks, evaluate:
- **Did I learn Agent SDK patterns?** (primary goal)
- **Does it save time?** (secondary goal)
- **What would I do differently?** (future projects)

If successful: Consider v2 features (queries, enhanced analysis)
If not: Document lessons and move on

---

