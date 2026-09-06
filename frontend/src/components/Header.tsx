import React, { useState, useRef, useEffect } from 'react';
import { Shield, FileText, UploadCloud, AlertTriangle, ChevronDown, Table, Code } from 'lucide-react';

interface HeaderProps {
  investigationId: string;
  personaA: string;
  personaB: string;
  activeCase: string;
  onSelectCase: (caseId: string) => void;
  onExportPdf?: () => void;
  onExportCsv?: () => void;
  onExportJson?: () => void;
  onExport: () => void;
  onOpenUpload: () => void;
  isProcessing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  investigationId,
  personaA,
  personaB,
  activeCase,
  onSelectCase,
  onExportPdf,
  onExportCsv,
  onExportJson,
  onExport,
  onOpenUpload,
  isProcessing
}) => {
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsExportMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const triggerExportPdf = () => {
    setIsExportMenuOpen(false);
    if (onExportPdf) onExportPdf();
    else onExport();
  };

  const triggerExportCsv = () => {
    setIsExportMenuOpen(false);
    if (onExportCsv) onExportCsv();
  };

  const triggerExportJson = () => {
    setIsExportMenuOpen(false);
    if (onExportJson) onExportJson();
    else onExport();
  };
  return (
    <header className="bg-slate-900 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between shadow-md">
      {/* Brand & Active Investigation */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="bg-cyan-500/10 border border-cyan-500/30 p-1.5 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold tracking-wider text-sm bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                TRACE-X
              </span>
              <span className="text-xs bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono border border-slate-700">
                NTRO SIH26151
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono">
              Threat Relationship & Attribution Correlation Engine
            </p>
          </div>
        </div>

        <div className="h-6 w-px bg-slate-800" />

        {/* Case Target Badges */}
        <div className="flex items-center space-x-2">
          <div className="text-xs font-mono bg-slate-950 px-2.5 py-1 rounded border border-slate-800 flex items-center space-x-1.5">
            <span className="text-slate-500 font-sans font-medium">CASE:</span>
            <span className="text-cyan-400 font-semibold">{investigationId}</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-200">{personaA}</span>
            <span className="text-slate-500 font-sans">↔</span>
            <span className="text-slate-200">{personaB}</span>
          </div>
        </div>
      </div>

      {/* Permanent Identity Scope Guard */}
      <div className="hidden lg:flex items-center bg-slate-950/80 border border-amber-500/30 px-3 py-1 rounded-md text-xs font-mono text-amber-300/90 shadow-inner">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mr-1.5 shrink-0" />
        <span>LEGAL SCOPE: <strong className="text-amber-200">REAL-WORLD IDENTITY: NOT ESTABLISHED</strong> (Investigative Decision Support)</span>
      </div>

      {/* Actions & 1-Click Benchmark Picker */}
      <div className="flex items-center space-x-2.5">
        <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800">
          <button
            onClick={() => onSelectCase('1')}
            disabled={isProcessing}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
              activeCase === '1'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            Case 1: Convergence
          </button>
          <button
            onClick={() => onSelectCase('2')}
            disabled={isProcessing}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
              activeCase === '2'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            Case 2: Contradiction
          </button>
        </div>

        <button
          onClick={onOpenUpload}
          className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md text-xs border border-slate-700 transition"
          title="Upload Custom Evidence Package"
        >
          <UploadCloud className="w-3.5 h-3.5 text-slate-300" />
          <span>Upload</span>
        </button>

        {/* Multi-Format Dossier Export Split Button */}
        <div className="relative inline-flex items-center rounded-md shadow-sm" ref={menuRef}>
          <button
            onClick={triggerExportPdf}
            className="flex items-center space-x-1.5 px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-l-md text-xs font-medium transition border-r border-cyan-700/60 shadow-sm"
            title="Export Publication-Grade PDF Dossier"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Export Dossier</span>
          </button>
          <button
            onClick={() => setIsExportMenuOpen(!isExportMenuOpen)}
            className="px-1.5 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-r-md text-xs font-medium transition shadow-sm"
            title="Select Dossier Export Format (PDF, CSV, JSON)"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>

          {isExportMenuOpen && (
            <div className="absolute right-0 top-full mt-1 w-56 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl z-50 py-1 font-sans text-xs">
              <div className="px-3 py-1.5 border-b border-slate-800 text-[11px] font-semibold text-slate-400">
                FORENSIC EXPORT FORMATS
              </div>
              <button
                onClick={triggerExportPdf}
                className="w-full text-left px-3 py-2 text-slate-200 hover:bg-cyan-950/50 hover:text-cyan-300 flex items-center space-x-2.5 transition"
              >
                <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                <div>
                  <div className="font-medium">Official Dossier (PDF)</div>
                  <div className="text-[10px] text-slate-400 font-mono">Publication grade with radar & audit ledger</div>
                </div>
              </button>
              <button
                onClick={triggerExportCsv}
                className="w-full text-left px-3 py-2 text-slate-200 hover:bg-cyan-950/50 hover:text-cyan-300 flex items-center space-x-2.5 transition"
              >
                <Table className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="font-medium">Tabular Data (CSV)</div>
                  <div className="text-[10px] text-slate-400 font-mono">Deterministic multi-section tables</div>
                </div>
              </button>
              <button
                onClick={triggerExportJson}
                className="w-full text-left px-3 py-2 text-slate-200 hover:bg-cyan-950/50 hover:text-cyan-300 flex items-center space-x-2.5 transition"
              >
                <Code className="w-4 h-4 text-amber-400 shrink-0" />
                <div>
                  <div className="font-medium">Canonical Model (JSON)</div>
                  <div className="text-[10px] text-slate-400 font-mono">SHA-256 report_hash & raw signals</div>
                </div>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
