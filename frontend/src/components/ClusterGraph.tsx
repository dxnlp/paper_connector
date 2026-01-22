import { useRef, useState, useMemo, useEffect, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { forceCollide, forceX, forceY } from 'd3-force';
import type { ClusterGraphData, ClusterNode } from '../api';

interface ClusterGraphProps {
  graphData: ClusterGraphData;
  onNodeClick: (node: ClusterNode) => void;
  onNodeHover?: (node: ClusterNode | null) => void;
  selectedNodeId?: string | null;
  width?: number;
  height?: number;
}

// Extended node type for force graph
interface GraphNode {
  id: string;
  name: string;
  paperCount: number;
  topTaskTags: string[];
  topModalities: string[];
  paperIds: string[];
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

// Extended link type
interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  sharedCount: number;
  sharedPaperIds: string[];
}

// Color palette for clusters
const clusterColors: Record<string, string> = {
  'benchmark-evaluation': '#3B82F6',
  'dataset-data-curation': '#22C55E',
  'architecture-model-design': '#A855F7',
  'training-recipe-scaling-distillation': '#F97316',
  'post-training-alignment': '#EC4899',
  'reasoning-test-time-compute': '#EAB308',
  'agents-tool-use-workflow': '#06B6D4',
  'multimodal-method': '#6366F1',
  'rag-retrieval-memory': '#14B8A6',
  'safety-robustness-interpretability': '#EF4444',
  'systems-efficiency': '#10B981',
  'survey-tutorial': '#F59E0B',
  'technical-report-model-release': '#8B5CF6',
  'theory-analysis': '#F43F5E',
  'other': '#6B7280',
};

const getNodeColor = (nodeId: string): string => {
  return clusterColors[nodeId] || clusterColors['other'];
};

export function ClusterGraph({
  graphData,
  onNodeClick,
  onNodeHover,
  selectedNodeId,
}: ClusterGraphProps) {
  const fgRef = useRef<any>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Toggle fullscreen mode
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => {
        setIsFullscreen(true);
      }).catch((err) => {
        console.error('Error entering fullscreen:', err);
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      }).catch((err) => {
        console.error('Error exiting fullscreen:', err);
      });
    }
  }, []);

  // Listen for fullscreen changes (e.g., user presses Escape)
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Transform data for force graph
  const transformedData = useMemo(() => {
    const nodes: GraphNode[] = graphData.nodes.map((node) => ({
      ...node,
      id: node.id,
    }));

    const links: GraphLink[] = graphData.links.map((link) => ({
      ...link,
      source: link.source,
      target: link.target,
    }));

    return { nodes, links };
  }, [graphData]);

  // Calculate max paper count for scaling
  const maxPaperCount = useMemo(() => {
    return Math.max(...graphData.nodes.map((n) => n.paperCount), 1);
  }, [graphData]);

  // Calculate max link strength for scaling
  const maxLinkStrength = useMemo(() => {
    return Math.max(...graphData.links.map((l) => l.sharedCount), 1);
  }, [graphData]);

  // Handle container resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Node size based on paper count with hover/selection scaling
  const getNodeSize = useCallback(
    (node: GraphNode): number => {
      const baseSize = 12 + (node.paperCount / maxPaperCount) * 28;
      const isHovered = hoveredNode === node.id;
      const isSelected = selectedNodeId === node.id;
      const isOtherHovered = hoveredNode !== null && hoveredNode !== node.id;

      if (isHovered || isSelected) {
        return baseSize * 1.4; // Enlarge hovered/selected
      } else if (isOtherHovered) {
        return baseSize * 0.75; // Shrink others when one is hovered
      }
      return baseSize;
    },
    [hoveredNode, selectedNodeId, maxPaperCount]
  );

  // Link width based on shared count
  const getLinkWidth = useCallback(
    (link: GraphLink): number => {
      const baseWidth = 1 + (link.sharedCount / maxLinkStrength) * 5;
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      
      if (hoveredNode === sourceId || hoveredNode === targetId) {
        return baseWidth * 2;
      }
      return baseWidth;
    },
    [hoveredNode, maxLinkStrength]
  );

  // Link color with hover highlight
  const getLinkColor = useCallback(
    (link: GraphLink): string => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      
      if (hoveredNode === sourceId || hoveredNode === targetId) {
        return 'rgba(255, 210, 30, 0.8)'; // HF yellow
      }
      return 'rgba(100, 100, 120, 0.3)';
    },
    [hoveredNode]
  );

  // Node canvas renderer for custom appearance
  const nodeCanvasObject = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const size = getNodeSize(node);
      const isHovered = hoveredNode === node.id;
      const isSelected = selectedNodeId === node.id;
      const color = getNodeColor(node.id);
      const x = node.x || 0;
      const y = node.y || 0;

      // Glow effect for hovered/selected
      if (isHovered || isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, size + 8, 0, 2 * Math.PI);
        const gradient = ctx.createRadialGradient(x, y, size, x, y, size + 15);
        gradient.addColorStop(0, `${color}66`);
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      // Main circle
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Border
      ctx.strokeStyle = isHovered || isSelected ? '#FFD21E' : 'rgba(255,255,255,0.3)';
      ctx.lineWidth = isHovered || isSelected ? 3 : 1;
      ctx.stroke();

      // Paper count label
      const fontSize = Math.max(10, size / 2.5);
      ctx.font = `bold ${fontSize}px Sans-Serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#fff';
      ctx.fillText(node.paperCount.toString(), x, y);

      // Cluster name label (only when zoomed in enough or hovered)
      if (globalScale > 0.8 || isHovered || isSelected) {
        const labelFontSize = Math.max(8, 10 / globalScale);
        ctx.font = `${labelFontSize}px Sans-Serif`;
        ctx.fillStyle = isHovered || isSelected ? '#FFD21E' : 'rgba(255,255,255,0.8)';
        
        // Truncate name if too long
        let name = node.name;
        if (name.length > 20) {
          name = name.substring(0, 18) + '...';
        }
        ctx.fillText(name, x, y + size + labelFontSize + 2);
      }
    },
    [hoveredNode, selectedNodeId, getNodeSize]
  );

  // Handle node hover
  const handleNodeHover = useCallback(
    (node: GraphNode | null) => {
      setHoveredNode(node?.id || null);
      if (onNodeHover && node) {
        onNodeHover({
          id: node.id,
          name: node.name,
          paperCount: node.paperCount,
          topTaskTags: node.topTaskTags,
          topModalities: node.topModalities,
          paperIds: node.paperIds,
        });
      } else if (onNodeHover) {
        onNodeHover(null);
      }
      
      // Change cursor
      if (containerRef.current) {
        containerRef.current.style.cursor = node ? 'pointer' : 'grab';
      }
    },
    [onNodeHover]
  );

  // Handle node click
  const handleNodeClick = useCallback(
    (node: GraphNode) => {
      onNodeClick({
        id: node.id,
        name: node.name,
        paperCount: node.paperCount,
        topTaskTags: node.topTaskTags,
        topModalities: node.topModalities,
        paperIds: node.paperIds,
      });
    },
    [onNodeClick]
  );

  // Zoom to fit on initial load
  useEffect(() => {
    if (fgRef.current && transformedData.nodes.length > 0) {
      setTimeout(() => {
        fgRef.current?.zoomToFit(400, 80);
      }, 500);
    }
  }, [transformedData]);

  // Identify isolated nodes (nodes with no connections)
  const isolatedNodeIds = useMemo(() => {
    const connectedIds = new Set<string>();
    graphData.links.forEach((link) => {
      connectedIds.add(link.source);
      connectedIds.add(link.target);
    });
    return new Set(graphData.nodes.filter((n) => !connectedIds.has(n.id)).map((n) => n.id));
  }, [graphData]);

  // Apply collision force after graph initializes
  useEffect(() => {
    if (fgRef.current && transformedData.nodes.length > 0) {
      const fg = fgRef.current;
      
      // Configure forces through ref API
      setTimeout(() => {
        // Stronger repulsion between nodes
        fg.d3Force?.('charge')?.strength(-600);
        // Longer link distance
        fg.d3Force?.('link')?.distance(180);
        // Add collision force to prevent overlap
        fg.d3Force?.('collision', 
          forceCollide((node: any) => {
            const baseSize = 12 + ((node.paperCount || 1) / maxPaperCount) * 28;
            return baseSize + 40; // Add padding around nodes
          })
        );
        
        // Add centering forces that pull isolated nodes closer to center
        // Isolated nodes get stronger centering force to stay near the main cluster
        fg.d3Force?.('x',
          forceX(dimensions.width / 2).strength((node: any) => {
            return isolatedNodeIds.has(node.id) ? 0.15 : 0.02;
          })
        );
        fg.d3Force?.('y',
          forceY(dimensions.height / 2).strength((node: any) => {
            return isolatedNodeIds.has(node.id) ? 0.15 : 0.02;
          })
        );
        
        // Reheat simulation to apply new forces
        fg.d3ReheatSimulation?.();
      }, 200);
    }
  }, [transformedData, maxPaperCount, dimensions, isolatedNodeIds]);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[500px] bg-[#0a0a1a] rounded-xl overflow-hidden"
      style={{ cursor: 'grab' }}
    >
      {/* Legend */}
      <div className="absolute top-4 left-4 z-10 bg-black/50 backdrop-blur-sm rounded-lg p-3 max-h-[300px] overflow-y-auto">
        <h4 className="text-xs text-gray-400 mb-2 font-medium">Clusters</h4>
        <div className="space-y-1">
          {graphData.nodes.slice(0, 10).map((node) => (
            <div
              key={node.id}
              className="flex items-center gap-2 text-xs cursor-pointer hover:bg-white/10 rounded px-1 py-0.5 transition-colors"
              onClick={() => handleNodeClick(node as unknown as GraphNode)}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
            >
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: getNodeColor(node.id) }}
              />
              <span className="text-gray-300 truncate max-w-[150px]">{node.name}</span>
              <span className="text-gray-500 ml-auto">{node.paperCount}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Controls hint */}
      <div className="absolute bottom-4 left-4 z-10 text-xs text-gray-500">
        Scroll to zoom • Drag to pan • Click node to view papers
      </div>

      {/* Fullscreen toggle button */}
      <button
        onClick={toggleFullscreen}
        className="absolute bottom-4 right-4 z-10 bg-black/50 hover:bg-black/70 backdrop-blur-sm rounded-lg p-2 text-gray-300 hover:text-white transition-all duration-200 group"
        title={isFullscreen ? 'Exit fullscreen (Esc)' : 'Enter fullscreen'}
      >
        {isFullscreen ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
          </svg>
        )}
        <span className="absolute bottom-full right-0 mb-2 px-2 py-1 text-xs bg-black/80 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          {isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        </span>
      </button>

      {/* Hovered node info */}
      {hoveredNode && (
        <div className="absolute top-4 right-4 z-10 bg-black/70 backdrop-blur-sm rounded-lg p-3 max-w-[250px]">
          {graphData.nodes
            .filter((n) => n.id === hoveredNode)
            .map((node) => (
              <div key={node.id}>
                <h4 className="text-white font-medium text-sm mb-1">{node.name}</h4>
                <p className="text-hf-yellow text-lg font-bold">{node.paperCount} papers</p>
                {node.topTaskTags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {node.topTaskTags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 bg-gray-700/50 rounded text-xs text-gray-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
        </div>
      )}

      <ForceGraph2D
        ref={fgRef}
        graphData={transformedData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="transparent"
        // Node settings
        nodeCanvasObject={nodeCanvasObject}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const size = getNodeSize(node);
          ctx.beginPath();
          ctx.arc(node.x || 0, node.y || 0, size + 5, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        onNodeClick={handleNodeClick as any}
        onNodeHover={handleNodeHover as any}
        // Link settings
        linkWidth={getLinkWidth as any}
        linkColor={getLinkColor as any}
        linkCurvature={0.25}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={(link: any) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
          const targetId = typeof link.target === 'object' ? link.target.id : link.target;
          return hoveredNode === sourceId || hoveredNode === targetId ? 4 : 0;
        }}
        linkDirectionalParticleColor={() => '#FFD21E'}
        // Physics settings - spread nodes apart more
        d3AlphaDecay={0.01}
        d3VelocityDecay={0.2}
        cooldownTime={5000}
        warmupTicks={100}
        // Interaction
        enableZoomInteraction={true}
        enablePanInteraction={true}
        enableNodeDrag={true}
        minZoom={0.2}
        maxZoom={8}
      />
    </div>
  );
}

export default ClusterGraph;
