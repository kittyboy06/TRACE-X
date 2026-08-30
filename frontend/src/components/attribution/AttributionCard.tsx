import React from 'react';
import { AttributionAssessment, AttributionState } from '../../types';
import { ShieldCheck, AlertCircle, HelpCircle, CheckCircle2, XCircle } from 'lucide-react';

interface AttributionCardProps {
  assessment: AttributionAssessment;
}

export const AttributionCard: React.FC<AttributionCardProps> = ({ assessment }) => {
  const { attribution_state, confidence_band, evidence_score, base_score, assessment_rationale } = assessment;

  const getStateBadgeConfig = (state: AttributionState) => {
    switch (state) {
      case 'CONFIRMED_LINK':
        return {
          bg: 'bg-emerald-500/10',
          border: 'border-emerald-500/40',
          text: 'text-emerald-400',
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
          label: 'CONFIRMED LINK'
        };
      case 'LIKELY_LINK':
        return {
          bg: 'bg-cyan-500/10',
          border: 'border-cyan-500/40',
          text: 'text-cyan-400',
          icon: <ShieldCheck className="w-4 h-4 text-cyan-400" />,
          label: 'LIKELY LINK'
        };
      case 'POSSIBLE_LINK':
        return {
          bg: 'bg-amber-500/10',
          border: 'border-amber-500/40',
          text: 'text-amber-400',
          icon: <AlertCircle className="w-4 h-4 text-amber-400" />,
          label: 'POSSIBLE LINK'
        };
      case 'INCONCLUSIVE':
        return {
          bg: 'bg-purple-500/10',
          border: 'border-purple-500/40',
          text: 'text-purple-400',
          icon: <HelpCircle className="w-4 h-4 text-purple-400" />,
          label: 'INCONCLUSIVE'
        };
      case 'LIKELY_DIFFERENT':
        return {
          bg: 'bg-rose-500/10',
          border: 'border-rose-500/40',
          text: 'text-rose-400',
          icon: <XCircle className="w-4 h-4 text-rose-400" />,
          label: 'LIKELY DIFFERENT'
        };
      default:
        return {
          bg: 'bg-slate-800',
          border: 'border-slate-700',
          text: 'text-slate-300',
          icon: <HelpCircle className="w-4 h-4 text-slate-400" />,
          label: state
        };
    }
  };

  const badge = getStateBadgeConfig(attribution_state);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 shadow-sm">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
          ATTRIBUTION ASSESSMENT
        </span>
        <span className="text-[10px] font-mono text-slate-500">
          ID: {assessment.assessment_id}
        </span>
      </div>

      {/* State & Score Hero */}
      <div className="flex items-center justify-between bg-slate-950 p-2.5 rounded-md border border-slate-800/80 mb-3">
        <div className="flex items-center space-x-2.5">
          <div className={`px-2.5 py-1 rounded-md border flex items-center space-x-1.5 ${badge.bg} ${badge.border}`}>
            {badge.icon}
            <span className={`text-xs font-bold font-mono tracking-wide ${badge.text}`}>
              {badge.label}
            </span>
          </div>
          <div className="text-left">
            <div className="text-[10px] font-mono text-slate-400">Confidence Band</div>
            <div className="text-xs font-semibold text-slate-200">{confidence_band}</div>
          </div>
        </div>

        <div className="text-right pl-3 border-l border-slate-800">
          <div className="text-[10px] font-mono text-slate-400">Fused Score</div>
          <div className="text-lg font-bold font-mono text-cyan-400">
            {evidence_score.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Rationale & Explainability Box */}
      <div className="bg-slate-950/60 border border-slate-800/60 rounded p-2.5 text-xs text-slate-300 leading-relaxed font-sans">
        <div className="text-[10px] font-mono text-slate-400 uppercase mb-1 font-semibold flex items-center justify-between">
          <span>Attribution Rationale</span>
          <span>{assessment_rationale.supporting_signal_count} Supporting / {assessment_rationale.contradiction_count} Anomaly</span>
        </div>
        <p>{assessment_rationale.summary}</p>
      </div>
    </div>
  );
};
