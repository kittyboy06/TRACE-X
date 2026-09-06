import React, { useState, useEffect } from 'react';
import { Sliders, RotateCcw, Check, Lock, AlertTriangle, Send } from 'lucide-react';
import { EvidenceDimensionsBlock, AttributionAssessment, AuditEvent } from '../../types';
import { api } from '../../services/api';

interface SensitivityTunerProps {
  investigationId: string;
  dimensions: EvidenceDimensionsBlock;
  baseScore: number;
  hardGateApplied: boolean;
  onPreviewChange: (previewAssessment: AttributionAssessment) => void;
  onCommitSuccess: (newAssessment: AttributionAssessment, auditEvent: AuditEvent) => void;
  onReset: () => void;
}

export const SensitivityTuner: React.FC<SensitivityTunerProps> = ({
  investigationId,
  dimensions,
  baseScore,
  hardGateApplied,
  onPreviewChange,
  onCommitSuccess,
  onReset
}) => {
  const [crypto, setCrypto] = useState(dimensions.cryptographic.configured_weight * 100);
  const [financial, setFinancial] = useState(dimensions.financial.configured_weight * 100);
  const [stylometry, setStylometry] = useState(dimensions.stylometric.configured_weight * 100);
  const [infra, setInfra] = useState(dimensions.infrastructure.configured_weight * 100);
  const [behavior, setBehavior] = useState(dimensions.behavioral_temporal.configured_weight * 100);

  const [isTuned, setIsTuned] = useState(false);
  const [previewScore, setPreviewScore] = useState<number | null>(null);
  const [previewState, setPreviewState] = useState<string | null>(null);
  const [showCommitPrompt, setShowCommitPrompt] = useState(false);
  const [rationale, setRationale] = useState('');
  const [isCommitting, setIsCommitting] = useState(false);
  const [lastCommittedHash, setLastCommittedHash] = useState<string | null>(null);

  useEffect(() => {
    setCrypto(dimensions.cryptographic.configured_weight * 100);
    setFinancial(dimensions.financial.configured_weight * 100);
    setStylometry(dimensions.stylometric.configured_weight * 100);
    setInfra(dimensions.infrastructure.configured_weight * 100);
    setBehavior(dimensions.behavioral_temporal.configured_weight * 100);
    setIsTuned(false);
    setPreviewScore(null);
    setPreviewState(null);
    setShowCommitPrompt(false);
    setLastCommittedHash(null);
  }, [investigationId]);

  const rawSum = crypto + financial + stylometry + infra + behavior;

  const handleSliderChange = async (type: string, val: number) => {
    let c = crypto, f = financial, s = stylometry, i = infra, b = behavior;
    if (type === 'crypto') { c = val; setCrypto(val); }
    if (type === 'financial') { f = val; setFinancial(val); }
    if (type === 'stylometry') { s = val; setStylometry(val); }
    if (type === 'infra') { i = val; setInfra(val); }
    if (type === 'behavior') { b = val; setBehavior(val); }

    setIsTuned(true);

    const sum = c + f + s + i + b;
    if (sum <= 0) return;

    try {
      const preview = await api.recalculateSensitivity({
        investigation_id: investigationId,
        weight_cryptographic: c / sum,
        weight_financial: f / sum,
        weight_stylometric: s / sum,
        weight_infrastructure: i / sum,
        weight_behavioral: b / sum
      });

      setPreviewScore(preview.base_score);
      setPreviewState(preview.attribution_state);
      onPreviewChange(preview);
    } catch (err) {
      console.error('Sensitivity preview recalculation failed', err);
    }
  };

  const handleResetClick = () => {
    setCrypto(30);
    setFinancial(25);
    setStylometry(20);
    setInfra(15);
    setBehavior(10);
    setIsTuned(false);
    setPreviewScore(null);
    setPreviewState(null);
    setShowCommitPrompt(false);
    onReset();
  };

  const handleCommitWeights = async () => {
    if (!rationale.trim()) {
      alert('Analyst rationale is mandatory to commit calibrated weights to the immutable audit ledger.');
      return;
    }

    setIsCommitting(true);
    const sum = crypto + financial + stylometry + infra + behavior;
    try {
      const res = await api.commitTunedWeights({
        investigation_id: investigationId,
        weight_cryptographic: crypto / sum,
        weight_financial: financial / sum,
        weight_stylometric: stylometry / sum,
        weight_infrastructure: infra / sum,
        weight_behavioral: behavior / sum
      });

      setLastCommittedHash(res.audit_event.event_hash);
      setIsTuned(false);
      setShowCommitPrompt(false);
      setRationale('');
      onCommitSuccess(res.assessment, res.audit_event);
    } catch (err: any) {
      console.error('Failed to commit weights', err);
      alert('Failed to commit calibrated weights to database.');
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 shadow-sm space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-1.5 text-slate-300">
          <Sliders className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-mono tracking-wider uppercase font-semibold">
            SENSITIVITY & WEIGHT TUNER
          </span>
        </div>
        <div className="flex items-center space-x-2">
          {isTuned ? (
            <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded text-[10px] font-bold font-mono animate-pulse">
              PREVIEW MODE
            </span>
          ) : (
            <span className="bg-slate-950 text-slate-400 border border-slate-800 px-2 py-0.5 rounded text-[10px] font-mono">
              COMMITTED
            </span>
          )}
          <button
            onClick={handleResetClick}
            className="flex items-center space-x-1 text-[10px] text-slate-400 hover:text-cyan-400 font-mono transition"
            title="Reset Canonical Defaults"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Dynamic Preview vs Baseline Score Delta */}
      {isTuned && previewScore !== null && (
        <div className="bg-slate-950 p-2 rounded border border-amber-500/30 text-xs font-mono space-y-1">
          <div className="flex justify-between items-center text-[11px]">
            <span className="text-slate-400">Baseline S_base:</span>
            <span className="text-slate-200">{baseScore.toFixed(4)}</span>
          </div>
          <div className="flex justify-between items-center text-[11px]">
            <span className="text-amber-300 font-semibold">Preview S_base:</span>
            <span className="text-amber-400 font-bold">{previewScore.toFixed(4)}</span>
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-400 border-t border-slate-800 pt-1">
            <span>Resulting State:</span>
            <span className="font-bold text-slate-200">{previewState}</span>
          </div>
        </div>
      )}

      {/* Hard Gate Protection Alert */}
      {hardGateApplied && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded p-2 text-xs font-mono text-rose-300 flex items-start space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-snug">
            <strong>Hard Gate Active:</strong> Weight tuning dynamically recalculates S_base, but CANNOT bypass the operational INCONCLUSIVE override.
          </div>
        </div>
      )}

      {/* Sliders Grid */}
      <div className="space-y-2 text-xs font-mono">
        <div>
          <div className="flex justify-between text-slate-300 text-[11px] mb-1">
            <span>Cryptographic (PGP)</span>
            <span className="text-cyan-400 font-bold">{Math.round(crypto)}%</span>
          </div>
          <input
            type="range" min="0" max="60" value={crypto}
            onChange={(e) => handleSliderChange('crypto', Number(e.target.value))}
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
            onChange={(e) => handleSliderChange('financial', Number(e.target.value))}
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
            onChange={(e) => handleSliderChange('stylometry', Number(e.target.value))}
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
            onChange={(e) => handleSliderChange('infra', Number(e.target.value))}
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
            onChange={(e) => handleSliderChange('behavior', Number(e.target.value))}
            className="w-full accent-amber-500 bg-slate-950 h-1.5 rounded cursor-pointer"
          />
        </div>
      </div>

      {/* Commit Weights Action */}
      {isTuned && (
        <div className="pt-2 border-t border-slate-800 space-y-2">
          {!showCommitPrompt ? (
            <button
              onClick={() => setShowCommitPrompt(true)}
              className="w-full flex items-center justify-center space-x-1.5 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 rounded text-xs font-mono font-semibold transition shadow-sm"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Commit Tuned Weights to Audit Ledger</span>
            </button>
          ) : (
            <div className="bg-slate-950 p-2.5 rounded border border-cyan-500/40 space-y-2 font-mono text-xs">
              <div className="text-cyan-300 font-bold text-[11px] flex items-center space-x-1">
                <Lock className="w-3 h-3" />
                <span>MANDATORY ANALYST RATIONALE</span>
              </div>
              <textarea
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder="Explain justification for adjusting dimension weights for this case..."
                rows={2}
                className="w-full bg-slate-900 border border-slate-800 rounded p-1.5 text-slate-200 text-[11px] placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-sans resize-none"
              />
              <div className="flex space-x-2">
                <button
                  onClick={handleCommitWeights}
                  disabled={isCommitting || !rationale.trim()}
                  className="flex-1 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded text-xs transition disabled:opacity-50"
                >
                  {isCommitting ? 'Writing Hash Chain...' : 'Confirm & Write Audit Event'}
                </button>
                <button
                  onClick={() => setShowCommitPrompt(false)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Last Committed Hash Badge */}
      {lastCommittedHash && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded p-2 text-[10px] font-mono text-emerald-300 space-y-0.5">
          <div className="flex items-center space-x-1 font-bold">
            <Check className="w-3 h-3 text-emerald-400" />
            <span>COMMITTED TO AUDIT LEDGER</span>
          </div>
          <div className="truncate text-slate-400">
            Hash: <span className="text-emerald-300">{lastCommittedHash}</span>
          </div>
        </div>
      )}
    </div>
  );
};
