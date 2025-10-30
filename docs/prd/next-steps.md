# Next Steps

## UX Expert Prompt

Not applicable for this project - primary interface is Telegram messages (no custom UI design needed).

## Architect Prompt

**Winston (Architect),**

Please review this PRD and create a detailed technical architecture for the Linear Chief of Staff agent system. Focus on:

1. **Agent SDK Integration Patterns:** How to structure the Anthropic Agent SDK integration for scheduled briefing generation. Document whether the SDK supports native scheduling or if we need external orchestration (APScheduler/cron).

2. **Data Flow Architecture:** Design the data flow from Linear API → Issue Analysis → Agent SDK → Telegram delivery, with emphasis on state management and caching strategies.

3. **Module Structure:** Define the Python package structure (agents, storage, telegram, linear, intelligence modules) with clear interfaces and dependency injection patterns.

4. **Cost Optimization Strategy:** Architecture decisions that minimize token usage (caching, incremental updates, prompt templates).

5. **Deployment Model:** Local development architecture and path to production (systemd service, monitoring, log aggregation).

Use the PRD's technical assumptions (Python, SQLite, monolith) as constraints. Output should be `docs/architecture.md` following BMad architecture template.

