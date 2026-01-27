#!/usr/bin/env python3
"""
Script to tag all existing papers in the database without re-scraping.
This is useful after downloading papers day-by-day.
"""

import asyncio
import aiosqlite
from database import (
    DATABASE_PATH, init_database, get_all_papers, get_paper_tags,
    save_paper_tags, save_taxonomy, get_taxonomy, Taxonomy
)
from llm_tagger import (
    tag_paper_heuristic, tag_paper,
    DEFAULT_CONTRIBUTION_TAGS, DEFAULT_TASK_TAGS, DEFAULT_MODALITY_TAGS
)


async def tag_all_existing_papers(month: str = "2026-01", use_llm: bool = False, provider: str = None):
    """
    Tag all papers in the database that don't have tags yet.

    Args:
        month: Month string for taxonomy (YYYY-MM format)
        use_llm: Whether to use LLM for tagging (False = heuristic)
        provider: LLM provider to use if use_llm=True
    """
    await init_database()

    # Get or create taxonomy
    taxonomy = await get_taxonomy(month)
    if not taxonomy:
        print(f"Creating default taxonomy for {month}...")
        taxonomy = Taxonomy(
            month=month,
            contribution_tags=DEFAULT_CONTRIBUTION_TAGS,
            task_tags=DEFAULT_TASK_TAGS,
            modality_tags=DEFAULT_MODALITY_TAGS,
            definitions={}
        )
        await save_taxonomy(taxonomy)

    # Get all papers
    papers = await get_all_papers()
    print(f"Found {len(papers)} papers in database")

    # Count papers without tags
    untagged = []
    for paper in papers:
        existing_tags = await get_paper_tags(paper.id)
        if not existing_tags:
            untagged.append(paper)

    print(f"Papers without tags: {len(untagged)}")

    if not untagged:
        print("All papers are already tagged!")
        return

    # Tag untagged papers
    for i, paper in enumerate(untagged):
        print(f"Tagging {i + 1}/{len(untagged)}: {paper.id} - {paper.title[:50]}...")

        if use_llm:
            tags = await tag_paper(paper, taxonomy, provider=provider)
        else:
            tags = tag_paper_heuristic(paper, taxonomy)

        await save_paper_tags(tags)

    print(f"\nDone! Tagged {len(untagged)} papers.")

    # Verify
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM paper_tags") as cursor:
            total_tagged = (await cursor.fetchone())[0]
            print(f"Total papers with tags: {total_tagged}")


async def retag_all_papers(month: str = "2026-01", use_llm: bool = False, provider: str = None):
    """
    Re-tag ALL papers (overwriting existing tags).

    Args:
        month: Month string for taxonomy (YYYY-MM format)
        use_llm: Whether to use LLM for tagging
        provider: LLM provider to use if use_llm=True
    """
    await init_database()

    # Get or create taxonomy
    taxonomy = await get_taxonomy(month)
    if not taxonomy:
        print(f"Creating default taxonomy for {month}...")
        taxonomy = Taxonomy(
            month=month,
            contribution_tags=DEFAULT_CONTRIBUTION_TAGS,
            task_tags=DEFAULT_TASK_TAGS,
            modality_tags=DEFAULT_MODALITY_TAGS,
            definitions={}
        )
        await save_taxonomy(taxonomy)

    # Get all papers
    papers = await get_all_papers()
    print(f"Found {len(papers)} papers in database")
    print("Re-tagging ALL papers...")

    for i, paper in enumerate(papers):
        print(f"Tagging {i + 1}/{len(papers)}: {paper.id} - {paper.title[:50]}...")

        if use_llm:
            tags = await tag_paper(paper, taxonomy, provider=provider)
        else:
            tags = tag_paper_heuristic(paper, taxonomy)

        await save_paper_tags(tags)

    print(f"\nDone! Tagged {len(papers)} papers.")


async def main():
    import sys

    use_llm = "--llm" in sys.argv
    retag = "--retag" in sys.argv
    provider = None

    for arg in sys.argv[1:]:
        if arg.startswith("--provider="):
            provider = arg.split("=")[1]

    if retag:
        print("Re-tagging ALL papers (overwriting existing tags)...")
        await retag_all_papers(use_llm=use_llm, provider=provider)
    else:
        print("Tagging papers that don't have tags yet...")
        await tag_all_existing_papers(use_llm=use_llm, provider=provider)


if __name__ == "__main__":
    asyncio.run(main())
