import React, { useState, useEffect } from 'react';
import { api, ensureAuthenticatedSession } from './services/api';
import { AttributionAssessment, CytoscapeGraphData, AnalystAction, AuditEvent, ExtractedEntityRecord } from './types';
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
  const [entities, setEntities] = useState<ExtractedEntityRecord[]>([]);

  // Pipeline SSE streaming state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressStage, setProgressStage] = useState('IDLE');
  const [progressPct, setProgressPct] = useState(0);
  const [progressMsg, setProgressMsg] = useState('Ready to execute CTI pipeline');

  // Upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Stable ID selections for bidirectional drilldown
  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>();
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | undefined>();

  const activeStreamRef = React.useRef<EventSource | null>(null);
  const hasInitialized = React.useRef(false);

  // Fetch entities & graph for active investigation
  const loadInvestigationSupportingData = async (invId: string) => {
    try {
      const [gRes, eRes, aRes] = await Promise.all([
        api.getGraph(invId).catch(() => ({ graph: { nodes: [], edges: [] } })),
        api.getEntities(invId).catch(() => ({ entities: [] })),
        api.getArtifacts(invId).catch(() => ({ artifacts: [] }))
      ]);
      setGraphData(gRes.graph);
      setEntities(eRes.entities || []);
      if (aRes.artifacts && aRes.artifacts.length > 0) {
        setArtifacts(aRes.artifacts);
      }
    } catch (e) {
      console.error('Failed to load supporting investigation data', e);
    }
  };

  // Run pipeline stream for any investigation
  const startPipelineStream = (invId: string) => {
    if (activeStreamRef.current) {
      activeStreamRef.current.close();
      activeStreamRef.current = null;
    }

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
        setProgressMsg(`Attribution finalized: ${completedAssessment.attribution_state} (S_base: ${completedAssessment.base_score.toFixed(4)})`);
        setIsProcessing(false);

        await loadInvestigationSupportingData(invId);
      },
      (err) => {
        console.error('Pipeline SSE stream error', err);
        setIsProcessing(false);
      }
    ).then(es => {
      if (es) activeStreamRef.current = es;
    });
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
    if (hasInitialized.current) return;
    hasInitialized.current = true;
    const init = async () => {
      await ensureAuthenticatedSession();
      runCase('1');
    };
    init();
  }, []);

  const handleResetSensitivity = () => {
    if (!investigationId) return;
    runCase(activeCase === '2' ? '2' : '1');
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

  const handleExportPdf = async () => {
    try {
      await api.downloadDossierPdf(investigationId);
    } catch (err) {
      alert('Failed to generate PDF dossier.');
    }
  };

  const handleExportCsv = async () => {
    try {
      await api.downloadDossierCsv(investigationId);
    } catch (err) {
      alert('Failed to generate CSV export.');
    }
  };

  const handleExportJson = async () => {
    try {
      await api.downloadDossierJson(investigationId);
    } catch (err) {
      alert('Failed to export JSON dossier.');
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
        onExportPdf={handleExportPdf}
        onExportCsv={handleExportCsv}
        onExportJson={handleExportJson}
        onExport={handleExportPdf}
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
              investigationId={investigationId}
              selectedNodeId={selectedNodeId}
              onSelectNode={(nodeId) => {
                setSelectedNodeId(nodeId);
                // Stable ID lookup across entities and artifacts
                const matchedEnt = entities.find(e => e.entity_id === nodeId);
                if (matchedEnt) {
                  setSelectedEvidenceId(matchedEnt.evidence_id);
                  return;
                }
                const matchedArt = artifacts.find(a => a.evidence_id === nodeId);
                if (matchedArt) {
                  setSelectedEvidenceId(matchedArt.evidence_id);
                  return;
                }
                // Prefix-agnostic fallback
                const cleanId = nodeId.replace(/^(PGP_|POST_|FORUM_|INFRA_|WALLET_|VASP_)/, '');
                const fallbackArt = artifacts.find(a =>
                  a.evidence_id === cleanId ||
                  a.raw_payload?.key_id === cleanId ||
                  a.raw_payload?.key_fingerprint === cleanId
                );
                if (fallbackArt) setSelectedEvidenceId(fallbackArt.evidence_id);
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
                baseScore={assessment.base_score}
                hardGateApplied={assessment.hard_gate_applied}
                onPreviewChange={(preview) => {
                  setAssessment(preview);
                }}
                onCommitSuccess={async (newAssess, _auditEvent) => {
                  setAssessment(newAssess);
                  // Refresh authoritative state and graph from backend
                  await loadInvestigationSupportingData(investigationId);
                }}
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
        entities={entities}
        selectedEvidenceId={selectedEvidenceId}
        selectedEntityId={selectedNodeId}
        realWorldIdentity={assessment?.real_world_identity}
        onSelectEvidence={(evId) => setSelectedEvidenceId(evId)}
        onSelectEntity={(entId) => setSelectedNodeId(entId)}
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
