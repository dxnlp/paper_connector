"""
Tests for emerging topic detection module.
"""

import pytest
from datetime import date, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from emerging import (
    compute_growth_rate,
    compute_percentage_change,
    detect_new_clusters,
    detect_upvote_surges,
    detect_keyword_emergence,
    compute_trend_signals,
    generate_emerging_topics_report,
    EmergingTopic,
    TrendSignal,
    EmergingTopicsReport,
)
from database import Paper, PaperTags


class TestComputeGrowthRate:
    """Tests for compute_growth_rate function."""

    def test_empty_list(self):
        """Growth rate of empty list should be 0."""
        assert compute_growth_rate([]) == 0.0

    def test_single_value(self):
        """Growth rate of single value should be 0."""
        assert compute_growth_rate([5]) == 0.0

    def test_constant_values(self):
        """Growth rate of constant values should be 0."""
        assert compute_growth_rate([5, 5, 5, 5]) == 0.0

    def test_increasing_values(self):
        """Growth rate of increasing values should be positive."""
        # Linear growth: 1, 2, 3, 4, 5
        rate = compute_growth_rate([1, 2, 3, 4, 5])
        assert rate > 0
        assert pytest.approx(rate, 0.01) == 1.0  # Slope is 1

    def test_decreasing_values(self):
        """Growth rate of decreasing values should be negative."""
        rate = compute_growth_rate([5, 4, 3, 2, 1])
        assert rate < 0
        assert pytest.approx(rate, 0.01) == -1.0


class TestComputePercentageChange:
    """Tests for compute_percentage_change function."""

    def test_no_change(self):
        """No change should return 0."""
        assert compute_percentage_change(10, 10) == 0.0

    def test_double(self):
        """Doubling should return 100%."""
        assert compute_percentage_change(20, 10) == 100.0

    def test_half(self):
        """Halving should return -50%."""
        assert compute_percentage_change(5, 10) == -50.0

    def test_from_zero(self):
        """Change from zero to positive should return 100%."""
        assert compute_percentage_change(10, 0) == 100.0

    def test_to_zero(self):
        """Change to zero should return -100%."""
        assert compute_percentage_change(0, 10) == -100.0

    def test_zero_to_zero(self):
        """No change from zero to zero should return 0%."""
        assert compute_percentage_change(0, 0) == 0.0


class TestDetectNewClusters:
    """Tests for detect_new_clusters function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty list when no papers exist."""
        today = date.today()
        current_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        current_end = today.strftime("%Y-%m-%d")
        comparison_start = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        comparison_end = (today - timedelta(days=8)).strftime("%Y-%m-%d")

        result = await detect_new_clusters(
            current_start, current_end,
            comparison_start, comparison_end
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_detects_new_cluster(self, populated_database):
        """Should detect clusters that appear in current period but not comparison."""
        # This test uses the populated database which has papers in 2024-01
        # For a proper test, we'd need papers in different time periods

        current_start = "2024-01-07"
        current_end = "2024-01-14"
        comparison_start = "2024-01-01"
        comparison_end = "2024-01-06"

        result = await detect_new_clusters(
            current_start, current_end,
            comparison_start, comparison_end
        )

        # Result should be a list of EmergingTopic objects
        assert isinstance(result, list)
        for topic in result:
            assert isinstance(topic, EmergingTopic)
            assert topic.signal_type in ["new_cluster", "rapid_growth"]
            assert 0 <= topic.confidence <= 1


class TestDetectUpvoteSurges:
    """Tests for detect_upvote_surges function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty list when no papers exist."""
        result = await detect_upvote_surges("2024-01-01", "2024-01-07")
        assert result == []

    @pytest.mark.asyncio
    async def test_detects_surges(self, populated_database):
        """Should detect clusters with above-average upvotes."""
        result = await detect_upvote_surges(
            "2024-01-01", "2024-01-14",
            min_papers=2
        )

        assert isinstance(result, list)
        for topic in result:
            assert isinstance(topic, EmergingTopic)
            assert topic.signal_type == "upvote_surge"
            assert "upvotes" in topic.evidence.lower()


class TestDetectKeywordEmergence:
    """Tests for detect_keyword_emergence function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty list when no papers exist."""
        result = await detect_keyword_emergence(
            "2024-01-07", "2024-01-14",
            "2024-01-01", "2024-01-06",
            min_occurrences=1
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_detects_keywords(self, populated_database):
        """Should detect emerging keywords in paper titles/abstracts."""
        result = await detect_keyword_emergence(
            "2024-01-07", "2024-01-14",
            "2024-01-01", "2024-01-06",
            min_occurrences=1
        )

        assert isinstance(result, list)
        for topic in result:
            assert isinstance(topic, EmergingTopic)
            assert topic.signal_type == "keyword_emergence"
            assert topic.name.startswith("Keyword:")


class TestComputeTrendSignals:
    """Tests for compute_trend_signals function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty list when no papers exist."""
        result = await compute_trend_signals("2024-01-14")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_signals(self, populated_database):
        """Should return trend signals for each cluster."""
        result = await compute_trend_signals("2024-01-14")

        assert isinstance(result, list)
        for signal in result:
            assert isinstance(signal, TrendSignal)
            assert signal.trend_direction in ["rising", "falling", "stable"]
            assert 0 <= signal.signal_strength <= 1
            assert signal.current_count >= 0
            assert signal.previous_count >= 0


class TestGenerateEmergingTopicsReport:
    """Tests for generate_emerging_topics_report function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should generate report even with no papers."""
        report = await generate_emerging_topics_report(
            end_date="2024-01-14",
            lookback_days=7,
            comparison_lookback_days=14
        )

        assert isinstance(report, EmergingTopicsReport)
        assert report.generated_at is not None
        assert "to" in report.analysis_period
        assert isinstance(report.emerging_topics, list)
        assert isinstance(report.trend_signals, list)
        assert isinstance(report.summary, str)

    @pytest.mark.asyncio
    async def test_with_data(self, populated_database):
        """Should generate comprehensive report with data."""
        report = await generate_emerging_topics_report(
            end_date="2024-01-14",
            lookback_days=7,
            comparison_lookback_days=7
        )

        assert isinstance(report, EmergingTopicsReport)
        assert report.summary  # Should not be empty

        # Check that topics are sorted by confidence
        if len(report.emerging_topics) > 1:
            confidences = [t.confidence for t in report.emerging_topics]
            assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_default_end_date(self, populated_database):
        """Should default to today's date."""
        report = await generate_emerging_topics_report()

        assert isinstance(report, EmergingTopicsReport)
        # End date should be today
        today = date.today().strftime("%Y-%m-%d")
        assert today in report.analysis_period


class TestEmergingTopicModel:
    """Tests for EmergingTopic Pydantic model."""

    def test_valid_topic(self):
        """Should create valid EmergingTopic."""
        topic = EmergingTopic(
            name="Test Cluster",
            signal_type="new_cluster",
            confidence=0.85,
            evidence="This is test evidence",
            first_seen="2024-01-01",
            growth_rate=50.0,
            related_clusters=["Other Cluster"],
            sample_paper_ids=["paper1", "paper2"]
        )

        assert topic.name == "Test Cluster"
        assert topic.signal_type == "new_cluster"
        assert topic.confidence == 0.85

    def test_optional_fields(self):
        """Should work with optional fields missing."""
        topic = EmergingTopic(
            name="Test",
            signal_type="rapid_growth",
            confidence=0.5,
            evidence="Evidence"
        )

        assert topic.first_seen is None
        assert topic.growth_rate is None
        assert topic.related_clusters == []


class TestTrendSignalModel:
    """Tests for TrendSignal Pydantic model."""

    def test_valid_signal(self):
        """Should create valid TrendSignal."""
        signal = TrendSignal(
            cluster_name="Test Cluster",
            signal_strength=0.75,
            trend_direction="rising",
            weekly_change=50.0,
            monthly_change=100.0,
            current_count=10,
            previous_count=5
        )

        assert signal.cluster_name == "Test Cluster"
        assert signal.trend_direction == "rising"
        assert signal.weekly_change == 50.0

    def test_signal_directions(self):
        """Should accept all valid trend directions."""
        for direction in ["rising", "falling", "stable"]:
            signal = TrendSignal(
                cluster_name="Test",
                signal_strength=0.5,
                trend_direction=direction,
                weekly_change=0,
                monthly_change=0,
                current_count=5,
                previous_count=5
            )
            assert signal.trend_direction == direction
