import React, { useState } from 'react';
import { ChevronUp, ChevronDown, Database, Hash, Link2, Clock, Code2, Copy, Check } from 'lucide-react';

interface EvidenceDrawerProps {
  artifacts: any[];
  selectedEvidenceId?: string;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  artifacts,
  selectedEvidenceId
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  const selectedArtifact = artifacts.find(a => a.evidence_id === selectedEvidenceId) || artifacts[0];

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="border-t border-slate-800 bg-slate-900 shadow-2xl transition-all duration-300">
      {/* Header Bar */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-slate-800/60 font-mono text-xs select-none"
      >
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-cyan-400">
            <Database className="w-3.5 h-3.5" />
            <span className="font-semibold uppercase tracking-wider">
              EVIDENCE & PROVENANCE INSPECTOR ({artifacts.length} ARTIFACTS IN CUSTODY)
            </span>
          </div>

          {selectedArtifact && (
            <div className="hidden md:flex items-center space-x-2 text-slate-400">
              <span>|</span>
              <span>Active: <strong className="text-slate-200">{selectedArtifact.evidence_id}</strong> ({selectedArtifact.artifact_type})</span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2 text-slate-400 text-[11px]">
          <span>{isOpen ? 'Collapse Drawer' : 'Expand Details'}</span>
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </div>
      </div>

      {/* Expanded Content */}
      {isOpen && selectedArtifact && (
        <div className="p-4 bg-slate-950 border-t border-slate-800/80 max-h-64 overflow-y-auto font-mono text-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Metadata Card */}
            <div className="bg-slate-900 border border-slate-800 rounded p-3 space-y-2">
              <div className="text-cyan-400 font-bold text-xs uppercase border-b border-slate-800 pb-1">
                Artifact Metadata
              </div>
              <div className="space-y-1 text-[11px]">
                <div><span className="text-slate-500">Evidence ID:</span> <span className="text-slate-200">{selectedArtifact.evidence_id}</span></div>
                <div><span className="text-slate-500">Type:</span> <span className="text-slate-200">{selectedArtifact.artifact_type}</span></div>
                <div><span className="text-slate-500">Collected:</span> <span className="text-slate-200">{selectedArtifact.collected_at}</span></div>
                <div className="truncate"><span className="text-slate-500">Source:</span> <span className="text-slate-200">{selectedArtifact.source_uri}</span></div>
              </div>
            </div>

            {/* Cryptographic Integrity & Lineage */}
            <div className="bg-slate-900 border border-slate-800 rounded p-3 space-y-2">
              <div className="text-emerald-400 font-bold text-xs uppercase border-b border-slate-800 pb-1 flex items-center justify-between">
                <span>Cryptographic Integrity</span>
                <button
                  onClick={() => handleCopyHash(selectedArtifact.content_hash || 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')}
                  className="text-[10px] text-slate-400 hover:text-cyan-400 flex items-center space-x-1"
                >
                  {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedHash ? 'Copied' : 'Copy Hash'}</span>
                </button>
              </div>

              <div className="space-y-1 text-[11px]">
                <div className="bg-slate-950 p-1.5 rounded border border-slate-800 text-[10px] text-emerald-300 break-all">
                  SHA-256: {selectedArtifact.content_hash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
                </div>
                <div><span className="text-slate-500">Extractor:</span> <span className="text-slate-200">{selectedArtifact.extractor_version || 'v1.4.0'}</span></div>
                <div><span className="text-slate-500">Model:</span> <span className="text-slate-200">{selectedArtifact.model_version || 'all-mpnet-base-v2'}</span></div>
                <div><span className="text-slate-500">Lineage:</span> <span className="text-cyan-400">RAW_INGEST → NORMALIZED → EMBEDDED</span></div>
              </div>
            </div>

            {/* Raw Payload JSON */}
            <div className="bg-slate-900 border border-slate-800 rounded p-3 space-y-2">
              <div className="text-purple-400 font-bold text-xs uppercase border-b border-slate-800 pb-1">
                Raw Artifact Payload
              </div>
              <pre className="bg-slate-950 p-2 rounded border border-slate-800 text-[10px] text-slate-300 max-h-28 overflow-y-auto font-mono">
                {JSON.stringify(selectedArtifact.raw_payload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
