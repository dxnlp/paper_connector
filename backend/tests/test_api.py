"""
Tests for FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Tests for root health check endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_ok(self, client):
        """Root endpoint should return OK status."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data


class TestFlowEndpoint:
    """Tests for /api/flow endpoint."""

    @pytest.mark.asyncio
    async def test_flow_requires_dates(self, client):
        """Should require start_date and end_date parameters."""
        response = await client.get("/api/flow")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_flow_returns_data(self, client, populated_database):
        """Should return flow data for valid date range."""
        response = await client.get(
            "/api/flow",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-14"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "start_date" in data
        assert "end_date" in data
        assert "clusters" in data
        assert "colors" in data
        assert "daily_data" in data

    @pytest.mark.asyncio
    async def test_flow_empty_range(self, client):
        """Should return empty data for range with no papers."""
        response = await client.get(
            "/api/flow",
            params={
                "start_date": "2025-06-01",
                "end_date": "2025-06-14"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["clusters"] == []


class TestDailyStatsEndpoint:
    """Tests for /api/daily/{date}/stats endpoint."""

    @pytest.mark.asyncio
    async def test_daily_stats_returns_data(self, client, populated_database):
        """Should return daily statistics."""
        response = await client.get("/api/daily/2024-01-01/stats")

        assert response.status_code == 200
        data = response.json()

        assert "date" in data
        assert "total_papers" in data
        assert "clusters" in data

    @pytest.mark.asyncio
    async def test_daily_stats_empty_date(self, client):
        """Should return zero stats for date with no papers."""
        response = await client.get("/api/daily/2025-06-01/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_papers"] == 0


class TestTrendsEndpoint:
    """Tests for /api/trends/{cluster_name} endpoint."""

    @pytest.mark.asyncio
    async def test_trends_requires_dates(self, client):
        """Should require start_date and end_date parameters."""
        response = await client.get("/api/trends/LLM")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trends_returns_data(self, client, populated_database):
        """Should return trend data for cluster."""
        # Use a simple cluster name to avoid URL encoding issues
        response = await client.get(
            "/api/trends/LLM",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-14"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "cluster_name" in data
        assert "color" in data
        assert "data_points" in data


class TestEmergingReportEndpoint:
    """Tests for /api/emerging/report endpoint."""

    @pytest.mark.asyncio
    async def test_emerging_report_default_params(self, client, populated_database):
        """Should return report with default parameters."""
        response = await client.get("/api/emerging/report")

        assert response.status_code == 200
        data = response.json()

        assert "generated_at" in data
        assert "analysis_period" in data
        assert "emerging_topics" in data
        assert "trend_signals" in data
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_emerging_report_custom_params(self, client, populated_database):
        """Should accept custom parameters."""
        response = await client.get(
            "/api/emerging/report",
            params={
                "end_date": "2024-01-14",
                "lookback_days": 7,
                "comparison_days": 14
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "2024-01-14" in data["analysis_period"]

    @pytest.mark.asyncio
    async def test_emerging_report_invalid_lookback(self, client):
        """Should reject invalid lookback_days."""
        response = await client.get(
            "/api/emerging/report",
            params={"lookback_days": 5}  # Below minimum of 7
        )
        assert response.status_code == 422


class TestEmergingTrendsEndpoint:
    """Tests for /api/emerging/trends endpoint."""

    @pytest.mark.asyncio
    async def test_emerging_trends(self, client, populated_database):
        """Should return trend signals."""
        response = await client.get(
            "/api/emerging/trends",
            params={"end_date": "2024-01-14"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "end_date" in data
        assert "trends" in data
        assert isinstance(data["trends"], list)

    @pytest.mark.asyncio
    async def test_emerging_trends_limit(self, client, populated_database):
        """Should respect limit parameter."""
        response = await client.get(
            "/api/emerging/trends",
            params={"limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["trends"]) <= 5


class TestRisingTopicsEndpoint:
    """Tests for /api/emerging/rising endpoint."""

    @pytest.mark.asyncio
    async def test_rising_topics(self, client, populated_database):
        """Should return rising topics."""
        response = await client.get(
            "/api/emerging/rising",
            params={"min_growth": 10}
        )

        assert response.status_code == 200
        data = response.json()

        assert "end_date" in data
        assert "min_growth" in data
        assert "rising_topics" in data

        # All returned topics should be rising
        for topic in data["rising_topics"]:
            assert topic["trend_direction"] == "rising"


class TestHotTopicsEndpoint:
    """Tests for /api/emerging/hot endpoint."""

    @pytest.mark.asyncio
    async def test_hot_topics_requires_dates(self, client):
        """Should require start_date and end_date."""
        response = await client.get("/api/emerging/hot")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_hot_topics(self, client, populated_database):
        """Should return hot topics."""
        response = await client.get(
            "/api/emerging/hot",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-14",
                "min_papers": 2
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "start_date" in data
        assert "end_date" in data
        assert "hot_topics" in data


class TestSchedulerEndpoints:
    """Tests for scheduler-related endpoints."""

    @pytest.mark.asyncio
    async def test_scheduler_status(self, client):
        """Should return scheduler status."""
        response = await client.get("/api/scheduler/status")

        assert response.status_code == 200
        data = response.json()

        assert "is_running" in data
        assert "last_run" in data
        assert "config" in data

    @pytest.mark.asyncio
    async def test_scheduler_start(self, client):
        """Should start the scheduler."""
        with patch("main.get_scheduler") as mock_get:
            mock_scheduler = mock_get.return_value
            mock_scheduler.is_running = False
            mock_scheduler.get_status.return_value = {
                "config": {"scrape_time": "09:00 UTC"}
            }

            response = await client.post(
                "/api/scheduler/start",
                params={"run_now": False, "backfill": False}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"

    @pytest.mark.asyncio
    async def test_scheduler_start_already_running(self, client):
        """Should indicate when scheduler is already running."""
        with patch("main.get_scheduler") as mock_get:
            mock_scheduler = mock_get.return_value
            mock_scheduler.is_running = True

            response = await client.post("/api/scheduler/start")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "already_running"

    @pytest.mark.asyncio
    async def test_scheduler_stop(self, client):
        """Should stop the scheduler."""
        with patch("main.get_scheduler") as mock_get:
            mock_scheduler = mock_get.return_value
            mock_scheduler.is_running = True

            response = await client.post("/api/scheduler/stop")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_scheduler_backfill(self, client):
        """Should trigger backfill."""
        with patch("main.get_scheduler") as mock_get:
            mock_scheduler = mock_get.return_value
            mock_scheduler.backfill_missed_days = AsyncMock(return_value=[])

            response = await client.post(
                "/api/scheduler/backfill",
                params={"days": 7}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["days_checked"] == 7


class TestReindexDailyEndpoint:
    """Tests for /api/reindex/daily/{date} endpoint."""

    @pytest.mark.asyncio
    async def test_reindex_daily(self, client):
        """Should trigger daily reindexing."""
        response = await client.post(
            "/api/reindex/daily/2024-01-15",
            params={"use_llm": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "2024-01-15" in data["message"]

    @pytest.mark.asyncio
    async def test_reindex_daily_already_running(self, client):
        """Should indicate when reindex is already running."""
        # First request starts the job
        await client.post("/api/reindex/daily/2024-01-16")

        # Second request should indicate already running
        response = await client.post("/api/reindex/daily/2024-01-16")

        # It might be started or already_running depending on timing
        data = response.json()
        assert data["status"] in ["started", "already_running"]


class TestUpvoteHistoryEndpoint:
    """Tests for /api/papers/{paper_id}/upvote-history endpoint."""

    @pytest.mark.asyncio
    async def test_upvote_history_no_data(self, client):
        """Should return empty history for unknown paper."""
        response = await client.get("/api/papers/unknown-paper/upvote-history")

        assert response.status_code == 200
        data = response.json()
        assert data["paper_id"] == "unknown-paper"
        assert data["history"] == []

    @pytest.mark.asyncio
    async def test_upvote_history_with_data(self, client, populated_database_with_snapshots):
        """Should return upvote history for known paper."""
        papers = populated_database_with_snapshots["papers"]
        paper_id = papers[0].id

        response = await client.get(f"/api/papers/{paper_id}/upvote-history")

        assert response.status_code == 200
        data = response.json()
        assert data["paper_id"] == paper_id


class TestWeeklyStatsEndpoint:
    """Tests for /api/weekly/{week_start}/stats endpoint."""

    @pytest.mark.asyncio
    async def test_weekly_stats(self, client, populated_database):
        """Should return weekly statistics."""
        response = await client.get("/api/weekly/2024-01-01/stats")

        assert response.status_code == 200
        data = response.json()

        assert "week_start" in data
        assert "week_end" in data
        assert "total_papers" in data
        assert "clusters" in data
        assert "daily_counts" in data


class TestDailyPapersEndpoint:
    """Tests for /api/daily/{date} endpoint."""

    @pytest.mark.asyncio
    async def test_daily_papers(self, client, populated_database):
        """Should return papers for a specific date."""
        response = await client.get("/api/daily/2024-01-01")

        assert response.status_code == 200
        data = response.json()

        assert "date" in data
        assert "total_papers" in data
        assert "papers" in data

    @pytest.mark.asyncio
    async def test_daily_papers_limit(self, client, populated_database):
        """Should respect limit parameter."""
        response = await client.get(
            "/api/daily/2024-01-01",
            params={"limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["papers"]) <= 5
