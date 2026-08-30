import React, { useState } from 'react';
import { CytoscapeGraphData, AttributionAssessment } from '../../types';
import { GraphCanvas } from './GraphCanvas';
import { FinancialFlow } from './FinancialFlow';
import { TemporalMatrix } from './TemporalMatrix';
import { EvidenceMap } from './EvidenceMap';
import { Share2, DollarSign, Clock, Network } from 'lucide-react';

interface VisualizerContainerProps {
  graphData: CytoscapeGraphData;
  assessment: AttributionAssessment;
  onSelectNode?: (nodeId: string) => void;
}

export const VisualizerContainer: React.FC<VisualizerContainerProps> = ({
  graphData,
  assessment,
  onSelectNode
}) => {
  const [activeTab, setActiveTab] = useState<'graph' | 'financial' | 'temporal' | 'evidence'>('graph');

  return (
    <div className="w-full h-full flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
      {/* Visualizer Tab Bar */}
      <div className="bg-slate-950 border-b border-slate-800 px-3 py-1.5 flex items-center justify-between">
        <div className="flex items-center space-x-1 font-mono text-xs">
          <button
            onClick={() => setActiveTab('graph')}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md transition ${
              activeTab === 'graph'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>Graph Visualizer</span>
          </button>

          <button
            onClick={() => setActiveTab('financial')}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md transition ${
              activeTab === 'financial'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <DollarSign className="w-3.5 h-3.5" />
            <span>Financial Peeling Flow</span>
          </button>

          <button
            onClick={() => setActiveTab('temporal')}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md transition ${
              activeTab === 'temporal'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Temporal Matrix</span>
          </button>

          <button
            onClick={() => setActiveTab('evidence')}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md transition ${
              activeTab === 'evidence'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>Evidence Map</span>
          </button>
        </div>

        <div className="text-[11px] font-mono text-slate-500 hidden sm:block">
          Interactive Intelligence Canvas
        </div>
      </div>

      {/* Main Tab Body */}
      <div className="flex-1 p-2 bg-slate-950 overflow-hidden relative">
        {activeTab === 'graph' && (
          <GraphCanvas data={graphData} onSelectNode={onSelectNode} />
        )}
        {activeTab === 'financial' && (
          <FinancialFlow financialSignal={assessment.evidence_dimensions.financial} />
        )}
        {activeTab === 'temporal' && (
          <TemporalMatrix
            behavioralSignal={assessment.evidence_dimensions.behavioral_temporal}
            contradictions={assessment.global_contradictions}
          />
        )}
        {activeTab === 'evidence' && (
          <EvidenceMap dimensions={assessment.evidence_dimensions} />
        )}
      </div>
    </div>
  );
};
