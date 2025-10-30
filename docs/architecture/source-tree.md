# Source Tree

```plaintext
linear-chief-of-staff/
├── .github/
│   └── workflows/
│       └── ci.yaml                 # GitHub Actions CI (future)
├── src/
│   └── linear_chief/
│       ├── __init__.py
│       ├── __main__.py             # CLI entry point (python -m linear_chief)
│       ├── config.py               # Configuration from .env (decouple)
│       ├── orchestrator.py         # Main briefing workflow
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── briefing_agent.py   # Anthropic Agent SDK wrapper
│       │   └── prompts.py          # Prompt templates
│       ├── linear/
│       │   ├── __init__.py
│       │   ├── client.py           # Linear API client
│       │   ├── models.py           # IssueDTO data transfer objects
│       │   └── queries.py          # GraphQL query strings
│       ├── telegram/
│       │   ├── __init__.py
│       │   └── bot.py              # Telegram bot wrapper
│       ├── intelligence/
│       │   ├── __init__.py
│       │   ├── analyzers.py        # Issue analysis logic
│       │   └── types.py            # AnalysisResult types
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py         # SQLAlchemy engine setup
│       │   ├── models.py           # SQLAlchemy ORM models
│       │   └── repositories.py     # Repository pattern implementations
│       ├── scheduling/
│       │   ├── __init__.py
│       │   ├── scheduler.py        # Scheduler interface
│       │   └── apscheduler_impl.py # APScheduler implementation
│       └── utils/
│           ├── __init__.py
│           ├── logging_config.py   # JSON logger setup
│           └── retry.py            # Tenacity retry decorators
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_intelligence.py
│   │   ├── test_briefing_agent.py
│   │   └── test_repositories.py
│   ├── integration/
│   │   ├── test_linear_client.py   # Mocked Linear API
│   │   ├── test_telegram_bot.py    # Mocked Telegram API
│   │   └── test_end_to_end.py      # Full workflow mock
│   └── fixtures/
│       └── sample_issues.json      # Test data
├── docs/
│   ├── brief.md
│   ├── prd/
│   │   └── (sharded PRD files)
│   └── architecture.md             # This file
├── scripts/
│   ├── setup_db.py                 # Initialize SQLite schema
│   └── manual_briefing.py          # CLI tool for manual trigger
├── .env.example                    # Environment variable template
├── .gitignore
├── pyproject.toml                  # Poetry dependency management
├── poetry.lock                     # Locked dependencies
├── pytest.ini                      # Pytest configuration
├── mypy.ini                        # Mypy type checking config
└── README.md
```

---
