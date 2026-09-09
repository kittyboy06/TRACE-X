import axios from 'axios';
import { AttributionAssessment, CytoscapeGraphData, AuditEvent, SourceReliabilityRecord, ExtractedEntityRecord } from '../types';

const envApiUrl = ((import.meta.env.VITE_API_URL as string) || '').trim();
const API_BASE = envApiUrl ? `${envApiUrl.replace(/\/$/, '')}/api/v1` : '/api/v1';

// Automatically inject JWT token into all outgoing requests
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('tracex_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-bootstrap authenticated session for demo environment
export async function ensureAuthenticatedSession(): Promise<string> {
  let token = localStorage.getItem('tracex_token');
  if (!token) {
    try {
      const res = await axios.post(`${API_BASE}/auth/token`, {
        username: 'analyst',
        password: 'tracex2026'
      });
      if (res.data.access_token) {
        token = res.data.access_token;
        localStorage.setItem('tracex_token', res.data.access_token);
        localStorage.setItem('tracex_analyst_id', res.data.analyst_id);
        localStorage.setItem('tracex_role', res.data.role);
      }
    } catch (e) {
      console.warn('Demo session auto-authentication notice:', e);
    }
  }
  return token || '';
}

// Intercept 401 Unauthorized responses and transparently refresh demo session
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      localStorage.removeItem('tracex_token');
      const token = await ensureAuthenticatedSession();
      if (token) {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return axios(originalRequest);
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  async login(username: string, password: string) {
    const res = await axios.post(`${API_BASE}/auth/token`, { username, password });
    if (res.data.access_token) {
      localStorage.setItem('tracex_token', res.data.access_token);
      localStorage.setItem('tracex_analyst_id', res.data.analyst_id);
      localStorage.setItem('tracex_role', res.data.role);
    }
    return res.data;
  },

  async getMe() {
    const res = await axios.get(`${API_BASE}/auth/me`);
    return res.data;
  },

  async loadBenchmark(caseId: string) {
    await ensureAuthenticatedSession();
    const res = await axios.post(`${API_BASE}/ingestion/benchmark/${caseId}`);
    return res.data;
  },

  async getArtifacts(investigationId: string) {
    await ensureAuthenticatedSession();
    const res = await axios.get(`${API_BASE}/ingestion/${investigationId}/artifacts`);
    return res.data;
  },

  async uploadPackage(payload: any) {
    await ensureAuthenticatedSession();
    const res = await axios.post(`${API_BASE}/ingestion/upload`, payload);
    return res.data;
  },

  async uploadFile(file: File) {
    await ensureAuthenticatedSession();
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post(`${API_BASE}/ingestion/upload-file`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
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
    await ensureAuthenticatedSession();
    const res = await axios.post(`${API_BASE}/attribution/recalculate`, payload);
    return res.data;
  },

  async commitTunedWeights(payload: {
    investigation_id: string;
    weight_cryptographic: number;
    weight_financial: number;
    weight_stylometric: number;
    weight_infrastructure: number;
    weight_behavioral: number;
  }): Promise<{ status: string; message: string; assessment: AttributionAssessment; audit_event: any }> {
    await ensureAuthenticatedSession();
    const res = await axios.post(`${API_BASE}/attribution/commit-weights`, payload);
    return res.data;
  },

  async recordDecision(payload: {
    investigation_id: string;
    assessment_id: string;
    action: string;
    analyst_id: string;
    rationale: string;
  }): Promise<AuditEvent> {
    await ensureAuthenticatedSession();
    const res = await axios.post(`${API_BASE}/audit/decision`, payload);
    return res.data;
  },

  async exportDossier(investigationId: string): Promise<any> {
    await ensureAuthenticatedSession();
    const res = await axios.get(`${API_BASE}/reports/${investigationId}/json`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('tracex_token')}` }
    });
    return res.data;
  },

  async downloadDossierPdf(investigationId: string): Promise<void> {
    await ensureAuthenticatedSession();
    const token = localStorage.getItem('tracex_token');
    const response = await axios.get(`${API_BASE}/reports/${investigationId}/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob'
    });
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TRACE-X_Dossier_${investigationId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  async downloadDossierCsv(investigationId: string): Promise<void> {
    await ensureAuthenticatedSession();
    const token = localStorage.getItem('tracex_token');
    const response = await axios.get(`${API_BASE}/reports/${investigationId}/csv`, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob'
    });
    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TRACE-X_Dossier_${investigationId}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  async downloadDossierJson(investigationId: string): Promise<void> {
    await ensureAuthenticatedSession();
    const token = localStorage.getItem('tracex_token');
    const response = await axios.get(`${API_BASE}/reports/${investigationId}/json`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const jsonStr = JSON.stringify(response.data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TRACE-X_Dossier_${investigationId}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  async createSseTicket(investigationId: string): Promise<{ ticket: string; expires_in: number; investigation_id: string }> {
    return this.getSSETicket(investigationId);
  },

  async getSSETicket(investigationId: string): Promise<{ ticket: string; expires_in: number; investigation_id: string }> {
    await ensureAuthenticatedSession();
    const res = await axios.post(
      `${API_BASE}/auth/sse-ticket`,
      { investigation_id: investigationId },
      { headers: { Authorization: `Bearer ${localStorage.getItem('tracex_token')}` } }
    );
    return res.data;
  },

  async getSourceReliability(investigationId: string): Promise<{ investigation_id: string; count: number; sources: SourceReliabilityRecord[] }> {
    await ensureAuthenticatedSession();
    const res = await axios.get(`${API_BASE}/reliability/${investigationId}/sources`);
    return res.data;
  },

  async getEntities(investigationId: string): Promise<{ investigation_id: string; count: number; entities: ExtractedEntityRecord[] }> {
    await ensureAuthenticatedSession();
    const res = await axios.get(`${API_BASE}/ingestion/${investigationId}/entities`);
    return res.data;
  },

  async subscribeToPipeline(
    investigationId: string,
    onProgress: (event: any) => void,
    onComplete: (assessment: AttributionAssessment) => void,
    onError?: (error: any) => void
  ) {
    try {
      const { ticket } = await this.createSseTicket(investigationId);
      const eventSource = new EventSource(
        `${API_BASE}/pipeline/stream/${investigationId}?ticket=${encodeURIComponent(ticket)}`
      );

      eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.stage === 'COMPLETE' && data.assessment) {
            onComplete(data.assessment);
            eventSource.close();
          } else {
            onProgress(data);
          }
        } catch (err) {
          console.error('Error parsing SSE event', err);
        }
      };

      eventSource.onerror = (err) => {
        if (onError) onError(err);
        eventSource.close();
      };

      return eventSource;
    } catch (err) {
      if (onError) onError(err);
    }
  }
};
