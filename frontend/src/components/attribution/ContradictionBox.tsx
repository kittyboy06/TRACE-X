import React from 'react';
import { ChannelDampening, GlobalContradiction } from '../../types';
import { AlertOctagon, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface ContradictionBoxProps {
  dampenings: ChannelDampening[];
  contradictions: GlobalContradiction[];
}

export const ContradictionBox: React.FC<ContradictionBoxProps> = ({
  dampenings,
  contradictions
}) => {
  const hardGates = contradictions.filter(c => c.triggers_hard_gate);
  const softContras = contradictions.filter(c => !c.triggers_hard_gate);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
          CONTRADICTIONS & ANOMALIES
        </span>
        <span className="text-[10px] font-mono text-slate-500">
          TWO-LEVEL MODEL
        </span>
      </div>

      <div className="space-y-2">
        {/* Hard Gates (Level 2) */}
        {hardGates.length > 0 ? (
          hardGates.map((gate, idx) => (
            <div
              key={idx}
              className="bg-rose-500/10 border border-rose-500/40 rounded p-2 text-xs flex items-start space-x-2"
            >
              <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-rose-300 font-mono">
                  HARD GATE: {gate.contradiction_type}
                </div>
                <div className="text-slate-300 text-[11px] mt-0.5 leading-snug">
                  {gate.detail}
                </div>
                <div className="text-rose-400 font-mono text-[10px] mt-1 font-semibold">
                  ⚡ Forced State: INCONCLUSIVE (Anti-False-Positive Safety)
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="bg-slate-950/70 border border-slate-800/80 rounded p-2 text-xs flex items-center space-x-2 text-emerald-400">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="font-mono text-[11px]">✓ No global hard contradiction triggered</span>
          </div>
        )}

        {/* Level 1 Channel Dampenings */}
        {dampenings.map((damp, idx) => (
          <div
            key={idx}
            className="bg-amber-500/10 border border-amber-500/30 rounded p-2 text-xs flex items-start space-x-2"
          >
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-amber-300 font-mono text-[11px]">
                LEVEL 1: {damp.dimension.toUpperCase()} CHANNEL DAMPENING
              </div>
              <div className="text-slate-300 text-[11px] mt-0.5">
                {damp.reason}
              </div>
              <div className="text-amber-400/80 font-mono text-[10px] mt-0.5">
                Channel reliability reduced to {Math.round(damp.factor_applied * 100)}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
