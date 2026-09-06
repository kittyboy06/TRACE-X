import React from 'react';
import { AttributionAssessment } from '../../types';
import { AlertOctagon, ShieldAlert, Info } from 'lucide-react';

interface WhyNotLinkedCardProps {
  assessment: AttributionAssessment;
}

export const WhyNotLinkedCard: React.FC<WhyNotLinkedCardProps> = ({ assessment }) => {
  const { hard_gate_applied, hard_gate_reason, base_score, global_contradictions, real_world_identity } = assessment;

  if (!hard_gate_applied && !global_contradictions.some(c => c.triggers_hard_gate)) {
    return null;
  }

  const hardGateContradiction = global_contradictions.find(c => c.triggers_hard_gate);
  const gateType = hardGateContradiction?.contradiction_type || 'LEVEL_2_HARD_GATE';
  const gateDetail = hard_gate_reason || hardGateContradiction?.detail || 'Operational concurrency clash detected across infrastructure endpoints.';

  return (
    <div className="bg-rose-950/30 border-2 border-rose-500/60 rounded-lg p-3.5 shadow-md text-xs font-mono space-y-2.5">
      {/* Header Banner */}
      <div className="flex items-center justify-between border-b border-rose-500/40 pb-2">
        <div className="flex items-center space-x-2 text-rose-400 font-bold tracking-wide">
          <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 animate-pulse" />
          <span className="text-xs uppercase">WHY NOT LINKED? — LEVEL 2 HARD GATE ACTIVE</span>
        </div>
        <span className="bg-rose-500/20 text-rose-300 border border-rose-500/50 px-2 py-0.5 rounded text-[10px] font-bold">
          OVERRIDE → INCONCLUSIVE
        </span>
      </div>

      {/* Paradox & Score Callout */}
      <div className="bg-slate-950/80 p-2.5 rounded border border-rose-500/30 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-[11px]">Calculated Fused Score (S_base):</span>
          <span className="text-cyan-400 font-bold text-sm">{base_score.toFixed(4)}</span>
        </div>
        <div className="text-[11px] text-slate-300 leading-relaxed font-sans">
          Although multi-channel correlation calculated an elevated numerical similarity of{' '}
          <strong className="text-cyan-300 font-mono">{base_score.toFixed(4)}</strong>, single-operator attribution is strictly blocked by a decisive operational contradiction.
        </div>
      </div>

      {/* Contradiction Telemetry & Incompatibility Explanation */}
      <div className="bg-rose-950/40 border border-rose-800/60 rounded p-2.5 space-y-1.5">
        <div className="flex items-center space-x-1.5 text-rose-300 font-semibold text-[11px]">
          <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          <span>Contradiction Rule: {gateType}</span>
        </div>
        <div className="text-slate-200 text-[11px] font-mono bg-slate-950/70 p-2 rounded border border-rose-900/60 leading-snug">
          {gateDetail}
        </div>
        <div className="text-[11px] text-slate-300 font-sans leading-relaxed pt-1">
          <strong className="text-rose-300 font-semibold">Operational Assessment:</strong> The observed session timestamps and infrastructure associations are operationally incompatible under the configured single-operator concurrency constraint.
        </div>
      </div>

      {/* Forensic Identity Disclaimer */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-rose-500/20">
        <div className="flex items-center space-x-1">
          <Info className="w-3 h-3 text-slate-500" />
          <span>Anti-False-Positive Safety Invariant Enforced</span>
        </div>
        <span className="text-amber-400/90 font-semibold uppercase">
          {real_world_identity || 'REAL-WORLD IDENTITY: NOT ESTABLISHED'}
        </span>
      </div>
    </div>
  );
};
