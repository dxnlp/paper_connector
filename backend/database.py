"""
Database models and utilities for HF Papers Explorer.
Uses SQLite with aiosqlite for async operations.
"""

import aiosqlite
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

DATABASE_PATH = Path(__file__).parent / "papers.db"


class Paper(BaseModel):
    """Paper data model."""
    id: str  # arxiv id
    title: str
    abstract: str
    published_date: str
    hf_url: str
    arxiv_url: Optional[str] = None
    pdf_url: Optional[str] = None
    upvotes: int = 0
    authors: list[str] = []
    content_hash: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Taxonomy(BaseModel):
    """Taxonomy for a given month."""
    month: str
    contribution_tags: list[str]
    task_tags: list[str]
    modality_tags: list[str]
    definitions: dict = {}
    version: int = 1


class PaperTags(BaseModel):
    """Tags assigned to a paper."""
    paper_id: str
    month: str
    primary_contribution_tag: str
    secondary_contribution_tags: list[str] = []
    task_tags: list[str] = []
    modality_tags: list[str] = []
    research_question: str = ""
    confidence: float = 0.0
    rationale: str = ""


def compute_content_hash(title: str, abstract: str) -> str:
    """Compute SHA256 hash of title + abstract for change detection."""
    content = f"{title}{abstract}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def init_database():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Papers table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                published_date TEXT,
                hf_url TEXT NOT NULL,
                arxiv_url TEXT,
                pdf_url TEXT,
                upvotes INTEGER DEFAULT 0,
                authors_json TEXT DEFAULT '[]',
                content_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Taxonomies table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS taxonomies (
                month TEXT PRIMARY KEY,
                contribution_tags_json TEXT NOT NULL,
                task_tags_json TEXT NOT NULL,
                modality_tags_json TEXT NOT NULL,
                definitions_json TEXT DEFAULT '{}',
                version INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Paper tags table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_tags (
                paper_id TEXT PRIMARY KEY,
                month TEXT NOT NULL,
                primary_contribution_tag TEXT NOT NULL,
                secondary_contribution_tags_json TEXT DEFAULT '[]',
                task_tags_json TEXT DEFAULT '[]',
                modality_tags_json TEXT DEFAULT '[]',
                research_question TEXT,
                confidence REAL DEFAULT 0.0,
                rationale TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
        """)
        
        # Indexes for faster queries
        await db.execute("CREATE INDEX IF NOT EXISTS idx_paper_tags_month ON paper_tags(month)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_paper_tags_primary ON paper_tags(primary_contribution_tag)")
        
        await db.commit()


async def upsert_paper(paper: Paper):
    """Insert or update a paper record."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO papers (id, title, abstract, published_date, hf_url, arxiv_url, pdf_url, upvotes, authors_json, content_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                abstract = excluded.abstract,
                published_date = excluded.published_date,
                hf_url = excluded.hf_url,
                arxiv_url = excluded.arxiv_url,
                pdf_url = excluded.pdf_url,
                upvotes = excluded.upvotes,
                authors_json = excluded.authors_json,
                content_hash = excluded.content_hash,
                updated_at = excluded.updated_at
        """, (
            paper.id, paper.title, paper.abstract, paper.published_date,
            paper.hf_url, paper.arxiv_url, paper.pdf_url, paper.upvotes,
            json.dumps(paper.authors), paper.content_hash,
            datetime.now().isoformat()
        ))
        await db.commit()


async def get_paper(paper_id: str) -> Optional[Paper]:
    """Get a paper by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return Paper(
                    id=row['id'],
                    title=row['title'],
                    abstract=row['abstract'],
                    published_date=row['published_date'] or "",
                    hf_url=row['hf_url'],
                    arxiv_url=row['arxiv_url'],
                    pdf_url=row['pdf_url'],
                    upvotes=row['upvotes'],
                    authors=json.loads(row['authors_json']),
                    content_hash=row['content_hash'] or "",
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
    return None


async def get_all_papers() -> list[Paper]:
    """Get all papers."""
    papers = []
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM papers ORDER BY upvotes DESC") as cursor:
            async for row in cursor:
                papers.append(Paper(
                    id=row['id'],
                    title=row['title'],
                    abstract=row['abstract'],
                    published_date=row['published_date'] or "",
                    hf_url=row['hf_url'],
                    arxiv_url=row['arxiv_url'],
                    pdf_url=row['pdf_url'],
                    upvotes=row['upvotes'],
                    authors=json.loads(row['authors_json']),
                    content_hash=row['content_hash'] or "",
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
    return papers


async def save_taxonomy(taxonomy: Taxonomy):
    """Save or update taxonomy for a month."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO taxonomies (month, contribution_tags_json, task_tags_json, modality_tags_json, definitions_json, version)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(month) DO UPDATE SET
                contribution_tags_json = excluded.contribution_tags_json,
                task_tags_json = excluded.task_tags_json,
                modality_tags_json = excluded.modality_tags_json,
                definitions_json = excluded.definitions_json,
                version = taxonomies.version + 1
        """, (
            taxonomy.month,
            json.dumps(taxonomy.contribution_tags),
            json.dumps(taxonomy.task_tags),
            json.dumps(taxonomy.modality_tags),
            json.dumps(taxonomy.definitions),
            taxonomy.version
        ))
        await db.commit()


async def get_taxonomy(month: str) -> Optional[Taxonomy]:
    """Get taxonomy for a month."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM taxonomies WHERE month = ?", (month,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return Taxonomy(
                    month=row['month'],
                    contribution_tags=json.loads(row['contribution_tags_json']),
                    task_tags=json.loads(row['task_tags_json']),
                    modality_tags=json.loads(row['modality_tags_json']),
                    definitions=json.loads(row['definitions_json']),
                    version=row['version']
                )
    return None


async def save_paper_tags(tags: PaperTags):
    """Save paper tags."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO paper_tags (paper_id, month, primary_contribution_tag, secondary_contribution_tags_json, task_tags_json, modality_tags_json, research_question, confidence, rationale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id) DO UPDATE SET
                month = excluded.month,
                primary_contribution_tag = excluded.primary_contribution_tag,
                secondary_contribution_tags_json = excluded.secondary_contribution_tags_json,
                task_tags_json = excluded.task_tags_json,
                modality_tags_json = excluded.modality_tags_json,
                research_question = excluded.research_question,
                confidence = excluded.confidence,
                rationale = excluded.rationale
        """, (
            tags.paper_id, tags.month, tags.primary_contribution_tag,
            json.dumps(tags.secondary_contribution_tags),
            json.dumps(tags.task_tags),
            json.dumps(tags.modality_tags),
            tags.research_question, tags.confidence, tags.rationale
        ))
        await db.commit()


async def get_paper_tags(paper_id: str) -> Optional[PaperTags]:
    """Get tags for a paper."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM paper_tags WHERE paper_id = ?", (paper_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return PaperTags(
                    paper_id=row['paper_id'],
                    month=row['month'],
                    primary_contribution_tag=row['primary_contribution_tag'],
                    secondary_contribution_tags=json.loads(row['secondary_contribution_tags_json']),
                    task_tags=json.loads(row['task_tags_json']),
                    modality_tags=json.loads(row['modality_tags_json']),
                    research_question=row['research_question'] or "",
                    confidence=row['confidence'],
                    rationale=row['rationale'] or ""
                )
    return None


async def get_all_paper_tags_for_month(month: str) -> list[PaperTags]:
    """Get all paper tags for a specific month."""
    tags_list = []
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM paper_tags WHERE month = ?", (month,)) as cursor:
            async for row in cursor:
                tags_list.append(PaperTags(
                    paper_id=row['paper_id'],
                    month=row['month'],
                    primary_contribution_tag=row['primary_contribution_tag'],
                    secondary_contribution_tags=json.loads(row['secondary_contribution_tags_json']),
                    task_tags=json.loads(row['task_tags_json']),
                    modality_tags=json.loads(row['modality_tags_json']),
                    research_question=row['research_question'] or "",
                    confidence=row['confidence'],
                    rationale=row['rationale'] or ""
                ))
    return tags_list


async def get_papers_with_tags_for_month(month: str) -> list[dict]:
    """Get all papers with their tags for a month (joined query)."""
    results = []
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT p.*, pt.primary_contribution_tag, pt.secondary_contribution_tags_json,
                   pt.task_tags_json, pt.modality_tags_json, pt.research_question,
                   pt.confidence, pt.rationale
            FROM papers p
            LEFT JOIN paper_tags pt ON p.id = pt.paper_id
            WHERE pt.month = ?
            ORDER BY p.upvotes DESC
        """
        async with db.execute(query, (month,)) as cursor:
            async for row in cursor:
                results.append({
                    "paper": Paper(
                        id=row['id'],
                        title=row['title'],
                        abstract=row['abstract'],
                        published_date=row['published_date'] or "",
                        hf_url=row['hf_url'],
                        arxiv_url=row['arxiv_url'],
                        pdf_url=row['pdf_url'],
                        upvotes=row['upvotes'],
                        authors=json.loads(row['authors_json']),
                        content_hash=row['content_hash'] or ""
                    ),
                    "tags": PaperTags(
                        paper_id=row['id'],
                        month=month,
                        primary_contribution_tag=row['primary_contribution_tag'] or "OTHER",
                        secondary_contribution_tags=json.loads(row['secondary_contribution_tags_json'] or '[]'),
                        task_tags=json.loads(row['task_tags_json'] or '[]'),
                        modality_tags=json.loads(row['modality_tags_json'] or '[]'),
                        research_question=row['research_question'] or "",
                        confidence=row['confidence'] or 0.0,
                        rationale=row['rationale'] or ""
                    ) if row['primary_contribution_tag'] else None
                })
    return results
