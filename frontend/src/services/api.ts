import axios from 'axios';
import { AttributionAssessment, CytoscapeGraphData, AuditEvent } from '../types';

const API_BASE = '/api/v1';

export const api = {
  async loadBenchmark(caseId: string) {
    const res = await axios.post(`${API_BASE}/ingestion/benchmark/${caseId}`);
    return res.data;
  },

  async uploadPackage(payload: any) {
    const res = await axios.post(`${API_BASE}/ingestion/upload`, payload);
    return res.data;
  },

  async getGraph(investigationId: string): Promise<{ graph: CytoscapeGraphData }> {
    const res = await axios.get(`${API_BASE}/graph/${investigationId}`);
    return res.data;
  },

  async getAttribution(investigationId: string): Promise<AttributionAssessment> {
    const res = await axios.get(`${API_BASE}/attribution/${investigationId}`);
    return res.data;
  },

  async recalculateSensitivity(payload: {
    investigation_id: string;
    weight_cryptographic: number;
    weight_financial: number;
    weight_stylometric: number;
    weight_infrastructure: number;
    weight_behavioral: number;
  }): Promise<AttributionAssessment> {
    const res = await axios.post(`${API_BASE}/attribution/recalculate`, payload);
    return res.data;
  },

  async recordDecision(payload: {
    investigation_id: string;
    assessment_id: string;
    action: string;
    analyst_id: string;
    rationale: string;
  }): Promise<AuditEvent> {
    const res = await axios.post(`${API_BASE}/audit/decision`, payload);
    return res.data;
  },

  async exportDossier(investigationId: string) {
    const res = await axios.get(`${API_BASE}/audit/export/${investigationId}`);
    return res.data;
  },

  subscribeToPipeline(
    investigationId: string,
    onProgress: (event: any) => void,
    onComplete: (assessment: AttributionAssessment) => void,
    onError: (err: any) => void
  ) {
    const eventSource = new EventSource(`${API_BASE}/pipeline/stream/${investigationId}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.stage === 'COMPLETE') {
          onComplete(data.assessment);
          eventSource.close();
        } else {
          onProgress(data);
        }
      } catch (err) {
        console.error('SSE JSON parse error', err);
      }
    };

    eventSource.onerror = (err) => {
      onError(err);
      eventSource.close();
    };

    return eventSource;
  }
};
