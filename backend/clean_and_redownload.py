#!/usr/bin/env python3
"""
Script to clean existing papers and re-download day by day.
This ensures proper appeared_date tracking for temporal flow visualization.
"""

import asyncio
import aiosqlite
import httpx
import random
from datetime import date, timedelta
from database import DATABASE_PATH, init_database, upsert_paper
from scraper import fetch_daily_paper_ids, fetch_paper_details


# Rate limiting settings
DELAY_BETWEEN_PAPERS = 1.5  # seconds between fetching each paper
DELAY_BETWEEN_DAYS = 3.0    # seconds between scraping days
MAX_RETRIES = 3
RETRY_BASE_DELAY = 30       # base delay for retry (will be multiplied by attempt)


async def clean_database():
    """Remove all existing paper data from the database."""
    print("Cleaning database...")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Delete in order to respect foreign key constraints
        await db.execute("DELETE FROM paper_tags")
        await db.execute("DELETE FROM upvote_history")
        await db.execute("DELETE FROM daily_snapshots")
        await db.execute("DELETE FROM papers")
        # Keep taxonomies as they can be reused
        await db.commit()
    print("Database cleaned.")


async def fetch_with_retry(fetch_func, *args, **kwargs):
    """Fetch with retry logic and exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await fetch_func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = RETRY_BASE_DELAY * attempt + random.uniform(0, 10)
                print(f"    Rate limited (attempt {attempt}/{MAX_RETRIES}). Waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
            else:
                raise
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            wait_time = RETRY_BASE_DELAY * attempt
            print(f"    Error (attempt {attempt}/{MAX_RETRIES}): {e}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    return None


async def scrape_daily_with_rate_limit(date_str: str):
    """
    Scrape papers for a specific date with rate limiting.

    Args:
        date_str: Date string in format YYYY-MM-DD

    Returns:
        List of Paper objects
    """
    print(f"  Fetching paper list...")
    paper_ids = await fetch_with_retry(fetch_daily_paper_ids, date_str)

    if paper_ids is None:
        return []

    print(f"  Found {len(paper_ids)} papers")

    papers = []
    for i, paper_id in enumerate(paper_ids):
        print(f"  Fetching paper {i + 1}/{len(paper_ids)}: {paper_id}")

        paper = await fetch_with_retry(fetch_paper_details, paper_id, appeared_date=date_str)
        if paper:
            papers.append(paper)

        # Rate limiting delay between papers
        if i < len(paper_ids) - 1:
            await asyncio.sleep(DELAY_BETWEEN_PAPERS)

    return papers


async def download_papers_day_by_day(start_date: str, end_date: str, resume_from: str = None):
    """
    Download papers day by day from HuggingFace.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        resume_from: Optional date to resume from (skip dates before this)
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if resume_from:
        resume = date.fromisoformat(resume_from)
        if resume > start:
            print(f"Resuming from {resume_from}")
            start = resume

    current = start
    total_papers = 0
    seen_ids = set()

    # If resuming, load existing paper IDs to avoid duplicates
    if resume_from:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT id FROM papers") as cursor:
                async for row in cursor:
                    seen_ids.add(row[0])
        print(f"Loaded {len(seen_ids)} existing paper IDs")

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        print(f"\n{'='*60}")
        print(f"Scraping {date_str}")
        print(f"{'='*60}")

        try:
            papers = await scrape_daily_with_rate_limit(date_str)

            new_count = 0
            for paper in papers:
                if paper.id not in seen_ids:
                    await upsert_paper(paper)
                    seen_ids.add(paper.id)
                    new_count += 1
                    total_papers += 1
                else:
                    print(f"    Skipping duplicate: {paper.id} (already appeared earlier)")

            print(f"  Saved {new_count} new papers (skipped {len(papers) - new_count} duplicates)")

        except Exception as e:
            print(f"  Error scraping {date_str}: {e}")
            print(f"  You can resume later with: resume_from='{date_str}'")

        # Delay between days
        if current < end:
            await asyncio.sleep(DELAY_BETWEEN_DAYS)

        current += timedelta(days=1)

    print(f"\n{'='*60}")
    print(f"DONE! Total unique papers downloaded: {total_papers}")
    print(f"{'='*60}")


async def main():
    import sys

    # Initialize database tables
    await init_database()

    # Check for resume argument
    resume_from = None
    clean = True

    for arg in sys.argv[1:]:
        if arg.startswith("--resume="):
            resume_from = arg.split("=")[1]
            clean = False
        elif arg == "--no-clean":
            clean = False

    # Clean existing data (unless resuming)
    if clean:
        await clean_database()

    # Download papers day by day
    await download_papers_day_by_day("2026-01-01", "2026-01-27", resume_from=resume_from)


if __name__ == "__main__":
    asyncio.run(main())
