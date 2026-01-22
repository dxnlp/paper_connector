"""
FastAPI backend for HF Papers Explorer.
Provides REST API for papers, clusters, and taxonomy management.
"""

import os
import re
import json
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from collections import defaultdict

from database import (
    init_database, 
    upsert_paper, get_paper, get_all_papers,
    save_taxonomy, get_taxonomy,
    save_paper_tags, get_paper_tags, get_all_paper_tags_for_month,
    get_papers_with_tags_for_month,
    Paper, Taxonomy, PaperTags
)
from scraper import scrape_month, fetch_month_paper_ids, fetch_paper_details
from llm_tagger import (
    generate_taxonomy, tag_paper, tag_all_papers, tag_paper_heuristic,
    DEFAULT_CONTRIBUTION_TAGS, DEFAULT_TASK_TAGS, DEFAULT_MODALITY_TAGS
)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down")


app = FastAPI(
    title="HF Papers Explorer API",
    description="API for exploring Hugging Face Papers of the Month",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Response Models =============

class PaperCard(BaseModel):
    """Paper card data for frontend display."""
    paperId: str
    title: str
    abstractSnippet: str
    publishedDate: str
    upvotes: int
    authorsShort: list[str]
    primaryTag: str
    secondaryTags: list[str]
    taskTags: list[str]
    modality: list[str]
    hfUrl: str
    pdfUrl: str
    arxivUrl: str
    researchQuestion: str
    confidence: float
    rationale: str


class ClusterInfo(BaseModel):
    """Cluster summary for frontend."""
    clusterId: str
    name: str
    paperCount: int
    topTaskTags: list[str]
    topModalities: list[str]


class MonthSummary(BaseModel):
    """Summary of a month's papers."""
    month: str
    totalPapers: int
    clusters: list[ClusterInfo]
    taxonomy: Optional[dict] = None


class ClusterNode(BaseModel):
    """Node in the cluster graph."""
    id: str
    name: str
    paperCount: int
    topTaskTags: list[str]
    topModalities: list[str]
    paperIds: list[str]  # List of paper IDs in this cluster


class ClusterLink(BaseModel):
    """Link between two clusters (shared papers via secondary tags)."""
    source: str
    target: str
    sharedCount: int  # Number of shared papers
    sharedPaperIds: list[str]  # IDs of shared papers


class ClusterGraph(BaseModel):
    """Graph structure for cluster visualization."""
    nodes: list[ClusterNode]
    links: list[ClusterLink]


# ============= Helper Functions =============

def paper_to_card(paper: Paper, tags: Optional[PaperTags]) -> PaperCard:
    """Convert Paper + PaperTags to PaperCard for frontend."""
    abstract_snippet = paper.abstract[:250] + "..." if len(paper.abstract) > 250 else paper.abstract
    authors_short = paper.authors[:3] if paper.authors else []
    
    return PaperCard(
        paperId=paper.id,
        title=paper.title,
        abstractSnippet=abstract_snippet,
        publishedDate=paper.published_date,
        upvotes=paper.upvotes,
        authorsShort=authors_short,
        primaryTag=tags.primary_contribution_tag if tags else "OTHER",
        secondaryTags=tags.secondary_contribution_tags if tags else [],
        taskTags=tags.task_tags if tags else [],
        modality=tags.modality_tags if tags else ["text"],
        hfUrl=paper.hf_url,
        pdfUrl=paper.pdf_url or f"https://arxiv.org/pdf/{paper.id}.pdf",
        arxivUrl=paper.arxiv_url or f"https://arxiv.org/abs/{paper.id}",
        researchQuestion=tags.research_question if tags else "",
        confidence=tags.confidence if tags else 0.0,
        rationale=tags.rationale if tags else ""
    )


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


def build_clusters(papers_with_tags: list[dict]) -> list[ClusterInfo]:
    """Build cluster information from papers with tags."""
    clusters_data = defaultdict(lambda: {
        "papers": [],
        "task_tags": defaultdict(int),
        "modalities": defaultdict(int)
    })
    
    for item in papers_with_tags:
        tags = item.get("tags")
        if not tags:
            continue
        
        primary_tag = tags.primary_contribution_tag
        clusters_data[primary_tag]["papers"].append(item)
        
        for task in tags.task_tags:
            clusters_data[primary_tag]["task_tags"][task] += 1
        
        for mod in tags.modality_tags:
            clusters_data[primary_tag]["modalities"][mod] += 1
    
    clusters = []
    for tag_name, data in clusters_data.items():
        top_tasks = sorted(data["task_tags"].items(), key=lambda x: -x[1])[:5]
        top_mods = sorted(data["modalities"].items(), key=lambda x: -x[1])[:3]
        
        clusters.append(ClusterInfo(
            clusterId=slugify(tag_name),
            name=tag_name,
            paperCount=len(data["papers"]),
            topTaskTags=[t[0] for t in top_tasks],
            topModalities=[m[0] for m in top_mods]
        ))
    
    # Sort by paper count descending
    clusters.sort(key=lambda c: -c.paperCount)
    return clusters


def build_cluster_graph(papers_with_tags: list[dict]) -> ClusterGraph:
    """Build cluster graph with nodes and connections based on shared papers."""
    # Build cluster nodes with paper IDs
    clusters_data = defaultdict(lambda: {
        "papers": [],
        "paper_ids": set(),
        "task_tags": defaultdict(int),
        "modalities": defaultdict(int)
    })
    
    # Also track papers by their task tags for finding connections
    task_to_papers = defaultdict(set)
    paper_to_clusters = defaultdict(set)
    
    for item in papers_with_tags:
        tags = item.get("tags")
        paper = item.get("paper")
        if not tags or not paper:
            continue
        
        primary_tag = tags.primary_contribution_tag
        paper_id = paper.id
        
        clusters_data[primary_tag]["papers"].append(item)
        clusters_data[primary_tag]["paper_ids"].add(paper_id)
        paper_to_clusters[paper_id].add(primary_tag)
        
        for task in tags.task_tags:
            clusters_data[primary_tag]["task_tags"][task] += 1
            task_to_papers[task].add(paper_id)
        
        for mod in tags.modality_tags:
            clusters_data[primary_tag]["modalities"][mod] += 1
        
        # Also consider secondary contribution tags for connections
        for secondary_tag in tags.secondary_contribution_tags:
            paper_to_clusters[paper_id].add(secondary_tag)
    
    # Build nodes
    nodes = []
    for tag_name, data in clusters_data.items():
        top_tasks = sorted(data["task_tags"].items(), key=lambda x: -x[1])[:5]
        top_mods = sorted(data["modalities"].items(), key=lambda x: -x[1])[:3]
        
        nodes.append(ClusterNode(
            id=slugify(tag_name),
            name=tag_name,
            paperCount=len(data["papers"]),
            topTaskTags=[t[0] for t in top_tasks],
            topModalities=[m[0] for m in top_mods],
            paperIds=list(data["paper_ids"])
        ))
    
    # Sort nodes by paper count
    nodes.sort(key=lambda n: -n.paperCount)
    
    # Build links based on shared task tags and secondary contribution tags
    links = []
    cluster_names = list(clusters_data.keys())
    
    for i, cluster1 in enumerate(cluster_names):
        for cluster2 in cluster_names[i+1:]:
            # Find shared papers (papers that have both clusters in their tags)
            shared_paper_ids = set()
            
            # Check papers in cluster1 that also reference cluster2
            for paper_id in clusters_data[cluster1]["paper_ids"]:
                if cluster2 in paper_to_clusters[paper_id]:
                    shared_paper_ids.add(paper_id)
            
            # Check papers in cluster2 that also reference cluster1
            for paper_id in clusters_data[cluster2]["paper_ids"]:
                if cluster1 in paper_to_clusters[paper_id]:
                    shared_paper_ids.add(paper_id)
            
            # Also find papers that share task tags between clusters
            cluster1_tasks = set(clusters_data[cluster1]["task_tags"].keys())
            cluster2_tasks = set(clusters_data[cluster2]["task_tags"].keys())
            common_tasks = cluster1_tasks & cluster2_tasks
            
            for task in common_tasks:
                task_papers = task_to_papers[task]
                cluster1_papers = clusters_data[cluster1]["paper_ids"]
                cluster2_papers = clusters_data[cluster2]["paper_ids"]
                
                # Papers from cluster1 sharing task with cluster2
                for pid in cluster1_papers & task_papers:
                    if clusters_data[cluster2]["paper_ids"] & task_papers:
                        shared_paper_ids.add(pid)
            
            if shared_paper_ids or common_tasks:
                # Connection strength based on shared tasks + secondary tags
                strength = len(shared_paper_ids) + len(common_tasks)
                if strength > 0:
                    links.append(ClusterLink(
                        source=slugify(cluster1),
                        target=slugify(cluster2),
                        sharedCount=strength,
                        sharedPaperIds=list(shared_paper_ids)[:10]  # Limit for performance
                    ))
    
    # Sort links by strength
    links.sort(key=lambda l: -l.sharedCount)
    
    return ClusterGraph(nodes=nodes, links=links)


# ============= API Endpoints =============

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "HF Papers Explorer API"}


@app.get("/api/months/{month}/papers", response_model=list[PaperCard])
async def get_month_papers(
    month: str,
    cluster: Optional[str] = None,
    task: Optional[str] = None,
    modality: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("upvotes", enum=["upvotes", "date", "confidence"]),
    limit: int = Query(100, le=500),
    offset: int = 0
):
    """
    Get all papers for a month with optional filtering.
    
    - **month**: Month in YYYY-MM format
    - **cluster**: Filter by primary contribution tag (cluster name)
    - **task**: Filter by task tag
    - **modality**: Filter by modality
    - **search**: Search in title/abstract
    - **sort_by**: Sort by upvotes, date, or confidence
    """
    papers_with_tags = await get_papers_with_tags_for_month(month)
    
    if not papers_with_tags:
        return []
    
    # Apply filters
    filtered = []
    for item in papers_with_tags:
        paper = item["paper"]
        tags = item["tags"]
        
        # Cluster filter
        if cluster and tags:
            if slugify(tags.primary_contribution_tag) != cluster:
                continue
        
        # Task filter
        if task and tags:
            if task not in tags.task_tags:
                continue
        
        # Modality filter
        if modality and tags:
            if modality not in tags.modality_tags:
                continue
        
        # Search filter
        if search:
            search_lower = search.lower()
            if search_lower not in paper.title.lower() and search_lower not in paper.abstract.lower():
                continue
        
        filtered.append(item)
    
    # Sort
    if sort_by == "upvotes":
        filtered.sort(key=lambda x: -x["paper"].upvotes)
    elif sort_by == "date":
        filtered.sort(key=lambda x: x["paper"].published_date, reverse=True)
    elif sort_by == "confidence":
        filtered.sort(key=lambda x: -(x["tags"].confidence if x["tags"] else 0))
    
    # Pagination
    paginated = filtered[offset:offset + limit]
    
    # Convert to cards
    cards = [paper_to_card(item["paper"], item["tags"]) for item in paginated]
    return cards


@app.get("/api/months/{month}/clusters", response_model=list[ClusterInfo])
async def get_month_clusters(month: str):
    """Get cluster summaries for a month."""
    papers_with_tags = await get_papers_with_tags_for_month(month)
    
    if not papers_with_tags:
        return []
    
    return build_clusters(papers_with_tags)


@app.get("/api/months/{month}/cluster-graph", response_model=ClusterGraph)
async def get_cluster_graph(month: str):
    """Get cluster graph with nodes and connections for visualization."""
    papers_with_tags = await get_papers_with_tags_for_month(month)
    
    if not papers_with_tags:
        return ClusterGraph(nodes=[], links=[])
    
    return build_cluster_graph(papers_with_tags)


@app.get("/api/months/{month}/summary", response_model=MonthSummary)
async def get_month_summary(month: str):
    """Get full summary for a month including taxonomy."""
    papers_with_tags = await get_papers_with_tags_for_month(month)
    taxonomy = await get_taxonomy(month)
    
    clusters = build_clusters(papers_with_tags) if papers_with_tags else []
    
    return MonthSummary(
        month=month,
        totalPapers=len(papers_with_tags),
        clusters=clusters,
        taxonomy={
            "contribution_tags": taxonomy.contribution_tags if taxonomy else DEFAULT_CONTRIBUTION_TAGS,
            "task_tags": taxonomy.task_tags if taxonomy else DEFAULT_TASK_TAGS,
            "modality_tags": taxonomy.modality_tags if taxonomy else DEFAULT_MODALITY_TAGS,
            "definitions": taxonomy.definitions if taxonomy else {}
        }
    )


@app.get("/api/clusters/{cluster_id}/papers", response_model=list[PaperCard])
async def get_cluster_papers(
    cluster_id: str,
    month: str = Query(..., description="Month in YYYY-MM format"),
    sort_by: str = Query("upvotes", enum=["upvotes", "date", "confidence"]),
    limit: int = Query(50, le=200),
    offset: int = 0
):
    """Get papers in a specific cluster."""
    papers_with_tags = await get_papers_with_tags_for_month(month)
    
    # Filter by cluster
    filtered = [
        item for item in papers_with_tags
        if item["tags"] and slugify(item["tags"].primary_contribution_tag) == cluster_id
    ]
    
    # Sort
    if sort_by == "upvotes":
        filtered.sort(key=lambda x: -x["paper"].upvotes)
    elif sort_by == "date":
        filtered.sort(key=lambda x: x["paper"].published_date, reverse=True)
    elif sort_by == "confidence":
        filtered.sort(key=lambda x: -(x["tags"].confidence if x["tags"] else 0))
    
    # Pagination
    paginated = filtered[offset:offset + limit]
    
    return [paper_to_card(item["paper"], item["tags"]) for item in paginated]


@app.get("/api/papers/{paper_id}")
async def get_paper_detail(paper_id: str):
    """Get full details for a single paper."""
    paper = await get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    tags = await get_paper_tags(paper_id)
    
    return {
        "paper": {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "publishedDate": paper.published_date,
            "upvotes": paper.upvotes,
            "authors": paper.authors,
            "hfUrl": paper.hf_url,
            "arxivUrl": paper.arxiv_url,
            "pdfUrl": paper.pdf_url
        },
        "tags": {
            "primaryContributionTag": tags.primary_contribution_tag if tags else "OTHER",
            "secondaryContributionTags": tags.secondary_contribution_tags if tags else [],
            "taskTags": tags.task_tags if tags else [],
            "modalityTags": tags.modality_tags if tags else [],
            "researchQuestion": tags.research_question if tags else "",
            "confidence": tags.confidence if tags else 0.0,
            "rationale": tags.rationale if tags else ""
        } if tags else None
    }


@app.get("/api/taxonomy/{month}")
async def get_month_taxonomy(month: str):
    """Get taxonomy for a month."""
    taxonomy = await get_taxonomy(month)
    
    if not taxonomy:
        return {
            "month": month,
            "contribution_tags": DEFAULT_CONTRIBUTION_TAGS,
            "task_tags": DEFAULT_TASK_TAGS,
            "modality_tags": DEFAULT_MODALITY_TAGS,
            "definitions": {},
            "version": 0
        }
    
    return {
        "month": taxonomy.month,
        "contribution_tags": taxonomy.contribution_tags,
        "task_tags": taxonomy.task_tags,
        "modality_tags": taxonomy.modality_tags,
        "definitions": taxonomy.definitions,
        "version": taxonomy.version
    }


# ============= Indexing Endpoints =============

class IndexRequest(BaseModel):
    """Request model for indexing."""
    month: str
    use_llm: bool = False  # If False, uses heuristic tagging
    api_key: Optional[str] = None


class IndexStatus(BaseModel):
    """Status of indexing operation."""
    status: str
    month: str
    papers_scraped: int = 0
    papers_tagged: int = 0
    message: str = ""


# In-memory status tracking (would use Redis/DB in production)
indexing_status = {}


@app.post("/api/reindex/month/{month}", response_model=IndexStatus)
async def reindex_month(month: str, background_tasks: BackgroundTasks, use_llm: bool = False):
    """
    Trigger re-indexing of a month's papers.
    
    This runs in the background. Poll /api/reindex/status/{month} for progress.
    """
    if month in indexing_status and indexing_status[month]["status"] == "running":
        return IndexStatus(
            status="already_running",
            month=month,
            message="Indexing already in progress for this month"
        )
    
    indexing_status[month] = {
        "status": "running",
        "papers_scraped": 0,
        "papers_tagged": 0,
        "message": "Starting..."
    }
    
    background_tasks.add_task(run_indexing, month, use_llm)
    
    return IndexStatus(
        status="started",
        month=month,
        message="Indexing started in background"
    )


async def run_indexing(month: str, use_llm: bool):
    """Background task to run the full indexing pipeline."""
    try:
        # Step 1: Scrape papers
        indexing_status[month]["message"] = "Scraping papers..."
        papers = await scrape_month(month)
        indexing_status[month]["papers_scraped"] = len(papers)
        
        # Save papers to database
        for paper in papers:
            await upsert_paper(paper)
        
        indexing_status[month]["message"] = f"Scraped {len(papers)} papers. Generating taxonomy..."
        
        # Step 2: Generate/get taxonomy
        taxonomy = await get_taxonomy(month)
        if not taxonomy:
            if use_llm:
                taxonomy = await generate_taxonomy(papers, month)
            else:
                taxonomy = Taxonomy(
                    month=month,
                    contribution_tags=DEFAULT_CONTRIBUTION_TAGS,
                    task_tags=DEFAULT_TASK_TAGS,
                    modality_tags=DEFAULT_MODALITY_TAGS,
                    definitions={}
                )
            await save_taxonomy(taxonomy)
        
        indexing_status[month]["message"] = "Tagging papers..."
        
        # Step 3: Tag papers
        for i, paper in enumerate(papers):
            if use_llm:
                tags = await tag_paper(paper, taxonomy)
            else:
                tags = tag_paper_heuristic(paper, taxonomy)
            
            await save_paper_tags(tags)
            indexing_status[month]["papers_tagged"] = i + 1
        
        indexing_status[month]["status"] = "completed"
        indexing_status[month]["message"] = f"Successfully indexed {len(papers)} papers"
        
    except Exception as e:
        indexing_status[month]["status"] = "failed"
        indexing_status[month]["message"] = str(e)


@app.get("/api/reindex/status/{month}", response_model=IndexStatus)
async def get_indexing_status(month: str):
    """Get the status of an indexing operation."""
    if month not in indexing_status:
        return IndexStatus(
            status="not_started",
            month=month,
            message="No indexing has been started for this month"
        )
    
    status = indexing_status[month]
    return IndexStatus(
        status=status["status"],
        month=month,
        papers_scraped=status["papers_scraped"],
        papers_tagged=status["papers_tagged"],
        message=status["message"]
    )


# ============= Available Months =============

@app.get("/api/months")
async def get_available_months():
    """Get list of available months (based on what's indexed)."""
    # In a production system, you'd query the database
    # For now, return a static list of recent months
    import datetime
    
    current = datetime.date.today()
    months = []
    
    for i in range(12):
        year = current.year
        month = current.month - i
        if month <= 0:
            month += 12
            year -= 1
        months.append(f"{year}-{month:02d}")
    
    return {"months": months}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
