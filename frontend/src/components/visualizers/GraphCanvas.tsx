import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { CytoscapeGraphData } from '../../types';
import { Filter, ZoomIn, ZoomOut, RefreshCw, Layers } from 'lucide-react';

import { 
  PERSONA_SVG, 
  PGP_KEY_SVG, 
  WALLET_SVG, 
  VASP_SVG, 
  FORUM_SVG, 
  FORUM_POST_SVG, 
  INFRASTRUCTURE_SVG 
} from '../../utils/graphIcons';

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
        // Base Node Style with Compact Card Labeling
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#e2e8f0',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '8.5px',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'text-background-color': '#020617',
            'text-background-opacity': 0.95,
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'text-border-color': '#334155',
            'text-border-width': 1,
            'text-max-width': '85px',
            'text-wrap': 'ellipsis',
            'background-fit': 'contain',
            'background-opacity': 0,
            'border-width': 0,
            'width': 30,
            'height': 30
          }
        },
        // 1. Persona SVG Node (Clean 38px)
        {
          selector: 'node[type = "Persona"]',
          style: {
            'background-image': PERSONA_SVG,
            'width': 38,
            'height': 38,
            'color': '#38bdf8',
            'font-weight': 'bold',
            'font-size': '9.5px',
            'text-border-color': '#0284c7',
            'text-border-width': 1.5,
            'z-index': 10
          }
        },
        // 2. PGP Key SVG Node (30px)
        {
          selector: 'node[type = "PGP_Key"]',
          style: {
            'background-image': PGP_KEY_SVG,
            'width': 30,
            'height': 30,
            'color': '#7dd3fc',
            'font-size': '8px'
          }
        },
        // 3. Crypto Wallet SVG Node (32px)
        {
          selector: 'node[type = "Wallet"]',
          style: {
            'background-image': WALLET_SVG,
            'width': 32,
            'height': 32,
            'color': '#6ee7b7',
            'font-size': '8px'
          }
        },
        // 4. VASP Exchange SVG Node (34x28px)
        {
          selector: 'node[type = "VASP"]',
          style: {
            'background-image': VASP_SVG,
            'width': 34,
            'height': 28,
            'color': '#fcd34d',
            'font-size': '8px'
          }
        },
        // 5. Forum Darknet Hub SVG Node (32px)
        {
          selector: 'node[type = "Forum"]',
          style: {
            'background-image': FORUM_SVG,
            'width': 32,
            'height': 32,
            'color': '#d8b4fe',
            'font-size': '9px',
            'font-weight': 'bold'
          }
        },
        // 6. Forum Post SVG Node (Compact 22px)
        {
          selector: 'node[type = "Forum_Post"]',
          style: {
            'background-image': FORUM_POST_SVG,
            'width': 22,
            'height': 22,
            'color': '#94a3b8',
            'font-size': '7.5px'
          }
        },
        // 7. Infrastructure SVG Node (32px)
        {
          selector: 'node[type = "Infrastructure"]',
          style: {
            'background-image': INFRASTRUCTURE_SVG,
            'width': 32,
            'height': 32,
            'color': '#fdba74',
            'font-size': '8px'
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
            'font-size': '7.5px',
            'text-rotation': 'autorotate',
            'text-background-color': '#020617',
            'text-background-opacity': 0.95,
            'text-background-padding': '2px',
            'text-background-shape': 'roundrectangle',
            'text-border-color': '#334155',
            'text-border-width': 1
          }
        },
        // Evidentiary Strength Edges
        {
          selector: 'edge[evidence_strength = "VERY_HIGH"]',
          style: {
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'width': 3,
            'line-style': 'solid'
          }
        },
        {
          selector: 'edge[evidence_strength = "CONTRADICTORY"]',
          style: {
            'line-color': '#f43f5e',
            'target-arrow-color': '#f43f5e',
            'width': 2.5,
            'line-style': 'dashed'
          }
        },
        {
          selector: 'edge[label = "LIKELY_SAME_AS"]',
          style: {
            'line-color': '#06b6d4',
            'target-arrow-color': '#06b6d4',
            'width': 3.5,
            'line-style': 'solid'
          }
        },
        {
          selector: 'edge[label = "CONFLICTS_WITH"]',
          style: {
            'line-color': '#f43f5e',
            'target-arrow-color': '#f43f5e',
            'width': 3,
            'line-style': 'dashed'
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 60,
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: () => 800000,
        idealEdgeLength: () => 220,
        edgeElasticity: () => 32,
        nestingFactor: 0.1,
        gravity: 0.1,
        numIter: 2500,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0
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
