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
1. **Prompt Engineering:** How to craft prompts that reliably produce concise, actionable briefings (1-2 sentences per issue)?
2. **Persistent Memory (mem0):** How to structure memory for agent context + user preferences? What's the right data model?
3. **Cost Optimization:** Real-world token usage patterns—how to stay under $20/month with quality briefings?
4. **Semantic Search:** How to use embeddings effectively for preference learning and issue prioritization?
5. **Error Handling:** How to build resilient agents that handle API failures, rate limits, and edge cases gracefully?

**Locked-in Technology Stack:**
- ✅ **Agent Framework:** Anthropic Agent SDK (LLM reasoning and briefing generation)
- ✅ **Memory Layer:** mem0 (persistent agent context + user preference learning)
- ✅ **Vector Store:** ChromaDB (semantic search and embeddings)
- ✅ **Embeddings:** sentence-transformers (all-MiniLM-L6-v2 model)
- ✅ **Scheduling:** APScheduler (cron-like triggers at 9 AM daily)
- ✅ **Linear API:** httpx with hand-written GraphQL queries

### Secondary: Real-World AI System Design

- **Prompt Engineering:** Crafting prompts that reliably produce structured intelligence briefings
- **Context Management:** Strategies for staying within context windows while tracking many issues
- **Evaluation:** How to measure and improve "briefing quality" without labeled datasets
- **Observability:** Logging, monitoring, and debugging autonomous agents in production

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

**Full-Featured System (No Artificial Phases):**

**Core Capabilities:**
- Monitors issues assigned to you or that you're watching
- Learns your preferences through interaction (topics, teams, labels)
- Semantic search across all issues using embeddings
- Delivers intelligent briefings with momentum analysis and learned prioritization
- Supports conversational queries via Telegram
- Remembers context across briefings and conversations
- Tracks feedback (👍/👎) to improve relevance

**Single-User MVP Scope:**
- Personal deployment (local or cloud VPS)
- Focus on individual workflow optimization
- No team collaboration features (yet)

**Future Expansion Opportunities (Post-MVP):**
- Multi-user support with role-based perspectives
- Team-level insights and escalation routing
- Predictive analytics and cross-project pattern recognition
- Integration with GitHub, Slack, Jira

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

### Full-Featured MVP (AI Agent Implementation = Hours, Not Weeks)

**Philosophy:** With AI agent-assisted implementation, we can build full-featured system from day 1. No artificial limitations or "Phase 2" deferrals.

**Core MVP Features:**

- **Linear Issue Tracking:** Fetch all issues assigned to you or explicitly watched using httpx + GraphQL
- **Intelligent Briefings:** Daily briefings (9:00 AM) delivered via Telegram with:
  - Issues with activity in last 24 hours
  - Blocked issues flagged explicitly
  - Stale issues (3+ days no updates, still "In Progress")
  - Concise 1-2 sentence summaries per issue
  - Learned prioritization using preference data

- **Full Memory & Learning (mem0):**
  - Agent context memory: last 7 days of briefing narratives
  - User preference learning: topics, teams, labels, historical patterns
  - Semantic search: find similar issues using embeddings
  - Feedback tracking: 👍/👎 per issue for refinement
  - Conversation history: multi-turn dialogue context

- **Conversational Interface:** Ask questions via Telegram
  - "What's blocked?"
  - "Show me stale backend issues"
  - "Issues similar to ENG-123"
  - Agent responds with context from mem0

- **Semantic Search:** ChromaDB + sentence-transformers
  - 384-dim embeddings per issue
  - Similarity search and clustering
  - Duplicate detection

- **Scheduling:** APScheduler for cron-like daily triggers
- **Local Development:** Run on local machine before cloud deployment
- **Manual Trigger:** CLI command for on-demand briefings

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
- **Infrastructure:** ~$12-24/month (Digital Ocean Droplet or local machine initially)
- **Anthropic API costs:** <$20/month realistic target
  - Calculation: 30 briefings × ~2K tokens × $0.003/1K tokens = $1.80/month base
  - With conversational queries and experimentation: <$20/month buffer
- **Total MVP budget:** <$50/month operational costs
- **Development time:** Solo project with AI agent assistance (~6-10 hours total for MVP implementation)

**Timeline:**
- **MVP target:** Days, not weeks. AI agent-assisted implementation dramatically accelerates development
- **Working prototype:** 6-10 hours of focused implementation with AI agent
- **No artificial phases:** Full-featured system built from start

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

## Implementation Notes

### Monitoring During Development

While we have locked-in technology decisions, we'll monitor these metrics during implementation:

- **Token Usage:** Track actual costs per briefing to validate <$20/month target
- **Linear API Rate Limits:** Monitor request patterns and adjust polling if needed
- **Briefing Quality:** Collect feedback (👍/👎) to refine relevance scoring
- **State Management:** Validate SQLite + mem0 performance with realistic data volumes

### Areas for Continuous Learning

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

### Implementation with AI Agent (6-10 Hours Total)

**Approach:** Build full-featured system directly with AI agent assistance. No validation spike, no phased rollout.

**Session 1: Foundation & Setup (2 hours)**
- Project initialization with Poetry
- Dependency installation: anthropic, mem0ai, chromadb, sentence-transformers, httpx, python-telegram-bot, sqlalchemy, apscheduler
- Project structure setup following architecture docs
- Configuration management (.env setup)

**Session 2: Core Integration (2-3 hours)**
- Linear API client with httpx + GraphQL queries
- Agent SDK integration with prompt templates
- mem0 memory layer setup
- ChromaDB vector store initialization
- Telegram bot basic setup

**Session 3: Intelligence & Memory (2 hours)**
- Issue analysis logic (stagnation, blocked, activity)
- IssueRanker with learned preferences
- Semantic search integration
- Feedback tracking setup

**Session 4: Orchestration & Testing (1-2 hours)**
- APScheduler cron setup
- End-to-end workflow testing
- Manual briefing trigger CLI
- Cost monitoring dashboard

**Session 5: Polish & Deploy (1 hour)**
- Error handling refinement
- Logging configuration
- Local deployment and validation
- Documentation updates

### Continuous Learning

Throughout implementation, document:
- Agent SDK patterns discovered
- Token usage and cost optimization strategies
- Memory management learnings
- User experience insights

### Success Metrics

After 1 week of daily use:
- ✅ Saves 10+ minutes per morning vs. manual Linear checking
- ✅ Briefings are relevant and actionable
- ✅ Costs stay under $20/month
- ✅ System runs reliably without intervention
- ✅ Learned valuable Agent SDK patterns for future projects

---

