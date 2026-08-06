export type RiskLevel = 'Safe' | 'Medium' | 'High' | 'Critical' | 'SAFE' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface PiiItem {
  type: string;
  value: string;
  bbox?: number[];
}

export interface ThreatItem {
  id?: string;
  type: string;
  severity: 'High' | 'Medium' | 'Critical' | 'Safe' | 'Low' | 'high' | 'medium' | 'critical' | 'safe' | 'low';
  description: string;
  bbox?: number[];
  dismissed?: boolean;
  deduction?: number;
  confidenceLabel?: string;
  whatWasDetected?: string;
  whyIsItRisky?: string;
  howSeriousIsIt?: string;
  howCanItBeFixed?: string;
}

export interface DetectionsSummary {
  facesDetected: number;
  piiFound: PiiItem[];
  qrCodesFound: number;
  gpsExposed: boolean;
}

export interface PrivacyReport {
  scanId: string;
  id?: string;
  targetName: string;
  scanMode?: string;
  privacyLevel?: string;
  status: string;
  progress?: number;
  currentStep?: string;
  privacyScore: number;
  score?: number; // fallback alias
  riskLevel: RiskLevel;
  level?: string; // fallback alias
  summary: string;
  recommendations: string[];
  sharingAdvice?: string;
  detections?: DetectionsSummary;
  threats: ThreatItem[];
  originalImage?: string;
  annotatedImage?: string;
  safeImage?: string;
  redactionStatus?: string;
  redactionMode?: string;
  originalScore?: number;
  safeScore?: number;
  scoreImprovement?: number;
  threatIndex?: number;
  processorLoad?: string;
  geminiSummary?: string;
  ocrFindingsCount?: number;
  biometricsCount?: number;
  identifiersCount?: number;
  exifMetadataCount?: number;
  threatVectors?: any[];
  timestamp?: string;
  createdAt?: string;
  scoreBreakdown?: Record<string, number>;
  scanReliability?: number;
  scanQuality?: any;
  metrics?: any;
}

export interface UploadResponse {
  scanId: string;
  status: string;
  targetName: string;
  message?: string;
}

export interface ScanStatusResponse {
  scanId: string;
  status: 'queued' | 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentStep: string;
  errorMessage?: string;
}

export interface RedactionResponse {
  success: boolean;
  status: string;
  error?: string;
  cached?: boolean;
}

export interface ComparisonResponse {
  scanId: string;
  originalImage: string;
  annotatedImage: string;
  redactedImage: string;
  safeImage: string;
  originalScore: number;
  safeScore: number;
  scoreImprovement: number;
  riskReductionPoints?: number;
  redactionMode: string;
}

export interface ScanHistoryItem {
  id: string;
  name: string;
  score: number;
  riskLevel: string;
  timestamp: string;
}

export interface SimulationParams {
  maxLatency?: string;
  scanMode: string;
  privacyLevel: string;
}

export interface AppSettings {
  darkMode: boolean;
  highContrast: boolean;
  notifHigh: boolean;
  notifWeekly: boolean;
  retention: string;
}
