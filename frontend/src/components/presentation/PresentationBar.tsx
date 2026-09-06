import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw, Compass, CheckCircle2, AlertTriangle, X } from 'lucide-react';

interface PresentationBarProps {
  activeScenario?: 'CASE_1' | 'CASE_2';
  onSelectScenario: (scenario: 'CASE_1' | 'CASE_2') => void;
  onOpenTour: () => void;
  onClosePresentationMode: () => void;
  isFallbackActive: boolean;
  isLoading: boolean;
}

export const PresentationBar: React.FC<PresentationBarProps> = ({
  activeScenario,
  onSelectScenario,
  onOpenTour,
  onClosePresentationMode,
  isFallbackActive,
  isLoading
}) => {
  const [secondsRemaining, setSecondsRemaining] = useState(300); // 5 minutes
  const [isTimerRunning, setIsTimerRunning] = useState(false);

  useEffect(() => {
    let interval: any = null;
    if (isTimerRunning && secondsRemaining > 0) {
      interval = setInterval(() => {
        setSecondsRemaining(prev => prev - 1);
      }, 1000);
    } else if (secondsRemaining === 0) {
      setIsTimerRunning(false);
    }
    return () => clearInterval(interval);
  }, [isTimerRunning, secondsRemaining]);

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainder = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${remainder.toString().padStart(2, '0')}`;
  };

  const getTimerColor = () => {
    if (secondsRemaining <= 30) return 'text-rose-400 animate-pulse font-bold';
    if (secondsRemaining <= 120) return 'text-amber-400 font-bold';
    return 'text-cyan-300 font-semibold';
  };

  return (
    <div className="bg-slate-950/95 border-b border-cyan-500/40 px-4 py-2 text-xs font-mono shadow-xl shadow-cyan-950/40 flex flex-wrap items-center justify-between gap-3 sticky top-0 z-40 backdrop-blur-md">
      {/* Left: Mode Badge & Live Status */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 uppercase tracking-wider font-bold">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping inline-block mr-1" />
          Presentation Mode
        </div>

        {isFallbackActive ? (
          <div className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-950/70 border border-amber-500/60 text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="font-bold">DEMO FALLBACK DATA | SOURCE: FROZEN SIH BENCHMARK</span>
          </div>
        ) : (
          <div className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-950/50 border border-emerald-500/40 text-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>LIVE BACKEND PIPELINE</span>
          </div>
        )}
      </div>

      {/* Center: Scenario Switcher */}
      <div className="flex items-center space-x-2">
        <span className="text-slate-400 uppercase tracking-wider text-[11px]">Demo Presets:</span>
        <button
          onClick={() => onSelectScenario('CASE_1')}
          disabled={isLoading}
          className={`px-3 py-1 rounded transition font-bold flex items-center space-x-1.5 ${
            activeScenario === 'CASE_1'
              ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/50 border border-cyan-400'
              : 'bg-slate-900 text-slate-300 hover:bg-slate-800 border border-slate-700'
          }`}
        >
          <span>Case 1: Convergence (GhostSpecter)</span>
        </button>

        <button
          onClick={() => onSelectScenario('CASE_2')}
          disabled={isLoading}
          className={`px-3 py-1 rounded transition font-bold flex items-center space-x-1.5 ${
            activeScenario === 'CASE_2'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/50 border border-indigo-400'
              : 'bg-slate-900 text-slate-300 hover:bg-slate-800 border border-slate-700'
          }`}
        >
          <span>Case 2: Hard Gate Refusal (DeceptiveClone)</span>
        </button>
      </div>

      {/* Right: 5:00 Timer & Controls */}
      <div className="flex items-center space-x-3">
        {/* Practice Timer */}
        <div className="flex items-center space-x-2 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
          <span className="text-slate-400 text-[11px] uppercase">5-Min Timer:</span>
          <span className={`text-sm ${getTimerColor()}`}>{formatTime(secondsRemaining)}</span>
          <button
            onClick={() => setIsTimerRunning(!isTimerRunning)}
            className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title={isTimerRunning ? "Pause timer" : "Start timer"}
          >
            {isTimerRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={() => {
              setIsTimerRunning(false);
              setSecondsRemaining(300);
            }}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            title="Reset timer to 5:00"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 5 Demonstration Pillars Tour Button */}
        <button
          onClick={onOpenTour}
          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition"
          title="Open 5 Demonstration Pillars Tour"
        >
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          <span className="hidden sm:inline">5 Pillars Tour</span>
        </button>

        {/* Exit Presentation Mode */}
        <button
          onClick={onClosePresentationMode}
          className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition"
          title="Exit presentation mode"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
