import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, Sparkles, Flame, Zap, AlertCircle } from 'lucide-react';
import type { EmergingTopicsReport, EmergingTopic, TrendSignal } from '../api';
import { fetchEmergingReport } from '../api';

interface EmergingTopicsProps {
  onClusterClick?: (clusterName: string) => void;
}

const signalTypeIcons = {
  new_cluster: Sparkles,
  rapid_growth: TrendingUp,
  upvote_surge: Flame,
  keyword_emergence: Zap,
};

const signalTypeColors = {
  new_cluster: 'text-purple-400 bg-purple-400/10',
  rapid_growth: 'text-green-400 bg-green-400/10',
  upvote_surge: 'text-orange-400 bg-orange-400/10',
  keyword_emergence: 'text-blue-400 bg-blue-400/10',
};

const signalTypeLabels = {
  new_cluster: 'New Area',
  rapid_growth: 'Growing',
  upvote_surge: 'Hot',
  keyword_emergence: 'New Keyword',
};

function TrendIndicator({ signal }: { signal: TrendSignal }) {
  const Icon = signal.trend_direction === 'rising' ? TrendingUp :
               signal.trend_direction === 'falling' ? TrendingDown : Minus;

  const colorClass = signal.trend_direction === 'rising' ? 'text-green-400' :
                     signal.trend_direction === 'falling' ? 'text-red-400' : 'text-gray-400';

  return (
    <div className="flex items-center gap-1">
      <Icon size={14} className={colorClass} />
      <span className={`text-xs ${colorClass}`}>
        {signal.weekly_change > 0 ? '+' : ''}{signal.weekly_change.toFixed(0)}%
      </span>
    </div>
  );
}

function EmergingTopicCard({
  topic,
  onClusterClick,
}: {
  topic: EmergingTopic;
  onClusterClick?: (name: string) => void;
}) {
  const Icon = signalTypeIcons[topic.signal_type] || Sparkles;
  const colorClass = signalTypeColors[topic.signal_type] || 'text-gray-400 bg-gray-400/10';
  const label = signalTypeLabels[topic.signal_type] || 'Signal';

  // Extract the actual name (remove "Keyword: " prefix if present)
  const displayName = topic.name.replace(/^Keyword: /, '');
  const isKeyword = topic.signal_type === 'keyword_emergence';

  return (
    <div
      className="bg-gray-800/50 rounded-lg p-4 hover:bg-gray-800/70 transition-colors cursor-pointer"
      onClick={() => !isKeyword && onClusterClick?.(displayName)}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-md ${colorClass}`}>
            <Icon size={14} />
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full ${colorClass}`}>
            {label}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-hf-yellow animate-pulse" />
          <span className="text-xs text-gray-500">
            {(topic.confidence * 100).toFixed(0)}% confidence
          </span>
        </div>
      </div>

      <h4 className="font-medium text-white mb-1 truncate" title={displayName}>
        {displayName}
      </h4>

      <p className="text-xs text-gray-400 line-clamp-2 mb-2">
        {topic.evidence}
      </p>

      {topic.growth_rate && topic.growth_rate > 0 && (
        <div className="text-xs text-green-400">
          +{topic.growth_rate.toFixed(0)}% growth
        </div>
      )}

      {topic.first_seen && (
        <div className="text-xs text-gray-500 mt-1">
          First seen: {topic.first_seen}
        </div>
      )}
    </div>
  );
}

function TrendSignalRow({
  signal,
  onClusterClick,
}: {
  signal: TrendSignal;
  onClusterClick?: (name: string) => void;
}) {
  const barWidth = Math.min(100, signal.signal_strength * 100);

  return (
    <div
      className="flex items-center gap-3 py-2 px-3 hover:bg-gray-800/30 rounded-lg cursor-pointer transition-colors"
      onClick={() => onClusterClick?.(signal.cluster_name)}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-white truncate">{signal.cluster_name}</span>
          <TrendIndicator signal={signal} />
        </div>
        <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              signal.trend_direction === 'rising' ? 'bg-green-500' :
              signal.trend_direction === 'falling' ? 'bg-red-500' : 'bg-gray-500'
            }`}
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>
      <div className="text-xs text-gray-500 w-16 text-right">
        {signal.current_count} papers
      </div>
    </div>
  );
}

export function EmergingTopics({ onClusterClick }: EmergingTopicsProps) {
  const [report, setReport] = useState<EmergingTopicsReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'emerging' | 'trends'>('emerging');

  useEffect(() => {
    loadReport();
  }, []);

  async function loadReport() {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchEmergingReport();
      setReport(data);
    } catch (err) {
      console.error('Failed to load emerging report:', err);
      setError('Could not load emerging topics. This feature requires temporal data.');
    } finally {
      setIsLoading(false);
    }
  }

  if (isLoading) {
    return (
      <div className="bg-gray-900/50 rounded-xl p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-hf-yellow" />
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="bg-gray-900/50 rounded-xl p-6">
        <div className="flex items-center gap-3 text-gray-400">
          <AlertCircle size={20} />
          <span>{error || 'No emerging topics data available'}</span>
        </div>
        <p className="text-sm text-gray-500 mt-2">
          Emerging topic detection requires papers indexed with daily tracking enabled.
        </p>
      </div>
    );
  }

  const risingTrends = report.trend_signals.filter(s => s.trend_direction === 'rising');
  const fallingTrends = report.trend_signals.filter(s => s.trend_direction === 'falling');

  return (
    <div className="bg-gray-900/50 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Sparkles className="text-hf-yellow" size={20} />
            Emerging Topics
          </h3>
          <button
            onClick={loadReport}
            className="text-xs text-gray-400 hover:text-white transition-colors"
          >
            Refresh
          </button>
        </div>
        <p className="text-xs text-gray-500">{report.summary}</p>
        <p className="text-xs text-gray-600 mt-1">
          Analysis period: {report.analysis_period}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        <button
          onClick={() => setActiveTab('emerging')}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            activeTab === 'emerging'
              ? 'text-hf-yellow border-b-2 border-hf-yellow'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Emerging ({report.emerging_topics.length})
        </button>
        <button
          onClick={() => setActiveTab('trends')}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            activeTab === 'trends'
              ? 'text-hf-yellow border-b-2 border-hf-yellow'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Trends ({report.trend_signals.length})
        </button>
      </div>

      {/* Content */}
      <div className="p-4 max-h-[500px] overflow-y-auto">
        {activeTab === 'emerging' && (
          <>
            {report.emerging_topics.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-8">
                No emerging topics detected in this period.
              </p>
            ) : (
              <div className="grid gap-3">
                {report.emerging_topics.map((topic, idx) => (
                  <EmergingTopicCard
                    key={`${topic.name}-${idx}`}
                    topic={topic}
                    onClusterClick={onClusterClick}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {activeTab === 'trends' && (
          <div className="space-y-4">
            {risingTrends.length > 0 && (
              <div>
                <h4 className="text-xs text-green-400 font-medium mb-2 flex items-center gap-1">
                  <TrendingUp size={12} />
                  Rising ({risingTrends.length})
                </h4>
                <div className="space-y-1">
                  {risingTrends.map((signal, idx) => (
                    <TrendSignalRow
                      key={`rising-${signal.cluster_name}-${idx}`}
                      signal={signal}
                      onClusterClick={onClusterClick}
                    />
                  ))}
                </div>
              </div>
            )}

            {fallingTrends.length > 0 && (
              <div>
                <h4 className="text-xs text-red-400 font-medium mb-2 flex items-center gap-1">
                  <TrendingDown size={12} />
                  Declining ({fallingTrends.length})
                </h4>
                <div className="space-y-1">
                  {fallingTrends.map((signal, idx) => (
                    <TrendSignalRow
                      key={`falling-${signal.cluster_name}-${idx}`}
                      signal={signal}
                      onClusterClick={onClusterClick}
                    />
                  ))}
                </div>
              </div>
            )}

            {risingTrends.length === 0 && fallingTrends.length === 0 && (
              <p className="text-gray-500 text-sm text-center py-8">
                No significant trends detected in this period.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default EmergingTopics;
