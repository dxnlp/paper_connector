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
