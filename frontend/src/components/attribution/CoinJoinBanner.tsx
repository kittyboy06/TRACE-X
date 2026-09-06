import React from 'react';
import { ChannelDampening, DimensionSignal } from '../../types';
import { ShieldAlert, Split, Layers, CheckCircle } from 'lucide-react';

interface CoinJoinBannerProps {
  dampening?: ChannelDampening;
  financialSignal?: DimensionSignal;
}

export const CoinJoinBanner: React.FC<CoinJoinBannerProps> = ({ dampening, financialSignal }) => {
  const details = financialSignal?.supporting_details || {};
  const isCoinJoin = Boolean(
    dampening?.dimension === 'financial' ||
    details.coinjoin_detected ||
    details.clustering_method?.includes('CoinJoin') ||
    financialSignal?.findings?.some(f => f.rule === 'POTENTIAL_COINJOIN_DETECTED')
  );

  if (!isCoinJoin) {
    return null;
  }

  const factor = dampening ? dampening.factor_applied : (financialSignal?.reliability_factor ?? 0.60);
  const factorPct = Math.round(factor * 100);
  const reductionPct = Math.round((1 - factor) * 100);

  return (
    <div className="bg-amber-500/10 border border-amber-500/40 rounded-lg p-3 shadow-sm text-xs font-mono space-y-2">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-amber-500/20 pb-1.5">
        <div className="flex items-center space-x-2 text-amber-300 font-bold">
          <Split className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="uppercase text-[11px] tracking-wide">
            LEVEL 1 FINANCIAL CHANNEL DAMPENING — COINJOIN ISOLATION
          </span>
        </div>
        <span className="bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded text-[10px] font-bold">
          {reductionPct}% DAMPENED ({factorPct}% RETENTION)
        </span>
      </div>

      {/* Rationale & CIOH Guard */}
      <p className="text-slate-300 font-sans text-xs leading-relaxed">
        {dampening?.reason || 'Equal-output collaborative transaction structure identified in transaction path. Common-Input-Ownership Heuristic (CIOH) clustering has been dampened to prevent cluster poisoning.'}
      </p>

      {/* Channel Isolation Invariant Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 pt-1">
        <div className="bg-slate-950/80 p-1.5 rounded border border-amber-500/40 text-center">
          <div className="text-[9px] text-slate-400">Financial</div>
          <div className="text-amber-400 font-bold text-[11px]">{factor.toFixed(2)}×</div>
          <div className="text-[9px] text-amber-300/80">DAMPENED</div>
        </div>

        <div className="bg-slate-950/80 p-1.5 rounded border border-slate-800 text-center">
          <div className="text-[9px] text-slate-400">Crypto</div>
          <div className="text-emerald-400 font-bold text-[11px]">1.00×</div>
          <div className="text-[9px] text-emerald-400/80">ISOLATED</div>
        </div>

        <div className="bg-slate-950/80 p-1.5 rounded border border-slate-800 text-center">
          <div className="text-[9px] text-slate-400">Stylometry</div>
          <div className="text-emerald-400 font-bold text-[11px]">1.00×</div>
          <div className="text-[9px] text-emerald-400/80">ISOLATED</div>
        </div>

        <div className="bg-slate-950/80 p-1.5 rounded border border-slate-800 text-center">
          <div className="text-[9px] text-slate-400">Infra</div>
          <div className="text-emerald-400 font-bold text-[11px]">1.00×</div>
          <div className="text-[9px] text-emerald-400/80">ISOLATED</div>
        </div>

        <div className="bg-slate-950/80 p-1.5 rounded border border-slate-800 text-center">
          <div className="text-[9px] text-slate-400">Behavioral</div>
          <div className="text-emerald-400 font-bold text-[11px]">1.00×</div>
          <div className="text-[9px] text-emerald-400/80">ISOLATED</div>
        </div>
      </div>

      <div className="flex items-center space-x-1.5 text-[10px] text-slate-400 pt-0.5">
        <CheckCircle className="w-3 h-3 text-emerald-400" />
        <span>Strict channel isolation invariant: Zero global score deduction applied.</span>
      </div>
    </div>
  );
};
