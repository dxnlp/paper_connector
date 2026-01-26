"""
Tests for database module.
"""

import pytest
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    Paper, PaperTags, Taxonomy, DailySnapshot, UpvoteSnapshot,
    init_database,
    upsert_paper, get_paper, get_all_papers,
    save_taxonomy, get_taxonomy,
    save_paper_tags, get_paper_tags, get_all_paper_tags_for_month,
    get_papers_with_tags_for_month,
    get_papers_by_date, get_papers_by_date_range,
    get_papers_with_tags_by_date_range,
    record_upvote_snapshot, get_upvote_history,
    save_daily_snapshot, get_daily_snapshot, get_daily_snapshots_range,
    compute_content_hash,
)


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_returns_string(self):
        """Should return a string hash."""
        result = compute_content_hash("Title", "Abstract")
        assert isinstance(result, str)
        assert len(result) == 16

    def test_deterministic(self):
        """Same input should produce same hash."""
        hash1 = compute_content_hash("Title", "Abstract")
        hash2 = compute_content_hash("Title", "Abstract")
        assert hash1 == hash2

    def test_different_inputs(self):
        """Different inputs should produce different hashes."""
        hash1 = compute_content_hash("Title A", "Abstract A")
        hash2 = compute_content_hash("Title B", "Abstract B")
        assert hash1 != hash2


class TestPaperModel:
    """Tests for Paper Pydantic model."""

    def test_valid_paper(self):
        """Should create valid Paper."""
        paper = Paper(
            id="2401.00001",
            title="Test Paper",
            abstract="Test abstract",
            published_date="2024-01-15",
            hf_url="https://huggingface.co/papers/2401.00001"
        )

        assert paper.id == "2401.00001"
        assert paper.title == "Test Paper"
        assert paper.upvotes == 0  # Default

    def test_optional_fields(self):
        """Optional fields should have defaults."""
        paper = Paper(
            id="test",
            title="Test",
            abstract="Abstract",
            published_date="2024-01-01",
            hf_url="https://example.com"
        )

        assert paper.arxiv_url is None
        assert paper.pdf_url is None
        assert paper.authors == []
        assert paper.content_hash == ""


class TestPaperCRUD:
    """Tests for paper CRUD operations."""

    @pytest.mark.asyncio
    async def test_upsert_and_get_paper(self, sample_paper):
        """Should insert and retrieve paper."""
        await upsert_paper(sample_paper)
        retrieved = await get_paper(sample_paper.id)

        assert retrieved is not None
        assert retrieved.id == sample_paper.id
        assert retrieved.title == sample_paper.title
        assert retrieved.upvotes == sample_paper.upvotes

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, sample_paper):
        """Should update existing paper."""
        await upsert_paper(sample_paper)

        # Update upvotes
        sample_paper.upvotes = 200
        await upsert_paper(sample_paper)

        retrieved = await get_paper(sample_paper.id)
        assert retrieved.upvotes == 200

    @pytest.mark.asyncio
    async def test_get_nonexistent_paper(self):
        """Should return None for nonexistent paper."""
        result = await get_paper("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_papers(self, sample_papers):
        """Should retrieve all papers."""
        for paper in sample_papers:
            await upsert_paper(paper)

        all_papers = await get_all_papers()

        assert len(all_papers) >= len(sample_papers)
        ids = [p.id for p in all_papers]
        for paper in sample_papers:
            assert paper.id in ids


class TestTaxonomyCRUD:
    """Tests for taxonomy CRUD operations."""

    @pytest.mark.asyncio
    async def test_save_and_get_taxonomy(self, sample_taxonomy):
        """Should save and retrieve taxonomy."""
        await save_taxonomy(sample_taxonomy)
        retrieved = await get_taxonomy(sample_taxonomy.month)

        assert retrieved is not None
        assert retrieved.month == sample_taxonomy.month
        assert retrieved.contribution_tags == sample_taxonomy.contribution_tags

    @pytest.mark.asyncio
    async def test_get_nonexistent_taxonomy(self):
        """Should return None for nonexistent taxonomy."""
        result = await get_taxonomy("9999-01")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_updates_version(self, sample_taxonomy):
        """Should increment version on update."""
        await save_taxonomy(sample_taxonomy)
        first = await get_taxonomy(sample_taxonomy.month)

        await save_taxonomy(sample_taxonomy)
        second = await get_taxonomy(sample_taxonomy.month)

        assert second.version == first.version + 1


class TestPaperTagsCRUD:
    """Tests for paper tags CRUD operations."""

    @pytest.mark.asyncio
    async def test_save_and_get_tags(self, sample_paper, sample_taxonomy):
        """Should save and retrieve paper tags."""
        await upsert_paper(sample_paper)
        await save_taxonomy(sample_taxonomy)

        tags = PaperTags(
            paper_id=sample_paper.id,
            month="2024-01",
            primary_contribution_tag="LLM / Foundation Models",
            secondary_contribution_tags=["AI Safety / Alignment"],
            task_tags=["generation"],
            modality_tags=["text"],
            research_question="Test question",
            confidence=0.9,
            rationale="Test rationale"
        )

        await save_paper_tags(tags)
        retrieved = await get_paper_tags(sample_paper.id)

        assert retrieved is not None
        assert retrieved.paper_id == sample_paper.id
        assert retrieved.primary_contribution_tag == "LLM / Foundation Models"
        assert retrieved.confidence == 0.9

    @pytest.mark.asyncio
    async def test_get_nonexistent_tags(self):
        """Should return None for paper without tags."""
        result = await get_paper_tags("nonexistent-paper")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_tags_for_month(self, populated_database):
        """Should retrieve all tags for a month."""
        tags = await get_all_paper_tags_for_month("2024-01")

        assert len(tags) > 0
        for t in tags:
            assert t.month == "2024-01"


class TestPapersWithTags:
    """Tests for combined papers with tags queries."""

    @pytest.mark.asyncio
    async def test_get_papers_with_tags_for_month(self, populated_database):
        """Should retrieve papers with their tags."""
        results = await get_papers_with_tags_for_month("2024-01")

        assert len(results) > 0
        for item in results:
            assert "paper" in item
            assert "tags" in item
            assert isinstance(item["paper"], Paper)

    @pytest.mark.asyncio
    async def test_get_papers_with_tags_by_date_range(self, populated_database):
        """Should retrieve papers in date range with tags."""
        results = await get_papers_with_tags_by_date_range(
            "2024-01-01", "2024-01-07"
        )

        assert isinstance(results, list)
        for item in results:
            paper = item["paper"]
            if paper.appeared_date:
                assert "2024-01-01" <= paper.appeared_date <= "2024-01-07"


class TestPapersByDate:
    """Tests for date-based paper queries."""

    @pytest.mark.asyncio
    async def test_get_papers_by_date(self, populated_database):
        """Should retrieve papers by appeared date."""
        papers = await get_papers_by_date("2024-01-01")

        for paper in papers:
            assert paper.appeared_date == "2024-01-01"

    @pytest.mark.asyncio
    async def test_get_papers_by_date_range(self, populated_database):
        """Should retrieve papers in date range."""
        papers = await get_papers_by_date_range("2024-01-01", "2024-01-07")

        for paper in papers:
            if paper.appeared_date:
                assert "2024-01-01" <= paper.appeared_date <= "2024-01-07"


class TestUpvoteHistory:
    """Tests for upvote history tracking."""

    @pytest.mark.asyncio
    async def test_record_and_get_history(self, sample_paper):
        """Should record and retrieve upvote history."""
        await upsert_paper(sample_paper)

        await record_upvote_snapshot(sample_paper.id, "2024-01-15", 100)
        await record_upvote_snapshot(sample_paper.id, "2024-01-16", 150)

        history = await get_upvote_history(sample_paper.id)

        assert len(history) == 2
        assert history[0].date == "2024-01-15"
        assert history[0].upvotes == 100
        assert history[1].date == "2024-01-16"
        assert history[1].upvotes == 150

    @pytest.mark.asyncio
    async def test_update_existing_snapshot(self, sample_paper):
        """Should update upvotes for existing date."""
        await upsert_paper(sample_paper)

        await record_upvote_snapshot(sample_paper.id, "2024-01-15", 100)
        await record_upvote_snapshot(sample_paper.id, "2024-01-15", 200)  # Same date

        history = await get_upvote_history(sample_paper.id)

        assert len(history) == 1
        assert history[0].upvotes == 200


class TestDailySnapshots:
    """Tests for daily snapshot operations."""

    @pytest.mark.asyncio
    async def test_save_and_get_snapshot(self):
        """Should save and retrieve daily snapshot."""
        snapshot = DailySnapshot(
            date="2024-01-15",
            total_papers=50,
            cluster_counts={"LLM": 20, "Vision": 15, "Other": 15},
            top_paper_ids=["paper1", "paper2"],
            new_paper_ids=["paper3", "paper4"]
        )

        await save_daily_snapshot(snapshot)
        retrieved = await get_daily_snapshot("2024-01-15")

        assert retrieved is not None
        assert retrieved.date == "2024-01-15"
        assert retrieved.total_papers == 50
        assert retrieved.cluster_counts["LLM"] == 20

    @pytest.mark.asyncio
    async def test_get_snapshots_range(self):
        """Should retrieve snapshots in date range."""
        for day in range(1, 8):
            snapshot = DailySnapshot(
                date=f"2024-01-{day:02d}",
                total_papers=day * 10,
                cluster_counts={},
                top_paper_ids=[],
                new_paper_ids=[]
            )
            await save_daily_snapshot(snapshot)

        snapshots = await get_daily_snapshots_range("2024-01-01", "2024-01-05")

        assert len(snapshots) == 5
        dates = [s.date for s in snapshots]
        assert dates == sorted(dates)


class TestModels:
    """Tests for Pydantic model validation."""

    def test_paper_tags_model(self):
        """PaperTags model should validate correctly."""
        tags = PaperTags(
            paper_id="test-paper",
            month="2024-01",
            primary_contribution_tag="LLM"
        )

        assert tags.paper_id == "test-paper"
        assert tags.secondary_contribution_tags == []

    def test_taxonomy_model(self):
        """Taxonomy model should validate correctly."""
        taxonomy = Taxonomy(
            month="2024-01",
            contribution_tags=["A", "B"],
            task_tags=["X", "Y"],
            modality_tags=["text"]
        )

        assert taxonomy.month == "2024-01"
        assert taxonomy.version == 1

    def test_daily_snapshot_model(self):
        """DailySnapshot model should validate correctly."""
        snapshot = DailySnapshot(
            date="2024-01-15",
            total_papers=100,
            cluster_counts={"A": 50, "B": 50},
            top_paper_ids=["p1"],
            new_paper_ids=["p2"]
        )

        assert snapshot.date == "2024-01-15"
        assert sum(snapshot.cluster_counts.values()) == 100

    def test_upvote_snapshot_model(self):
        """UpvoteSnapshot model should validate correctly."""
        snapshot = UpvoteSnapshot(
            paper_id="test",
            date="2024-01-15",
            upvotes=100
        )

        assert snapshot.paper_id == "test"
        assert snapshot.upvotes == 100
