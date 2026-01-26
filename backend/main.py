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
    get_papers_by_date, get_papers_by_date_range,
    get_upvote_history,
    Paper, Taxonomy, PaperTags
)
from scraper import scrape_month, scrape_daily, scrape_date_range, fetch_month_paper_ids, fetch_paper_details
from aggregation import (
    compute_daily_stats, compute_weekly_stats, compute_flow_data,
    compute_trend_data, save_daily_snapshot_for_date,
    DailyStats, WeeklyStats, FlowData, TrendData
)
from scheduler import get_scheduler, PaperScheduler
from llm_tagger import (
    generate_taxonomy, tag_paper, tag_all_papers, tag_paper_heuristic,
    DEFAULT_CONTRIBUTION_TAGS, DEFAULT_TASK_TAGS, DEFAULT_MODALITY_TAGS
)
from llm import list_available_providers, get_config, LLMError, ProviderName
from taxonomy import get_taxonomy_with_colors, get_category_color
from emerging import (
    generate_emerging_topics_report,
    detect_new_clusters,
    detect_upvote_surges,
    compute_trend_signals,
    EmergingTopicsReport,
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
async def reindex_month(
    month: str,
    background_tasks: BackgroundTasks,
    use_llm: bool = False,
    provider: Optional[str] = Query(
        None,
        description="LLM provider to use (minimax, openai, anthropic). Uses default if not specified."
    )
):
    """
    Trigger re-indexing of a month's papers.

    This runs in the background. Poll /api/reindex/status/{month} for progress.

    - **use_llm**: If True, uses LLM for taxonomy generation and tagging. Otherwise uses heuristics.
    - **provider**: LLM provider to use (minimax, openai, anthropic). Only used if use_llm=True.
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

    background_tasks.add_task(run_indexing, month, use_llm, provider)

    return IndexStatus(
        status="started",
        month=month,
        message=f"Indexing started in background" + (f" with {provider} provider" if provider else "")
    )


async def run_indexing(month: str, use_llm: bool, provider: Optional[str] = None):
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
                taxonomy = await generate_taxonomy(papers, month, provider=provider)
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
                tags = await tag_paper(paper, taxonomy, provider=provider)
            else:
                tags = tag_paper_heuristic(paper, taxonomy)

            await save_paper_tags(tags)
            indexing_status[month]["papers_tagged"] = i + 1

        indexing_status[month]["status"] = "completed"
        indexing_status[month]["message"] = f"Successfully indexed {len(papers)} papers"

    except LLMError as e:
        indexing_status[month]["status"] = "failed"
        indexing_status[month]["message"] = f"LLM Error: {e}"
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


# ============= LLM Provider Endpoints =============

@app.get("/api/llm/providers")
async def get_llm_providers():
    """
    Get list of available LLM providers.

    Returns the list of configured providers and the default provider.
    A provider is available if its API key is configured in the environment.
    """
    config = get_config()
    available = list_available_providers()

    return {
        "available": available,
        "default": config.default_provider,
        "providers": {
            "minimax": {
                "name": "MiniMax",
                "available": "minimax" in available,
                "model": config.minimax_model
            },
            "openai": {
                "name": "OpenAI",
                "available": "openai" in available,
                "model": config.openai_model
            },
            "anthropic": {
                "name": "Anthropic Claude",
                "available": "anthropic" in available,
                "model": config.anthropic_model
            }
        }
    }


# ============= Taxonomy Endpoints =============

@app.get("/api/taxonomy/curated")
async def get_curated_taxonomy():
    """
    Get the curated taxonomy with stable colors.

    Returns contribution types, task areas, and modalities with their
    assigned colors for consistent visualization.
    """
    return get_taxonomy_with_colors()


@app.get("/api/taxonomy/color/{category_name}")
async def get_taxonomy_color(category_name: str, taxonomy_type: str = "contribution"):
    """
    Get the color for a specific category.

    Args:
        category_name: The category name to look up
        taxonomy_type: One of 'contribution', 'task', or 'modality'
    """
    color = get_category_color(category_name, taxonomy_type)
    return {"category": category_name, "color": color}


# ============= Temporal / Daily Endpoints =============

@app.get("/api/daily/{date}")
async def get_daily_papers(
    date: str,
    cluster: Optional[str] = None,
    sort_by: str = Query("upvotes", enum=["upvotes", "date", "confidence"]),
    limit: int = Query(100, le=500)
):
    """
    Get papers for a specific date with optional filtering.

    Args:
        date: Date in YYYY-MM-DD format
        cluster: Optional cluster filter
        sort_by: Sort order
        limit: Maximum papers to return
    """
    papers = await get_papers_by_date(date)

    # TODO: Add filtering and join with tags
    return {
        "date": date,
        "total_papers": len(papers),
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "upvotes": p.upvotes,
                "appeared_date": p.appeared_date
            }
            for p in papers[:limit]
        ]
    }


@app.get("/api/daily/{date}/stats")
async def get_daily_statistics(date: str):
    """
    Get aggregated statistics for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
    """
    stats = await compute_daily_stats(date)
    return stats


@app.get("/api/weekly/{week_start}/stats")
async def get_weekly_statistics(week_start: str):
    """
    Get aggregated statistics for a week.

    Args:
        week_start: Start date (Monday) in YYYY-MM-DD format
    """
    stats = await compute_weekly_stats(week_start)
    return stats


@app.get("/api/flow")
async def get_flow_visualization(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD")
):
    """
    Get flow visualization data showing cluster evolution over time.

    Returns daily cluster counts for creating stream/flow charts.
    """
    flow_data = await compute_flow_data(start_date, end_date)
    return flow_data


@app.get("/api/trends/{cluster_name}")
async def get_cluster_trend(
    cluster_name: str,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD")
):
    """
    Get trend data for a specific cluster over time.
    """
    trend = await compute_trend_data(cluster_name, start_date, end_date)
    return trend


@app.get("/api/papers/{paper_id}/upvote-history")
async def get_paper_upvote_history(paper_id: str):
    """
    Get upvote history for a paper over time.

    Useful for identifying papers with growing influence.
    """
    history = await get_upvote_history(paper_id)
    return {
        "paper_id": paper_id,
        "history": [{"date": h.date, "upvotes": h.upvotes} for h in history]
    }


@app.post("/api/reindex/daily/{date}")
async def reindex_daily(
    date: str,
    background_tasks: BackgroundTasks,
    use_llm: bool = False,
    provider: Optional[str] = None
):
    """
    Index papers for a specific date from HF Daily Papers.

    Args:
        date: Date in YYYY-MM-DD format
        use_llm: Whether to use LLM for tagging
        provider: LLM provider to use
    """
    task_key = f"daily_{date}"

    if task_key in indexing_status and indexing_status[task_key]["status"] == "running":
        return IndexStatus(
            status="already_running",
            month=date,
            message="Indexing already in progress for this date"
        )

    indexing_status[task_key] = {
        "status": "running",
        "papers_scraped": 0,
        "papers_tagged": 0,
        "message": "Starting..."
    }

    background_tasks.add_task(run_daily_indexing, date, use_llm, provider)

    return IndexStatus(
        status="started",
        month=date,
        message=f"Daily indexing started for {date}"
    )


async def run_daily_indexing(date: str, use_llm: bool, provider: Optional[str] = None):
    """Background task to index a single day's papers."""
    task_key = f"daily_{date}"

    try:
        # Step 1: Scrape papers for the date
        indexing_status[task_key]["message"] = f"Scraping papers for {date}..."
        papers = await scrape_daily(date)
        indexing_status[task_key]["papers_scraped"] = len(papers)

        # Save papers
        for paper in papers:
            await upsert_paper(paper)

        indexing_status[task_key]["message"] = f"Scraped {len(papers)} papers. Tagging..."

        # Step 2: Get or create taxonomy (use month-based for now)
        month = date[:7]  # YYYY-MM
        taxonomy = await get_taxonomy(month)
        if not taxonomy:
            if use_llm:
                from llm_tagger import generate_taxonomy
                taxonomy = await generate_taxonomy(papers, month, provider=provider)
            else:
                taxonomy = Taxonomy(
                    month=month,
                    contribution_tags=DEFAULT_CONTRIBUTION_TAGS,
                    task_tags=DEFAULT_TASK_TAGS,
                    modality_tags=DEFAULT_MODALITY_TAGS,
                    definitions={}
                )
            await save_taxonomy(taxonomy)

        # Step 3: Tag papers
        from llm_tagger import tag_paper, tag_paper_heuristic
        for i, paper in enumerate(papers):
            if use_llm:
                tags = await tag_paper(paper, taxonomy, provider=provider)
            else:
                tags = tag_paper_heuristic(paper, taxonomy)

            await save_paper_tags(tags)
            indexing_status[task_key]["papers_tagged"] = i + 1

        # Step 4: Save daily snapshot
        await save_daily_snapshot_for_date(date)

        indexing_status[task_key]["status"] = "completed"
        indexing_status[task_key]["message"] = f"Successfully indexed {len(papers)} papers for {date}"

    except Exception as e:
        indexing_status[task_key]["status"] = "failed"
        indexing_status[task_key]["message"] = str(e)


# ============= Scheduler Endpoints =============

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get the current status of the paper scraping scheduler."""
    scheduler = get_scheduler()
    return scheduler.get_status()


@app.post("/api/scheduler/start")
async def start_scheduler(
    run_now: bool = False,
    backfill: bool = True
):
    """
    Start the paper scraping scheduler.

    Args:
        run_now: If True, run an immediate scrape for today
        backfill: If True, backfill missed days on startup
    """
    scheduler = get_scheduler()

    if scheduler.is_running:
        return {"status": "already_running", "message": "Scheduler is already running"}

    scheduler.start(run_now=run_now, backfill=backfill)

    return {
        "status": "started",
        "message": "Scheduler started successfully",
        "config": scheduler.get_status()["config"]
    }


@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Stop the paper scraping scheduler."""
    scheduler = get_scheduler()

    if not scheduler.is_running:
        return {"status": "not_running", "message": "Scheduler is not running"}

    scheduler.stop()

    return {"status": "stopped", "message": "Scheduler stopped successfully"}


@app.post("/api/scheduler/backfill")
async def trigger_backfill(days: int = Query(7, ge=1, le=30)):
    """
    Trigger a backfill of missed days.

    Args:
        days: Number of days to look back (1-30)
    """
    scheduler = get_scheduler()
    results = await scheduler.backfill_missed_days(days)

    return {
        "status": "completed",
        "days_checked": days,
        "days_backfilled": len(results),
        "results": results
    }


# ============= Emerging Topics Endpoints =============

@app.get("/api/emerging/report")
async def get_emerging_topics_report(
    end_date: Optional[str] = Query(None, description="Analysis end date (defaults to today)"),
    lookback_days: int = Query(14, ge=7, le=30, description="Days to analyze"),
    comparison_days: int = Query(30, ge=14, le=60, description="Days for comparison period")
):
    """
    Generate a comprehensive emerging topics report.

    Analyzes recent papers to detect:
    - New research clusters appearing
    - Rapid growth in existing areas
    - Upvote surges indicating community interest
    - Emerging keywords and phrases

    Args:
        end_date: End date for analysis (YYYY-MM-DD, defaults to today)
        lookback_days: Number of days to analyze (current period)
        comparison_days: Number of days for comparison (previous period)
    """
    report = await generate_emerging_topics_report(
        end_date=end_date,
        lookback_days=lookback_days,
        comparison_lookback_days=comparison_days
    )
    return report


@app.get("/api/emerging/trends")
async def get_emerging_trends(
    end_date: Optional[str] = Query(None, description="Analysis end date"),
    limit: int = Query(15, ge=5, le=30)
):
    """
    Get trend signals for all clusters.

    Returns clusters sorted by signal strength (rising/falling trends).
    """
    from datetime import date as date_type
    if not end_date:
        end_date = date_type.today().strftime("%Y-%m-%d")

    signals = await compute_trend_signals(end_date)
    return {
        "end_date": end_date,
        "trends": signals[:limit]
    }


@app.get("/api/emerging/rising")
async def get_rising_topics(
    end_date: Optional[str] = Query(None, description="Analysis end date"),
    min_growth: float = Query(20.0, description="Minimum weekly growth percentage")
):
    """
    Get topics that are rising in popularity.

    Filters trend signals to show only clusters with positive growth
    above the specified threshold.
    """
    from datetime import date as date_type
    if not end_date:
        end_date = date_type.today().strftime("%Y-%m-%d")

    signals = await compute_trend_signals(end_date)

    rising = [
        s for s in signals
        if s.trend_direction == "rising" and s.weekly_change >= min_growth
    ]

    return {
        "end_date": end_date,
        "min_growth": min_growth,
        "rising_topics": rising
    }


@app.get("/api/emerging/hot")
async def get_hot_topics(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    min_papers: int = Query(3, ge=1)
):
    """
    Get hot topics based on upvote activity.

    Returns clusters where papers are receiving above-average attention.
    """
    surges = await detect_upvote_surges(start_date, end_date, min_papers=min_papers)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "hot_topics": surges
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
