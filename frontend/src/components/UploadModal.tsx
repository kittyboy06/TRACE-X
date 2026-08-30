import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertTriangle, X, ArrowRight, Database } from 'lucide-react';
import { api } from '../services/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (investigationId: string) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose, onUploadSuccess }) => {
  const [activeTab, setActiveTab] = useState<'file' | 'json'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jsonText, setJsonText] = useState<string>('');
  const [parsedPreview, setParsedPreview] = useState<any | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setValidationError(null);

      if (file.name.endsWith('.json')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const data = JSON.parse(event.target?.result as string);
            validateAndPreview(data);
          } catch (err: any) {
            setValidationError('Failed to parse JSON file: ' + err.message);
            setParsedPreview(null);
          }
        };
        reader.readAsText(file);
      } else if (file.name.endsWith('.zip')) {
        setParsedPreview({
          filename: file.name,
          size_kb: Math.round(file.size / 1024),
          isZip: true
        });
      }
    }
  };

  const handleJsonChange = (text: string) => {
    setJsonText(text);
    setValidationError(null);
    if (!text.trim()) {
      setParsedPreview(null);
      return;
    }
    try {
      const parsed = JSON.parse(text);
      validateAndPreview(parsed);
    } catch (err: any) {
      setValidationError('Invalid JSON syntax: ' + err.message);
      setParsedPreview(null);
    }
  };

  const validateAndPreview = (data: any) => {
    if (!data.target_persona_a || !data.target_persona_b) {
      setValidationError('Package must specify "target_persona_a" and "target_persona_b"');
      setParsedPreview(null);
      return;
    }
    if (!Array.isArray(data.artifacts) || data.artifacts.length === 0) {
      setValidationError('Package must contain non-empty "artifacts" array');
      setParsedPreview(null);
      return;
    }

    setParsedPreview({
      investigation_id: data.investigation_id || `INV-${Date.now().toString().slice(-6)}`,
      persona_a: data.target_persona_a,
      persona_b: data.target_persona_b,
      artifact_count: data.artifacts.length,
      types: Array.from(new Set(data.artifacts.map((a: any) => a.artifact_type || 'UNKNOWN')))
    });
    setValidationError(null);
  };

  const handleSubmit = async () => {
    setIsUploading(true);
    setValidationError(null);
    try {
      let invId = '';
      if (activeTab === 'file' && selectedFile) {
        const res = await api.uploadFile(selectedFile);
        invId = res.investigation_id;
      } else if (activeTab === 'json' && parsedPreview) {
        const payload = JSON.parse(jsonText);
        if (!payload.investigation_id) {
          payload.investigation_id = parsedPreview.investigation_id;
        }
        const res = await api.uploadPackage(payload);
        invId = res.investigation_id;
      }

      if (invId) {
        onClose();
        onUploadSuccess(invId);
      }
    } catch (err: any) {
      setValidationError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const sampleJson = JSON.stringify({
    investigation_id: "INV-CUSTOM-001",
    target_persona_a: "DarkGhost_Admin",
    target_persona_b: "Specter_Operator",
    artifacts: [
      {
        evidence_id: "EV-CUSTOM-001",
        artifact_type: "PGP_KEY",
        source_uri: "darknet://forum.onion/users/darkghost",
        collected_at: new Date().toISOString(),
        raw_payload: {
          key_id: "0x89AB_CDEF",
          key_fingerprint: "F7A9 3B12 C45E 89AB CDEF 1029 48FA 90B1",
          persona: "DarkGhost_Admin"
        }
      }
    ]
  }, null, 2);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">Live Evidence Package Ingestion</h2>
              <p className="text-xs text-slate-400">Upload raw darknet artifacts (.json / .zip) for cryptographic attribution</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selection */}
        <div className="flex border-b border-slate-800 px-6 pt-3 bg-slate-950/30 gap-4">
          <button
            onClick={() => setActiveTab('file')}
            className={`pb-3 text-xs font-medium border-b-2 flex items-center gap-2 transition ${
              activeTab === 'file'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            Upload File (.json / .zip)
          </button>
          <button
            onClick={() => setActiveTab('json')}
            className={`pb-3 text-xs font-medium border-b-2 flex items-center gap-2 transition ${
              activeTab === 'json'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Raw JSON Package Editor
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {activeTab === 'file' ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-700 hover:border-blue-500/60 rounded-xl p-8 text-center cursor-pointer bg-slate-950/40 hover:bg-blue-500/5 transition flex flex-col items-center justify-center gap-3"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.zip"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                <Upload className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-200">
                  {selectedFile ? selectedFile.name : 'Click to select or drag & drop evidence package'}
                </p>
                <p className="text-xs text-slate-500 mt-1">Supports structured JSON and ZIP artifact archives</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>Paste evidence package JSON:</span>
                <button
                  type="button"
                  onClick={() => handleJsonChange(sampleJson)}
                  className="text-blue-400 hover:underline"
                >
                  Load Sample Template
                </button>
              </div>
              <textarea
                value={jsonText}
                onChange={(e) => handleJsonChange(e.target.value)}
                placeholder="{\n  &quot;investigation_id&quot;: &quot;INV-001&quot;,\n  &quot;target_persona_a&quot;: &quot;...&quot;,\n  &quot;target_persona_b&quot;: &quot;...&quot;,\n  &quot;artifacts&quot;: [...]\n}"
                rows={9}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          )}

          {/* Validation & Preview Card */}
          {parsedPreview && (
            <div className="p-3.5 bg-blue-950/20 border border-blue-500/30 rounded-lg space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-400">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Validated Evidence Package Preview
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                <div>
                  <span className="text-slate-500">Investigation:</span>{' '}
                  <span className="font-mono">{parsedPreview.investigation_id || parsedPreview.filename}</span>
                </div>
                {parsedPreview.persona_a && (
                  <div>
                    <span className="text-slate-500">Correlating:</span>{' '}
                    <span className="font-semibold text-amber-300">{parsedPreview.persona_a}</span> ↔{' '}
                    <span className="font-semibold text-amber-300">{parsedPreview.persona_b}</span>
                  </div>
                )}
                {parsedPreview.artifact_count && (
                  <div className="col-span-2 flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-500">Artifacts ({parsedPreview.artifact_count}):</span>
                    {parsedPreview.types.map((t: string) => (
                      <span key={t} className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-blue-300 border border-slate-700">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {validationError && (
            <div className="p-3 bg-rose-950/30 border border-rose-500/40 rounded-lg flex items-center gap-2.5 text-xs text-rose-300">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{validationError}</span>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/80">
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <Database className="w-3.5 h-3.5 text-slate-500" />
            <span>SHA-256 integrity hashing applied automatically</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isUploading || (!selectedFile && !parsedPreview)}
              className="px-4 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:pointer-events-none rounded-lg transition flex items-center gap-2 shadow-lg shadow-blue-500/20"
            >
              {isUploading ? (
                <span>Ingesting Evidence...</span>
              ) : (
                <>
                  <span>Ingest & Launch Pipeline</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
