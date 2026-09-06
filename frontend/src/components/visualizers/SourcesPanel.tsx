import React, { useEffect, useState } from 'react';
import { SourceReliabilityRecord } from '../../types';
import { api } from '../../services/api';
import { ShieldCheck, RefreshCw, Clock, Link2, CheckCircle2, AlertCircle } from 'lucide-react';

interface SourcesPanelProps {
  investigationId: string;
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({ investigationId }) => {
  const [sources, setSources] = useState<SourceReliabilityRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getSourceReliability(investigationId);
      setSources(res.sources || []);
    } catch (err: any) {
      console.error('Failed to load source reliability records', err);
      setError('Unable to fetch source reliability evaluations for this investigation.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (investigationId) {
      fetchSources();
    }
  }, [investigationId]);

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'VERIFIED_GOV_FED':
        return { label: 'VERIFIED GOV / FED', bg: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/40' };
      case 'ESTABLISHED_COMMERCIAL':
        return { label: 'ESTABLISHED COMMERCIAL', bg: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/40' };
      case 'OPEN_COMMUNITY':
        return { label: 'OPEN COMMUNITY', bg: 'bg-blue-500/10 text-blue-300 border-blue-500/40' };
      case 'ADVERSARY_CONTROLLED_SUSPECTED':
        return { label: 'ADVERSARY CONTROLLED (SUSPECTED)', bg: 'bg-rose-500/10 text-rose-300 border-rose-500/40' };
      default:
        return { label: tier || 'UNVERIFIED / UNKNOWN', bg: 'bg-slate-800 text-slate-400 border-slate-700' };
    }
  };

  return (
    <div className="w-full h-full bg-slate-950 p-4 rounded-lg border border-slate-800 overflow-y-auto font-mono text-xs text-slate-300 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span className="font-bold text-slate-100 text-sm">
            EVIDENCE SOURCE RELIABILITY & TRUST TIERS (DECISION #10)
          </span>
        </div>
        <div className="flex items-center space-x-3">
          <span className="text-[11px] text-slate-400">
            Active Sources: <strong className="text-cyan-400">{sources.length}</strong>
          </span>
          <button
            onClick={fetchSources}
            disabled={isLoading}
            className="p-1 text-slate-400 hover:text-cyan-400 rounded transition"
            title="Refresh Sources"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Decision #10 Formula Header */}
      <div className="bg-slate-900 border border-slate-800 rounded p-3 text-[11px] space-y-1">
        <div className="text-cyan-400 font-bold uppercase tracking-wider text-[10px]">
          Transparent Multi-Factor Reliability Formula
        </div>
        <div className="text-slate-300 font-mono text-[10px] leading-relaxed">
          R = (0.40 × R_rep) + (0.30 × R_fresh) + (0.20 × R_corr) + (0.10 × R_cons)
        </div>
        <div className="text-slate-400 font-sans text-[11px]">
          Channel Modulation Factor = (0.50 + 0.50 × R). Clamped strictly to [0.50, 1.00] to prevent zeroing valid technical indicators.
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/40 rounded p-3 text-xs text-rose-300 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Sources List */}
      {sources.length > 0 ? (
        <div className="space-y-3">
          {sources.map((src) => {
            const tier = getTierBadge(src.trust_tier);
            const repContrib = (src.factors.reputation * 0.40);
            const freshContrib = (src.factors.freshness * 0.30);
            const corrContrib = (src.factors.corroboration * 0.20);
            const consContrib = (src.factors.consistency * 0.10);
            const rScore = src.reliability_score;
            const channelModifier = 0.5 + 0.5 * rScore;

            return (
              <div key={src.id} className="bg-slate-900 border border-slate-800 rounded-lg p-3 space-y-2.5">
                {/* Source URI & Tier */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                  <div className="flex items-center space-x-2 truncate">
                    <Link2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="text-slate-200 font-bold truncate">{src.source_uri}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${tier.bg}`}>
                      {tier.label}
                    </span>
                    <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-[10px] text-cyan-300 font-bold">
                      Class: {src.reliability_class}
                    </span>
                  </div>
                </div>

                {/* 4-Factor Weighted Contribution Table */}
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800/80 space-y-1.5 font-mono text-[11px]">
                  <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-1 border-b border-slate-800 flex justify-between">
                    <span>Factor</span>
                    <span>Raw × Weight = Contribution</span>
                  </div>

                  <div className="flex justify-between items-center text-slate-300">
                    <span>Reputation (R_rep)</span>
                    <span className="text-cyan-300">
                      {src.factors.reputation.toFixed(2)} × 0.40 = <strong className="text-cyan-400">{repContrib.toFixed(3)}</strong>
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-slate-300">
                    <span>Freshness (R_fresh)</span>
                    <span className="text-cyan-300">
                      {src.factors.freshness.toFixed(2)} × 0.30 = <strong className="text-cyan-400">{freshContrib.toFixed(3)}</strong>
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-slate-300">
                    <span>Corroboration (R_corr)</span>
                    <span className="text-cyan-300">
                      {src.factors.corroboration.toFixed(2)} × 0.20 = <strong className="text-cyan-400">{corrContrib.toFixed(3)}</strong>
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-slate-300">
                    <span>Consistency (R_cons)</span>
                    <span className="text-cyan-300">
                      {src.factors.consistency.toFixed(2)} × 0.10 = <strong className="text-cyan-400">{consContrib.toFixed(3)}</strong>
                    </span>
                  </div>

                  {/* Summary Totals */}
                  <div className="pt-1.5 border-t border-slate-800 flex justify-between items-center font-bold">
                    <span className="text-slate-200">Overall Reliability Score (R)</span>
                    <span className="text-emerald-400 text-xs">
                      = {rScore.toFixed(4)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-[10px] text-slate-400 pt-0.5">
                    <span>Channel Modulation Factor (0.50 + 0.50 × R)</span>
                    <span className="text-amber-400 font-bold">
                      {channelModifier.toFixed(4)}×
                    </span>
                  </div>
                </div>

                {/* Footer Metadata */}
                <div className="flex items-center justify-between text-[10px] text-slate-500 pt-0.5">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>Last Scan: {new Date(src.last_scan).toUTCString()}</span>
                  </div>
                  <div>
                    Diagnostic: <span className="text-slate-300">{src.diagnostic_status}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-slate-900/60 border border-slate-800 rounded p-6 text-center text-slate-500 font-sans">
          {isLoading ? 'Evaluating source trust tiers and freshness...' : 'No source reliability records evaluated yet.'}
        </div>
      )}
    </div>
  );
};
