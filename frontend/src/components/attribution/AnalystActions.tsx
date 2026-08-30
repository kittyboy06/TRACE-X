import React, { useState } from 'react';
import { AnalystAction, AuditEvent } from '../../types';
import { CheckCircle2, XCircle, Search, Lock, UserCheck } from 'lucide-react';

interface AnalystActionsProps {
  investigationId: string;
  assessmentId: string;
  onRecordDecision: (action: AnalystAction, rationale: string) => Promise<AuditEvent>;
}

export const AnalystActions: React.FC<AnalystActionsProps> = ({
  investigationId,
  assessmentId,
  onRecordDecision
}) => {
  const [rationale, setRationale] = useState('');
  const [lastAudit, setLastAudit] = useState<AuditEvent | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAction = async (action: AnalystAction) => {
    if (!rationale.trim()) {
      alert('Please enter an analyst rationale before submitting the audit event.');
      return;
    }
    setIsSubmitting(true);
    try {
      const result = await onRecordDecision(action, rationale);
      setLastAudit(result);
    } catch (err) {
      console.error(err);
      alert('Failed to record audit event.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-1.5 text-slate-300">
          <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-mono tracking-wider uppercase font-semibold">
            HUMAN-IN-THE-LOOP AUDIT
          </span>
        </div>
        <span className="text-[10px] font-mono text-slate-500">
          APPEND-ONLY RECORD
        </span>
      </div>

      {lastAudit ? (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded p-2.5 text-xs font-mono">
          <div className="flex items-center space-x-1.5 text-emerald-400 font-bold mb-1">
            <Lock className="w-3.5 h-3.5" />
            <span>DECISION COMMITTED: {lastAudit.action}</span>
          </div>
          <div className="text-slate-300 text-[11px] space-y-0.5">
            <div>Analyst: <span className="text-slate-100">{lastAudit.analyst_id}</span></div>
            <div>Time: <span className="text-slate-100">{new Date(lastAudit.timestamp).toUTCString()}</span></div>
            <div>Rationale: <span className="text-slate-100">{lastAudit.rationale}</span></div>
            <div className="text-[10px] text-slate-400 truncate pt-1 border-t border-emerald-500/20 mt-1">
              Audit Hash: <span className="text-emerald-300">{lastAudit.event_hash}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <textarea
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            placeholder="Enter operational rationale for attribution confirmation, rejection, or further investigation..."
            rows={2}
            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-sans resize-none"
          />

          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => handleAction('CONFIRMED')}
              disabled={isSubmitting}
              className="flex items-center justify-center space-x-1 px-2 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 rounded text-xs font-mono font-semibold transition"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Confirm</span>
            </button>

            <button
              onClick={() => handleAction('REJECTED')}
              disabled={isSubmitting}
              className="flex items-center justify-center space-x-1 px-2 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 rounded text-xs font-mono font-semibold transition"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Reject</span>
            </button>

            <button
              onClick={() => handleAction('INVESTIGATE')}
              disabled={isSubmitting}
              className="flex items-center justify-center space-x-1 px-2 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 rounded text-xs font-mono font-semibold transition"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Investigate</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
