"""Unit tests for intelligence layer (IssueAnalyzer)."""

from datetime import datetime, timedelta

import pytest

from src.linear_chief.intelligence import AnalysisResult, IssueAnalyzer


class TestIssueAnalyzer:
    """Test suite for IssueAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create IssueAnalyzer instance."""
        return IssueAnalyzer()

    @pytest.fixture
    def sample_issue_in_progress(self):
        """Create sample issue in progress state."""
        return {
            "id": "PROJ-123",
            "title": "Test Issue",
            "description": "Test description",
            "state": {"name": "In Progress"},
            "labels": {"nodes": []},
            "createdAt": (datetime.now() - timedelta(days=5)).isoformat(),
            "updatedAt": datetime.now().isoformat(),
        }

    def test_detect_stagnation_active_issue(self, analyzer, sample_issue_in_progress):
        """Test stagnation detection for recently updated issue."""
        is_stagnant = analyzer.detect_stagnation(sample_issue_in_progress)
        assert is_stagnant is False

    def test_detect_stagnation_old_issue(self, analyzer, sample_issue_in_progress):
        """Test stagnation detection for old issue."""
        # Make issue old
        sample_issue_in_progress["updatedAt"] = (datetime.now() - timedelta(days=5)).isoformat()

        is_stagnant = analyzer.detect_stagnation(sample_issue_in_progress)
        assert is_stagnant is True

    def test_detect_stagnation_on_hold_label(self, analyzer, sample_issue_in_progress):
        """Test that 'On Hold' label prevents stagnation detection."""
        sample_issue_in_progress["updatedAt"] = (datetime.now() - timedelta(days=5)).isoformat()
        sample_issue_in_progress["labels"]["nodes"] = [{"name": "On Hold"}]

        is_stagnant = analyzer.detect_stagnation(sample_issue_in_progress)
        assert is_stagnant is False

    def test_detect_stagnation_paused_keyword(self, analyzer, sample_issue_in_progress):
        """Test that 'paused' keyword prevents stagnation detection."""
        sample_issue_in_progress["updatedAt"] = (datetime.now() - timedelta(days=5)).isoformat()
        sample_issue_in_progress["description"] = "This is paused waiting for approval"

        is_stagnant = analyzer.detect_stagnation(sample_issue_in_progress)
        assert is_stagnant is False

    def test_detect_stagnation_not_in_progress(self, analyzer, sample_issue_in_progress):
        """Test that non-InProgress issues aren't marked stagnant."""
        sample_issue_in_progress["state"]["name"] = "Todo"
        sample_issue_in_progress["updatedAt"] = (datetime.now() - timedelta(days=5)).isoformat()

        is_stagnant = analyzer.detect_stagnation(sample_issue_in_progress)
        assert is_stagnant is False

    def test_detect_blocking_blocked_label(self, analyzer, sample_issue_in_progress):
        """Test blocking detection with 'Blocked' label."""
        sample_issue_in_progress["labels"]["nodes"] = [{"name": "Blocked"}]

        is_blocked = analyzer.detect_blocking(sample_issue_in_progress)
        assert is_blocked is True

    def test_detect_blocking_keyword_in_title(self, analyzer, sample_issue_in_progress):
        """Test blocking detection with keyword in title."""
        sample_issue_in_progress["title"] = "Blocked on external API"

        is_blocked = analyzer.detect_blocking(sample_issue_in_progress)
        assert is_blocked is True

    def test_detect_blocking_no_blockers(self, analyzer, sample_issue_in_progress):
        """Test blocking detection returns False when no blockers."""
        is_blocked = analyzer.detect_blocking(sample_issue_in_progress)
        assert is_blocked is False

    def test_calculate_priority_base(self, analyzer, sample_issue_in_progress):
        """Test priority calculation for basic issue."""
        priority = analyzer.calculate_priority(sample_issue_in_progress)
        assert 1 <= priority <= 10

    def test_calculate_priority_critical_label(self, analyzer, sample_issue_in_progress):
        """Test priority calculation with P0/Critical label."""
        sample_issue_in_progress["labels"]["nodes"] = [{"name": "P0"}]

        priority = analyzer.calculate_priority(sample_issue_in_progress)
        assert priority == 10

    def test_calculate_priority_old_issue(self, analyzer, sample_issue_in_progress):
        """Test priority boost for old issues."""
        sample_issue_in_progress["createdAt"] = (datetime.now() - timedelta(days=10)).isoformat()

        priority = analyzer.calculate_priority(sample_issue_in_progress)
        assert priority >= 6  # Base 5 + age bonus

    def test_calculate_priority_blocked_issue(self, analyzer, sample_issue_in_progress):
        """Test priority boost for blocked issues."""
        sample_issue_in_progress["labels"]["nodes"] = [{"name": "Blocked"}]

        priority = analyzer.calculate_priority(sample_issue_in_progress)
        assert priority >= 8  # Base 5 + blocking bonus

    def test_analyze_issue_complete(self, analyzer, sample_issue_in_progress):
        """Test complete issue analysis."""
        result = analyzer.analyze_issue(sample_issue_in_progress)

        assert isinstance(result, AnalysisResult)
        assert 1 <= result.priority <= 10
        assert isinstance(result.is_stagnant, bool)
        assert isinstance(result.is_blocked, bool)
        assert isinstance(result.insights, list)
        assert len(result.insights) > 0

    def test_generate_insights_stagnant(self, analyzer, sample_issue_in_progress):
        """Test insight generation for stagnant issue."""
        sample_issue_in_progress["updatedAt"] = (datetime.now() - timedelta(days=5)).isoformat()

        result = analyzer.analyze_issue(sample_issue_in_progress)

        assert any("activity" in insight.lower() for insight in result.insights)

    def test_generate_insights_blocked(self, analyzer, sample_issue_in_progress):
        """Test insight generation for blocked issue."""
        sample_issue_in_progress["labels"]["nodes"] = [{"name": "Blocked"}]

        result = analyzer.analyze_issue(sample_issue_in_progress)

        assert any("blocked" in insight.lower() for insight in result.insights)

    def test_generate_insights_high_priority(self, analyzer, sample_issue_in_progress):
        """Test insight generation for high priority issue."""
        sample_issue_in_progress["labels"]["nodes"] = [{"name": "P0"}]

        result = analyzer.analyze_issue(sample_issue_in_progress)

        assert any("high priority" in insight.lower() for insight in result.insights)


class TestAnalysisResult:
    """Test suite for AnalysisResult dataclass."""

    def test_analysis_result_creation(self):
        """Test creating AnalysisResult."""
        result = AnalysisResult(
            priority=8,
            is_stagnant=True,
            is_blocked=False,
            insights=["Test insight"],
        )

        assert result.priority == 8
        assert result.is_stagnant is True
        assert result.is_blocked is False
        assert result.insights == ["Test insight"]

    def test_analysis_result_invalid_priority_high(self):
        """Test AnalysisResult rejects priority > 10."""
        with pytest.raises(ValueError, match="Priority must be 1-10"):
            AnalysisResult(priority=11, is_stagnant=False, is_blocked=False, insights=[])

    def test_analysis_result_invalid_priority_low(self):
        """Test AnalysisResult rejects priority < 1."""
        with pytest.raises(ValueError, match="Priority must be 1-10"):
            AnalysisResult(priority=0, is_stagnant=False, is_blocked=False, insights=[])
