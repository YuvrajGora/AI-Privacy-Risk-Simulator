import api from './api';
import {
  PrivacyReport,
  ScanHistoryItem,
  SimulationParams,
  UploadResponse,
  ScanStatusResponse,
  RedactionResponse,
  ComparisonResponse,
} from '../types';

/**
 * Resolves a backend image URL.
 * Converts relative paths starting with /api/v1/... to full absolute URLs if VITE_API_BASE_URL is set to a remote domain.
 */
export const resolveImageUrl = (url?: string | null): string => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('blob:') || url.startsWith('data:')) {
    return url;
  }
  
  const rawBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (rawBaseUrl && (rawBaseUrl.startsWith('http://') || rawBaseUrl.startsWith('https://'))) {
    const cleanBase = rawBaseUrl.replace(/\/+$/, '');
    if (url.startsWith('/api/v1')) {
      const origin = cleanBase.endsWith('/api/v1') ? cleanBase.slice(0, -7) : cleanBase;
      return `${origin}${url}`;
    }
    const cleanPath = url.startsWith('/') ? url : `/${url}`;
    return `${cleanBase}${cleanPath}`;
  }
  return url;
};

export const scanService = {

  /**
   * POST /upload
   * Sends image file & params to Flask backend
   */
  async uploadImage(file: File, params?: SimulationParams): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('image', file);
    if (params) {
      formData.append('scanMode', params.scanMode);
      formData.append('privacyLevel', params.privacyLevel);
    }

    const response = await api.post<UploadResponse>('upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * GET /status/:scanId
   * Polling real-time background analysis progress
   */
  async getScanStatus(scanId: string): Promise<ScanStatusResponse> {
    const response = await api.get<ScanStatusResponse>(`status/${scanId}`);
    return response.data;
  },

  /**
   * GET /report/:scanId
   * Fetches full privacy report JSON
   */
  async getReportById(scanId: string): Promise<PrivacyReport> {
    const response = await api.get<PrivacyReport>(`report/${scanId}`);
    return response.data;
  },

  /**
   * POST /redact/:scanId
   * Triggers auto-redaction engine
   */
  async triggerRedact(scanId: string, mode: string = 'blur'): Promise<RedactionResponse> {
    const response = await api.post<RedactionResponse>(`redact/${scanId}`, { mode });
    return response.data;
  },

  /**
   * GET /redaction-status/:scanId
   * Polling background redaction progress
   */
  async getRedactionStatus(scanId: string): Promise<ScanStatusResponse> {
    const response = await api.get<ScanStatusResponse>(`redaction-status/${scanId}`);
    return response.data;
  },

  /**
   * GET /comparison/:scanId
   * Fetches Before vs After image URLs and score metrics
   */
  async getComparison(scanId: string): Promise<ComparisonResponse> {
    const response = await api.get<ComparisonResponse>(`comparison/${scanId}`);
    return response.data;
  },

  /**
   * Returns full URL to download PDF report
   */
  getPdfExportUrl(scanId: string): string {
    return resolveImageUrl(`/api/v1/export/pdf/${scanId}`);
  },

  /**
   * GET /history
   * Fetches scan audit trail
   */
  async getHistory(): Promise<ScanHistoryItem[]> {
    try {
      const response = await api.get<ScanHistoryItem[]>('history/');
      return response.data;
    } catch {
      return [];
    }
  },

  /**
   * DELETE /history/:scanId
   */
  async deleteHistoryItem(scanId: string): Promise<void> {
    try {
      await api.delete(`history/${scanId}`);
    } catch (err) {
      console.warn('Failed to delete history item on server:', err);
    }
  },

  /**
   * DELETE /history
   */
  async clearAllHistory(): Promise<void> {
    try {
      await api.delete('history/');
    } catch (err) {
      console.warn('Failed to clear history on server:', err);
    }
  },

  /**
   * POST /report/:scanId/action
   * Confirms or dismisses a threat finding (false positive override)
   */
  async postThreatAction(scanId: string, threatId: string, action: 'confirm' | 'dismiss'): Promise<any> {
    const response = await api.post(`report/${scanId}/action`, { threatId, action });
    return response.data;
  },
};

export default scanService;
