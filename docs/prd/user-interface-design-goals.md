# User Interface Design Goals

**Note:** This is primarily a backend/agent system. The only user-facing interface is Telegram messages.

## Overall UX Vision

The user receives a concise, actionable morning briefing via Telegram that feels like a human chief of staff providing a situational update. The tone is professional yet conversational, highlighting what needs attention without overwhelming detail.

## Key Interaction Paradigms

- **Push notification model:** Agent proactively delivers briefings at scheduled time
- **Read-only for MVP:** No interactive responses or queries (v2 feature)
- **Structured message format:** Briefing uses Telegram markdown for readability (headers, bullet points, bold for issue IDs)

## Core Screens and Views

1. **Telegram Briefing Message** (primary interface)
   - Header: "🌅 Morning Briefing - [Date]"
   - Section 1: Active Issues (updated in last 24h)
   - Section 2: Blocked Issues (needs attention)
   - Section 3: Stale Issues (no activity 3+ days)
   - Footer: Summary count and timestamp

2. **CLI Manual Trigger** (testing only)
   - Command: `python -m linear_chief.cli generate-briefing`
   - Output: Same briefing sent to Telegram + token usage stats

## Accessibility

None - Telegram is the interface, inherits Telegram's accessibility features.

## Branding

Minimal. Use emoji sparingly (🌅 for morning, ⚠️ for blocked, 🕐 for stale). Keep professional tone suitable for work context.

## Target Device and Platforms

- **Primary:** Telegram mobile app (iOS/Android)
- **Secondary:** Telegram desktop/web clients
- Device-agnostic: Telegram handles rendering

---
