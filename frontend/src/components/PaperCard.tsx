import type { PaperCard as PaperCardType } from '../api';
import { ExternalLink, FileText, ThumbsUp, Users, ChevronRight } from 'lucide-react';
import clsx from 'clsx';

interface PaperCardProps {
  paper: PaperCardType;
  onClick?: () => void;
  onTagClick?: (tag: string) => void;
}

// Color mapping for contribution tags
const tagColors: Record<string, string> = {
  'Benchmark / Evaluation': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  'Dataset / Data Curation': 'bg-green-500/20 text-green-300 border-green-500/30',
  'Architecture / Model Design': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  'Training Recipe / Scaling / Distillation': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  'Post-training / Alignment': 'bg-pink-500/20 text-pink-300 border-pink-500/30',
  'Reasoning / Test-time Compute': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  'Agents / Tool Use / Workflow': 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  'Multimodal Method': 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  'RAG / Retrieval / Memory': 'bg-teal-500/20 text-teal-300 border-teal-500/30',
  'Safety / Robustness / Interpretability': 'bg-red-500/20 text-red-300 border-red-500/30',
  'Systems / Efficiency': 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  'Survey / Tutorial': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  'Technical Report / Model Release': 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  'Theory / Analysis': 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  'OTHER': 'bg-gray-500/20 text-gray-300 border-gray-500/30',
};

const modalityIcons: Record<string, string> = {
  text: '📝',
  vision: '👁️',
  video: '🎬',
  audio: '🔊',
  multimodal: '🔀',
  code: '💻',
  '3D': '🎲',
};

export function PaperCardComponent({ paper, onClick, onTagClick }: PaperCardProps) {
  const primaryTagColor = tagColors[paper.primaryTag] || tagColors['OTHER'];

  return (
    <div
      className="paper-card glass-card rounded-xl p-5 w-[340px] h-[380px] flex flex-col cursor-pointer hover:border-hf-yellow/30"
      onClick={onClick}
    >
      {/* Header: ArXiv ID */}
      <div className="text-xs text-gray-400 mb-2">
        <span className="font-mono">arxiv:{paper.paperId}</span>
      </div>

      {/* Title */}
      <h3 className="text-white font-semibold text-sm leading-tight mb-2 line-clamp-2">
        {paper.title}
      </h3>

      {/* Abstract snippet */}
      <p className="text-gray-400 text-xs leading-relaxed mb-3 line-clamp-4 flex-grow">
        {paper.abstractSnippet}
      </p>

      {/* Tags */}
      <div className="space-y-2 mb-3">
        {/* Primary tag */}
        <div
          className={clsx(
            'tag-chip border inline-block',
            primaryTagColor
          )}
          onClick={(e) => {
            e.stopPropagation();
            onTagClick?.(paper.primaryTag);
          }}
        >
          {paper.primaryTag}
        </div>

        {/* Task tags */}
        {paper.taskTags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {paper.taskTags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="tag-chip bg-gray-700/50 text-gray-300 border border-gray-600/50"
                onClick={(e) => {
                  e.stopPropagation();
                  onTagClick?.(tag);
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Modality icons */}
        <div className="flex gap-1">
          {paper.modality.map((mod) => (
            <span key={mod} className="text-sm" title={mod}>
              {modalityIcons[mod] || '📄'}
            </span>
          ))}
        </div>
      </div>

      {/* Footer: Upvotes + Authors + Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-700/50">
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <ThumbsUp size={12} className="text-hf-yellow" />
            {paper.upvotes}
          </span>
          {paper.authorsShort.length > 0 && (
            <span className="flex items-center gap-1">
              <Users size={12} />
              {paper.authorsShort.length}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <a
            href={paper.hfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-hf-yellow transition-colors"
            onClick={(e) => e.stopPropagation()}
            title="Open on Hugging Face"
          >
            <ExternalLink size={14} />
          </a>
          <a
            href={paper.pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-hf-yellow transition-colors"
            onClick={(e) => e.stopPropagation()}
            title="Open PDF"
          >
            <FileText size={14} />
          </a>
          <ChevronRight size={14} className="text-gray-500" />
        </div>
      </div>
    </div>
  );
}

export default PaperCardComponent;
