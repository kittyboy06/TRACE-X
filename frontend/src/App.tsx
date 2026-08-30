import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { AttributionAssessment, CytoscapeGraphData, AnalystAction, AuditEvent } from './types';
import { Header } from './components/Header';
import { PipelineProgress } from './components/PipelineProgress';
import { VisualizerContainer } from './components/visualizers/VisualizerContainer';
import { AttributionCard } from './components/attribution/AttributionCard';
import { EvidenceRadar } from './components/attribution/EvidenceRadar';
import { ContradictionBox } from './components/attribution/ContradictionBox';
import { SensitivityTuner } from './components/attribution/SensitivityTuner';
import { AnalystActions } from './components/attribution/AnalystActions';
import { EvidenceDrawer } from './components/drawer/EvidenceDrawer';

export const App: React.FC = () => {
  const [activeCase, setActiveCase] = useState<'1' | '2'>('1');
  const [investigationId, setInvestigationId] = useState('INV-SIH-001');
  const [personaA, setPersonaA] = useState('KryptonGhost');
  const [personaB, setPersonaB] = useState('SpecterOp');

  const [assessment, setAssessment] = useState<AttributionAssessment | null>(null);
  const [graphData, setGraphData] = useState<CytoscapeGraphData>({ nodes: [], edges: [] });
  const [artifacts, setArtifacts] = useState<any[]>([]);

  // Pipeline SSE streaming state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressStage, setProgressStage] = useState('IDLE');
  const [progressPct, setProgressPct] = useState(0);
  const [progressMsg, setProgressMsg] = useState('Ready to execute CTI pipeline');

  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>();
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | undefined>();

  // Load benchmark case and trigger pipeline
  const runCase = async (caseNum: string) => {
    setActiveCase(caseNum as '1' | '2');
    setIsProcessing(true);
    setProgressStage('INITIALIZING');
    setProgressPct(5);
    setProgressMsg(`Loading Benchmark Case ${caseNum} into Evidence Ingestion Layer...`);

    try {
      // 1. Ingest benchmark into backend
      const loadRes = await api.loadBenchmark(caseNum);
      setInvestigationId(loadRes.investigation_id);
      setPersonaA(loadRes.persona_a);
      setPersonaB(loadRes.persona_b);
      setArtifacts(loadRes.artifacts || []);

      // 2. Subscribe to live pipeline SSE stream
      api.subscribeToPipeline(
        loadRes.investigation_id,
        (progressEvent) => {
          setProgressStage(progressEvent.stage);
          setProgressPct(progressEvent.progress_percentage);
          setProgressMsg(progressEvent.message);
        },
        async (completedAssessment) => {
          setAssessment(completedAssessment);
          setProgressStage('COMPLETE');
          setProgressPct(100);
          setProgressMsg(`Attribution finalized: ${completedAssessment.attribution_state}`);
          setIsProcessing(false);

          // Fetch graph data
          const gRes = await api.getGraph(loadRes.investigation_id);
          setGraphData(gRes.graph);
        },
        (err) => {
          console.error('Pipeline SSE error', err);
          setIsProcessing(false);
        }
      );
    } catch (err) {
      console.error('Failed to load benchmark', err);
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    runCase('1');
  }, []);

  const handleSensitivityChange = async (weights: {
    crypto: number;
    financial: number;
    stylometry: number;
    infra: number;
    behavior: number;
  }) => {
    if (!assessment) return;
    try {
      const updated = await api.recalculateSensitivity({
        investigation_id: investigationId,
        weight_cryptographic: weights.crypto,
        weight_financial: weights.financial,
        weight_stylometric: weights.stylometry,
        weight_infrastructure: weights.infra,
        weight_behavioral: weights.behavior
      });
      setAssessment(updated);
    } catch (err) {
      console.error('Sensitivity recalculation failed', err);
    }
  };

  const handleResetSensitivity = () => {
    handleSensitivityChange({
      crypto: 0.30,
      financial: 0.25,
      stylometry: 0.20,
      infra: 0.15,
      behavior: 0.10
    });
  };

  const handleRecordDecision = async (action: AnalystAction, rationale: string): Promise<AuditEvent> => {
    if (!assessment) throw new Error('No assessment to commit');
    return await api.recordDecision({
      investigation_id: investigationId,
      assessment_id: assessment.assessment_id,
      action,
      analyst_id: 'ANALYST-SIH-014',
      rationale
    });
  };

  const handleExportDossier = async () => {
    try {
      const dossier = await api.exportDossier(investigationId);
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(dossier, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `TRACE-X_Dossier_${investigationId}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err) {
      alert('Failed to export investigation dossier.');
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#030712] text-slate-100 overflow-hidden select-none">
      {/* Header Bar */}
      <Header
        investigationId={investigationId}
        personaA={personaA}
        personaB={personaB}
        activeCase={activeCase}
        onSelectCase={runCase}
        onExport={handleExportDossier}
        onOpenUpload={() => alert('Custom evidence package upload modal')}
        isProcessing={isProcessing}
      />

      {/* Pipeline SSE Status Ticker */}
      <PipelineProgress
        stage={progressStage}
        percentage={progressPct}
        message={progressMsg}
        isProcessing={isProcessing}
      />

      {/* Main Tactical Grid (Canvas 65% / Sidebar 35%) */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 p-3 min-h-0 overflow-hidden">
        {/* Left Visualizer Canvas (8 cols) */}
        <section className="lg:col-span-8 h-full flex flex-col min-h-0">
          {assessment ? (
            <VisualizerContainer
              graphData={graphData}
              assessment={assessment}
              onSelectNode={(nodeId) => {
                setSelectedNodeId(nodeId);
                const art = artifacts.find(a => a.raw_payload?.key_id === nodeId || a.evidence_id === nodeId);
                if (art) setSelectedEvidenceId(art.evidence_id);
              }}
            />
          ) : (
            <div className="w-full h-full bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-center text-slate-500 font-mono text-sm">
              Loading TRACE-X Intelligence Pipeline...
            </div>
          )}
        </section>

        {/* Right Intelligence & Attribution Panel (4 cols) */}
        <aside className="lg:col-span-4 h-full flex flex-col space-y-3 min-h-0 overflow-y-auto pr-1">
          {assessment ? (
            <>
              <AttributionCard assessment={assessment} />
              <EvidenceRadar dimensions={assessment.evidence_dimensions} />
              <ContradictionBox
                dampenings={assessment.channel_dampenings}
                contradictions={assessment.global_contradictions}
              />
              <SensitivityTuner
                investigationId={investigationId}
                dimensions={assessment.evidence_dimensions}
                onWeightsChange={handleSensitivityChange}
                onReset={handleResetSensitivity}
              />
              <AnalystActions
                investigationId={investigationId}
                assessmentId={assessment.assessment_id}
                onRecordDecision={handleRecordDecision}
              />
            </>
          ) : (
            <div className="w-full h-full bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-center text-slate-500 font-mono text-xs">
              Waiting for assessment generation...
            </div>
          )}
        </aside>
      </main>

      {/* Bottom Collapsible Evidence Drawer */}
      <EvidenceDrawer
        artifacts={artifacts}
        selectedEvidenceId={selectedEvidenceId}
      />
    </div>
  );
};
export default App;
