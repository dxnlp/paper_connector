import { useState, useEffect } from 'react';
import { Search, Calendar, RefreshCw, X, Grid3X3, GitBranch, TrendingUp } from 'lucide-react';
import type { MonthSummary, ClusterInfo, PaperCard as PaperCardType, ClusterGraphData, ClusterNode, FlowData } from './api';
import {
  fetchMonthSummary,
  fetchMonthPapers,
  fetchClusterPapers,
  fetchClusterGraph,
  triggerReindex,
  fetchIndexStatus,
  fetchFlowData,
} from './api';
import ClusterCard from './components/ClusterCard';
import ClusterView from './components/ClusterView';
import PaperModal from './components/PaperModal';
import PaperCarousel from './components/PaperCarousel';
import ClusterGraph from './components/ClusterGraph';
import FlowVisualization from './components/FlowVisualization';
import EmergingTopics from './components/EmergingTopics';

// Generate recent months
function getRecentMonths(count: number = 12): string[] {
  const months: string[] = [];
  const now = new Date();
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  }
  return months;
}

type ViewMode = 'grid' | 'graph' | 'flow';

function App() {
  // State
  const [selectedMonth, setSelectedMonth] = useState<string>(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [summary, setSummary] = useState<MonthSummary | null>(null);
  const [allPapers, setAllPapers] = useState<PaperCardType[]>([]);
  const [filteredPapers, setFilteredPapers] = useState<PaperCardType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // View mode
  const [viewMode, setViewMode] = useState<ViewMode>('graph');

  // Graph data
  const [graphData, setGraphData] = useState<ClusterGraphData | null>(null);

  // Flow data (temporal visualization)
  const [flowData, setFlowData] = useState<FlowData | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCluster, setSelectedCluster] = useState<ClusterInfo | null>(null);
  const [clusterPapers, setClusterPapers] = useState<PaperCardType[]>([]);
  const [clusterLoading, setClusterLoading] = useState(false);
  const [sortBy, setSortBy] = useState<'upvotes' | 'date' | 'confidence'>('upvotes');

  // Modal
  const [selectedPaper, setSelectedPaper] = useState<PaperCardType | null>(null);

  // Indexing
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexStatus, setIndexStatus] = useState<string>('');

  const months = getRecentMonths(12);

  // Load month data
  useEffect(() => {
    loadMonthData();
  }, [selectedMonth]);

  async function loadMonthData() {
    setIsLoading(true);
    setError(null);
    try {
      // Calculate date range for flow data (entire selected month)
      const [year, month] = selectedMonth.split('-').map(Number);
      const startDate = `${selectedMonth}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${selectedMonth}-${String(lastDay).padStart(2, '0')}`;

      const [summaryData, papersData, graphDataResult, flowDataResult] = await Promise.all([
        fetchMonthSummary(selectedMonth),
        fetchMonthPapers(selectedMonth, { sortBy, limit: 200 }),
        fetchClusterGraph(selectedMonth),
        fetchFlowData(startDate, endDate).catch(() => null), // Flow data is optional
      ]);
      setSummary(summaryData);
      setAllPapers(papersData);
      setFilteredPapers(papersData);
      setGraphData(graphDataResult);
      setFlowData(flowDataResult);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load papers. Make sure the backend is running and papers are indexed.');
      setSummary(null);
      setAllPapers([]);
      setFilteredPapers([]);
      setGraphData(null);
      setFlowData(null);
    } finally {
      setIsLoading(false);
    }
  }

  // Search filtering
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredPapers(allPapers);
      return;
    }
    const query = searchQuery.toLowerCase();
    const filtered = allPapers.filter(
      (p) =>
        p.title.toLowerCase().includes(query) ||
        p.abstractSnippet.toLowerCase().includes(query) ||
        p.primaryTag.toLowerCase().includes(query) ||
        p.taskTags.some((t) => t.toLowerCase().includes(query))
    );
    setFilteredPapers(filtered);
  }, [searchQuery, allPapers]);

  // Handle cluster click from graph
  function handleGraphNodeClick(node: ClusterNode) {
    // Convert ClusterNode to ClusterInfo for compatibility
    const clusterInfo: ClusterInfo = {
      clusterId: node.id,
      name: node.name,
      paperCount: node.paperCount,
      topTaskTags: node.topTaskTags,
      topModalities: node.topModalities,
    };
    handleClusterClick(clusterInfo);
  }

  // Load cluster papers
  async function handleClusterClick(cluster: ClusterInfo) {
    setSelectedCluster(cluster);
    setClusterLoading(true);
    try {
      const papers = await fetchClusterPapers(cluster.clusterId, selectedMonth, sortBy);
      setClusterPapers(papers);
    } catch (err) {
      console.error('Failed to load cluster papers:', err);
      setClusterPapers([]);
    } finally {
      setClusterLoading(false);
    }
  }

  // Handle tag click (filter)
  function handleTagClick(tag: string) {
    setSearchQuery(tag);
    setSelectedCluster(null);
  }

  // Trigger reindexing
  async function handleReindex() {
    if (isIndexing) return;
    setIsIndexing(true);
    setIndexStatus('Starting...');

    try {
      await triggerReindex(selectedMonth, false);

      // Poll for status
      const pollStatus = async () => {
        const status = await fetchIndexStatus(selectedMonth);
        setIndexStatus(`${status.message} (${status.papers_scraped} scraped, ${status.papers_tagged} tagged)`);

        if (status.status === 'completed') {
          setIsIndexing(false);
          loadMonthData();
        } else if (status.status === 'failed') {
          setIsIndexing(false);
          setError(status.message);
        } else {
          setTimeout(pollStatus, 2000);
        }
      };

      setTimeout(pollStatus, 1000);
    } catch (err) {
      console.error('Failed to start reindex:', err);
      setIsIndexing(false);
      setError('Failed to start indexing');
    }
  }

  return (
    <div className="min-h-screen text-white">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0f0f23]/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between gap-4">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-hf-yellow to-hf-orange rounded-lg flex items-center justify-center">
                <span className="text-xl">📄</span>
              </div>
              <div>
                <h1 className="text-lg font-bold gradient-text">HF Papers Explorer</h1>
                <p className="text-xs text-gray-500">Papers of the Month</p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-3">
              {/* View mode toggle */}
              <div className="flex items-center bg-gray-800/50 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('graph')}
                  className={`p-2 rounded-md transition-colors ${
                    viewMode === 'graph'
                      ? 'bg-hf-yellow text-black'
                      : 'text-gray-400 hover:text-white'
                  }`}
                  title="Cluster Network"
                >
                  <GitBranch size={16} />
                </button>
                <button
                  onClick={() => setViewMode('flow')}
                  className={`p-2 rounded-md transition-colors ${
                    viewMode === 'flow'
                      ? 'bg-hf-yellow text-black'
                      : 'text-gray-400 hover:text-white'
                  }`}
                  title="Flow View (Timeline)"
                >
                  <TrendingUp size={16} />
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded-md transition-colors ${
                    viewMode === 'grid'
                      ? 'bg-hf-yellow text-black'
                      : 'text-gray-400 hover:text-white'
                  }`}
                  title="Grid View"
                >
                  <Grid3X3 size={16} />
                </button>
              </div>

              {/* Month selector */}
              <div className="flex items-center gap-2 bg-gray-800/50 rounded-lg px-3 py-2">
                <Calendar size={16} className="text-gray-500" />
                <select
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="bg-transparent text-white text-sm focus:outline-none cursor-pointer"
                >
                  {months.map((m) => (
                    <option key={m} value={m} className="bg-gray-800">
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              {/* Search */}
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search papers..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-gray-800/50 text-white pl-10 pr-4 py-2 rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-hf-yellow/50"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>

              {/* Reindex button */}
              <button
                onClick={handleReindex}
                disabled={isIndexing}
                className="flex items-center gap-2 bg-hf-yellow text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-hf-orange transition-colors disabled:opacity-50"
              >
                <RefreshCw size={16} className={isIndexing ? 'animate-spin' : ''} />
                {isIndexing ? 'Indexing...' : 'Index'}
              </button>
            </div>
          </div>

          {/* Index status */}
          {isIndexing && indexStatus && (
            <div className="mt-2 text-sm text-hf-yellow">{indexStatus}</div>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Error state */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-300 rounded-lg p-4 mb-6">
            <p>{error}</p>
            <p className="text-sm mt-2 text-red-400">
              Click "Index" to scrape and index papers for this month.
            </p>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-hf-yellow"></div>
          </div>
        )}

        {/* Content */}
        {!isLoading && summary && (
          <>
            {/* Stats */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-2">
                <span className="gradient-text">{summary.totalPapers}</span> Papers
              </h2>
              <p className="text-gray-400">
                {summary.clusters.length} clusters for {selectedMonth}
                {graphData && graphData.links.length > 0 && (
                  <span className="ml-2">• {graphData.links.length} connections</span>
                )}
              </p>
            </div>

            {/* Search results */}
            {searchQuery && (
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">
                    Search Results ({filteredPapers.length})
                  </h3>
                  <button
                    onClick={() => setSearchQuery('')}
                    className="text-sm text-gray-400 hover:text-white"
                  >
                    Clear search
                  </button>
                </div>
                <PaperCarousel
                  papers={filteredPapers}
                  onPaperClick={setSelectedPaper}
                  onTagClick={handleTagClick}
                />
              </div>
            )}

            {/* Graph View */}
            {!searchQuery && viewMode === 'graph' && graphData && (
              <div className="mb-8">
                <h3 className="text-lg font-semibold mb-4">Cluster Network</h3>
                <div className="h-[600px] rounded-xl overflow-hidden border border-gray-800">
                  <ClusterGraph
                    graphData={graphData}
                    onNodeClick={handleGraphNodeClick}
                    selectedNodeId={selectedCluster?.clusterId}
                  />
                </div>
              </div>
            )}

            {/* Flow View */}
            {!searchQuery && viewMode === 'flow' && (
              <div className="mb-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Flow visualization - takes 2/3 */}
                  <div className="lg:col-span-2">
                    <h3 className="text-lg font-semibold mb-4">Research Trends Over Time</h3>
                    {flowData && flowData.daily_data.length > 0 ? (
                      <div className="rounded-xl overflow-hidden border border-gray-800">
                        <FlowVisualization
                          flowData={flowData}
                          height={500}
                          onClusterClick={(cluster, _date) => {
                            // Find matching cluster info and show it
                            const clusterInfo = summary?.clusters.find(
                              c => c.name === cluster
                            );
                            if (clusterInfo) {
                              handleClusterClick(clusterInfo);
                            }
                          }}
                        />
                      </div>
                    ) : (
                      <div className="h-[500px] rounded-xl border border-gray-800 bg-[#0a0a1a] flex items-center justify-center">
                        <div className="text-center">
                          <TrendingUp size={48} className="mx-auto mb-4 text-gray-600" />
                          <p className="text-gray-400">No temporal data available yet</p>
                          <p className="text-sm text-gray-500 mt-2">
                            Daily paper tracking will populate this view over time
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Emerging topics sidebar - takes 1/3 */}
                  <div>
                    <EmergingTopics
                      onClusterClick={(clusterName) => {
                        const clusterInfo = summary?.clusters.find(
                          c => c.name === clusterName
                        );
                        if (clusterInfo) {
                          handleClusterClick(clusterInfo);
                        }
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Grid View */}
            {!searchQuery && viewMode === 'grid' && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Clusters by Contribution</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {summary.clusters.map((cluster) => (
                    <ClusterCard
                      key={cluster.clusterId}
                      cluster={cluster}
                      onClick={() => handleClusterClick(cluster)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* All papers section */}
            {!searchQuery && filteredPapers.length > 0 && (
              <div className="mt-12">
                <h3 className="text-lg font-semibold mb-4">All Papers</h3>
                <PaperCarousel
                  papers={filteredPapers.slice(0, 20)}
                  onPaperClick={setSelectedPaper}
                  onTagClick={handleTagClick}
                />
              </div>
            )}
          </>
        )}

        {/* Empty state */}
        {!isLoading && !error && summary && summary.totalPapers === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📭</div>
            <h3 className="text-xl font-semibold mb-2">No papers indexed yet</h3>
            <p className="text-gray-400 mb-6">
              Click the "Index" button to scrape and index papers for {selectedMonth}
            </p>
            <button
              onClick={handleReindex}
              className="bg-hf-yellow text-black px-6 py-3 rounded-lg font-medium hover:bg-hf-orange transition-colors"
            >
              Start Indexing
            </button>
          </div>
        )}
      </main>

      {/* Cluster view modal */}
      {selectedCluster && (
        <ClusterView
          cluster={selectedCluster}
          papers={clusterPapers}
          isLoading={clusterLoading}
          onClose={() => setSelectedCluster(null)}
          onPaperClick={setSelectedPaper}
          onTagClick={handleTagClick}
          sortBy={sortBy}
          onSortChange={setSortBy}
        />
      )}

      {/* Paper detail modal */}
      {selectedPaper && (
        <PaperModal
          paper={selectedPaper}
          onClose={() => setSelectedPaper(null)}
          onTagClick={handleTagClick}
        />
      )}
    </div>
  );
}

export default App;
