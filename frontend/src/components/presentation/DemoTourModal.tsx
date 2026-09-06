import React, { useState } from 'react';
import { X, ChevronRight, ChevronLeft, ShieldCheck, Cpu, Network, Sliders, FileText } from 'lucide-react';

interface DemoTourModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectScenario: (scenario: 'CASE_1' | 'CASE_2') => void;
}

interface PillarItem {
  id: number;
  title: string;
  badge: string;
  icon: React.ComponentType<{ className?: string }>;
  headline: string;
  description: string;
  keyPoints: string[];
  suggestedAction?: {
    label: string;
    action: () => void;
  };
}

export const DemoTourModal: React.FC<DemoTourModalProps> = ({
  isOpen,
  onClose,
  onSelectScenario
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const pillars: PillarItem[] = [
    {
      id: 1,
      title: "Pillar 1: Multi-Modal Ingestion & Source Reliability",
      badge: "Decision #10 Validated",
      icon: ShieldCheck,
      headline: "Untrusted Artifacts Dynamically Calibrated, Not Blindly Trusted",
      description: "Dark-web threat intelligence arrives from unvetted darknet forums, leak dumps, and transaction ledgers. TRACE-X never assumes equal trustworthiness.",
      keyPoints: [
        "4-Factor Formula: R = 0.40·Reputation + 0.30·Freshness + 0.20·Corroboration + 0.10·Consistency.",
        "Channel Modulation: Modulates raw evidence scores into [0.50, 1.00] range: 0.50 + 0.50·R.",
        "Earliest-Layer Security: 10 MB strict limit, 50 file entries, 25 MB uncompressed ZIP bomb defense."
      ]
    },
    {
      id: 2,
      title: "Pillar 2: Two-Level Fusion & Obfuscation Dampening",
      badge: "Anti-Hallucination Core",
      icon: Cpu,
      headline: "Level 1 Channel Dampening vs. Level 2 Global Hard Gating",
      description: "Traditional neural attribution either ignores obfuscation or lets CoinJoin poison independent vectors. TRACE-X isolates obfuscation to its originating channel.",
      keyPoints: [
        "Level 1 Channel Dampening: CoinJoin mixers (Wasabi, Samourai Whirlpool) apply a 0.60x dampener strictly to the Financial vector (0.90 -> 0.54), leaving PGP and stylometry untainted.",
        "Level 2 Global Hard Gate: Mutually exclusive operational realities (e.g. concurrent authenticated admin sessions across conflicting geos) immediately force verdict to INCONCLUSIVE.",
        "Authoritative S_base Preservation: The mathematical dot product S_base is preserved without artificial zeroing, providing forensic transparency."
      ],
      suggestedAction: {
        label: "Load Case 2 (Hard Gate Demo)",
        action: () => {
          onSelectScenario('CASE_2');
          onClose();
        }
      }
    },
    {
      id: 3,
      title: "Pillar 3: Explainable Attribution & Bi-directional Graph",
      badge: "Human-in-the-Loop",
      icon: Network,
      headline: "Attribution is an Explainable Lead, Never a Black-Box Accusation",
      description: "Every assessment displays an explicit legal disclaimer: 'REAL-WORLD IDENTITY: NOT ESTABLISHED'. Analysts can interrogate exactly why signals were connected or rejected.",
      keyPoints: [
        "Bi-directional Navigation: Clicking any graph node highlights corresponding raw evidence; clicking evidence highlights graph edges.",
        "Why Not Linked Card: Explains why personas were not linked (e.g., Level 2 Hard Gate, sub-threshold stylometry).",
        "Stylometry Guardrail: Strictly requires >= 150 words AND >= 500 tokenizer tokens. Sub-threshold samples are rejected rather than hallucinated."
      ],
      suggestedAction: {
        label: "Load Case 1 (Convergence Demo)",
        action: () => {
          onSelectScenario('CASE_1');
          onClose();
        }
      }
    },
    {
      id: 4,
      title: "Pillar 4: Sensitivity Tuner (Preview vs. Commit)",
      badge: "Cryptographic Isolation",
      icon: Sliders,
      headline: "Hypothesis Testing Without Audit Poisoning",
      description: "Threat analysts must test 'what-if' scenarios under different agency priorities. TRACE-X strictly separates exploratory simulation from legal record-keeping.",
      keyPoints: [
        "Preview Mode: 100% audit-neutral; calculates real-time sensitivity preview in memory with zero database writes.",
        "Explicit Commit: Only when the analyst clicks 'Commit Adjusted Weights' is an append-only event recorded in the tamper-evident chain.",
        "Mathematical Rigor: Automatically re-normalizes weights to ensure sum(w_i) = 1.0000 at all times."
      ]
    },
    {
      id: 5,
      title: "Pillar 5: Cryptographic Audit Trail & Forensic Dossier",
      badge: "Decision #11 & #12",
      icon: FileText,
      headline: "Tamper-Evident SHA-256 Provenance & Database-Reconstructed Reports",
      description: "To support supervisory review, all analyst actions form an append-only SHA-256 hash chain from genesis '0'*64 to terminal hash. Reports are reconstructed from DB state.",
      keyPoints: [
        "Cryptographic Audit Chain: Each event hashes previous_hash + timestamp + action + analyst_id + payload_details.",
        "Pure DB Reconstruction: Reports are generated strictly from persisted DB state, never by re-running non-deterministic pipelines.",
        "Multi-Format Dossiers: Generates official PDF (with 'Page X of Y' NumberedCanvas and NTRO banner), CSV summary, and canonical JSON."
      ]
    }
  ];

  const pillar = pillars[currentStep];
  const Icon = pillar.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-cyan-500/40 rounded-xl max-w-2xl w-full shadow-2xl shadow-cyan-950/50 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-mono font-bold tracking-wider text-cyan-400 uppercase">
                TRACE-X Five Demonstration Pillars
              </div>
              <h2 className="text-base font-bold text-white tracking-wide">
                {pillar.title}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs px-2.5 py-1 rounded-full font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-700/50">
              {pillar.badge}
            </span>
            <span className="text-xs font-mono text-slate-400">
              Step {currentStep + 1} of {pillars.length}
            </span>
          </div>

          <h3 className="text-lg font-semibold text-slate-100 leading-snug">
            {pillar.headline}
          </h3>

          <p className="text-sm text-slate-300 leading-relaxed">
            {pillar.description}
          </p>

          <div className="bg-slate-950/50 border border-slate-800 rounded-lg p-4 space-y-2.5">
            <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider font-semibold">
              Evidentiary & Architectural Rules:
            </div>
            {pillar.keyPoints.map((pt, idx) => (
              <div key={idx} className="flex items-start space-x-2 text-xs text-slate-300">
                <span className="text-cyan-500 font-mono font-bold mt-0.5">•</span>
                <span className="leading-relaxed">{pt}</span>
              </div>
            ))}
          </div>

          {pillar.suggestedAction && (
            <div className="pt-2">
              <button
                onClick={pillar.suggestedAction.action}
                className="w-full py-2.5 px-4 rounded-lg font-mono text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white transition flex items-center justify-center space-x-2 shadow-lg shadow-cyan-900/30"
              >
                <span>{pillar.suggestedAction.label}</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-slate-800 bg-slate-950/60">
          <button
            onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
            disabled={currentStep === 0}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:hover:bg-transparent transition"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <div className="flex items-center space-x-1.5">
            {pillars.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentStep(i)}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === currentStep ? 'w-6 bg-cyan-400' : 'bg-slate-700 hover:bg-slate-500'
                }`}
              />
            ))}
          </div>

          <button
            onClick={() => {
              if (currentStep < pillars.length - 1) {
                setCurrentStep(prev => prev + 1);
              } else {
                onClose();
              }
            }}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono text-cyan-300 hover:bg-cyan-950/60 border border-cyan-800/40 transition"
          >
            <span>{currentStep === pillars.length - 1 ? 'Finish Tour' : 'Next'}</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
