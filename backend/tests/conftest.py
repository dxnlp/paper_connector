"""
Pytest configuration and shared fixtures for HF Papers Explorer tests.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import date, timedelta
import pytest
import aiosqlite

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import Paper, PaperTags, Taxonomy, DailySnapshot


# Use a separate test database
TEST_DATABASE_PATH = Path(__file__).parent / "test_papers.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_database(monkeypatch):
    """Set up and tear down test database for each test."""
    # Patch the database path
    import database
    monkeypatch.setattr(database, "DATABASE_PATH", TEST_DATABASE_PATH)

    # Initialize fresh database
    await database.init_database()

    yield

    # Clean up test database
    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()


@pytest.fixture
def sample_paper():
    """Create a sample paper for testing."""
    return Paper(
        id="2401.00001",
        title="Test Paper: A Novel Approach to AI Safety",
        abstract="This paper presents a novel approach to AI safety using reinforcement learning from human feedback (RLHF). We demonstrate significant improvements in alignment metrics.",
        published_date="2024-01-15",
        hf_url="https://huggingface.co/papers/2401.00001",
        arxiv_url="https://arxiv.org/abs/2401.00001",
        pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
        upvotes=150,
        authors=["Alice Smith", "Bob Jones"],
        content_hash="abc123",
        appeared_date="2024-01-15"
    )


@pytest.fixture
def sample_papers():
    """Create a list of sample papers with varied clusters and dates."""
    papers = []
    base_date = date(2024, 1, 1)

    clusters = [
        ("LLM / Foundation Models", "language model"),
        ("Computer Vision", "image classification"),
        ("Multimodal AI", "vision-language"),
        ("AI Safety / Alignment", "RLHF alignment"),
        ("Efficient AI", "quantization optimization"),
    ]

    for i in range(20):
        cluster_idx = i % len(clusters)
        cluster_name, keyword = clusters[cluster_idx]
        day_offset = i % 14  # Spread across 2 weeks

        papers.append(Paper(
            id=f"2401.{i:05d}",
            title=f"Paper {i}: Research on {keyword}",
            abstract=f"This paper explores {keyword} techniques. Keywords: {cluster_name.lower()}",
            published_date=(base_date + timedelta(days=day_offset)).strftime("%Y-%m-%d"),
            hf_url=f"https://huggingface.co/papers/2401.{i:05d}",
            arxiv_url=f"https://arxiv.org/abs/2401.{i:05d}",
            pdf_url=f"https://arxiv.org/pdf/2401.{i:05d}.pdf",
            upvotes=100 + i * 10,
            authors=[f"Author {i}"],
            content_hash=f"hash{i}",
            appeared_date=(base_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        ))

    return papers


@pytest.fixture
def sample_taxonomy():
    """Create a sample taxonomy."""
    return Taxonomy(
        month="2024-01",
        contribution_tags=[
            "LLM / Foundation Models",
            "Computer Vision",
            "Multimodal AI",
            "AI Safety / Alignment",
            "Efficient AI",
            "OTHER"
        ],
        task_tags=["classification", "generation", "retrieval", "reasoning"],
        modality_tags=["text", "image", "audio", "video"],
        definitions={
            "LLM / Foundation Models": "Research on large language models",
            "Computer Vision": "Research on visual understanding"
        }
    )


@pytest.fixture
def sample_paper_tags(sample_papers, sample_taxonomy):
    """Create sample paper tags matching the sample papers."""
    tags_list = []
    clusters = sample_taxonomy.contribution_tags[:5]

    for i, paper in enumerate(sample_papers):
        cluster_idx = i % len(clusters)

        tags_list.append(PaperTags(
            paper_id=paper.id,
            month="2024-01",
            primary_contribution_tag=clusters[cluster_idx],
            secondary_contribution_tags=[clusters[(cluster_idx + 1) % len(clusters)]],
            task_tags=["generation", "classification"] if i % 2 == 0 else ["reasoning"],
            modality_tags=["text"] if cluster_idx == 0 else ["image", "text"],
            research_question=f"Research question for paper {i}",
            confidence=0.85,
            rationale=f"Rationale for paper {i}"
        ))

    return tags_list


@pytest.fixture
async def populated_database(sample_papers, sample_taxonomy, sample_paper_tags):
    """Populate the test database with sample data."""
    import database

    # Save taxonomy
    await database.save_taxonomy(sample_taxonomy)

    # Save papers and tags
    for paper, tags in zip(sample_papers, sample_paper_tags):
        await database.upsert_paper(paper)
        await database.save_paper_tags(tags)

    return {
        "papers": sample_papers,
        "taxonomy": sample_taxonomy,
        "tags": sample_paper_tags
    }


@pytest.fixture
async def populated_database_with_snapshots(populated_database):
    """Populate database with daily snapshots as well."""
    import database
    from aggregation import save_daily_snapshot_for_date

    # Get unique dates from papers
    papers = populated_database["papers"]
    dates = set(p.appeared_date for p in papers if p.appeared_date)

    # Create snapshots for each date
    for date_str in sorted(dates):
        await save_daily_snapshot_for_date(date_str)

    return populated_database
