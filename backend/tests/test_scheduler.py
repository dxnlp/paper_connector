"""
Tests for scheduler module.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scheduler import (
    PaperScheduler,
    get_scheduler,
    SCRAPE_HOUR,
    SCRAPE_MINUTE,
)


class TestPaperSchedulerInit:
    """Tests for PaperScheduler initialization."""

    def test_initial_state(self):
        """Scheduler should start in stopped state."""
        scheduler = PaperScheduler()

        assert scheduler.is_running is False
        assert scheduler.last_run is None
        assert scheduler.last_status == "not_started"

    def test_scheduler_instance_created(self):
        """AsyncIOScheduler should be created."""
        scheduler = PaperScheduler()

        assert scheduler.scheduler is not None


class TestPaperSchedulerStatus:
    """Tests for PaperScheduler.get_status method."""

    def test_status_not_running(self):
        """Status should reflect stopped state."""
        scheduler = PaperScheduler()
        status = scheduler.get_status()

        assert status["is_running"] is False
        assert status["last_run"] is None
        assert status["last_status"] == "not_started"
        assert "config" in status

    def test_status_config(self):
        """Status should include configuration."""
        scheduler = PaperScheduler()
        status = scheduler.get_status()

        config = status["config"]
        assert "scrape_time" in config
        assert "use_llm" in config
        assert "backfill_days" in config


class TestPaperSchedulerScrapeAndIndex:
    """Tests for PaperScheduler.scrape_and_index_date method."""

    @pytest.mark.asyncio
    async def test_scrape_returns_result_dict(self):
        """Should return a result dictionary."""
        scheduler = PaperScheduler()

        # Mock scrape_daily to avoid actual scraping
        with patch("scheduler.scrape_daily", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = []

            result = await scheduler.scrape_and_index_date("2024-01-15")

            assert isinstance(result, dict)
            assert "date" in result
            assert "status" in result
            assert "papers_scraped" in result
            assert "papers_tagged" in result

    @pytest.mark.asyncio
    async def test_scrape_no_papers_found(self):
        """Should complete successfully when no papers found."""
        scheduler = PaperScheduler()

        with patch("scheduler.scrape_daily", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = []

            result = await scheduler.scrape_and_index_date("2024-01-15")

            assert result["status"] == "completed"
            assert result["papers_scraped"] == 0
            assert "No papers found" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_scrape_handles_error(self):
        """Should handle errors gracefully."""
        scheduler = PaperScheduler()

        with patch("scheduler.scrape_daily", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Network error")

            result = await scheduler.scrape_and_index_date("2024-01-15")

            assert result["status"] == "failed"
            assert result["error"] == "Network error"

    @pytest.mark.asyncio
    async def test_scrape_with_papers(self, sample_papers, sample_taxonomy):
        """Should process papers when found."""
        scheduler = PaperScheduler()

        test_papers = sample_papers[:2]

        with patch("scheduler.scrape_daily", new_callable=AsyncMock) as mock_scrape, \
             patch("scheduler.upsert_paper", new_callable=AsyncMock), \
             patch("scheduler.get_taxonomy", new_callable=AsyncMock) as mock_get_tax, \
             patch("scheduler.save_taxonomy", new_callable=AsyncMock), \
             patch("scheduler.tag_paper_heuristic") as mock_tag, \
             patch("scheduler.save_paper_tags", new_callable=AsyncMock), \
             patch("scheduler.save_daily_snapshot_for_date", new_callable=AsyncMock):

            mock_scrape.return_value = test_papers
            mock_get_tax.return_value = sample_taxonomy
            mock_tag.return_value = MagicMock()

            result = await scheduler.scrape_and_index_date("2024-01-15")

            assert result["status"] == "completed"
            assert result["papers_scraped"] == 2
            assert result["papers_tagged"] == 2


class TestPaperSchedulerDailyJob:
    """Tests for PaperScheduler.daily_job method."""

    @pytest.mark.asyncio
    async def test_skips_weekend(self):
        """Should skip execution on weekends."""
        scheduler = PaperScheduler()

        # Find a Saturday
        saturday = date(2024, 1, 13)  # This is a Saturday
        assert saturday.weekday() == 5

        with patch("scheduler.date") as mock_date, \
             patch("scheduler.is_weekday", return_value=False):
            mock_date.today.return_value = saturday

            result = await scheduler.daily_job()

            assert result is None

    @pytest.mark.asyncio
    async def test_runs_on_weekday(self):
        """Should run on weekdays."""
        scheduler = PaperScheduler()

        monday = date(2024, 1, 15)  # This is a Monday
        assert monday.weekday() == 0

        with patch("scheduler.date") as mock_date, \
             patch("scheduler.is_weekday", return_value=True), \
             patch.object(scheduler, "scrape_and_index_date", new_callable=AsyncMock) as mock_scrape:

            mock_date.today.return_value = monday
            mock_scrape.return_value = {"status": "completed", "date": "2024-01-15"}

            result = await scheduler.daily_job()

            mock_scrape.assert_called_once_with("2024-01-15")
            assert scheduler.last_run is not None
            assert scheduler.last_status == "completed"


class TestPaperSchedulerBackfill:
    """Tests for PaperScheduler.backfill_missed_days method."""

    @pytest.mark.asyncio
    async def test_backfill_empty_days(self):
        """Should check and backfill missing days."""
        scheduler = PaperScheduler()

        # Patch at the database module level since it's imported inside the function
        with patch("database.get_papers_by_date", new_callable=AsyncMock) as mock_get_papers, \
             patch("scheduler.is_weekday", return_value=True), \
             patch.object(scheduler, "scrape_and_index_date", new_callable=AsyncMock) as mock_scrape:

            # No existing papers
            mock_get_papers.return_value = []
            mock_scrape.return_value = {"status": "completed"}

            results = await scheduler.backfill_missed_days(days=3)

            # Should have attempted to backfill
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_backfill_skips_existing(self):
        """Should skip dates that already have papers."""
        scheduler = PaperScheduler()

        # Patch at the database module level since it's imported inside the function
        with patch("database.get_papers_by_date", new_callable=AsyncMock) as mock_get_papers, \
             patch("scheduler.is_weekday", return_value=True), \
             patch.object(scheduler, "scrape_and_index_date", new_callable=AsyncMock) as mock_scrape:

            # Papers exist
            mock_get_papers.return_value = [MagicMock()]

            results = await scheduler.backfill_missed_days(days=3)

            # Should not have called scrape since papers exist
            mock_scrape.assert_not_called()


class TestPaperSchedulerStartStop:
    """Tests for PaperScheduler start/stop methods."""

    def test_start_scheduler(self):
        """Should start the scheduler."""
        scheduler = PaperScheduler()

        with patch.object(scheduler.scheduler, "add_job"), \
             patch.object(scheduler.scheduler, "start"), \
             patch("asyncio.get_event_loop") as mock_loop:

            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance

            scheduler.start(run_now=False, backfill=False)

            assert scheduler.is_running is True
            scheduler.scheduler.start.assert_called_once()

    def test_stop_scheduler(self):
        """Should stop the scheduler."""
        scheduler = PaperScheduler()
        scheduler.is_running = True

        with patch.object(scheduler.scheduler, "shutdown"):
            scheduler.stop()

            assert scheduler.is_running is False
            scheduler.scheduler.shutdown.assert_called_once()


class TestGetScheduler:
    """Tests for get_scheduler singleton function."""

    def test_returns_scheduler(self):
        """Should return a PaperScheduler instance."""
        # Reset global scheduler
        import scheduler as sched_module
        sched_module._scheduler = None

        scheduler = get_scheduler()
        assert isinstance(scheduler, PaperScheduler)

    def test_returns_same_instance(self):
        """Should return the same instance on subsequent calls."""
        import scheduler as sched_module
        sched_module._scheduler = None

        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()

        assert scheduler1 is scheduler2


class TestSchedulerConfiguration:
    """Tests for scheduler configuration."""

    def test_default_scrape_hour(self):
        """Default scrape hour should be set."""
        assert SCRAPE_HOUR >= 0
        assert SCRAPE_HOUR <= 23

    def test_default_scrape_minute(self):
        """Default scrape minute should be valid."""
        assert SCRAPE_MINUTE >= 0
        assert SCRAPE_MINUTE <= 59
