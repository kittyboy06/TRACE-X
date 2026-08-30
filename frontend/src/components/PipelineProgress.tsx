import React from 'react';
import { Activity, CheckCircle, Clock } from 'lucide-react';

interface PipelineProgressProps {
  stage: string;
  percentage: number;
  message: string;
  isProcessing: boolean;
}

export const PipelineProgress: React.FC<PipelineProgressProps> = ({
  stage,
  percentage,
  message,
  isProcessing
}) => {
  if (!isProcessing && percentage === 100) return null;

  return (
    <div className="bg-slate-900/90 border-b border-cyan-500/20 px-4 py-1.5 flex items-center justify-between text-xs font-mono">
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 text-cyan-400">
          <Activity className="w-3.5 h-3.5 animate-pulse" />
          <span className="font-semibold uppercase tracking-wide">PIPELINE STAGE: {stage}</span>
        </div>
        <span className="text-slate-400">|</span>
        <span className="text-slate-300 truncate max-w-xl">{message}</span>
      </div>

      <div className="flex items-center space-x-3 w-64">
        <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
          <div
            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full transition-all duration-300"
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-cyan-400 font-bold shrink-0">{percentage}%</span>
      </div>
    </div>
  );
};
