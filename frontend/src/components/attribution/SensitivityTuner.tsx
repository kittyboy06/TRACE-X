import React, { useState, useEffect } from 'react';
import { Sliders, RotateCcw } from 'lucide-react';
import { EvidenceDimensionsBlock } from '../../types';

interface SensitivityTunerProps {
  investigationId: string;
  dimensions: EvidenceDimensionsBlock;
  onWeightsChange: (weights: {
    crypto: number;
    financial: number;
    stylometry: number;
    infra: number;
    behavior: number;
  }) => void;
  onReset: () => void;
}

export const SensitivityTuner: React.FC<SensitivityTunerProps> = ({
  investigationId,
  dimensions,
  onWeightsChange,
  onReset
}) => {
  const [crypto, setCrypto] = useState(dimensions.cryptographic.configured_weight * 100);
  const [financial, setFinancial] = useState(dimensions.financial.configured_weight * 100);
  const [stylometry, setStylometry] = useState(dimensions.stylometric.configured_weight * 100);
  const [infra, setInfra] = useState(dimensions.infrastructure.configured_weight * 100);
  const [behavior, setBehavior] = useState(dimensions.behavioral_temporal.configured_weight * 100);

  useEffect(() => {
    setCrypto(dimensions.cryptographic.configured_weight * 100);
    setFinancial(dimensions.financial.configured_weight * 100);
    setStylometry(dimensions.stylometric.configured_weight * 100);
    setInfra(dimensions.infrastructure.configured_weight * 100);
    setBehavior(dimensions.behavioral_temporal.configured_weight * 100);
  }, [dimensions]);

  const handleChange = (type: string, val: number) => {
    let c = crypto, f = financial, s = stylometry, i = infra, b = behavior;
    if (type === 'crypto') { c = val; setCrypto(val); }
    if (type === 'financial') { f = val; setFinancial(val); }
    if (type === 'stylometry') { s = val; setStylometry(val); }
    if (type === 'infra') { i = val; setInfra(val); }
    if (type === 'behavior') { b = val; setBehavior(val); }

    onWeightsChange({
      crypto: c / 100,
      financial: f / 100,
      stylometry: s / 100,
      infra: i / 100,
      behavior: b / 100
    });
  };

  const handleResetClick = () => {
    setCrypto(30);
    setFinancial(25);
    setStylometry(20);
    setInfra(15);
    setBehavior(10);
    onReset();
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 shadow-sm">
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center space-x-1.5 text-slate-300">
          <Sliders className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-mono tracking-wider uppercase font-semibold">
            SENSITIVITY & WEIGHT TUNER
          </span>
        </div>
        <button
          onClick={handleResetClick}
          className="flex items-center space-x-1 text-[10px] text-slate-400 hover:text-cyan-400 font-mono transition"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset Defaults</span>
        </button>
      </div>

      <div className="space-y-2 text-xs font-mono">
        <div>
          <div className="flex justify-between text-slate-300 text-[11px] mb-1">
            <span>Cryptographic (PGP)</span>
            <span className="text-cyan-400 font-bold">{Math.round(crypto)}%</span>
          </div>
          <input
            type="range" min="0" max="60" value={crypto}
            onChange={(e) => handleChange('crypto', Number(e.target.value))}
            className="w-full accent-cyan-500 bg-slate-950 h-1.5 rounded cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-slate-300 text-[11px] mb-1">
            <span>Financial (UTXO/CIOH)</span>
            <span className="text-emerald-400 font-bold">{Math.round(financial)}%</span>
          </div>
          <input
            type="range" min="0" max="60" value={financial}
            onChange={(e) => handleChange('financial', Number(e.target.value))}
            className="w-full accent-emerald-500 bg-slate-950 h-1.5 rounded cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-slate-300 text-[11px] mb-1">
            <span>Stylometric (NLP)</span>
            <span className="text-purple-400 font-bold">{Math.round(stylometry)}%</span>
          </div>
          <input
            type="range" min="0" max="60" value={stylometry}
            onChange={(e) => handleChange('stylometry', Number(e.target.value))}
            className="w-full accent-purple-500 bg-slate-950 h-1.5 rounded cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-slate-300 text-[11px] mb-1">
            <span>Infrastructure (TLS/Host)</span>
            <span className="text-blue-400 font-bold">{Math.round(infra)}%</span>
          </div>
          <input
            type="range" min="0" max="60" value={infra}
            onChange={(e) => handleChange('infra', Number(e.target.value))}
            className="w-full accent-blue-500 bg-slate-950 h-1.5 rounded cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-slate-300 text-[11px] mb-1">
            <span>Behavioral (Temporal)</span>
            <span className="text-amber-400 font-bold">{Math.round(behavior)}%</span>
          </div>
          <input
            type="range" min="0" max="60" value={behavior}
            onChange={(e) => handleChange('behavior', Number(e.target.value))}
            className="w-full accent-amber-500 bg-slate-950 h-1.5 rounded cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
};
