import { X, ExternalLink, FileText, ThumbsUp, Users, BookOpen } from 'lucide-react';
import type { PaperCard } from '../api';

interface PaperModalProps {
  paper: PaperCard;
  onClose: () => void;
  onTagClick?: (tag: string) => void;
}

export function PaperModal({ paper, onClose, onTagClick }: PaperModalProps) {
  return (
    <div
      className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-[#1a1a2e] rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-[#1a1a2e] border-b border-gray-800 p-4 flex items-start justify-between">
          <div className="flex-1 pr-4">
            <div className="text-xs text-gray-500 font-mono mb-1">
              arxiv:{paper.paperId}
            </div>
            <h2 className="text-xl font-bold text-white leading-tight">
              {paper.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X size={20} className="text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Meta row */}
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <span className="flex items-center gap-1">
              <ThumbsUp size={14} className="text-hf-yellow" />
              {paper.upvotes} upvotes
            </span>
            {paper.authorsShort.length > 0 && (
              <span className="flex items-center gap-1">
                <Users size={14} />
                {paper.authorsShort.join(', ')}
                {paper.authorsShort.length >= 3 && ' et al.'}
              </span>
            )}
            <span>{paper.publishedDate}</span>
          </div>

          {/* Tags section */}
          <div className="space-y-3">
            <div>
              <span className="text-xs text-gray-500 block mb-1">Primary Contribution</span>
              <button
                onClick={() => onTagClick?.(paper.primaryTag)}
                className="px-3 py-1 bg-hf-yellow/20 text-hf-yellow rounded-full text-sm font-medium hover:bg-hf-yellow/30 transition-colors"
              >
                {paper.primaryTag}
              </button>
            </div>

            {paper.secondaryTags.length > 0 && (
              <div>
                <span className="text-xs text-gray-500 block mb-1">Secondary</span>
                <div className="flex flex-wrap gap-2">
                  {paper.secondaryTags.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => onTagClick?.(tag)}
                      className="px-3 py-1 bg-gray-700/50 text-gray-300 rounded-full text-sm hover:bg-gray-700 transition-colors"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {paper.taskTags.length > 0 && (
              <div>
                <span className="text-xs text-gray-500 block mb-1">Tasks</span>
                <div className="flex flex-wrap gap-2">
                  {paper.taskTags.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => onTagClick?.(tag)}
                      className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm hover:bg-blue-500/30 transition-colors"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div>
              <span className="text-xs text-gray-500 block mb-1">Modalities</span>
              <div className="flex flex-wrap gap-2">
                {paper.modality.map((mod) => (
                  <span
                    key={mod}
                    className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm"
                  >
                    {mod}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Research question */}
          {paper.researchQuestion && (
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                <BookOpen size={14} />
                Research Question
              </div>
              <p className="text-white text-sm leading-relaxed">
                {paper.researchQuestion}
              </p>
            </div>
          )}

          {/* Abstract */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-2">Abstract</h3>
            <p className="text-gray-300 text-sm leading-relaxed">
              {paper.abstractSnippet}
            </p>
          </div>

          {/* Confidence & Rationale */}
          {paper.rationale && (
            <div className="bg-gray-800/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500">Tagging Confidence</span>
                <span className="text-sm text-hf-yellow font-medium">
                  {(paper.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-gray-400 text-xs">{paper.rationale}</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 pt-4 border-t border-gray-800">
            <a
              href={paper.hfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 bg-hf-yellow text-black font-medium py-3 rounded-lg hover:bg-hf-orange transition-colors"
            >
              <ExternalLink size={16} />
              Open on Hugging Face
            </a>
            <a
              href={paper.pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 bg-gray-800 text-white px-6 py-3 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <FileText size={16} />
              PDF
            </a>
            <a
              href={paper.arxivUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 bg-gray-800 text-white px-6 py-3 rounded-lg hover:bg-gray-700 transition-colors"
            >
              arXiv
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PaperModal;
