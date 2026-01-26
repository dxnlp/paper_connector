"""
Emerging topic detection module.

Detects paradigm shifts and emerging research areas by analyzing:
1. New clusters appearing that weren't present before
2. Rapid growth in paper counts for specific clusters
3. Changes in upvote velocity (topics gaining attention)
4. Keyword pattern emergence across papers
"""

from datetime import date, datetime, timedelta
from typing import Optional
from collections import defaultdict
from pydantic import BaseModel

from database import (
    get_papers_with_tags_by_date_range,
    get_daily_snapshots_range,
    get_upvote_history,
)


class EmergingTopic(BaseModel):
    """An emerging topic detected from the data."""
    name: str
    signal_type: str  # "new_cluster", "rapid_growth", "upvote_surge", "keyword_emergence"
    confidence: float  # 0-1
    evidence: str  # Human-readable explanation
    first_seen: Optional[str] = None
    growth_rate: Optional[float] = None  # Papers per day increase
    related_clusters: list[str] = []
    sample_paper_ids: list[str] = []


class TrendSignal(BaseModel):
    """A trend signal indicating potential paradigm shift."""
    cluster_name: str
    signal_strength: float  # 0-1, higher = stronger signal
    trend_direction: str  # "rising", "falling", "stable"
    weekly_change: float  # Percentage change from previous week
    monthly_change: float  # Percentage change from previous month
    current_count: int
    previous_count: int


class EmergingTopicsReport(BaseModel):
    """Full report of emerging topics and trends."""
    generated_at: str
    analysis_period: str  # e.g., "2025-01-01 to 2025-01-26"
    emerging_topics: list[EmergingTopic]
    trend_signals: list[TrendSignal]
    summary: str


def compute_growth_rate(counts: list[int]) -> float:
    """
    Compute average daily growth rate from a list of counts.
    Returns papers per day increase.
    """
    if len(counts) < 2:
        return 0.0

    # Simple linear regression slope
    n = len(counts)
    x_mean = (n - 1) / 2
    y_mean = sum(counts) / n

    numerator = sum((i - x_mean) * (counts[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0

    return numerator / denominator


def compute_percentage_change(current: int, previous: int) -> float:
    """Compute percentage change between two values."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100


async def detect_new_clusters(
    current_start: str,
    current_end: str,
    comparison_start: str,
    comparison_end: str,
) -> list[EmergingTopic]:
    """
    Detect clusters that are new or have significantly more presence
    compared to a previous period.
    """
    emerging = []

    # Get papers for both periods
    current_papers = await get_papers_with_tags_by_date_range(current_start, current_end)
    comparison_papers = await get_papers_with_tags_by_date_range(comparison_start, comparison_end)

    # Count papers per cluster in each period
    current_clusters = defaultdict(list)
    comparison_clusters = defaultdict(list)

    for item in current_papers:
        tags = item["tags"]
        if tags:
            cluster = tags.primary_contribution_tag
            current_clusters[cluster].append(item["paper"].id)

    for item in comparison_papers:
        tags = item["tags"]
        if tags:
            cluster = tags.primary_contribution_tag
            comparison_clusters[cluster].append(item["paper"].id)

    # Find new or rapidly growing clusters
    for cluster, paper_ids in current_clusters.items():
        current_count = len(paper_ids)
        previous_count = len(comparison_clusters.get(cluster, []))

        # New cluster (not seen before or very small)
        if previous_count <= 2 and current_count >= 5:
            emerging.append(EmergingTopic(
                name=cluster,
                signal_type="new_cluster",
                confidence=min(0.9, 0.5 + (current_count - previous_count) * 0.05),
                evidence=f"Cluster '{cluster}' appeared with {current_count} papers "
                         f"(up from {previous_count} in comparison period)",
                first_seen=current_start,
                growth_rate=None,
                related_clusters=[],
                sample_paper_ids=paper_ids[:5],
            ))

        # Rapid growth (more than 2x increase)
        elif previous_count > 2 and current_count >= previous_count * 2:
            growth_pct = compute_percentage_change(current_count, previous_count)
            emerging.append(EmergingTopic(
                name=cluster,
                signal_type="rapid_growth",
                confidence=min(0.95, 0.6 + growth_pct / 500),
                evidence=f"Cluster '{cluster}' grew {growth_pct:.0f}% "
                         f"({previous_count} -> {current_count} papers)",
                first_seen=None,
                growth_rate=growth_pct,
                related_clusters=[],
                sample_paper_ids=paper_ids[:5],
            ))

    return emerging


async def detect_upvote_surges(
    start_date: str,
    end_date: str,
    min_papers: int = 3,
) -> list[EmergingTopic]:
    """
    Detect clusters where papers are receiving unusually high upvotes,
    indicating community interest surge.
    """
    emerging = []

    papers = await get_papers_with_tags_by_date_range(start_date, end_date)

    # Group by cluster and compute upvote stats
    cluster_upvotes = defaultdict(list)
    cluster_papers = defaultdict(list)

    for item in papers:
        paper = item["paper"]
        tags = item["tags"]
        if tags:
            cluster = tags.primary_contribution_tag
            cluster_upvotes[cluster].append(paper.upvotes)
            cluster_papers[cluster].append(paper.id)

    # Compute overall average upvotes
    all_upvotes = [u for upvotes in cluster_upvotes.values() for u in upvotes]
    if not all_upvotes:
        return emerging

    overall_avg = sum(all_upvotes) / len(all_upvotes)

    # Find clusters with above-average upvotes
    for cluster, upvotes in cluster_upvotes.items():
        if len(upvotes) < min_papers:
            continue

        cluster_avg = sum(upvotes) / len(upvotes)

        # Significant upvote surge (1.5x overall average)
        if cluster_avg > overall_avg * 1.5:
            ratio = cluster_avg / overall_avg
            emerging.append(EmergingTopic(
                name=cluster,
                signal_type="upvote_surge",
                confidence=min(0.9, 0.5 + (ratio - 1) * 0.2),
                evidence=f"Cluster '{cluster}' papers avg {cluster_avg:.0f} upvotes "
                         f"({ratio:.1f}x the overall average of {overall_avg:.0f})",
                first_seen=None,
                growth_rate=None,
                related_clusters=[],
                sample_paper_ids=cluster_papers[cluster][:5],
            ))

    return emerging


async def detect_keyword_emergence(
    current_start: str,
    current_end: str,
    comparison_start: str,
    comparison_end: str,
    min_occurrences: int = 5,
) -> list[EmergingTopic]:
    """
    Detect new keywords/phrases appearing in paper titles/abstracts
    that weren't common before.
    """
    import re

    emerging = []

    # Get papers for both periods
    current_papers = await get_papers_with_tags_by_date_range(current_start, current_end)
    comparison_papers = await get_papers_with_tags_by_date_range(comparison_start, comparison_end)

    # Extract keywords (simple approach: 2-3 word phrases that appear multiple times)
    def extract_keywords(text: str) -> set[str]:
        text = text.lower()
        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()

        keywords = set()
        # Single important words (filter common ones)
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'for', 'on', 'in', 'to',
                    'of', 'and', 'with', 'from', 'by', 'we', 'our', 'this', 'that', 'these',
                    'their', 'can', 'which', 'using', 'based', 'via', 'through', 'into',
                    'its', 'be', 'as', 'at', 'or', 'have', 'has', 'been', 'more', 'new'}

        for word in words:
            if len(word) > 4 and word not in stopwords:
                keywords.add(word)

        # Bigrams
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if words[i] not in stopwords and words[i+1] not in stopwords:
                keywords.add(bigram)

        return keywords

    # Count keywords in both periods
    current_keyword_count = defaultdict(int)
    current_keyword_papers = defaultdict(list)
    comparison_keyword_count = defaultdict(int)

    for item in current_papers:
        paper = item["paper"]
        keywords = extract_keywords(paper.title + " " + paper.abstract[:500])
        for kw in keywords:
            current_keyword_count[kw] += 1
            if paper.id not in current_keyword_papers[kw]:
                current_keyword_papers[kw].append(paper.id)

    for item in comparison_papers:
        paper = item["paper"]
        keywords = extract_keywords(paper.title + " " + paper.abstract[:500])
        for kw in keywords:
            comparison_keyword_count[kw] += 1

    # Find emerging keywords
    for keyword, current_count in current_keyword_count.items():
        if current_count < min_occurrences:
            continue

        previous_count = comparison_keyword_count.get(keyword, 0)

        # New keyword (not seen before or very rare)
        if previous_count <= 1 and current_count >= min_occurrences:
            emerging.append(EmergingTopic(
                name=f"Keyword: {keyword}",
                signal_type="keyword_emergence",
                confidence=min(0.85, 0.4 + current_count * 0.05),
                evidence=f"New keyword '{keyword}' appeared in {current_count} papers "
                         f"(was in {previous_count} papers before)",
                first_seen=current_start,
                growth_rate=None,
                related_clusters=[],
                sample_paper_ids=current_keyword_papers[keyword][:3],
            ))

    # Limit to top emerging keywords
    emerging.sort(key=lambda x: -x.confidence)
    return emerging[:10]


async def compute_trend_signals(
    end_date: str,
    lookback_days: int = 30,
) -> list[TrendSignal]:
    """
    Compute trend signals for all clusters based on recent data.
    """
    signals = []

    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Current week
    current_week_start = (end - timedelta(days=6)).strftime("%Y-%m-%d")
    current_week_end = end.strftime("%Y-%m-%d")

    # Previous week
    prev_week_start = (end - timedelta(days=13)).strftime("%Y-%m-%d")
    prev_week_end = (end - timedelta(days=7)).strftime("%Y-%m-%d")

    # Current month (last 30 days)
    current_month_start = (end - timedelta(days=29)).strftime("%Y-%m-%d")

    # Previous month (30-60 days ago)
    prev_month_start = (end - timedelta(days=59)).strftime("%Y-%m-%d")
    prev_month_end = (end - timedelta(days=30)).strftime("%Y-%m-%d")

    # Get papers for each period
    current_week = await get_papers_with_tags_by_date_range(current_week_start, current_week_end)
    prev_week = await get_papers_with_tags_by_date_range(prev_week_start, prev_week_end)
    current_month = await get_papers_with_tags_by_date_range(current_month_start, current_week_end)
    prev_month = await get_papers_with_tags_by_date_range(prev_month_start, prev_month_end)

    # Count per cluster
    def count_by_cluster(papers):
        counts = defaultdict(int)
        for item in papers:
            if item["tags"]:
                counts[item["tags"].primary_contribution_tag] += 1
        return counts

    current_week_counts = count_by_cluster(current_week)
    prev_week_counts = count_by_cluster(prev_week)
    current_month_counts = count_by_cluster(current_month)
    prev_month_counts = count_by_cluster(prev_month)

    # Compute signals for each cluster
    all_clusters = set(current_week_counts.keys()) | set(prev_week_counts.keys()) | \
                   set(current_month_counts.keys()) | set(prev_month_counts.keys())

    for cluster in all_clusters:
        current = current_week_counts.get(cluster, 0)
        previous = prev_week_counts.get(cluster, 0)
        monthly_current = current_month_counts.get(cluster, 0)
        monthly_previous = prev_month_counts.get(cluster, 0)

        weekly_change = compute_percentage_change(current, previous)
        monthly_change = compute_percentage_change(monthly_current, monthly_previous)

        # Determine trend direction
        if weekly_change > 20:
            direction = "rising"
        elif weekly_change < -20:
            direction = "falling"
        else:
            direction = "stable"

        # Signal strength based on magnitude of change
        signal_strength = min(1.0, abs(weekly_change) / 100)

        signals.append(TrendSignal(
            cluster_name=cluster,
            signal_strength=signal_strength,
            trend_direction=direction,
            weekly_change=weekly_change,
            monthly_change=monthly_change,
            current_count=current,
            previous_count=previous,
        ))

    # Sort by signal strength
    signals.sort(key=lambda x: -x.signal_strength)

    return signals


async def generate_emerging_topics_report(
    end_date: Optional[str] = None,
    lookback_days: int = 14,
    comparison_lookback_days: int = 30,
) -> EmergingTopicsReport:
    """
    Generate a comprehensive emerging topics report.

    Args:
        end_date: Analysis end date (defaults to today)
        lookback_days: Days to analyze for current period
        comparison_lookback_days: Days for comparison period

    Returns:
        EmergingTopicsReport with detected topics and trends
    """
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Current analysis period
    current_start = (end - timedelta(days=lookback_days - 1)).strftime("%Y-%m-%d")
    current_end = end_date

    # Comparison period (before current)
    comparison_end = (end - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    comparison_start = (end - timedelta(days=lookback_days + comparison_lookback_days - 1)).strftime("%Y-%m-%d")

    # Run all detection methods
    new_clusters = await detect_new_clusters(
        current_start, current_end,
        comparison_start, comparison_end
    )

    upvote_surges = await detect_upvote_surges(current_start, current_end)

    keyword_emergence = await detect_keyword_emergence(
        current_start, current_end,
        comparison_start, comparison_end
    )

    trend_signals = await compute_trend_signals(end_date)

    # Combine all emerging topics
    all_emerging = new_clusters + upvote_surges + keyword_emergence

    # Sort by confidence
    all_emerging.sort(key=lambda x: -x.confidence)

    # Generate summary
    rising_count = sum(1 for s in trend_signals if s.trend_direction == "rising")
    falling_count = sum(1 for s in trend_signals if s.trend_direction == "falling")

    if all_emerging:
        top_topic = all_emerging[0]
        summary = f"Detected {len(all_emerging)} emerging signals. "
        summary += f"Top signal: {top_topic.name} ({top_topic.signal_type}). "
    else:
        summary = "No significant emerging topics detected. "

    summary += f"Trend analysis: {rising_count} rising, {falling_count} falling clusters."

    return EmergingTopicsReport(
        generated_at=datetime.now().isoformat(),
        analysis_period=f"{current_start} to {current_end}",
        emerging_topics=all_emerging[:20],  # Limit to top 20
        trend_signals=trend_signals[:15],  # Limit to top 15
        summary=summary,
    )
