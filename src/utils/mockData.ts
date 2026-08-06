import { PrivacyReport, ScanHistoryItem } from '../types';

export const initialHistoryData: ScanHistoryItem[] = [
  {
    id: 'SIM-8829-X',
    name: 'Llama-3-70b-Infra-Audit',
    score: 24,
    riskLevel: 'CRITICAL',
    timestamp: 'Oct 24, 2026 • 14:22 UTC',
  },
  {
    id: 'SIM-8710-V',
    name: 'Customer-Support-Bot-V2',
    score: 62,
    riskLevel: 'ELEVATED',
    timestamp: 'Oct 23, 2026 • 09:15 UTC',
  },
  {
    id: 'SIM-8692-K',
    name: 'Internal-HR-Assistant',
    score: 94,
    riskLevel: 'SAFE',
    timestamp: 'Oct 22, 2026 • 18:04 UTC',
  },
  {
    id: 'SIM-8551-M',
    name: 'Data-Lake-Export-Sync',
    score: 54,
    riskLevel: 'MEDIUM',
    timestamp: 'Oct 21, 2026 • 11:30 UTC',
  },
  {
    id: 'SIM-8440-L',
    name: 'Global-Auth-Gateway',
    score: 88,
    riskLevel: 'SAFE',
    timestamp: 'Oct 20, 2026 • 08:00 UTC',
  },
];

export const sampleReportData: PrivacyReport = {
  scanId: 'SIM-8829-X',
  id: 'SIM-8829-X',
  targetName: 'Neural_Scan_Batch_04.json',
  status: 'completed',
  privacyScore: 68,
  riskLevel: 'Medium',
  summary: 'Our LLM analysis has identified a potential Shadow Profile Match. The combination of your recent OCR findings and EXIF metadata creates a unique fingerprint.',
  threats: [
    { type: 'Geospatial Meta', severity: 'High', description: 'High-precision GPS coordinates embedded in EXIF tag' },
    { type: 'Document OCR', severity: 'Medium', description: 'PII text string detected in document scan' }
  ],
  threatIndex: 7.2,
  processorLoad: '94.8%',
  geminiSummary: 'Our LLM analysis has identified a potential Shadow Profile Match. The combination of your recent OCR findings and EXIF metadata creates a unique fingerprint with 92% confidence.',
  recommendations: [
    'Scrub EXIF GPS coordinates from all images before uploading to shared repositories.',
    'Obfuscate text in scanned documents using the Varnish anonymizer tool.',
  ],
  ocrFindingsCount: 12,
  biometricsCount: 2,
  identifiersCount: 84,
  exifMetadataCount: 216,
  threatVectors: [
    {
      entityId: 'TXN_8842_Z9',
      type: 'Geospatial Meta',
      leakProbability: 0.88,
      status: 'Exposed',
      description: 'High-precision GPS coordinates embedded in EXIF tag',
    },
    {
      entityId: 'LOG_SIM_002',
      type: 'Document OCR',
      leakProbability: 0.45,
      status: 'Anonymized',
      description: 'PII text string detected in document scan',
    },
    {
      entityId: 'BIO_FACE_L4',
      type: 'Facial Geometry',
      leakProbability: 0.12,
      status: 'Protected',
      description: 'Partial facial landmarks detected in background',
    },
  ],
  timestamp: 'Oct 24, 2026 • 14:22:10 UTC',
};
