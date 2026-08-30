import React from 'react';
import { DimensionSignal } from '../../types';
import { ArrowRight, DollarSign, ShieldAlert, Building2, Layers } from 'lucide-react';

interface FinancialFlowProps {
  financialSignal: DimensionSignal;
}

export const FinancialFlow: React.FC<FinancialFlowProps> = ({ financialSignal }) => {
  const details = financialSignal.supporting_details || {};
  const hops = details.hops_to_vasp || [];
  const isCoinJoin = details.coinjoin_detected;

  return (
    <div className="w-full h-full bg-slate-950 p-4 rounded-lg border border-slate-800 overflow-y-auto font-mono text-xs text-slate-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <DollarSign className="w-4 h-4 text-emerald-400" />
          <span className="font-bold text-slate-100 text-sm">BITCOIN UTXO FORENSICS & PEELING CHAIN</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-[11px] text-slate-400">
            Cluster: <strong className="text-emerald-400">{details.cluster_id || 'CIOH_DETECTED'}</strong>
          </span>
          <span className="bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-[11px] text-slate-400">
            Method: <strong className="text-cyan-400">{details.clustering_method || 'CIOH'}</strong>
          </span>
        </div>
      </div>

      {/* CoinJoin Alert Banner */}
      {isCoinJoin && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded p-3 mb-4 flex items-start space-x-3">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-amber-300">
              COLLABORATIVE TRANSACTION ANOMALY ({details.coinjoin_protocol || 'CoinJoin'})
            </div>
            <p className="text-slate-300 text-xs mt-0.5 font-sans">
              Equal-output collaborative transaction structure identified in transaction path. Financial linkage confidence has been safely dampened by {details.reliability_adjustment || '40%'} to prevent cluster poisoning.
            </p>
          </div>
        </div>
      )}

      {/* Interactive Peeling Chain Diagram */}
      <div className="space-y-4">
        <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
          Identified Transaction Hops & VASP Exits
        </div>

        {hops.length > 0 ? (
          <div className="space-y-3">
            {hops.map((hop: any, idx: number) => (
              <div key={idx} className="bg-slate-900 border border-slate-800 rounded-lg p-3 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-slate-950 px-2 py-1 rounded border border-slate-800 text-[11px] text-slate-400">
                    HOP #{idx + 1}
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-400">Source: <span className="text-slate-200">{hop.from}</span></div>
                    <div className="text-[11px] text-slate-400">Target: <span className="text-slate-200">{hop.to}</span></div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500">Volume</div>
                    <div className="text-emerald-400 font-bold">{hop.amount_btc} BTC</div>
                  </div>

                  {hop.vasp_entity && (
                    <div className="bg-amber-500/10 border border-amber-500/40 px-2.5 py-1 rounded flex items-center space-x-1.5 text-amber-300">
                      <Building2 className="w-3.5 h-3.5" />
                      <span className="font-bold text-xs">{hop.vasp_entity}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-slate-900/60 border border-slate-800 rounded p-4 text-center text-slate-400 font-sans">
            No direct clearnet VASP exit identified. Transaction path terminated at internal unhosted mixing cluster.
          </div>
        )}
      </div>
    </div>
  );
};
