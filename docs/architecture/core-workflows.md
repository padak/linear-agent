# Core Workflows

## Daily Briefing Generation Workflow

```mermaid
sequenceDiagram
    participant Scheduler
    participant Orchestrator
    participant LinearClient
    participant Storage
    participant Intelligence
    participant AgentSDK
    participant TelegramBot
    participant User

    Scheduler->>Orchestrator: Trigger at 9:00 AM
    activate Orchestrator

    Orchestrator->>Storage: Get last briefing timestamp
    Storage-->>Orchestrator: timestamp

    Orchestrator->>LinearClient: fetch_my_issues()
    activate LinearClient
    LinearClient->>LinearAPI: GraphQL query
    LinearAPI-->>LinearClient: Issue data
    LinearClient-->>Orchestrator: List[IssueDTO]
    deactivate LinearClient

    Orchestrator->>Storage: get_issues_changed_since(timestamp)
    Storage-->>Orchestrator: List[Issue] (cached)

    Orchestrator->>Intelligence: analyze(issues)
    activate Intelligence
    Intelligence->>Intelligence: Detect stagnation
    Intelligence->>Intelligence: Detect blocked issues
    Intelligence->>Intelligence: Detect recent activity
    Intelligence-->>Orchestrator: AnalysisResult
    deactivate Intelligence

    Orchestrator->>IssueRanker: rank_issues(analyzed_issues, max_count=10)
    IssueRanker-->>Orchestrator: Top 3-10 ranked issues

    Orchestrator->>AgentSDK: generate_briefing(issues, analysis)
    activate AgentSDK
    AgentSDK->>AnthropicAPI: LLM request with prompt
    AnthropicAPI-->>AgentSDK: Generated briefing text
    AgentSDK-->>Orchestrator: BriefingText + TokenUsage
    deactivate AgentSDK

    Orchestrator->>Storage: save_briefing(briefing)
    Storage-->>Orchestrator: Briefing saved

    Orchestrator->>TelegramBot: send_briefing(text, chat_id)
    activate TelegramBot
    TelegramBot->>TelegramAPI: POST /sendMessage
    TelegramAPI-->>TelegramBot: Message sent
    TelegramBot-->>Orchestrator: MessageResult
    deactivate TelegramBot

    Orchestrator->>Storage: update_briefing_status("sent")

    TelegramBot-->>User: Briefing delivered

    deactivate Orchestrator
```

## Error Handling in API Calls

```mermaid
sequenceDiagram
    participant Orchestrator
    participant LinearClient
    participant TenacityRetry
    participant LinearAPI

    Orchestrator->>LinearClient: fetch_my_issues()
    activate LinearClient

    LinearClient->>TenacityRetry: @retry(stop=stop_after_attempt(3))
    activate TenacityRetry

    TenacityRetry->>LinearAPI: GraphQL query
    LinearAPI-->>TenacityRetry: 500 Internal Server Error

    TenacityRetry->>TenacityRetry: Wait 1s (exponential backoff)
    TenacityRetry->>LinearAPI: Retry query
    LinearAPI-->>TenacityRetry: 500 Internal Server Error

    TenacityRetry->>TenacityRetry: Wait 2s
    TenacityRetry->>LinearAPI: Retry query
    LinearAPI-->>TenacityRetry: 200 OK + data

    TenacityRetry-->>LinearClient: Success
    deactivate TenacityRetry

    LinearClient-->>Orchestrator: List[IssueDTO]
    deactivate LinearClient

    Note over Orchestrator: If all retries fail,<br/>log error and skip briefing
```

## Workflow Optimization

**Optimization (Epic 3.3):** Workflow uses `get_issues_changed_since(last_briefing_timestamp)` to fetch only changed issues from storage, reducing token consumption. Only delta issues are sent to Agent SDK, not full 50-issue list.

---
