import React from 'react';
import { EvidenceDimensionsBlock } from '../../types';
import { Key, DollarSign, Type, Server, Clock } from 'lucide-react';

interface EvidenceRadarProps {
  dimensions: EvidenceDimensionsBlock;
}

export const EvidenceRadar: React.FC<EvidenceRadarProps> = ({ dimensions }) => {
  const items = [
    {
      key: 'cryptographic',
      label: 'CRYPTOGRAPHIC',
      sub: 'PGP / Key Reuse',
      icon: <Key className="w-3.5 h-3.5 text-cyan-400" />,
      signal: dimensions.cryptographic,
      color: 'bg-cyan-500'
    },
    {
      key: 'financial',
      label: 'FINANCIAL',
      sub: 'UTXO / CIOH Cluster',
      icon: <DollarSign className="w-3.5 h-3.5 text-emerald-400" />,
      signal: dimensions.financial,
      color: 'bg-emerald-500'
    },
    {
      key: 'stylometric',
      label: 'STYLOMETRIC',
      sub: 'NLP Embeddings',
      icon: <Type className="w-3.5 h-3.5 text-purple-400" />,
      signal: dimensions.stylometric,
      color: 'bg-purple-500'
    },
    {
      key: 'infrastructure',
      label: 'INFRASTRUCTURE',
      sub: 'TLS / SSH Banners',
      icon: <Server className="w-3.5 h-3.5 text-blue-400" />,
      signal: dimensions.infrastructure,
      color: 'bg-blue-500'
    },
    {
      key: 'behavioral_temporal',
      label: 'BEHAVIORAL',
      sub: 'Migration & Windows',
      icon: <Clock className="w-3.5 h-3.5 text-amber-400" />,
      signal: dimensions.behavioral_temporal,
      color: 'bg-amber-500'
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 shadow-sm">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
          5-DIMENSION EVIDENCE RADAR
        </span>
        <span className="text-[10px] font-mono text-slate-500">
          RAW → ADJ → CONTRIBUTION
        </span>
      </div>

      <div className="space-y-2.5">
        {items.map(({ key, label, sub, icon, signal, color }) => {
          const isReliabilityDampened = signal.reliability_factor < 1.0;
          const isNotEnough = signal.status === 'NOT_ENOUGH_EVIDENCE';

          return (
            <div key={key} className="bg-slate-950/70 border border-slate-800/80 rounded p-2 text-xs">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-1.5">
                  {icon}
                  <span className="font-mono font-semibold text-slate-200 text-[11px]">{label}</span>
                  <span className="text-[10px] text-slate-500 font-sans">({sub})</span>
                  {isReliabilityDampened && (
                    <span className="text-[9px] bg-amber-500/10 text-amber-400 border border-amber-500/30 px-1 rounded font-mono">
                      ⚠ Dampened ({Math.round((1 - signal.reliability_factor) * 100)}%)
                    </span>
                  )}
                </div>

                <div className="font-mono text-right flex items-center space-x-2">
                  <span className="text-slate-400 text-[11px]">
                    {isNotEnough ? 'N/A' : signal.adjusted_score.toFixed(2)}
                  </span>
                  <span className="text-slate-600">×</span>
                  <span className="text-slate-500 text-[10px]">
                    {Math.round(signal.configured_weight * 100)}%
                  </span>
                  <span className="text-slate-600">=</span>
                  <span className="text-cyan-400 font-bold text-[11px]">
                    +{signal.contribution.toFixed(3)}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${color}`}
                  style={{ width: `${Math.min(100, Math.max(0, signal.adjusted_score * 100))}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
