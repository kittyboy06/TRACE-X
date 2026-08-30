import React from 'react';
import { DimensionSignal, GlobalContradiction } from '../../types';
import { Clock, AlertOctagon, ArrowRight, Calendar } from 'lucide-react';

interface TemporalMatrixProps {
  behavioralSignal: DimensionSignal;
  contradictions: GlobalContradiction[];
}

export const TemporalMatrix: React.FC<TemporalMatrixProps> = ({
  behavioralSignal,
  contradictions
}) => {
  const details = behavioralSignal.supporting_details || {};
  const hasClash = contradictions.some(c => c.contradiction_type === 'TEMPORAL_CONCURRENCY_CLASH');

  return (
    <div className="w-full h-full bg-slate-950 p-4 rounded-lg border border-slate-800 overflow-y-auto font-mono text-xs text-slate-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-amber-400" />
          <span className="font-bold text-slate-100 text-sm">BEHAVIORAL & TEMPORAL CONCURRENCY MATRIX</span>
        </div>
        <div className="bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-[11px] text-slate-400">
          Pattern: <strong className="text-amber-400">{details.sequence_type || 'TEMPORAL_ANALYSIS'}</strong>
        </div>
      </div>

      {/* Concurrency Clash Alert */}
      {hasClash ? (
        <div className="bg-rose-500/10 border border-rose-500/40 rounded p-3 mb-4">
          <div className="flex items-center space-x-2 text-rose-400 font-bold mb-1">
            <AlertOctagon className="w-4 h-4" />
            <span>CRITICAL CONTRADICTION: SIMULTANEOUS AUTHENTICATED ACTIVITY</span>
          </div>
          <p className="text-slate-300 font-sans text-xs leading-relaxed">
            {details.contradiction_summary || 'Both target personas conducted simultaneous administrative activities within an impossible temporal window across distinct physical endpoints.'}
          </p>
          <div className="mt-2 text-rose-300 font-mono text-[11px] bg-rose-950/60 p-2 rounded border border-rose-800/40">
            ⚡ Level 2 Hard Gate Triggered: Attribution forced to INCONCLUSIVE.
          </div>
        </div>
      ) : (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded p-3 mb-4">
          <div className="flex items-center space-x-2 text-emerald-400 font-bold mb-1">
            <Calendar className="w-4 h-4" />
            <span>CLEAN SEQUENTIAL MIGRATION OBSERVED</span>
          </div>
          <p className="text-slate-300 font-sans text-xs">
            Persona A exhibited a period of complete dormancy on Dread/Hydra preceding the sudden emergence of Persona B on Exploit Forum with consistent operating cadence.
          </p>
        </div>
      )}

      {/* Timeline Comparison View */}
      <div className="space-y-4">
        <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
          Temporal Activity Sequence
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
            <div className="text-cyan-400 font-bold mb-2">TARGET PERSONA A</div>
            <div className="space-y-2 text-[11px]">
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <div className="text-slate-500 text-[10px]">T1: Active Posting Window</div>
                <div className="text-slate-200">2026-01-10T19:40:00Z (Dread)</div>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <div className="text-slate-500 text-[10px]">T2: Last Activity / Key Signing</div>
                <div className="text-slate-200">2026-01-14T08:30:00Z</div>
              </div>
              <div className="bg-amber-500/10 text-amber-300 p-2 rounded border border-amber-500/30 text-[10px]">
                Dormancy Window: 48 Days
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
            <div className="text-purple-400 font-bold mb-2">TARGET PERSONA B</div>
            <div className="space-y-2 text-[11px]">
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <div className="text-slate-500 text-[10px]">T3: Profile Emergence & Key Registration</div>
                <div className="text-slate-200">2026-03-02T14:15:00Z (Exploit)</div>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <div className="text-slate-500 text-[10px]">T4: Initial Vendor Listing</div>
                <div className="text-slate-200">2026-03-05T11:20:00Z</div>
              </div>
              <div className="bg-cyan-500/10 text-cyan-300 p-2 rounded border border-cyan-500/30 text-[10px]">
                Cadence Alignment: 94%
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
