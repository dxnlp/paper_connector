import type { ClusterInfo } from '../api';
import { Folder, ChevronRight } from 'lucide-react';
import clsx from 'clsx';

interface ClusterCardProps {
  cluster: ClusterInfo;
  onClick?: () => void;
  isSelected?: boolean;
}

// Gradient colors for clusters
const clusterGradients: Record<string, string> = {
  'benchmark-evaluation': 'from-blue-600/20 to-blue-800/20 hover:from-blue-600/30 hover:to-blue-800/30',
  'dataset-data-curation': 'from-green-600/20 to-green-800/20 hover:from-green-600/30 hover:to-green-800/30',
  'architecture-model-design': 'from-purple-600/20 to-purple-800/20 hover:from-purple-600/30 hover:to-purple-800/30',
  'training-recipe-scaling-distillation': 'from-orange-600/20 to-orange-800/20 hover:from-orange-600/30 hover:to-orange-800/30',
  'post-training-alignment': 'from-pink-600/20 to-pink-800/20 hover:from-pink-600/30 hover:to-pink-800/30',
  'reasoning-test-time-compute': 'from-yellow-600/20 to-yellow-800/20 hover:from-yellow-600/30 hover:to-yellow-800/30',
  'agents-tool-use-workflow': 'from-cyan-600/20 to-cyan-800/20 hover:from-cyan-600/30 hover:to-cyan-800/30',
  'multimodal-method': 'from-indigo-600/20 to-indigo-800/20 hover:from-indigo-600/30 hover:to-indigo-800/30',
  'rag-retrieval-memory': 'from-teal-600/20 to-teal-800/20 hover:from-teal-600/30 hover:to-teal-800/30',
  'safety-robustness-interpretability': 'from-red-600/20 to-red-800/20 hover:from-red-600/30 hover:to-red-800/30',
  'systems-efficiency': 'from-emerald-600/20 to-emerald-800/20 hover:from-emerald-600/30 hover:to-emerald-800/30',
  'survey-tutorial': 'from-amber-600/20 to-amber-800/20 hover:from-amber-600/30 hover:to-amber-800/30',
  'technical-report-model-release': 'from-violet-600/20 to-violet-800/20 hover:from-violet-600/30 hover:to-violet-800/30',
  'theory-analysis': 'from-rose-600/20 to-rose-800/20 hover:from-rose-600/30 hover:to-rose-800/30',
};

const modalityEmoji: Record<string, string> = {
  text: '📝',
  vision: '👁️',
  video: '🎬',
  audio: '🔊',
  multimodal: '🔀',
  code: '💻',
  '3D': '🎲',
};

export function ClusterCard({ cluster, onClick, isSelected }: ClusterCardProps) {
  const gradient = clusterGradients[cluster.clusterId] || 'from-gray-600/20 to-gray-800/20 hover:from-gray-600/30 hover:to-gray-800/30';

  return (
    <div
      onClick={onClick}
      className={clsx(
        'cluster-card glass-card rounded-xl p-5 cursor-pointer bg-gradient-to-br transition-all',
        gradient,
        isSelected && 'ring-2 ring-hf-yellow/50'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Folder size={18} className="text-hf-yellow" />
          <span className="text-2xl font-bold text-white">{cluster.paperCount}</span>
        </div>
        <ChevronRight size={18} className="text-gray-500" />
      </div>

      {/* Cluster name */}
      <h3 className="text-white font-semibold text-sm mb-3 leading-tight">
        {cluster.name}
      </h3>

      {/* Top task tags */}
      {cluster.topTaskTags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {cluster.topTaskTags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-white/5 rounded text-xs text-gray-400"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Modalities */}
      <div className="flex gap-1 text-sm">
        {cluster.topModalities.map((mod) => (
          <span key={mod} title={mod}>
            {modalityEmoji[mod] || '📄'}
          </span>
        ))}
      </div>
    </div>
  );
}

export default ClusterCard;
