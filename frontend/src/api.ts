// API types matching backend response models

export interface PaperCard {
  paperId: string;
  title: string;
  abstractSnippet: string;
  publishedDate: string;
  upvotes: number;
  authorsShort: string[];
  primaryTag: string;
  secondaryTags: string[];
  taskTags: string[];
  modality: string[];
  hfUrl: string;
  pdfUrl: string;
  arxivUrl: string;
  researchQuestion: string;
  confidence: number;
  rationale: string;
}

export interface ClusterInfo {
  clusterId: string;
  name: string;
  paperCount: number;
  topTaskTags: string[];
  topModalities: string[];
}

export interface MonthSummary {
  month: string;
  totalPapers: number;
  clusters: ClusterInfo[];
  taxonomy: {
    contribution_tags: string[];
    task_tags: string[];
    modality_tags: string[];
    definitions: Record<string, string>;
  } | null;
}

export interface PaperDetail {
  paper: {
    id: string;
    title: string;
    abstract: string;
    publishedDate: string;
    upvotes: number;
    authors: string[];
    hfUrl: string;
    arxivUrl: string;
    pdfUrl: string;
  };
  tags: {
    primaryContributionTag: string;
    secondaryContributionTags: string[];
    taskTags: string[];
    modalityTags: string[];
    researchQuestion: string;
    confidence: number;
    rationale: string;
  } | null;
}

export interface IndexStatus {
  status: string;
  month: string;
  papers_scraped: number;
  papers_tagged: number;
  message: string;
}

export interface ClusterNode {
  id: string;
  name: string;
  paperCount: number;
  topTaskTags: string[];
  topModalities: string[];
  paperIds: string[];
}

export interface ClusterLink {
  source: string;
  target: string;
  sharedCount: number;
  sharedPaperIds: string[];
}

export interface ClusterGraphData {
  nodes: ClusterNode[];
  links: ClusterLink[];
}

// Flow visualization types
export interface FlowData {
  start_date: string;
  end_date: string;
  clusters: string[];
  colors: Record<string, string>;
  daily_data: Array<{
    date: string;
    cluster_counts: Record<string, number>;
  }>;
}

export interface TrendData {
  cluster_name: string;
  color: string;
  data_points: Array<{
    date: string;
    count: number;
    cumulative: number;
  }>;
}

export interface DailyStats {
  date: string;
  total_papers: number;
  new_papers: number;
  clusters: Array<{
    name: string;
    color: string;
    paper_count: number;
    top_papers: string[];
    avg_upvotes: number;
    total_upvotes: number;
  }>;
  top_papers: string[];
  total_upvotes: number;
}

// API base URL - adjust for production
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API functions
export async function fetchMonthSummary(month: string): Promise<MonthSummary> {
  const res = await fetch(`${API_BASE}/api/months/${month}/summary`);
  if (!res.ok) throw new Error('Failed to fetch month summary');
  return res.json();
}

export async function fetchMonthPapers(
  month: string,
  options?: {
    cluster?: string;
    task?: string;
    modality?: string;
    search?: string;
    sortBy?: 'upvotes' | 'date' | 'confidence';
    limit?: number;
    offset?: number;
  }
): Promise<PaperCard[]> {
  const params = new URLSearchParams();
  if (options?.cluster) params.set('cluster', options.cluster);
  if (options?.task) params.set('task', options.task);
  if (options?.modality) params.set('modality', options.modality);
  if (options?.search) params.set('search', options.search);
  if (options?.sortBy) params.set('sort_by', options.sortBy);
  if (options?.limit) params.set('limit', options.limit.toString());
  if (options?.offset) params.set('offset', options.offset.toString());

  const url = `${API_BASE}/api/months/${month}/papers?${params}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch papers');
  return res.json();
}

export async function fetchClusters(month: string): Promise<ClusterInfo[]> {
  const res = await fetch(`${API_BASE}/api/months/${month}/clusters`);
  if (!res.ok) throw new Error('Failed to fetch clusters');
  return res.json();
}

export async function fetchClusterGraph(month: string): Promise<ClusterGraphData> {
  const res = await fetch(`${API_BASE}/api/months/${month}/cluster-graph`);
  if (!res.ok) throw new Error('Failed to fetch cluster graph');
  return res.json();
}

export async function fetchClusterPapers(
  clusterId: string,
  month: string,
  sortBy: 'upvotes' | 'date' | 'confidence' = 'upvotes'
): Promise<PaperCard[]> {
  const res = await fetch(
    `${API_BASE}/api/clusters/${clusterId}/papers?month=${month}&sort_by=${sortBy}`
  );
  if (!res.ok) throw new Error('Failed to fetch cluster papers');
  return res.json();
}

export async function fetchPaperDetail(paperId: string): Promise<PaperDetail> {
  const res = await fetch(`${API_BASE}/api/papers/${paperId}`);
  if (!res.ok) throw new Error('Failed to fetch paper detail');
  return res.json();
}

export async function fetchAvailableMonths(): Promise<{ months: string[] }> {
  const res = await fetch(`${API_BASE}/api/months`);
  if (!res.ok) throw new Error('Failed to fetch months');
  return res.json();
}

export async function triggerReindex(month: string, useLlm: boolean = false): Promise<IndexStatus> {
  const res = await fetch(`${API_BASE}/api/reindex/month/${month}?use_llm=${useLlm}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to trigger reindex');
  return res.json();
}

export async function fetchIndexStatus(month: string): Promise<IndexStatus> {
  const res = await fetch(`${API_BASE}/api/reindex/status/${month}`);
  if (!res.ok) throw new Error('Failed to fetch index status');
  return res.json();
}

// Flow visualization API functions
export async function fetchFlowData(startDate: string, endDate: string): Promise<FlowData> {
  const res = await fetch(`${API_BASE}/api/flow?start_date=${startDate}&end_date=${endDate}`);
  if (!res.ok) throw new Error('Failed to fetch flow data');
  return res.json();
}

export async function fetchDailyStats(date: string): Promise<DailyStats> {
  const res = await fetch(`${API_BASE}/api/daily/${date}/stats`);
  if (!res.ok) throw new Error('Failed to fetch daily stats');
  return res.json();
}

export async function fetchTrendData(clusterName: string, startDate: string, endDate: string): Promise<TrendData> {
  const res = await fetch(`${API_BASE}/api/trends/${encodeURIComponent(clusterName)}?start_date=${startDate}&end_date=${endDate}`);
  if (!res.ok) throw new Error('Failed to fetch trend data');
  return res.json();
}

export async function fetchCuratedTaxonomy(): Promise<{
  contribution: Array<{ id: string; name: string; color: string; description: string }>;
  task: Array<{ id: string; name: string; color: string; description: string }>;
  modality: Array<{ id: string; name: string; color: string; description: string }>;
}> {
  const res = await fetch(`${API_BASE}/api/taxonomy/curated`);
  if (!res.ok) throw new Error('Failed to fetch curated taxonomy');
  return res.json();
}

// Emerging topics types
export interface EmergingTopic {
  name: string;
  signal_type: 'new_cluster' | 'rapid_growth' | 'upvote_surge' | 'keyword_emergence';
  confidence: number;
  evidence: string;
  first_seen: string | null;
  growth_rate: number | null;
  related_clusters: string[];
  sample_paper_ids: string[];
}

export interface TrendSignal {
  cluster_name: string;
  signal_strength: number;
  trend_direction: 'rising' | 'falling' | 'stable';
  weekly_change: number;
  monthly_change: number;
  current_count: number;
  previous_count: number;
}

export interface EmergingTopicsReport {
  generated_at: string;
  analysis_period: string;
  emerging_topics: EmergingTopic[];
  trend_signals: TrendSignal[];
  summary: string;
}

// Emerging topics API functions
export async function fetchEmergingReport(
  endDate?: string,
  lookbackDays: number = 14,
  comparisonDays: number = 30
): Promise<EmergingTopicsReport> {
  const params = new URLSearchParams();
  if (endDate) params.set('end_date', endDate);
  params.set('lookback_days', lookbackDays.toString());
  params.set('comparison_days', comparisonDays.toString());

  const res = await fetch(`${API_BASE}/api/emerging/report?${params}`);
  if (!res.ok) throw new Error('Failed to fetch emerging report');
  return res.json();
}

export async function fetchEmergingTrends(
  endDate?: string,
  limit: number = 15
): Promise<{ end_date: string; trends: TrendSignal[] }> {
  const params = new URLSearchParams();
  if (endDate) params.set('end_date', endDate);
  params.set('limit', limit.toString());

  const res = await fetch(`${API_BASE}/api/emerging/trends?${params}`);
  if (!res.ok) throw new Error('Failed to fetch emerging trends');
  return res.json();
}

export async function fetchRisingTopics(
  endDate?: string,
  minGrowth: number = 20
): Promise<{ end_date: string; rising_topics: TrendSignal[] }> {
  const params = new URLSearchParams();
  if (endDate) params.set('end_date', endDate);
  params.set('min_growth', minGrowth.toString());

  const res = await fetch(`${API_BASE}/api/emerging/rising?${params}`);
  if (!res.ok) throw new Error('Failed to fetch rising topics');
  return res.json();
}

export async function fetchHotTopics(
  startDate: string,
  endDate: string,
  minPapers: number = 3
): Promise<{ hot_topics: EmergingTopic[] }> {
  const params = new URLSearchParams();
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  params.set('min_papers', minPapers.toString());

  const res = await fetch(`${API_BASE}/api/emerging/hot?${params}`);
  if (!res.ok) throw new Error('Failed to fetch hot topics');
  return res.json();
}
