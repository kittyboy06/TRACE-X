import axios from 'axios';
import { AttributionAssessment, CytoscapeGraphData, AuditEvent } from '../types';

const API_BASE = '/api/v1';

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
    const res = await axios.get(`${API_BASE}/audit/export/${investigationId}`);
    return res.data;
  },

  subscribeToPipeline(
    investigationId: string,
    onProgress: (event: any) => void,
    onComplete: (assessment: AttributionAssessment) => void,
    onError?: (error: any) => void
  ) {
    const token = localStorage.getItem('tracex_token');
    const eventSource = new EventSource(
      `${API_BASE}/pipeline/stream/${investigationId}${token ? `?token=${encodeURIComponent(token)}` : ''}`
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
  }
};
