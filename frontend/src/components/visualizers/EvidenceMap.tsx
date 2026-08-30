import React from 'react';
import { EvidenceDimensionsBlock } from '../../types';
import { Network, CheckCircle, AlertTriangle } from 'lucide-react';

interface EvidenceMapProps {
  dimensions: EvidenceDimensionsBlock;
}

export const EvidenceMap: React.FC<EvidenceMapProps> = ({ dimensions }) => {
  const allDims = [
    { title: 'Cryptographic Channel', data: dimensions.cryptographic },
    { title: 'Financial Channel', data: dimensions.financial },
    { title: 'Stylometric Channel', data: dimensions.stylometric },
    { title: 'Infrastructure Channel', data: dimensions.infrastructure },
    { title: 'Behavioral & Temporal Channel', data: dimensions.behavioral_temporal },
  ];

  return (
    <div className="w-full h-full bg-slate-950 p-4 rounded-lg border border-slate-800 overflow-y-auto font-mono text-xs text-slate-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <Network className="w-4 h-4 text-cyan-400" />
          <span className="font-bold text-slate-100 text-sm">MULTI-MODAL EVIDENCE CORRELATION MAP</span>
        </div>
        <div className="text-[11px] text-slate-500">
          Cross-Channel Contributing Signals
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {allDims.map((dim, idx) => {
          const s = dim.data;
          const isSupporting = s.adjusted_score >= 0.50;

          return (
            <div key={idx} className="bg-slate-900 border border-slate-800 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-1.5">
                  {isSupporting ? (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  )}
                  <span className="font-bold text-slate-200 text-xs">{dim.title}</span>
                </div>
                <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-cyan-400 font-bold">
                  Score: {s.adjusted_score.toFixed(2)}
                </span>
              </div>

              <div className="space-y-1 text-[11px] text-slate-400 bg-slate-950/70 p-2 rounded border border-slate-800/60 font-sans">
                <div><strong>Weight:</strong> {Math.round(s.configured_weight * 100)}% ({s.contribution.toFixed(3)} contribution)</div>
                <div><strong>Reliability:</strong> {Math.round(s.reliability_factor * 100)}%</div>
                <div><strong>Evidence IDs:</strong> {s.evidence_ids.join(', ') || 'N/A'}</div>
                {s.supporting_details && (
                  <div className="text-[10px] text-slate-500 font-mono pt-1 truncate">
                    {JSON.stringify(s.supporting_details)}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
