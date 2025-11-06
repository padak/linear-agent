# Manual Test Scripts

This directory contains manual test scripts used during development and debugging.
These are NOT part of the automated test suite (pytest).

## Scripts

- `test_database_singleton.py` - Verify DB engine singleton pattern
- `test_singleton_real_world.py` - Simulate real-world bot interactions
- `test_before_after_comparison.py` - Performance comparison before/after fix
- `test_original_problem.py` - Demonstrate original DB engine issue
- `test_clickable_links.py` - Test Markdown link generation
- `test_token_logging.py` - Verify token usage logging
- `test_real_time_fetch.py` - Test real-time issue fetching from Linear API
- `verify_user_matching.py` - Test user identity matching with diacritics

## Usage

Run any script directly:
```bash
python tests/manual/test_database_singleton.py
python tests/manual/test_token_logging.py
```

These scripts are useful for:
- Manual verification during development
- Debugging specific features
- Performance testing
- Demonstrating fixes to users
