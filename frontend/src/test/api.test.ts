import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchFlowData,
  fetchEmergingReport,
  fetchEmergingTrends,
  fetchRisingTopics,
  fetchHotTopics,
  fetchDailyStats,
  fetchTrendData,
  type FlowData,
  type EmergingTopicsReport,
  type TrendSignal,
  type EmergingTopic,
  type DailyStats,
  type TrendData,
} from '../api';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('API Functions', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe('fetchFlowData', () => {
    const mockFlowData: FlowData = {
      start_date: '2024-01-01',
      end_date: '2024-01-14',
      clusters: ['LLM', 'Vision', 'Multimodal'],
      colors: {
        LLM: '#FF6B6B',
        Vision: '#4ECDC4',
        Multimodal: '#45B7D1',
      },
      daily_data: [
        {
          date: '2024-01-01',
          cluster_counts: { LLM: 5, Vision: 3, Multimodal: 2 },
        },
        {
          date: '2024-01-02',
          cluster_counts: { LLM: 7, Vision: 4, Multimodal: 3 },
        },
      ],
    };

    it('should fetch flow data with correct parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockFlowData,
      });

      const result = await fetchFlowData('2024-01-01', '2024-01-14');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/flow?start_date=2024-01-01&end_date=2024-01-14')
      );
      expect(result).toEqual(mockFlowData);
    });

    it('should throw error on failed request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(fetchFlowData('2024-01-01', '2024-01-14')).rejects.toThrow(
        'Failed to fetch flow data'
      );
    });
  });

  describe('fetchEmergingReport', () => {
    const mockReport: EmergingTopicsReport = {
      generated_at: '2024-01-15T10:00:00Z',
      analysis_period: '2024-01-01 to 2024-01-14',
      emerging_topics: [
        {
          name: 'Test Topic',
          signal_type: 'new_cluster',
          confidence: 0.85,
          evidence: 'Test evidence',
          first_seen: '2024-01-10',
          growth_rate: null,
          related_clusters: [],
          sample_paper_ids: ['paper1'],
        },
      ],
      trend_signals: [
        {
          cluster_name: 'LLM',
          signal_strength: 0.75,
          trend_direction: 'rising',
          weekly_change: 50,
          monthly_change: 100,
          current_count: 10,
          previous_count: 5,
        },
      ],
      summary: 'Test summary',
    };

    it('should fetch emerging report with default parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockReport,
      });

      const result = await fetchEmergingReport();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/emerging/report')
      );
      expect(result).toEqual(mockReport);
    });

    it('should fetch with custom parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockReport,
      });

      await fetchEmergingReport('2024-01-14', 7, 14);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('end_date=2024-01-14')
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('lookback_days=7')
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('comparison_days=14')
      );
    });
  });

  describe('fetchEmergingTrends', () => {
    const mockTrends: { end_date: string; trends: TrendSignal[] } = {
      end_date: '2024-01-14',
      trends: [
        {
          cluster_name: 'LLM',
          signal_strength: 0.8,
          trend_direction: 'rising',
          weekly_change: 60,
          monthly_change: 120,
          current_count: 15,
          previous_count: 8,
        },
      ],
    };

    it('should fetch trends with limit', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrends,
      });

      const result = await fetchEmergingTrends('2024-01-14', 10);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=10')
      );
      expect(result.trends).toHaveLength(1);
    });
  });

  describe('fetchRisingTopics', () => {
    const mockRising: { end_date: string; rising_topics: TrendSignal[] } = {
      end_date: '2024-01-14',
      rising_topics: [
        {
          cluster_name: 'Multimodal',
          signal_strength: 0.9,
          trend_direction: 'rising',
          weekly_change: 80,
          monthly_change: 150,
          current_count: 20,
          previous_count: 10,
        },
      ],
    };

    it('should fetch rising topics with min growth', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRising,
      });

      const result = await fetchRisingTopics('2024-01-14', 30);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('min_growth=30')
      );
      expect(result.rising_topics).toHaveLength(1);
    });
  });

  describe('fetchHotTopics', () => {
    const mockHot: { hot_topics: EmergingTopic[] } = {
      hot_topics: [
        {
          name: 'Hot Topic',
          signal_type: 'upvote_surge',
          confidence: 0.9,
          evidence: 'High upvotes',
          first_seen: null,
          growth_rate: null,
          related_clusters: [],
          sample_paper_ids: ['paper1', 'paper2'],
        },
      ],
    };

    it('should fetch hot topics with date range', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHot,
      });

      const result = await fetchHotTopics('2024-01-01', '2024-01-14', 5);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('start_date=2024-01-01')
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('end_date=2024-01-14')
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('min_papers=5')
      );
      expect(result.hot_topics).toHaveLength(1);
    });
  });

  describe('fetchDailyStats', () => {
    const mockStats: DailyStats = {
      date: '2024-01-15',
      total_papers: 50,
      new_papers: 20,
      clusters: [
        {
          name: 'LLM',
          color: '#FF6B6B',
          paper_count: 25,
          top_papers: ['paper1'],
          avg_upvotes: 100,
          total_upvotes: 2500,
        },
      ],
      top_papers: ['paper1', 'paper2'],
      total_upvotes: 5000,
    };

    it('should fetch daily stats', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats,
      });

      const result = await fetchDailyStats('2024-01-15');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/daily/2024-01-15/stats')
      );
      expect(result.date).toBe('2024-01-15');
      expect(result.total_papers).toBe(50);
    });
  });

  describe('fetchTrendData', () => {
    const mockTrend: TrendData = {
      cluster_name: 'LLM',
      color: '#FF6B6B',
      data_points: [
        { date: '2024-01-01', count: 5, cumulative: 5 },
        { date: '2024-01-02', count: 7, cumulative: 12 },
      ],
    };

    it('should fetch trend data for cluster', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrend,
      });

      const result = await fetchTrendData('LLM', '2024-01-01', '2024-01-14');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/trends/LLM')
      );
      expect(result.cluster_name).toBe('LLM');
      expect(result.data_points).toHaveLength(2);
    });

    it('should encode cluster names with special characters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrend,
      });

      await fetchTrendData('LLM / Foundation Models', '2024-01-01', '2024-01-14');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('LLM%20%2F%20Foundation%20Models')
      );
    });
  });
});

describe('Type Guards', () => {
  it('EmergingTopic should have correct signal_type values', () => {
    const validTypes: EmergingTopic['signal_type'][] = [
      'new_cluster',
      'rapid_growth',
      'upvote_surge',
      'keyword_emergence',
    ];

    validTypes.forEach((type) => {
      const topic: EmergingTopic = {
        name: 'Test',
        signal_type: type,
        confidence: 0.5,
        evidence: 'Test',
        first_seen: null,
        growth_rate: null,
        related_clusters: [],
        sample_paper_ids: [],
      };
      expect(topic.signal_type).toBe(type);
    });
  });

  it('TrendSignal should have correct trend_direction values', () => {
    const validDirections: TrendSignal['trend_direction'][] = [
      'rising',
      'falling',
      'stable',
    ];

    validDirections.forEach((direction) => {
      const signal: TrendSignal = {
        cluster_name: 'Test',
        signal_strength: 0.5,
        trend_direction: direction,
        weekly_change: 0,
        monthly_change: 0,
        current_count: 5,
        previous_count: 5,
      };
      expect(signal.trend_direction).toBe(direction);
    });
  });
});
