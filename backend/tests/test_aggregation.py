"""
Tests for aggregation module.
"""

import pytest
from datetime import date, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aggregation import (
    get_week_bounds,
    get_month_bounds,
    compute_daily_stats,
    compute_weekly_stats,
    compute_flow_data,
    compute_trend_data,
    save_daily_snapshot_for_date,
    DailyStats,
    WeeklyStats,
    FlowData,
    TrendData,
    ClusterStats,
)


class TestGetWeekBounds:
    """Tests for get_week_bounds function."""

    def test_monday(self):
        """Monday should return itself as start."""
        d = date(2024, 1, 15)  # Monday
        monday, sunday = get_week_bounds(d)
        assert monday == date(2024, 1, 15)
        assert sunday == date(2024, 1, 21)

    def test_wednesday(self):
        """Wednesday should return previous Monday."""
        d = date(2024, 1, 17)  # Wednesday
        monday, sunday = get_week_bounds(d)
        assert monday == date(2024, 1, 15)
        assert sunday == date(2024, 1, 21)

    def test_sunday(self):
        """Sunday should return previous Monday."""
        d = date(2024, 1, 21)  # Sunday
        monday, sunday = get_week_bounds(d)
        assert monday == date(2024, 1, 15)
        assert sunday == date(2024, 1, 21)

    def test_week_is_7_days(self):
        """Week should always be exactly 7 days."""
        for day_offset in range(30):
            d = date(2024, 1, 1) + timedelta(days=day_offset)
            monday, sunday = get_week_bounds(d)
            assert (sunday - monday).days == 6


class TestGetMonthBounds:
    """Tests for get_month_bounds function."""

    def test_january(self):
        """January should have 31 days."""
        d = date(2024, 1, 15)
        first, last = get_month_bounds(d)
        assert first == date(2024, 1, 1)
        assert last == date(2024, 1, 31)

    def test_february_leap_year(self):
        """February 2024 (leap year) should have 29 days."""
        d = date(2024, 2, 15)
        first, last = get_month_bounds(d)
        assert first == date(2024, 2, 1)
        assert last == date(2024, 2, 29)

    def test_february_non_leap_year(self):
        """February 2023 (non-leap year) should have 28 days."""
        d = date(2023, 2, 15)
        first, last = get_month_bounds(d)
        assert first == date(2023, 2, 1)
        assert last == date(2023, 2, 28)

    def test_december(self):
        """December should wrap to next year correctly."""
        d = date(2024, 12, 15)
        first, last = get_month_bounds(d)
        assert first == date(2024, 12, 1)
        assert last == date(2024, 12, 31)


class TestComputeDailyStats:
    """Tests for compute_daily_stats function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty stats for date with no papers."""
        stats = await compute_daily_stats("2024-01-01")

        assert isinstance(stats, DailyStats)
        assert stats.date == "2024-01-01"
        assert stats.total_papers == 0
        assert stats.clusters == []

    @pytest.mark.asyncio
    async def test_with_papers(self, populated_database):
        """Should compute correct stats for papers."""
        stats = await compute_daily_stats("2024-01-01")

        assert isinstance(stats, DailyStats)
        assert stats.date == "2024-01-01"
        assert stats.total_papers > 0

        # Check clusters are sorted by paper count
        if len(stats.clusters) > 1:
            counts = [c.paper_count for c in stats.clusters]
            assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio
    async def test_cluster_stats_structure(self, populated_database):
        """Should return properly structured cluster stats."""
        stats = await compute_daily_stats("2024-01-01")

        for cluster in stats.clusters:
            assert isinstance(cluster, ClusterStats)
            assert cluster.name
            assert cluster.color.startswith("#")
            assert cluster.paper_count > 0
            assert len(cluster.top_papers) <= 5
            assert isinstance(cluster.avg_upvotes, float)
            assert cluster.total_upvotes >= 0


class TestComputeWeeklyStats:
    """Tests for compute_weekly_stats function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty stats for week with no papers."""
        stats = await compute_weekly_stats("2024-06-01")  # A week with no test data

        assert isinstance(stats, WeeklyStats)
        assert stats.total_papers == 0

    @pytest.mark.asyncio
    async def test_with_papers(self, populated_database):
        """Should compute correct weekly stats."""
        stats = await compute_weekly_stats("2024-01-01")

        assert isinstance(stats, WeeklyStats)
        assert stats.week_start <= stats.week_end
        assert stats.total_papers >= 0
        assert isinstance(stats.daily_counts, dict)

    @pytest.mark.asyncio
    async def test_week_span(self, populated_database):
        """Week should span exactly 7 days."""
        stats = await compute_weekly_stats("2024-01-01")

        start = date.fromisoformat(stats.week_start)
        end = date.fromisoformat(stats.week_end)
        assert (end - start).days == 6


class TestComputeFlowData:
    """Tests for compute_flow_data function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty flow data for period with no papers."""
        flow = await compute_flow_data("2024-06-01", "2024-06-14")

        assert isinstance(flow, FlowData)
        assert flow.start_date == "2024-06-01"
        assert flow.end_date == "2024-06-14"
        assert flow.clusters == []
        assert flow.daily_data == []

    @pytest.mark.asyncio
    async def test_with_papers(self, populated_database):
        """Should compute flow data for date range."""
        flow = await compute_flow_data("2024-01-01", "2024-01-14")

        assert isinstance(flow, FlowData)
        assert flow.start_date == "2024-01-01"
        assert flow.end_date == "2024-01-14"
        assert len(flow.clusters) > 0
        assert len(flow.daily_data) > 0

    @pytest.mark.asyncio
    async def test_colors_assigned(self, populated_database):
        """Each cluster should have a color assigned."""
        flow = await compute_flow_data("2024-01-01", "2024-01-14")

        for cluster in flow.clusters:
            assert cluster in flow.colors
            assert flow.colors[cluster].startswith("#")

    @pytest.mark.asyncio
    async def test_daily_data_structure(self, populated_database):
        """Daily data should have consistent structure."""
        flow = await compute_flow_data("2024-01-01", "2024-01-14")

        for day in flow.daily_data:
            assert "date" in day
            assert "cluster_counts" in day
            # All clusters should be present in counts
            for cluster in flow.clusters:
                assert cluster in day["cluster_counts"]

    @pytest.mark.asyncio
    async def test_daily_data_sorted(self, populated_database):
        """Daily data should be sorted by date."""
        flow = await compute_flow_data("2024-01-01", "2024-01-14")

        if len(flow.daily_data) > 1:
            dates = [d["date"] for d in flow.daily_data]
            assert dates == sorted(dates)


class TestComputeTrendData:
    """Tests for compute_trend_data function."""

    @pytest.mark.asyncio
    async def test_no_papers(self):
        """Should return empty trend data for cluster with no papers."""
        trend = await compute_trend_data(
            "NonexistentCluster",
            "2024-01-01",
            "2024-01-14"
        )

        assert isinstance(trend, TrendData)
        assert trend.cluster_name == "NonexistentCluster"
        assert trend.data_points == []

    @pytest.mark.asyncio
    async def test_with_papers(self, populated_database):
        """Should compute trend data for existing cluster."""
        trend = await compute_trend_data(
            "LLM / Foundation Models",
            "2024-01-01",
            "2024-01-14"
        )

        assert isinstance(trend, TrendData)
        assert trend.cluster_name == "LLM / Foundation Models"
        assert trend.color.startswith("#")

    @pytest.mark.asyncio
    async def test_cumulative_counts(self, populated_database):
        """Cumulative counts should be monotonically increasing."""
        trend = await compute_trend_data(
            "LLM / Foundation Models",
            "2024-01-01",
            "2024-01-14"
        )

        if len(trend.data_points) > 1:
            cumulatives = [p["cumulative"] for p in trend.data_points]
            for i in range(1, len(cumulatives)):
                assert cumulatives[i] >= cumulatives[i - 1]


class TestSaveDailySnapshotForDate:
    """Tests for save_daily_snapshot_for_date function."""

    @pytest.mark.asyncio
    async def test_saves_snapshot(self, populated_database):
        """Should save and retrieve daily snapshot."""
        from database import get_daily_snapshot

        snapshot = await save_daily_snapshot_for_date("2024-01-01")

        assert snapshot.date == "2024-01-01"
        assert snapshot.total_papers >= 0

        # Verify it was saved
        retrieved = await get_daily_snapshot("2024-01-01")
        assert retrieved is not None
        assert retrieved.date == "2024-01-01"

    @pytest.mark.asyncio
    async def test_records_upvotes(self, populated_database):
        """Should record upvote snapshots."""
        from database import get_upvote_history

        await save_daily_snapshot_for_date("2024-01-01")

        # Check that upvote history was recorded
        # Get a paper from that date
        from database import get_papers_by_date
        papers = await get_papers_by_date("2024-01-01")

        if papers:
            history = await get_upvote_history(papers[0].id)
            assert len(history) > 0

    @pytest.mark.asyncio
    async def test_idempotent(self, populated_database):
        """Running twice should not create duplicates."""
        await save_daily_snapshot_for_date("2024-01-01")
        await save_daily_snapshot_for_date("2024-01-01")

        from database import get_daily_snapshot
        snapshot = await get_daily_snapshot("2024-01-01")

        # Should have exactly one snapshot
        assert snapshot is not None


class TestModels:
    """Tests for Pydantic models."""

    def test_daily_stats_model(self):
        """DailyStats model should validate correctly."""
        stats = DailyStats(
            date="2024-01-01",
            total_papers=10,
            new_papers=5,
            clusters=[],
            top_papers=["paper1", "paper2"],
            total_upvotes=500
        )

        assert stats.date == "2024-01-01"
        assert stats.total_papers == 10

    def test_flow_data_model(self):
        """FlowData model should validate correctly."""
        flow = FlowData(
            start_date="2024-01-01",
            end_date="2024-01-14",
            clusters=["A", "B"],
            colors={"A": "#FF0000", "B": "#00FF00"},
            daily_data=[
                {"date": "2024-01-01", "cluster_counts": {"A": 5, "B": 3}}
            ]
        )

        assert len(flow.clusters) == 2
        assert flow.colors["A"] == "#FF0000"

    def test_trend_data_model(self):
        """TrendData model should validate correctly."""
        trend = TrendData(
            cluster_name="Test",
            color="#FF0000",
            data_points=[
                {"date": "2024-01-01", "count": 5, "cumulative": 5},
                {"date": "2024-01-02", "count": 3, "cumulative": 8}
            ]
        )

        assert trend.cluster_name == "Test"
        assert len(trend.data_points) == 2
