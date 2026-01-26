"""
Scheduler for automated daily paper scraping.

Runs Monday-Friday at a configurable time (default 9:00 AM UTC).
Can also backfill missed days on startup.
"""

import asyncio
import os
from datetime import date, datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import init_database, upsert_paper, save_taxonomy, get_taxonomy, save_paper_tags
from scraper import scrape_daily, is_weekday
from llm_tagger import generate_taxonomy, tag_paper, tag_paper_heuristic, DEFAULT_CONTRIBUTION_TAGS, DEFAULT_TASK_TAGS, DEFAULT_MODALITY_TAGS
from aggregation import save_daily_snapshot_for_date
from database import Taxonomy


# Configuration from environment
SCRAPE_HOUR = int(os.environ.get("SCRAPE_HOUR", "9"))  # Hour in UTC
SCRAPE_MINUTE = int(os.environ.get("SCRAPE_MINUTE", "0"))
USE_LLM = os.environ.get("USE_LLM", "false").lower() == "true"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
BACKFILL_DAYS = int(os.environ.get("BACKFILL_DAYS", "7"))  # Days to backfill on startup


class PaperScheduler:
    """Scheduler for daily paper scraping jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_status: str = "not_started"

    async def scrape_and_index_date(self, date_str: str) -> dict:
        """
        Scrape and index papers for a specific date.

        Returns:
            Status dict with results
        """
        print(f"\n{'='*50}")
        print(f"[{datetime.now().isoformat()}] Starting scrape for {date_str}")
        print(f"{'='*50}")

        result = {
            "date": date_str,
            "status": "running",
            "papers_scraped": 0,
            "papers_tagged": 0,
            "error": None
        }

        try:
            # Step 1: Scrape papers
            print(f"Scraping papers for {date_str}...")
            papers = await scrape_daily(date_str)
            result["papers_scraped"] = len(papers)
            print(f"Found {len(papers)} papers")

            if not papers:
                result["status"] = "completed"
                result["message"] = "No papers found for this date"
                return result

            # Step 2: Save papers to database
            for paper in papers:
                await upsert_paper(paper)

            # Step 3: Get or create taxonomy
            month = date_str[:7]
            taxonomy = await get_taxonomy(month)

            if not taxonomy:
                print(f"Creating taxonomy for {month}...")
                if USE_LLM:
                    taxonomy = await generate_taxonomy(papers, month, provider=LLM_PROVIDER)
                else:
                    taxonomy = Taxonomy(
                        month=month,
                        contribution_tags=DEFAULT_CONTRIBUTION_TAGS,
                        task_tags=DEFAULT_TASK_TAGS,
                        modality_tags=DEFAULT_MODALITY_TAGS,
                        definitions={}
                    )
                await save_taxonomy(taxonomy)

            # Step 4: Tag papers
            print("Tagging papers...")
            for i, paper in enumerate(papers):
                if USE_LLM:
                    tags = await tag_paper(paper, taxonomy, provider=LLM_PROVIDER)
                else:
                    tags = tag_paper_heuristic(paper, taxonomy)

                await save_paper_tags(tags)
                result["papers_tagged"] = i + 1

                if (i + 1) % 10 == 0:
                    print(f"  Tagged {i + 1}/{len(papers)} papers")

            # Step 5: Save daily snapshot
            print("Saving daily snapshot...")
            await save_daily_snapshot_for_date(date_str)

            result["status"] = "completed"
            result["message"] = f"Successfully indexed {len(papers)} papers"
            print(f"Completed: {result['message']}")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"Failed: {e}")

        return result

    async def daily_job(self):
        """Job that runs daily to scrape today's papers."""
        today = date.today()

        # Only run on weekdays
        if not is_weekday(today):
            print(f"Skipping {today} - not a weekday")
            return

        date_str = today.strftime("%Y-%m-%d")
        self.last_run = datetime.now()

        result = await self.scrape_and_index_date(date_str)
        self.last_status = result["status"]

        return result

    async def backfill_missed_days(self, days: int = 7):
        """
        Check for and backfill any missed days in the past N days.

        Args:
            days: Number of days to look back
        """
        print(f"\nChecking for missed days in the past {days} days...")

        today = date.today()
        results = []

        for i in range(days, 0, -1):
            check_date = today - timedelta(days=i)

            # Skip weekends
            if not is_weekday(check_date):
                continue

            date_str = check_date.strftime("%Y-%m-%d")

            # Check if we have papers for this date
            from database import get_papers_by_date
            existing = await get_papers_by_date(date_str)

            if not existing:
                print(f"  Missing data for {date_str} - backfilling...")
                result = await self.scrape_and_index_date(date_str)
                results.append(result)
            else:
                print(f"  {date_str}: {len(existing)} papers already indexed")

        return results

    def start(self, run_now: bool = False, backfill: bool = True):
        """
        Start the scheduler.

        Args:
            run_now: If True, run an immediate scrape for today
            backfill: If True, backfill missed days on startup
        """
        # Schedule daily job at configured time (Mon-Fri)
        self.scheduler.add_job(
            self.daily_job,
            CronTrigger(
                day_of_week="mon-fri",
                hour=SCRAPE_HOUR,
                minute=SCRAPE_MINUTE
            ),
            id="daily_scrape",
            name="Daily Paper Scrape",
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True

        print(f"\nScheduler started!")
        print(f"  Daily scrape: {SCRAPE_HOUR:02d}:{SCRAPE_MINUTE:02d} UTC (Mon-Fri)")
        print(f"  LLM tagging: {'enabled' if USE_LLM else 'disabled'}")
        if USE_LLM:
            print(f"  LLM provider: {LLM_PROVIDER}")

        # Run async tasks
        loop = asyncio.get_event_loop()

        if backfill:
            loop.create_task(self.backfill_missed_days(BACKFILL_DAYS))

        if run_now:
            loop.create_task(self.daily_job())

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        self.is_running = False
        print("Scheduler stopped")

    def get_status(self) -> dict:
        """Get scheduler status."""
        next_run = None
        job = self.scheduler.get_job("daily_scrape")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()

        return {
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
            "next_run": next_run,
            "config": {
                "scrape_time": f"{SCRAPE_HOUR:02d}:{SCRAPE_MINUTE:02d} UTC",
                "use_llm": USE_LLM,
                "llm_provider": LLM_PROVIDER if USE_LLM else None,
                "backfill_days": BACKFILL_DAYS
            }
        }


# Global scheduler instance
_scheduler: Optional[PaperScheduler] = None


def get_scheduler() -> PaperScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PaperScheduler()
    return _scheduler


# CLI for running scheduler standalone
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Paper scraping scheduler")
    parser.add_argument("--run-now", action="store_true", help="Run immediate scrape")
    parser.add_argument("--no-backfill", action="store_true", help="Skip backfill on startup")
    parser.add_argument("--backfill-only", action="store_true", help="Only backfill, then exit")
    parser.add_argument("--date", type=str, help="Scrape specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    async def main():
        await init_database()

        scheduler = get_scheduler()

        if args.date:
            # Scrape specific date
            result = await scheduler.scrape_and_index_date(args.date)
            print(f"\nResult: {result}")
            return

        if args.backfill_only:
            # Just backfill and exit
            results = await scheduler.backfill_missed_days(BACKFILL_DAYS)
            print(f"\nBackfill complete: {len(results)} days processed")
            return

        # Start scheduler
        scheduler.start(
            run_now=args.run_now,
            backfill=not args.no_backfill
        )

        # Keep running
        print("\nScheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()

    asyncio.run(main())
