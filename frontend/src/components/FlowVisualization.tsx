import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import type { FlowData } from '../api';

interface FlowVisualizationProps {
  flowData: FlowData;
  onClusterClick?: (clusterName: string, date: string) => void;
  height?: number;
}

interface TooltipData {
  x: number;
  y: number;
  date: string;
  cluster: string;
  count: number;
  total: number;
  color: string;
}

export function FlowVisualization({
  flowData,
  onClusterClick,
  height = 400,
}: FlowVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height });
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredCluster, setHoveredCluster] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);

  const margin = { top: 20, right: 150, bottom: 50, left: 60 };

  // Process data for stacked area chart
  const processedData = useMemo(() => {
    if (!flowData.daily_data.length) return null;

    const clusters = flowData.clusters;
    const dates = flowData.daily_data.map(d => d.date);

    // Build stacked data
    const stackedData: Array<{
      date: string;
      values: Array<{ cluster: string; y0: number; y1: number; count: number }>;
      total: number;
    }> = [];

    flowData.daily_data.forEach(day => {
      let y0 = 0;
      const values: Array<{ cluster: string; y0: number; y1: number; count: number }> = [];
      let total = 0;

      clusters.forEach(cluster => {
        const count = day.cluster_counts[cluster] || 0;
        total += count;
        values.push({
          cluster,
          y0,
          y1: y0 + count,
          count,
        });
        y0 += count;
      });

      stackedData.push({ date: day.date, values, total });
    });

    // Calculate max value for y-axis
    const maxY = Math.max(...stackedData.map(d => d.total), 1);

    return { stackedData, dates, maxY, clusters };
  }, [flowData]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [height]);

  // Scale functions
  const scales = useMemo(() => {
    if (!processedData) return null;

    const innerWidth = dimensions.width - margin.left - margin.right;
    const innerHeight = dimensions.height - margin.top - margin.bottom;

    const xScale = (date: string): number => {
      const idx = processedData.dates.indexOf(date);
      return margin.left + (idx / Math.max(processedData.dates.length - 1, 1)) * innerWidth;
    };

    const yScale = (value: number): number => {
      return margin.top + innerHeight - (value / processedData.maxY) * innerHeight;
    };

    return { xScale, yScale, innerWidth, innerHeight };
  }, [processedData, dimensions, margin]);

  // Draw the chart
  useEffect(() => {
    if (!canvasRef.current || !processedData || !scales) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size for high DPI
    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    canvas.style.width = `${dimensions.width}px`;
    canvas.style.height = `${dimensions.height}px`;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    // Background
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, dimensions.width, dimensions.height);

    // Draw grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;

    // Horizontal grid lines
    const yTicks = 5;
    for (let i = 0; i <= yTicks; i++) {
      const y = scales.yScale((processedData.maxY / yTicks) * i);
      ctx.beginPath();
      ctx.moveTo(margin.left, y);
      ctx.lineTo(dimensions.width - margin.right, y);
      ctx.stroke();
    }

    // Draw stacked areas
    const { clusters } = processedData;

    // Draw from bottom to top
    for (let i = clusters.length - 1; i >= 0; i--) {
      const cluster = clusters[i];
      const color = flowData.colors[cluster] || '#6B7280';
      const isHovered = hoveredCluster === cluster;
      const isSelected = selectedCluster === cluster;
      const isOtherHovered = hoveredCluster !== null && hoveredCluster !== cluster;

      ctx.beginPath();

      // Top line (y1 values)
      processedData.stackedData.forEach((day, idx) => {
        const x = scales.xScale(day.date);
        const y = scales.yScale(day.values[i].y1);
        if (idx === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });

      // Bottom line (y0 values) - reverse order
      for (let j = processedData.stackedData.length - 1; j >= 0; j--) {
        const day = processedData.stackedData[j];
        const x = scales.xScale(day.date);
        const y = scales.yScale(day.values[i].y0);
        ctx.lineTo(x, y);
      }

      ctx.closePath();

      // Fill with transparency based on hover state
      let alpha = 0.7;
      if (isOtherHovered) alpha = 0.3;
      if (isHovered || isSelected) alpha = 0.9;

      ctx.fillStyle = color + Math.round(alpha * 255).toString(16).padStart(2, '0');
      ctx.fill();

      // Border for hovered/selected
      if (isHovered || isSelected) {
        ctx.strokeStyle = '#FFD21E';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    // Draw axes
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;

    // Y-axis
    ctx.beginPath();
    ctx.moveTo(margin.left, margin.top);
    ctx.lineTo(margin.left, dimensions.height - margin.bottom);
    ctx.stroke();

    // X-axis
    ctx.beginPath();
    ctx.moveTo(margin.left, dimensions.height - margin.bottom);
    ctx.lineTo(dimensions.width - margin.right, dimensions.height - margin.bottom);
    ctx.stroke();

    // Y-axis labels
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    for (let i = 0; i <= yTicks; i++) {
      const value = Math.round((processedData.maxY / yTicks) * i);
      const y = scales.yScale(value);
      ctx.fillText(value.toString(), margin.left - 8, y);
    }

    // X-axis labels (show every nth date to avoid crowding)
    const dateCount = processedData.dates.length;
    const labelInterval = Math.max(1, Math.ceil(dateCount / 10));

    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    processedData.dates.forEach((date, idx) => {
      if (idx % labelInterval === 0 || idx === dateCount - 1) {
        const x = scales.xScale(date);
        // Format date as MM-DD
        const formatted = date.slice(5);
        ctx.fillText(formatted, x, dimensions.height - margin.bottom + 8);
      }
    });

    // Y-axis title
    ctx.save();
    ctx.translate(15, dimensions.height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.fillText('Papers', 0, 0);
    ctx.restore();

  }, [processedData, scales, dimensions, flowData.colors, hoveredCluster, selectedCluster, margin]);

  // Handle mouse move for tooltip
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!processedData || !scales) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if within chart area
    if (x < margin.left || x > dimensions.width - margin.right ||
        y < margin.top || y > dimensions.height - margin.bottom) {
      setTooltip(null);
      setHoveredCluster(null);
      return;
    }

    // Find closest date
    const innerWidth = dimensions.width - margin.left - margin.right;
    const relX = x - margin.left;
    const dateIdx = Math.round((relX / innerWidth) * (processedData.dates.length - 1));
    const clampedIdx = Math.max(0, Math.min(dateIdx, processedData.dates.length - 1));
    const day = processedData.stackedData[clampedIdx];

    if (!day) {
      setTooltip(null);
      setHoveredCluster(null);
      return;
    }

    // Find which cluster the mouse is over
    let foundCluster: string | null = null;
    for (const v of day.values) {
      const y0Screen = scales.yScale(v.y0);
      const y1Screen = scales.yScale(v.y1);
      if (y >= y1Screen && y <= y0Screen && v.count > 0) {
        foundCluster = v.cluster;
        break;
      }
    }

    setHoveredCluster(foundCluster);

    if (foundCluster) {
      const value = day.values.find(v => v.cluster === foundCluster);
      if (value) {
        setTooltip({
          x: e.clientX,
          y: e.clientY,
          date: day.date,
          cluster: foundCluster,
          count: value.count,
          total: day.total,
          color: flowData.colors[foundCluster] || '#6B7280',
        });
      }
    } else {
      setTooltip(null);
    }
  }, [processedData, scales, dimensions, flowData.colors, margin]);

  // Handle click
  const handleClick = useCallback(() => {
    if (hoveredCluster) {
      setSelectedCluster(prev => prev === hoveredCluster ? null : hoveredCluster);
      if (onClusterClick && tooltip) {
        onClusterClick(hoveredCluster, tooltip.date);
      }
    }
  }, [hoveredCluster, onClusterClick, tooltip]);

  if (!processedData) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No flow data available
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full" style={{ height }}>
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-crosshair"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => {
          setTooltip(null);
          setHoveredCluster(null);
        }}
        onClick={handleClick}
      />

      {/* Legend */}
      <div className="absolute top-4 right-4 bg-black/70 backdrop-blur-sm rounded-lg p-3 max-h-[300px] overflow-y-auto">
        <h4 className="text-xs text-gray-400 mb-2 font-medium">Research Areas</h4>
        <div className="space-y-1">
          {flowData.clusters.slice(0, 12).map(cluster => (
            <div
              key={cluster}
              className={`flex items-center gap-2 text-xs cursor-pointer rounded px-1 py-0.5 transition-colors ${
                hoveredCluster === cluster || selectedCluster === cluster
                  ? 'bg-white/20'
                  : 'hover:bg-white/10'
              }`}
              onMouseEnter={() => setHoveredCluster(cluster)}
              onMouseLeave={() => setHoveredCluster(null)}
              onClick={() => setSelectedCluster(prev => prev === cluster ? null : cluster)}
            >
              <div
                className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ backgroundColor: flowData.colors[cluster] || '#6B7280' }}
              />
              <span className="text-gray-300 truncate max-w-[120px]">
                {cluster.replace(/ \/ /g, '/').replace(' / ', '/')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none bg-black/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-xl border border-gray-700"
          style={{
            left: tooltip.x + 15,
            top: tooltip.y - 10,
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: tooltip.color }}
            />
            <span className="text-white font-medium text-sm">
              {tooltip.cluster}
            </span>
          </div>
          <div className="text-gray-400 text-xs">
            {tooltip.date}
          </div>
          <div className="text-hf-yellow font-bold text-lg">
            {tooltip.count} papers
          </div>
          <div className="text-gray-500 text-xs">
            {Math.round((tooltip.count / tooltip.total) * 100)}% of total
          </div>
        </div>
      )}

      {/* Controls hint */}
      <div className="absolute bottom-4 left-4 text-xs text-gray-500">
        Hover to explore • Click to select area
      </div>

      {/* Date range display */}
      <div className="absolute bottom-4 right-4 text-xs text-gray-500">
        {flowData.start_date} to {flowData.end_date}
      </div>
    </div>
  );
}

export default FlowVisualization;
