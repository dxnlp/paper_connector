import { X, ArrowLeft, SortAsc } from 'lucide-react';
import type { ClusterInfo, PaperCard as PaperCardType } from '../api';
import PaperCarousel from './PaperCarousel';

interface ClusterViewProps {
  cluster: ClusterInfo;
  papers: PaperCardType[];
  isLoading: boolean;
  onClose: () => void;
  onPaperClick: (paper: PaperCardType) => void;
  onTagClick: (tag: string) => void;
  sortBy: 'upvotes' | 'date' | 'confidence';
  onSortChange: (sort: 'upvotes' | 'date' | 'confidence') => void;
}

export function ClusterView({
  cluster,
  papers,
  isLoading,
  onClose,
  onPaperClick,
  onTagClick,
  sortBy,
  onSortChange,
}: ClusterViewProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm">
      <div className="h-full w-full flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-[#0f0f23]/95">
          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <ArrowLeft size={20} className="text-gray-400" />
            </button>
            <div>
              <h2 className="text-xl font-bold text-white">{cluster.name}</h2>
              <p className="text-sm text-gray-400">
                {cluster.paperCount} papers
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Sort dropdown */}
            <div className="flex items-center gap-2">
              <SortAsc size={16} className="text-gray-500" />
              <select
                value={sortBy}
                onChange={(e) => onSortChange(e.target.value as 'upvotes' | 'date' | 'confidence')}
                className="bg-gray-800 text-white text-sm rounded-lg px-3 py-1.5 border border-gray-700 focus:outline-none focus:border-hf-yellow"
              >
                <option value="upvotes">Most Upvotes</option>
                <option value="date">Newest First</option>
                <option value="confidence">Confidence</option>
              </select>
            </div>

            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#0f0f23]/95">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-hf-yellow"></div>
            </div>
          ) : (
            <>
              {/* Top task tags */}
              {cluster.topTaskTags.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm text-gray-500 mb-2">Top Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {cluster.topTaskTags.map((tag) => (
                      <button
                        key={tag}
                        onClick={() => onTagClick(tag)}
                        className="px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded-full text-sm text-gray-300 transition-colors"
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Papers carousel */}
              <div>
                <h3 className="text-sm text-gray-500 mb-3">Papers</h3>
                <PaperCarousel
                  papers={papers}
                  onPaperClick={onPaperClick}
                  onTagClick={onTagClick}
                />
              </div>

              {/* Papers grid (alternative view) */}
              <div className="mt-8">
                <h3 className="text-sm text-gray-500 mb-3">All Papers</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {papers.map((paper) => (
                    <div
                      key={paper.paperId}
                      onClick={() => onPaperClick(paper)}
                      className="glass-card rounded-lg p-4 cursor-pointer hover:border-hf-yellow/30 transition-all"
                    >
                      <div className="text-xs text-gray-500 mb-1">
                        arxiv:{paper.paperId}
                      </div>
                      <h4 className="text-white text-sm font-medium line-clamp-2 mb-2">
                        {paper.title}
                      </h4>
                      <div className="flex items-center justify-between text-xs text-gray-400">
                        <span>⬆ {paper.upvotes}</span>
                        <span>{paper.publishedDate}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ClusterView;
