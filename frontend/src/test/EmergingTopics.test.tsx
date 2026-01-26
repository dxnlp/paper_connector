import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EmergingTopics } from '../components/EmergingTopics';
import * as api from '../api';
import type { EmergingTopicsReport } from '../api';

// Mock the API module
vi.mock('../api', async () => {
  const actual = await vi.importActual('../api');
  return {
    ...actual,
    fetchEmergingReport: vi.fn(),
  };
});

const mockReport: EmergingTopicsReport = {
  generated_at: '2024-01-15T10:00:00Z',
  analysis_period: '2024-01-01 to 2024-01-14',
  emerging_topics: [
    {
      name: 'Vision Transformers',
      signal_type: 'new_cluster',
      confidence: 0.85,
      evidence: 'New cluster with 10 papers appeared',
      first_seen: '2024-01-10',
      growth_rate: null,
      related_clusters: [],
      sample_paper_ids: ['paper1', 'paper2'],
    },
    {
      name: 'RLHF Advances',
      signal_type: 'rapid_growth',
      confidence: 0.75,
      evidence: 'Cluster grew by 150%',
      first_seen: null,
      growth_rate: 150,
      related_clusters: ['AI Safety'],
      sample_paper_ids: ['paper3'],
    },
    {
      name: 'LLM Fine-tuning',
      signal_type: 'upvote_surge',
      confidence: 0.9,
      evidence: 'Papers receiving 2.5x average upvotes',
      first_seen: null,
      growth_rate: null,
      related_clusters: [],
      sample_paper_ids: ['paper4'],
    },
    {
      name: 'Keyword: diffusion model',
      signal_type: 'keyword_emergence',
      confidence: 0.6,
      evidence: 'New keyword appeared in 8 papers',
      first_seen: '2024-01-05',
      growth_rate: null,
      related_clusters: [],
      sample_paper_ids: ['paper5'],
    },
  ],
  trend_signals: [
    {
      cluster_name: 'LLM / Foundation Models',
      signal_strength: 0.8,
      trend_direction: 'rising',
      weekly_change: 60,
      monthly_change: 120,
      current_count: 15,
      previous_count: 8,
    },
    {
      cluster_name: 'Computer Vision',
      signal_strength: 0.5,
      trend_direction: 'falling',
      weekly_change: -30,
      monthly_change: -20,
      current_count: 5,
      previous_count: 10,
    },
    {
      cluster_name: 'Efficient AI',
      signal_strength: 0.1,
      trend_direction: 'stable',
      weekly_change: 5,
      monthly_change: 10,
      current_count: 8,
      previous_count: 8,
    },
  ],
  summary: 'Detected 4 emerging signals. Top signal: Vision Transformers (new_cluster). Trend analysis: 1 rising, 1 falling clusters.',
};

const emptyReport: EmergingTopicsReport = {
  generated_at: '2024-01-15T10:00:00Z',
  analysis_period: '2024-01-01 to 2024-01-14',
  emerging_topics: [],
  trend_signals: [],
  summary: 'No significant emerging topics detected.',
};

describe('EmergingTopics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading spinner initially', async () => {
      vi.mocked(api.fetchEmergingReport).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<EmergingTopics />);

      expect(document.querySelector('.animate-spin')).toBeTruthy();
    });
  });

  describe('Error State', () => {
    it('should show error message on API failure', async () => {
      vi.mocked(api.fetchEmergingReport).mockRejectedValue(new Error('API Error'));

      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText(/Could not load emerging topics/)).toBeTruthy();
      });
    });
  });

  describe('Success State', () => {
    it('should render report data correctly', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('Emerging Topics')).toBeTruthy();
      });

      expect(screen.getByText(mockReport.summary)).toBeTruthy();
      expect(screen.getByText(`Analysis period: ${mockReport.analysis_period}`)).toBeTruthy();
    });

    it('should render emerging topics tab by default', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('Vision Transformers')).toBeTruthy();
      });
    });

    it('should switch to trends tab when clicked', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('Trends (3)')).toBeTruthy();
      });

      fireEvent.click(screen.getByText('Trends (3)'));

      await waitFor(() => {
        expect(screen.getByText('LLM / Foundation Models')).toBeTruthy();
      });
    });

    it('should show refresh button', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeTruthy();
      });
    });

    it('should reload data when refresh is clicked', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeTruthy();
      });

      fireEvent.click(screen.getByText('Refresh'));

      expect(api.fetchEmergingReport).toHaveBeenCalledTimes(2);
    });
  });

  describe('Emerging Topics Tab', () => {
    beforeEach(async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);
    });

    it('should show topic count in tab', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('Emerging (4)')).toBeTruthy();
      });
    });

    it('should display signal type labels correctly', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('New Area')).toBeTruthy();
        expect(screen.getByText('Growing')).toBeTruthy();
        expect(screen.getByText('Hot')).toBeTruthy();
        expect(screen.getByText('New Keyword')).toBeTruthy();
      });
    });

    it('should display confidence percentages', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('85% confidence')).toBeTruthy();
        expect(screen.getByText('75% confidence')).toBeTruthy();
      });
    });

    it('should display evidence text', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText(/New cluster with 10 papers/)).toBeTruthy();
      });
    });

    it('should show growth rate when available', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('+150% growth')).toBeTruthy();
      });
    });

    it('should show first seen date when available', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText('First seen: 2024-01-10')).toBeTruthy();
      });
    });
  });

  describe('Trends Tab', () => {
    beforeEach(async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);
    });

    it('should show rising and falling sections', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Trends (3)'));
      });

      await waitFor(() => {
        expect(screen.getByText('Rising (1)')).toBeTruthy();
        expect(screen.getByText('Declining (1)')).toBeTruthy();
      });
    });

    it('should display weekly change percentages', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Trends (3)'));
      });

      await waitFor(() => {
        expect(screen.getByText('+60%')).toBeTruthy();
        expect(screen.getByText('-30%')).toBeTruthy();
      });
    });

    it('should display paper counts', async () => {
      render(<EmergingTopics />);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Trends (3)'));
      });

      await waitFor(() => {
        expect(screen.getByText('15 papers')).toBeTruthy();
        expect(screen.getByText('5 papers')).toBeTruthy();
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty message when no emerging topics', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(emptyReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        expect(screen.getByText(/No emerging topics detected/)).toBeTruthy();
      });
    });

    it('should show empty message when no trends', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(emptyReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Trends (0)'));
      });

      await waitFor(() => {
        expect(screen.getByText(/No significant trends detected/)).toBeTruthy();
      });
    });
  });

  describe('Callbacks', () => {
    it('should call onClusterClick when clicking on topic card', async () => {
      const onClusterClick = vi.fn();
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics onClusterClick={onClusterClick} />);

      await waitFor(() => {
        expect(screen.getByText('Vision Transformers')).toBeTruthy();
      });

      // Click on a topic card (not a keyword type)
      const topicCard = screen.getByText('Vision Transformers').closest('[class*="cursor-pointer"]');
      if (topicCard) {
        fireEvent.click(topicCard);
        expect(onClusterClick).toHaveBeenCalledWith('Vision Transformers');
      }
    });

    it('should not call onClusterClick for keyword topics', async () => {
      const onClusterClick = vi.fn();
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics onClusterClick={onClusterClick} />);

      await waitFor(() => {
        expect(screen.getByText('diffusion model')).toBeTruthy();
      });

      // Click on keyword topic
      const keywordCard = screen.getByText('diffusion model').closest('[class*="cursor-pointer"]');
      if (keywordCard) {
        fireEvent.click(keywordCard);
        // Should not be called because it's a keyword type
        expect(onClusterClick).not.toHaveBeenCalled();
      }
    });

    it('should call onClusterClick when clicking on trend row', async () => {
      const onClusterClick = vi.fn();
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics onClusterClick={onClusterClick} />);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Trends (3)'));
      });

      await waitFor(() => {
        expect(screen.getByText('LLM / Foundation Models')).toBeTruthy();
      });

      const trendRow = screen.getByText('LLM / Foundation Models').closest('[class*="cursor-pointer"]');
      if (trendRow) {
        fireEvent.click(trendRow);
        expect(onClusterClick).toHaveBeenCalledWith('LLM / Foundation Models');
      }
    });
  });

  describe('Visual Indicators', () => {
    it('should show trend direction icons', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Trends (3)'));
      });

      // Icons are rendered (checking for SVG elements)
      await waitFor(() => {
        const svgs = document.querySelectorAll('svg');
        expect(svgs.length).toBeGreaterThan(0);
      });
    });

    it('should show signal strength progress bars', async () => {
      vi.mocked(api.fetchEmergingReport).mockResolvedValue(mockReport);

      render(<EmergingTopics />);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Trends (3)'));
      });

      // Progress bars exist
      await waitFor(() => {
        const progressBars = document.querySelectorAll('[class*="bg-gray-700"]');
        expect(progressBars.length).toBeGreaterThan(0);
      });
    });
  });
});
