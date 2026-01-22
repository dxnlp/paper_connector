import { useCallback, useEffect, useState } from 'react';
import useEmblaCarousel from 'embla-carousel-react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { PaperCard as PaperCardType } from '../api';
import PaperCardComponent from './PaperCard';

interface PaperCarouselProps {
  papers: PaperCardType[];
  onPaperClick?: (paper: PaperCardType) => void;
  onTagClick?: (tag: string) => void;
}

export function PaperCarousel({ papers, onPaperClick, onTagClick }: PaperCarouselProps) {
  const [emblaRef, emblaApi] = useEmblaCarousel({
    align: 'start',
    containScroll: 'trimSnaps',
    dragFree: true,
  });

  const scrollPrev = useCallback(() => {
    if (emblaApi) emblaApi.scrollPrev();
  }, [emblaApi]);

  const scrollNext = useCallback(() => {
    if (emblaApi) emblaApi.scrollNext();
  }, [emblaApi]);

  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(false);

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setCanScrollPrev(emblaApi.canScrollPrev());
    setCanScrollNext(emblaApi.canScrollNext());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    onSelect();
    emblaApi.on('select', onSelect);
    emblaApi.on('reInit', onSelect);
    return () => {
      emblaApi.off('select', onSelect);
      emblaApi.off('reInit', onSelect);
    };
  }, [emblaApi, onSelect]);

  if (papers.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No papers in this cluster
      </div>
    );
  }

  return (
    <div className="relative group">
      {/* Navigation buttons */}
      {canScrollPrev && (
        <button
          onClick={scrollPrev}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-gray-900/90 hover:bg-gray-800 text-white p-2 rounded-full shadow-lg transition-all opacity-0 group-hover:opacity-100 -translate-x-4 group-hover:translate-x-0"
        >
          <ChevronLeft size={24} />
        </button>
      )}
      {canScrollNext && (
        <button
          onClick={scrollNext}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-gray-900/90 hover:bg-gray-800 text-white p-2 rounded-full shadow-lg transition-all opacity-0 group-hover:opacity-100 translate-x-4 group-hover:translate-x-0"
        >
          <ChevronRight size={24} />
        </button>
      )}

      {/* Carousel */}
      <div className="embla overflow-hidden" ref={emblaRef}>
        <div className="embla__container flex gap-4 py-2">
          {papers.map((paper, index) => (
            <div
              key={paper.paperId}
              className="embla__slide flex-shrink-0 animate-fade-in"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <PaperCardComponent
                paper={paper}
                onClick={() => onPaperClick?.(paper)}
                onTagClick={onTagClick}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Scroll hint gradient */}
      {canScrollNext && (
        <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-[#0f0f23] to-transparent pointer-events-none" />
      )}
      {canScrollPrev && (
        <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-[#0f0f23] to-transparent pointer-events-none" />
      )}
    </div>
  );
}

export default PaperCarousel;
