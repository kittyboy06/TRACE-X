import React, { useState, useEffect } from 'react';
import { ChevronUp, ChevronDown, Database, Hash, Link2, Clock, Copy, Check, Fingerprint, Shield } from 'lucide-react';
import { ExtractedEntityRecord } from '../../types';

interface EvidenceDrawerProps {
  artifacts: any[];
  entities?: ExtractedEntityRecord[];
  selectedEvidenceId?: string;
  selectedEntityId?: string;
  onSelectEvidence?: (evidenceId: string) => void;
  onSelectEntity?: (entityId: string) => void;
  realWorldIdentity?: string;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  artifacts,
  entities = [],
  selectedEvidenceId,
  selectedEntityId,
  onSelectEvidence,
  onSelectEntity,
  realWorldIdentity = 'NOT ESTABLISHED'
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'artifacts' | 'indicators'>('artifacts');
  const [copiedHash, setCopiedHash] = useState(false);

  // Auto-expand drawer when external selection occurs
  useEffect(() => {
    if (selectedEvidenceId || selectedEntityId) {
      setIsOpen(true);
    }
  }, [selectedEvidenceId, selectedEntityId]);

  const activeArtifact = artifacts.find(a => a.evidence_id === selectedEvidenceId) || artifacts[0];

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="border-t border-slate-800 bg-slate-900 shadow-2xl transition-all duration-300 select-none">
      {/* Drawer Header Bar */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-slate-800/60 font-mono text-xs"
      >
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-cyan-400 font-semibold">
            <Database className="w-3.5 h-3.5" />
            <span className="uppercase tracking-wider">
              EVIDENCE & PROVENANCE INSPECTOR ({artifacts.length} ARTIFACTS / {entities.length} EXTRACTED INDICATORS)
            </span>
          </div>

          {activeArtifact && (
            <div className="hidden md:flex items-center space-x-2 text-slate-400">
              <span>|</span>
              <span>Active: <strong className="text-cyan-300">{activeArtifact.evidence_id}</strong> ({activeArtifact.artifact_type})</span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-3 text-slate-400 text-[11px]">
          <span className="text-amber-400 font-semibold hidden lg:inline">
            {realWorldIdentity || 'REAL-WORLD IDENTITY: NOT ESTABLISHED'}
          </span>
          <span>{isOpen ? 'Collapse Drawer' : 'Expand Details'}</span>
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </div>
      </div>

      {/* Expanded Drawer Content */}
      {isOpen && (
        <div className="p-3 bg-slate-950 border-t border-slate-800/80 max-h-72 overflow-y-auto font-mono text-xs space-y-3">
          {/* Sub-tab navigation */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <button
                onClick={(e) => { e.stopPropagation(); setActiveTab('artifacts'); }}
                className={`px-3 py-1 rounded text-xs transition ${
                  activeTab === 'artifacts'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Artifacts Repository ({artifacts.length})
              </button>

              <button
                onClick={(e) => { e.stopPropagation(); setActiveTab('indicators'); }}
                className={`px-3 py-1 rounded text-xs transition ${
                  activeTab === 'indicators'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Extracted Technical Indicators ({entities.length})
              </button>
            </div>

            <div className="text-[10px] text-slate-500 font-sans hidden sm:block">
              Bidirectional Graph $\leftrightarrow$ Evidence Drilldown Active
            </div>
          </div>

          {activeTab === 'artifacts' ? (
            <div className="space-y-3">
              {/* Horizontal Artifact Selector Strip */}
              <div className="flex items-center space-x-1.5 overflow-x-auto pb-1">
                {artifacts.map((art) => {
                  const isSelected = art.evidence_id === activeArtifact?.evidence_id;
                  return (
                    <button
                      key={art.evidence_id}
                      onClick={() => onSelectEvidence && onSelectEvidence(art.evidence_id)}
                      className={`px-2.5 py-1 rounded border text-[10px] whitespace-nowrap transition ${
                        isSelected
                          ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-bold'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {art.evidence_id} ({art.artifact_type})
                    </button>
                  );
                })}
              </div>

              {activeArtifact && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {/* Artifact Metadata */}
                  <div className="bg-slate-900 border border-slate-800 rounded p-3 space-y-1.5">
                    <div className="text-cyan-400 font-bold text-[11px] uppercase border-b border-slate-800 pb-1">
                      Artifact Metadata
                    </div>
                    <div className="space-y-1 text-[11px]">
                      <div><span className="text-slate-500">Evidence ID:</span> <span className="text-slate-200">{activeArtifact.evidence_id}</span></div>
                      <div><span className="text-slate-500">Type:</span> <span className="text-slate-200">{activeArtifact.artifact_type}</span></div>
                      <div><span className="text-slate-500">Collected:</span> <span className="text-slate-200">{activeArtifact.collected_at}</span></div>
                      <div className="truncate"><span className="text-slate-500">Source:</span> <span className="text-slate-200">{activeArtifact.source_uri}</span></div>
                    </div>
                  </div>

                  {/* Cryptographic Hash & Lineage */}
                  <div className="bg-slate-900 border border-slate-800 rounded p-3 space-y-1.5">
                    <div className="text-emerald-400 font-bold text-[11px] uppercase border-b border-slate-800 pb-1 flex items-center justify-between">
                      <span>Cryptographic Integrity</span>
                      <button
                        onClick={() => handleCopyHash(activeArtifact.content_hash || 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')}
                        className="text-[10px] text-slate-400 hover:text-cyan-400 flex items-center space-x-1"
                      >
                        {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedHash ? 'Copied' : 'Copy Hash'}</span>
                      </button>
                    </div>

                    <div className="space-y-1 text-[11px]">
                      <div className="bg-slate-950 p-1.5 rounded border border-slate-800 text-[10px] text-emerald-300 break-all font-mono">
                        SHA-256: {activeArtifact.content_hash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
                      </div>
                      <div><span className="text-slate-500">Extractor:</span> <span className="text-slate-200">{activeArtifact.extractor_version || 'v1.4.0'}</span></div>
                      <div><span className="text-slate-500">Model:</span> <span className="text-slate-200">{activeArtifact.model_version || 'sentence-transformers/all-mpnet-base-v2'}</span></div>
                      <div><span className="text-slate-500">Provenance:</span> <span className="text-cyan-400">RAW_INGEST → NORMALIZED → EMBEDDED</span></div>
                    </div>
                  </div>

                  {/* Raw Payload */}
                  <div className="bg-slate-900 border border-slate-800 rounded p-3 space-y-1.5">
                    <div className="text-purple-400 font-bold text-[11px] uppercase border-b border-slate-800 pb-1">
                      Raw Artifact Payload
                    </div>
                    <pre className="bg-slate-950 p-2 rounded border border-slate-800 text-[10px] text-slate-300 max-h-24 overflow-y-auto font-mono">
                      {JSON.stringify(activeArtifact.raw_payload, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Indicators Tab */
            <div className="space-y-2">
              <div className="text-[11px] text-slate-400">
                Click any indicator to focus and center its node in the Cytoscape graph:
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {entities.map((ent) => {
                  const isSelected = ent.entity_id === selectedEntityId;
                  return (
                    <div
                      key={ent.entity_id}
                      onClick={() => onSelectEntity && onSelectEntity(ent.entity_id)}
                      className={`p-2.5 rounded border cursor-pointer transition ${
                        isSelected
                          ? 'bg-purple-500/20 border-purple-400 shadow-sm'
                          : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] bg-slate-950 px-1.5 py-0.5 rounded text-purple-300 border border-purple-500/30">
                          {ent.entity_type}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          Conf: {Math.round(ent.confidence * 100)}%
                        </span>
                      </div>
                      <div className="text-slate-200 font-bold text-[11px] truncate" title={ent.value}>
                        {ent.value}
                      </div>
                      <div className="text-[9px] text-slate-500 pt-1 flex justify-between">
                        <span>ID: {ent.entity_id}</span>
                        <span>Evidence: {ent.evidence_id}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
