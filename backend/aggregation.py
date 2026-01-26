"""
Aggregation engine for computing daily, weekly, and monthly statistics.
Supports trend detection and flow visualization data.
"""

from datetime import date, datetime, timedelta
from typing import Optional
from collections import defaultdict
from pydantic import BaseModel

from database import (
    Paper, PaperTags, DailySnapshot,
    get_papers_by_date_range,
    get_papers_with_tags_by_date_range,
    get_daily_snapshot,
    get_daily_snapshots_range,
    save_daily_snapshot,
    record_upvote_snapshot,
)
from taxonomy import get_category_color


class ClusterStats(BaseModel):
    """Statistics for a single cluster."""
    name: str
    color: str
    paper_count: int
    paper_ids: list[str]
    top_papers: list[str]  # Top 5 by upvotes
    avg_upvotes: float
    total_upvotes: int


class DailyStats(BaseModel):
    """Aggregated statistics for a single day."""
    date: str
    total_papers: int
    new_papers: int
    clusters: list[ClusterStats]
    top_papers: list[str]
    total_upvotes: int


class WeeklyStats(BaseModel):
    """Aggregated statistics for a week."""
    week_start: str
    week_end: str
    total_papers: int
    new_papers: int
    clusters: list[ClusterStats]
    daily_counts: dict[str, int]  # date -> paper count
    growing_clusters: list[str]
    declining_clusters: list[str]


class TrendData(BaseModel):
    """Trend data for a cluster over time."""
    cluster_name: str
    color: str
    data_points: list[dict]  # [{date, count, cumulative}]


class FlowData(BaseModel):
    """Data for flow visualization."""
    start_date: str
    end_date: str
    clusters: list[str]
    colors: dict[str, str]
    daily_data: list[dict]  # [{date, cluster_counts: {name: count}}]


def get_week_bounds(d: date) -> tuple[date, date]:
    """Get Monday and Sunday of the week containing date d."""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_month_bounds(d: date) -> tuple[date, date]:
    """Get first and last day of the month containing date d."""
    first = d.replace(day=1)
    # Last day: go to next month, subtract 1 day
    if d.month == 12:
        last = d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last = d.replace(month=d.month + 1, day=1) - timedelta(days=1)
    return first, last


async def compute_daily_stats(date_str: str) -> DailyStats:
    """
    Compute statistics for a single day.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        DailyStats for the day
    """
    papers_with_tags = await get_papers_with_tags_by_date_range(date_str, date_str)

    # Group by cluster
    clusters_data = defaultdict(lambda: {
        "paper_ids": [],
        "upvotes": [],
    })

    for item in papers_with_tags:
        paper = item["paper"]
        tags = item["tags"]
        cluster_name = tags.primary_contribution_tag if tags else "Uncategorized"

        clusters_data[cluster_name]["paper_ids"].append(paper.id)
        clusters_data[cluster_name]["upvotes"].append(paper.upvotes)

    # Build cluster stats
    clusters = []
    for name, data in clusters_data.items():
        paper_ids = data["paper_ids"]
        upvotes = data["upvotes"]

        # Sort by upvotes for top papers
        sorted_papers = sorted(zip(paper_ids, upvotes), key=lambda x: -x[1])
        top_papers = [p[0] for p in sorted_papers[:5]]

        clusters.append(ClusterStats(
            name=name,
            color=get_category_color(name, "contribution"),
            paper_count=len(paper_ids),
            paper_ids=paper_ids,
            top_papers=top_papers,
            avg_upvotes=sum(upvotes) / len(upvotes) if upvotes else 0,
            total_upvotes=sum(upvotes)
        ))

    # Sort clusters by paper count
    clusters.sort(key=lambda c: -c.paper_count)

    # Overall top papers
    all_papers = [(item["paper"].id, item["paper"].upvotes) for item in papers_with_tags]
    all_papers.sort(key=lambda x: -x[1])
    top_papers = [p[0] for p in all_papers[:10]]

    return DailyStats(
        date=date_str,
        total_papers=len(papers_with_tags),
        new_papers=len(papers_with_tags),  # All papers on this day are "new" for that day
        clusters=clusters,
        top_papers=top_papers,
        total_upvotes=sum(p[1] for p in all_papers)
    )


async def compute_weekly_stats(week_start: str) -> WeeklyStats:
    """
    Compute statistics for a week starting on the given date.

    Args:
        week_start: Start date (Monday) in YYYY-MM-DD format

    Returns:
        WeeklyStats for the week
    """
    start = datetime.strptime(week_start, "%Y-%m-%d").date()
    monday, sunday = get_week_bounds(start)

    start_str = monday.strftime("%Y-%m-%d")
    end_str = sunday.strftime("%Y-%m-%d")

    papers_with_tags = await get_papers_with_tags_by_date_range(start_str, end_str)

    # Group by cluster and track daily counts
    clusters_data = defaultdict(lambda: {"paper_ids": [], "upvotes": []})
    daily_counts = defaultdict(int)

    for item in papers_with_tags:
        paper = item["paper"]
        tags = item["tags"]
        cluster_name = tags.primary_contribution_tag if tags else "Uncategorized"

        clusters_data[cluster_name]["paper_ids"].append(paper.id)
        clusters_data[cluster_name]["upvotes"].append(paper.upvotes)

        if paper.appeared_date:
            daily_counts[paper.appeared_date] += 1

    # Build cluster stats
    clusters = []
    for name, data in clusters_data.items():
        paper_ids = data["paper_ids"]
        upvotes = data["upvotes"]

        sorted_papers = sorted(zip(paper_ids, upvotes), key=lambda x: -x[1])
        top_papers = [p[0] for p in sorted_papers[:5]]

        clusters.append(ClusterStats(
            name=name,
            color=get_category_color(name, "contribution"),
            paper_count=len(paper_ids),
            paper_ids=paper_ids,
            top_papers=top_papers,
            avg_upvotes=sum(upvotes) / len(upvotes) if upvotes else 0,
            total_upvotes=sum(upvotes)
        ))

    clusters.sort(key=lambda c: -c.paper_count)

    # TODO: Compare with previous week for growing/declining detection
    growing = []
    declining = []

    return WeeklyStats(
        week_start=start_str,
        week_end=end_str,
        total_papers=len(papers_with_tags),
        new_papers=len(papers_with_tags),
        clusters=clusters,
        daily_counts=dict(daily_counts),
        growing_clusters=growing,
        declining_clusters=declining
    )


async def compute_flow_data(start_date: str, end_date: str) -> FlowData:
    """
    Compute data for flow visualization showing cluster evolution over time.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        FlowData with daily cluster counts
    """
    papers_with_tags = await get_papers_with_tags_by_date_range(start_date, end_date)

    # Group papers by date and cluster
    date_cluster_counts = defaultdict(lambda: defaultdict(int))
    all_clusters = set()
    colors = {}

    for item in papers_with_tags:
        paper = item["paper"]
        tags = item["tags"]

        if not paper.appeared_date:
            continue

        cluster_name = tags.primary_contribution_tag if tags else "Uncategorized"
        date_cluster_counts[paper.appeared_date][cluster_name] += 1
        all_clusters.add(cluster_name)

        if cluster_name not in colors:
            colors[cluster_name] = get_category_color(cluster_name, "contribution")

    # Build daily data sorted by date
    dates = sorted(date_cluster_counts.keys())
    daily_data = []

    for d in dates:
        counts = dict(date_cluster_counts[d])
        # Fill in zeros for missing clusters
        for cluster in all_clusters:
            if cluster not in counts:
                counts[cluster] = 0
        daily_data.append({
            "date": d,
            "cluster_counts": counts
        })

    return FlowData(
        start_date=start_date,
        end_date=end_date,
        clusters=sorted(list(all_clusters)),
        colors=colors,
        daily_data=daily_data
    )


async def compute_trend_data(
    cluster_name: str,
    start_date: str,
    end_date: str
) -> TrendData:
    """
    Compute trend data for a specific cluster over time.

    Args:
        cluster_name: Name of the cluster to track
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        TrendData with daily counts and cumulative totals
    """
    papers_with_tags = await get_papers_with_tags_by_date_range(start_date, end_date)

    # Filter to cluster and group by date
    daily_counts = defaultdict(int)

    for item in papers_with_tags:
        paper = item["paper"]
        tags = item["tags"]

        if not paper.appeared_date:
            continue

        paper_cluster = tags.primary_contribution_tag if tags else "Uncategorized"
        if paper_cluster == cluster_name:
            daily_counts[paper.appeared_date] += 1

    # Build data points
    dates = sorted(daily_counts.keys())
    data_points = []
    cumulative = 0

    for d in dates:
        count = daily_counts[d]
        cumulative += count
        data_points.append({
            "date": d,
            "count": count,
            "cumulative": cumulative
        })

    return TrendData(
        cluster_name=cluster_name,
        color=get_category_color(cluster_name, "contribution"),
        data_points=data_points
    )


async def save_daily_snapshot_for_date(date_str: str) -> DailySnapshot:
    """
    Compute and save a daily snapshot for a specific date.
    Also records upvote snapshots for all papers.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        The saved DailySnapshot
    """
    stats = await compute_daily_stats(date_str)

    # Build cluster counts dict
    cluster_counts = {c.name: c.paper_count for c in stats.clusters}

    # Create snapshot
    snapshot = DailySnapshot(
        date=date_str,
        total_papers=stats.total_papers,
        cluster_counts=cluster_counts,
        top_paper_ids=stats.top_papers,
        new_paper_ids=[p for c in stats.clusters for p in c.paper_ids]
    )

    await save_daily_snapshot(snapshot)

    # Record upvote snapshots for trending analysis
    papers_with_tags = await get_papers_with_tags_by_date_range(date_str, date_str)
    for item in papers_with_tags:
        paper = item["paper"]
        await record_upvote_snapshot(paper.id, date_str, paper.upvotes)

    return snapshot
