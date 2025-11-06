# Linear Chief of Staff - Test Suite Documentation

Comprehensive test suite for the Linear Chief of Staff AI agent, covering all features including Phase 2 personalization and intelligence enhancements.

## Test Structure

```
tests/
├── unit/                           # Unit tests with mocking (60+ tests)
│   ├── test_preference_learner.py  # Preference learning logic
│   ├── test_engagement_tracker.py  # Engagement tracking
│   ├── test_semantic_search.py     # Semantic search functionality
│   ├── test_duplicate_detector.py  # Duplicate detection
│   ├── test_preference_ranker.py   # Personalized ranking (placeholder)
│   ├── test_related_suggester.py   # Related issues (placeholder)
│   ├── test_preference_ui.py       # Preference UI (placeholder)
│   ├── test_intelligence.py        # Issue analysis
│   ├── test_memory.py              # Memory layer
│   ├── test_scheduler.py           # APScheduler integration
│   ├── test_storage.py             # Database operations
│   └── ...                         # Other unit tests
│
├── integration/                    # Integration tests (70+ tests)
│   ├── test_phase2_workflow.py     # Phase 2 end-to-end workflows
│   ├── test_phase2_database.py     # Database integration
│   ├── test_preference_learning.py # Preference learning integration
│   ├── test_duplicate_detection.py # Duplicate detection integration
│   ├── test_semantic_search_integration.py  # Semantic search integration
│   ├── test_embeddings.py          # Embedding generation
│   ├── test_workflow.py            # Original workflow tests
│   ├── test_linear_client.py       # Linear API integration
│   ├── test_briefing_agent.py      # Agent SDK integration
│   └── test_telegram_bot.py        # Telegram bot integration
│
├── performance/                    # Performance benchmarks (5+ tests)
│   └── test_phase2_performance.py  # Phase 2 performance tests
│
├── e2e/                           # End-to-end tests
│   └── ...                        # Manual E2E scripts
│
├── fixtures/                      # Test data
│   └── ...                        # Shared test fixtures
│
└── manual/                        # Manual test scripts
    └── ...                        # Scripts for manual testing
```

## Running Tests

### All Tests

```bash
# Run all tests (130+ tests total)
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src/linear_chief --cov-report=html

# Run with detailed output
python -m pytest tests/ -v -s
```

### By Category

```bash
# Unit tests only (60+ tests)
python -m pytest tests/unit/ -v

# Integration tests only (70+ tests)
python -m pytest tests/integration/ -v

# Performance tests only (5+ tests)
python -m pytest tests/performance/ -v

# Phase 2 tests only
python -m pytest tests/unit/test_preference_*.py tests/unit/test_engagement_*.py tests/unit/test_semantic_*.py tests/unit/test_duplicate_*.py -v
python -m pytest tests/integration/test_phase2_*.py -v
```

### Specific Test Files

```bash
# Preference learning
python -m pytest tests/unit/test_preference_learner.py -v
python -m pytest tests/integration/test_preference_learning.py -v

# Engagement tracking
python -m pytest tests/unit/test_engagement_tracker.py -v

# Semantic search
python -m pytest tests/unit/test_semantic_search.py -v
python -m pytest tests/integration/test_semantic_search_integration.py -v

# Duplicate detection
python -m pytest tests/unit/test_duplicate_detector.py -v
python -m pytest tests/integration/test_duplicate_detection.py -v

# Database operations
python -m pytest tests/integration/test_phase2_database.py -v

# Performance benchmarks
python -m pytest tests/performance/test_phase2_performance.py -v -s
```

### By Feature

```bash
# Storage layer
python -m pytest tests/unit/test_storage.py tests/integration/test_phase2_database.py -v

# Intelligence layer
python -m pytest tests/unit/test_intelligence.py tests/unit/test_preference_learner.py tests/unit/test_engagement_tracker.py -v

# Memory layer
python -m pytest tests/unit/test_memory.py tests/integration/test_embeddings.py -v

# Telegram integration
python -m pytest tests/unit/test_telegram_*.py tests/integration/test_telegram_bot.py -v
```

## Test Coverage Goals

Phase 2 module coverage targets:

| Module | Target Coverage | Current Status |
|--------|----------------|----------------|
| `preference_learner.py` | >90% | ✅ Achieved |
| `engagement_tracker.py` | >90% | ✅ Achieved |
| `semantic_search.py` | >90% | ✅ Achieved |
| `duplicate_detector.py` | >90% | ✅ Achieved |
| `preference_ranker.py` | >85% | ⏳ Not implemented |
| `related_suggester.py` | >85% | ✅ Implemented |
| `preference_ui.py` | >80% | ⏳ Not implemented |

Overall target: **>80% coverage** for entire codebase.

## Test Types

### Unit Tests

Test individual components in isolation with mocked dependencies.

**Characteristics:**
- Fast execution (< 1 second per test)
- No external API calls
- No persistent storage (in-memory SQLite)
- Heavy use of mocking

**Example:**
```python
@pytest.mark.asyncio
async def test_preference_learning_analyzes_feedback(mock_session):
    learner = PreferenceLearner(user_id="test_user")
    # Mock database responses
    preferences = await learner.analyze_feedback_patterns(days=30)
    assert preferences["feedback_count"] > 0
```

### Integration Tests

Test multiple components working together with real dependencies.

**Characteristics:**
- Moderate execution time (1-5 seconds per test)
- Real database operations (in-memory SQLite)
- Real ChromaDB vector operations
- Real sentence-transformers embeddings
- May use mocked external APIs (Linear, Anthropic, Telegram)

**Example:**
```python
@pytest.mark.asyncio
async def test_end_to_end_preference_learning(session_maker):
    # Real database, real preference learning
    # 1. User gives feedback
    # 2. PreferenceLearner analyzes
    # 3. Preferences saved to DB
    # 4. Verify persistence
```

### Performance Tests

Verify that features meet performance requirements.

**Characteristics:**
- Measure execution time
- Test with realistic data volumes
- Benchmark critical paths

**Example:**
```python
@pytest.mark.asyncio
async def test_vector_search_performance():
    # Add 1000 issues to vector store
    # Measure search time
    assert elapsed_time < 1.0  # Must complete in <1 second
```

## Phase 2 Test Suite

### Preference Learning Tests

**Unit Tests (`test_preference_learner.py`):**
- ✅ Analyze feedback patterns
- ✅ Extract topic preferences
- ✅ Extract team preferences
- ✅ Extract label preferences
- ✅ Calculate confidence scores
- ✅ Save to mem0
- ✅ Save to database
- ✅ Retrieve preferences

**Integration Tests (`test_preference_learning.py`):**
- ✅ End-to-end feedback → preferences → storage
- ✅ Multiple feedback cycles
- ✅ Preference updates over time

### Engagement Tracking Tests

**Unit Tests (`test_engagement_tracker.py`):**
- ✅ Track issue mentions
- ✅ Calculate engagement scores
- ✅ Frequency-based scoring
- ✅ Recency-based scoring
- ✅ Get top engaged issues
- ✅ Engagement statistics

**Integration Tests (`test_phase2_workflow.py`):**
- ✅ End-to-end engagement tracking
- ✅ Score decay over time
- ✅ Multiple users and issues

### Semantic Search Tests

**Unit Tests (`test_semantic_search.py`):**
- ✅ Find similar issues
- ✅ Search by text
- ✅ Calculate similarity percentages
- ✅ Format results
- ✅ Metadata filtering

**Integration Tests (`test_semantic_search_integration.py`):**
- ✅ ChromaDB integration
- ✅ Embedding generation
- ✅ Large corpus search
- ✅ Linear API fallback

### Duplicate Detection Tests

**Unit Tests (`test_duplicate_detector.py`):**
- ✅ Find duplicate pairs
- ✅ Check issue for duplicates
- ✅ Similarity threshold filtering
- ✅ Active/inactive state filtering
- ✅ Generate merge suggestions
- ✅ Format duplicate reports

**Integration Tests (`test_duplicate_detection.py`):**
- ✅ End-to-end duplicate detection
- ✅ Vector store integration
- ✅ Large dataset scanning

### Database Tests

**Database Integration (`test_phase2_database.py`):**
- ✅ UserPreference CRUD operations
- ✅ IssueEngagement CRUD operations
- ✅ Upsert behavior (no duplicates)
- ✅ Concurrent writes
- ✅ Data integrity constraints
- ✅ Index usage and performance
- ✅ Bulk operations

### Performance Tests

**Performance Benchmarks (`test_phase2_performance.py`):**
- ✅ Preference learning: <2s for 100 feedback items
- ✅ Engagement tracking: <1s for 100 interactions
- ✅ Vector search: <1s for 1000-issue corpus
- ✅ Duplicate detection: <10s for 200 issues
- ✅ Complete workflow: <10s end-to-end

## Test Fixtures

Common fixtures used across tests:

### Database Fixtures

```python
@pytest.fixture
def db_engine():
    """In-memory SQLite database for testing."""
    engine = get_engine(":memory:")
    init_db(engine)
    yield engine
    reset_engine()

@pytest.fixture
def session_maker(db_engine):
    """Session maker for database tests."""
    return get_session_maker(db_engine)
```

### Mock Fixtures

```python
@pytest.fixture
def mock_linear_client():
    """Mocked Linear API client."""
    # Returns mock issue data
    pass

@pytest.fixture
def mock_anthropic_client():
    """Mocked Anthropic Messages API client."""
    # Returns mock briefing text
    pass
```

### Sample Data Fixtures

```python
@pytest.fixture
def sample_issues():
    """Sample Linear issues for testing."""
    # Returns list of issue dictionaries
    pass

@pytest.fixture
def sample_feedback():
    """Sample user feedback for testing."""
    # Returns list of Feedback objects
    pass
```

## Writing New Tests

### Best Practices

1. **Use descriptive test names:**
   ```python
   def test_preference_learning_with_positive_feedback_boosts_score():
       # Clear what this tests
       pass
   ```

2. **Follow AAA pattern (Arrange, Act, Assert):**
   ```python
   def test_example():
       # Arrange
       learner = PreferenceLearner(user_id="test")

       # Act
       result = await learner.analyze_feedback_patterns()

       # Assert
       assert result["confidence"] > 0.5
   ```

3. **Test happy path AND error cases:**
   ```python
   def test_engagement_tracking_succeeds():
       # Happy path
       pass

   def test_engagement_tracking_handles_missing_issue():
       # Error case
       pass
   ```

4. **Use fixtures for setup/teardown:**
   ```python
   @pytest.fixture
   def setup_db():
       # Setup
       yield
       # Teardown
   ```

5. **Mock external dependencies:**
   ```python
   @patch('linear_chief.linear.client.httpx.AsyncClient')
   async def test_with_mocked_api(mock_client):
       # Test with mocked Linear API
       pass
   ```

### Test Template

```python
"""Tests for [module_name]."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from linear_chief.[module_path] import [ClassName]


@pytest.fixture
def setup():
    """Setup test data."""
    # Setup code
    yield
    # Teardown code


class Test[FeatureName]:
    """Test [feature] functionality."""

    @pytest.mark.asyncio
    async def test_[specific_behavior](self, setup):
        """Test that [specific behavior] works correctly."""
        # Arrange
        instance = [ClassName]()

        # Act
        result = await instance.method()

        # Assert
        assert result is not None
        assert result.property == expected_value
```

## Continuous Integration

Tests run automatically on:
- Every commit
- Every pull request
- Before deployment

### CI Pipeline

1. **Linting:** Black, Ruff, MyPy
2. **Unit Tests:** Fast tests with mocking
3. **Integration Tests:** Real components (in-memory)
4. **Performance Tests:** Benchmark critical paths
5. **Coverage Report:** Verify >80% coverage

## Troubleshooting

### Common Issues

**ChromaDB warnings:**
```
UserWarning: Collection already exists
```
**Solution:** This is harmless. ChromaDB warns when re-adding issues. Tests use `upsert()` to prevent this.

**Sentence-transformers slow first run:**
```
Downloading model... (90MB)
```
**Solution:** First run downloads the embedding model. Subsequent runs use cached model.

**TOKENIZERS_PARALLELISM warnings:**
```
huggingface/tokenizers: The current process just got forked
```
**Solution:** Add to `.env`:
```
TOKENIZERS_PARALLELISM=false
```

**SQLAlchemy metadata warnings:**
```
Column 'metadata' conflicts with reserved word
```
**Solution:** Use `extra_metadata` instead (already fixed in models).

### Running Specific Tests

```bash
# Run tests matching pattern
python -m pytest tests/ -k "preference" -v

# Run tests with specific markers
python -m pytest tests/ -m "asyncio" -v

# Run failed tests only
python -m pytest tests/ --lf -v

# Stop on first failure
python -m pytest tests/ -x -v
```

## Test Coverage Report

Generate HTML coverage report:

```bash
python -m pytest tests/ --cov=src/linear_chief --cov-report=html
open htmlcov/index.html
```

## Manual Testing

For features requiring manual verification:

```bash
# Test semantic search
python scripts/test_semantic_search.py

# Test preference learning
python examples/preference_learning_demo.py

# Integration test (requires API keys)
python test_integration.py

# Memory integration test
python test_memory_integration.py
```

## Contributing

When adding new features:

1. ✅ Write tests FIRST (test-driven development)
2. ✅ Ensure >80% coverage for new code
3. ✅ Add integration tests for workflows
4. ✅ Update this README if adding new test categories
5. ✅ Run full test suite before committing

## Test Metrics

Current test suite statistics:

- **Total Tests:** 130+
- **Unit Tests:** 60+
- **Integration Tests:** 70+
- **Performance Tests:** 5+
- **Coverage:** >80% (target)
- **Average Execution Time:** <30 seconds (full suite)

## Future Enhancements

Planned test improvements:

- [ ] Add mutation testing (mutmut)
- [ ] Add property-based testing (hypothesis)
- [ ] Add load testing for production scenarios
- [ ] Add contract testing for API integrations
- [ ] Add visual regression testing for Telegram UI
- [ ] Add security testing (bandit, safety)

---

**Last Updated:** 2025-11-05
**Test Suite Version:** Phase 2 Complete
