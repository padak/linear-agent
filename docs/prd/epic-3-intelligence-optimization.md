# Epic 3: Intelligence & Optimization

**Expanded Goal:**

Refine the briefing quality by improving issue analysis logic, optimize costs through prompt engineering and caching, and add instrumentation to track learning goals (token usage trends, API patterns, briefing effectiveness).

## Story 3.1: Enhanced Issue Analysis - Stagnation Detection

**As a** user,
**I want** the agent to accurately identify truly stale issues,
**so that** I'm not spammed with false positives for issues that are intentionally paused.

**Acceptance Criteria:**
1. `src/linear_chief/intelligence/analyzers.py` module created with `StagnationAnalyzer` class
2. Stale issue criteria refined: no updates for 3+ days AND status is "In Progress" AND not labeled "On Hold" or "Waiting"
3. Analyzer checks issue comments for keywords: "paused", "blocked on external", "waiting for" → exclude from stale list
4. Unit tests verify edge cases: issue updated 72 hours ago (stale), issue with "On Hold" label (not stale)
5. Integration test with 20 real issues verifies <10% false positive rate (manually review flagged issues)

## Story 3.2: Prompt Engineering for Concise Summaries

**As a** user,
**I want** issue summaries to be concise (1-2 sentences) and action-oriented,
**so that** I can quickly understand what needs attention without reading full descriptions.

**Acceptance Criteria:**
1. Prompt template updated to emphasize: "Summarize in 1-2 sentences focusing on current status and next action needed"
2. Prompt includes few-shot examples of good summaries
3. Agent instructed to avoid regurgitating issue description verbatim
4. Unit tests verify summary length: <200 characters per issue
5. Manual review: 10 generated summaries are concise and actionable (subjective but documentable)

## Story 3.3: Cost Optimization - Issue Data Caching

**As a** project owner,
**I want** to reduce Anthropic API costs by sending only changed issues,
**so that** monthly costs stay well below $100 budget.

**Acceptance Criteria:**
1. `Database.get_issues_changed_since(timestamp)` method queries SQLite for issues updated since last briefing
2. Orchestrator sends only changed issues to Agent SDK (not full 50-issue list daily)
3. Agent prompt adjusted: "Here are issues that changed since yesterday. Summarize changes and flag concerns."
4. Token usage logged before/after optimization for comparison
5. Test: generate briefing on Day 1 (50 issues, baseline tokens), Day 2 (5 changed issues, reduced tokens)
6. Document token reduction: target 50% reduction on days with <10 changed issues

## Story 3.4: Learning Metrics Dashboard (CLI)

**As a** learner,
**I want** a CLI command to view token usage trends and system health,
**so that** I can track learning goals and optimize costs.

**Acceptance Criteria:**
1. CLI command: `python -m linear_chief.cli metrics` displays summary table
2. Metrics shown: total briefings generated, avg tokens per briefing, total cost, uptime %, missed briefings
3. Data pulled from `Briefing` table in SQLite
4. Graph (ASCII art or simple) showing token usage over last 7 days
5. Warnings: flag if any day exceeded $5 cost or briefing failed
6. Manual test: run for 7 days, review metrics, verify accuracy

---
