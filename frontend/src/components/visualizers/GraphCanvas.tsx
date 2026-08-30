import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { CytoscapeGraphData } from '../../types';
import { Filter, ZoomIn, ZoomOut, RefreshCw, Layers } from 'lucide-react';

interface GraphCanvasProps {
  data: CytoscapeGraphData;
  onSelectNode?: (nodeId: string) => void;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({ data, onSelectNode }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [filterCrypto, setFilterCrypto] = useState(true);
  const [filterFinancial, setFilterFinancial] = useState(true);
  const [filterPosts, setFilterPosts] = useState(true);
  const [filterInfra, setFilterInfra] = useState(true);

  useEffect(() => {
    if (!containerRef.current) return;

    // Filter elements according to active toggles
    const filteredNodes = data.nodes.filter(n => {
      const type = n.data.type;
      if (type === 'PGP_Key' && !filterCrypto) return false;
      if (type === 'Wallet' && !filterFinancial) return false;
      if (type === 'VASP' && !filterFinancial) return false;
      if (type === 'Forum_Post' && !filterPosts) return false;
      if (type === 'Forum' && !filterPosts) return false;
      if (type === 'Infrastructure' && !filterInfra) return false;
      return true;
    });

    const activeNodeIds = new Set(filteredNodes.map(n => n.data.id));

    const filteredEdges = data.edges.filter(e => {
      return activeNodeIds.has(e.data.source!) && activeNodeIds.has(e.data.target!);
    });

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...filteredNodes, ...filteredEdges],
      style: [
        // Base Node Style
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#cbd5e1',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '11px',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'background-color': '#334155',
            'border-width': 2,
            'border-color': '#64748b',
            'width': 36,
            'height': 36
          }
        },
        // Persona Node
        {
          selector: 'node[type = "Persona"]',
          style: {
            'background-color': '#06b6d4',
            'border-color': '#22d3ee',
            'border-width': 3,
            'width': 48,
            'height': 48,
            'color': '#38bdf8',
            'font-weight': 'bold',
            'font-size': '12px'
          }
        },
        // PGP Key Node
        {
          selector: 'node[type = "PGP_Key"]',
          style: {
            'background-color': '#0284c7',
            'border-color': '#38bdf8',
            'shape': 'diamond',
            'width': 38,
            'height': 38
          }
        },
        // Wallet Node
        {
          selector: 'node[type = "Wallet"]',
          style: {
            'background-color': '#059669',
            'border-color': '#34d399',
            'shape': 'hexagon',
            'width': 40,
            'height': 40
          }
        },
        // VASP Node
        {
          selector: 'node[type = "VASP"]',
          style: {
            'background-color': '#d97706',
            'border-color': '#fbbf24',
            'shape': 'round-rectangle',
            'width': 44,
            'height': 32
          }
        },
        // Forum & Post Nodes
        {
          selector: 'node[type = "Forum"]',
          style: {
            'background-color': '#7c3aed',
            'border-color': '#a78bfa',
            'shape': 'rectangle'
          }
        },
        {
          selector: 'node[type = "Forum_Post"]',
          style: {
            'background-color': '#475569',
            'border-color': '#94a3b8',
            'width': 28,
            'height': 28
          }
        },
        // Base Edge Style
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'color': '#94a3b8',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '9px',
            'text-rotation': 'autorotate',
            'text-background-color': '#090d16',
            'text-background-opacity': 0.8,
            'text-background-padding': '2px'
          }
        },
        // Evidentiary Strength Edges
        {
          selector: 'edge[evidence_strength = "VERY_HIGH"]',
          style: {
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'width': 3.5,
            'line-style': 'solid'
          }
        },
        {
          selector: 'edge[evidence_strength = "CONTRADICTORY"]',
          style: {
            'line-color': '#f43f5e',
            'target-arrow-color': '#f43f5e',
            'width': 3,
            'line-style': 'dashed'
          }
        },
        {
          selector: 'edge[label = "LIKELY_SAME_AS"]',
          style: {
            'line-color': '#06b6d4',
            'target-arrow-color': '#06b6d4',
            'width': 4,
            'line-style': 'solid'
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 40,
        nodeRepulsion: () => 4500,
        idealEdgeLength: () => 100
      }
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (onSelectNode) onSelectNode(node.id());
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [data, filterCrypto, filterFinancial, filterPosts, filterInfra]);

  const handleFit = () => {
    if (cyRef.current) cyRef.current.fit(undefined, 30);
  };

  const handleZoom = (factor: number) => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * factor);
      cyRef.current.center();
    }
  };

  return (
    <div className="relative w-full h-full bg-slate-950 rounded-lg overflow-hidden border border-slate-800 flex flex-col">
      {/* Filter Toolbar */}
      <div className="absolute top-2.5 left-2.5 z-10 bg-slate-900/90 border border-slate-800 rounded-lg p-1.5 flex items-center space-x-1.5 backdrop-blur-sm text-xs font-mono">
        <div className="flex items-center px-1 text-slate-400">
          <Filter className="w-3.5 h-3.5 mr-1" />
          <span>Filters:</span>
        </div>
        <button
          onClick={() => setFilterCrypto(!filterCrypto)}
          className={`px-2 py-0.5 rounded text-[11px] transition ${
            filterCrypto ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          PGP Keys
        </button>
        <button
          onClick={() => setFilterFinancial(!filterFinancial)}
          className={`px-2 py-0.5 rounded text-[11px] transition ${
            filterFinancial ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Wallets & VASP
        </button>
        <button
          onClick={() => setFilterPosts(!filterPosts)}
          className={`px-2 py-0.5 rounded text-[11px] transition ${
            filterPosts ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Forums & Posts
        </button>
      </div>

      {/* Zoom Controls */}
      <div className="absolute bottom-2.5 right-2.5 z-10 bg-slate-900/90 border border-slate-800 rounded-lg p-1 flex items-center space-x-1 backdrop-blur-sm">
        <button
          onClick={() => handleZoom(1.2)}
          className="p-1.5 hover:bg-slate-800 text-slate-300 rounded"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => handleZoom(0.8)}
          className="p-1.5 hover:bg-slate-800 text-slate-300 rounded"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleFit}
          className="p-1.5 hover:bg-slate-800 text-slate-300 rounded"
          title="Reset View"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Cytoscape Canvas */}
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
};
