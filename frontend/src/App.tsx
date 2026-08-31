import React, { useState, useEffect } from 'react';
import { api, ensureAuthenticatedSession } from './services/api';
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
import { UploadModal } from './components/UploadModal';

export const App: React.FC = () => {
  const [activeCase, setActiveCase] = useState<'1' | '2' | 'custom'>('1');
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

  // Upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>();
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | undefined>();

  // Run pipeline stream for any investigation
  const startPipelineStream = (invId: string) => {
    setIsProcessing(true);
    setProgressStage('EVIDENCE_INGESTION');
    setProgressPct(15);
    setProgressMsg('Initiating real-time analytical pipeline stream...');

    api.subscribeToPipeline(
      invId,
      (progressEvent) => {
        setProgressStage(progressEvent.stage);
        setProgressPct(progressEvent.progress_percentage);
        setProgressMsg(progressEvent.message);
      },
      async (completedAssessment) => {
        setAssessment(completedAssessment);
        setPersonaA(completedAssessment.target_persona_a);
        setPersonaB(completedAssessment.target_persona_b);
        setProgressStage('COMPLETE');
        setProgressPct(100);
        setProgressMsg(`Attribution finalized: ${completedAssessment.attribution_state} (Score: ${completedAssessment.evidence_score})`);
        setIsProcessing(false);

        // Fetch property graph data
        try {
          const gRes = await api.getGraph(invId);
          setGraphData(gRes.graph);
        } catch (e) {
          console.error('Failed to load graph payload', e);
        }
      },
      (err) => {
        console.error('Pipeline SSE stream error', err);
        setIsProcessing(false);
      }
    );
  };

  // Load benchmark case and trigger pipeline
  const runCase = async (caseNum: string) => {
    setActiveCase(caseNum as '1' | '2');
    setIsProcessing(true);
    setProgressStage('INITIALIZING');
    setProgressPct(5);
    setProgressMsg(`Loading Benchmark Case ${caseNum} into Evidence Ingestion Layer...`);

    try {
      const loadRes = await api.loadBenchmark(caseNum);
      setInvestigationId(loadRes.investigation_id);
      setPersonaA(loadRes.persona_a);
      setPersonaB(loadRes.persona_b);
      setArtifacts(loadRes.artifacts || []);

      startPipelineStream(loadRes.investigation_id);
    } catch (err) {
      console.error('Failed to load benchmark', err);
      setIsProcessing(false);
    }
  };

  // Handle uploaded custom package
  const handleUploadSuccess = async (newInvId: string, uploadedArtifacts: any[], pA?: string, pB?: string) => {
    setActiveCase('custom');
    setInvestigationId(newInvId);
    if (pA) setPersonaA(pA);
    if (pB) setPersonaB(pB);
    if (uploadedArtifacts && uploadedArtifacts.length > 0) {
      setArtifacts(uploadedArtifacts);
    } else {
      try {
        const artRes = await api.getArtifacts(newInvId);
        setArtifacts(artRes.artifacts || []);
      } catch (e) {
        console.error('Failed to fetch artifacts', e);
      }
    }
    startPipelineStream(newInvId);
  };

  useEffect(() => {
    const init = async () => {
      await ensureAuthenticatedSession();
      runCase('1');
    };
    init();
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
        onOpenUpload={() => setIsUploadOpen(true)}
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
                const cleanId = nodeId.replace(/^PGP_/, '').replace(/^POST_/, '').replace(/^FORUM_/, '').replace(/^INFRA_/, '');
                const art = artifacts.find(a => 
                  a.evidence_id === nodeId || 
                  a.raw_payload?.key_id === cleanId || 
                  a.raw_payload?.key_id === nodeId ||
                  a.evidence_id === cleanId ||
                  `POST_${a.evidence_id}` === nodeId ||
                  `INFRA_${a.evidence_id}` === nodeId
                );
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

      {/* Live Evidence Ingestion Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
};
export default App;
