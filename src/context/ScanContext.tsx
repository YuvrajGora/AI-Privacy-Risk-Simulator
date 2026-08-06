import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  PrivacyReport,
  ScanHistoryItem,
  SimulationParams,
  ComparisonResponse,
  AppSettings,
} from '../types';
import scanService from '../services/scanService';

interface Toast {
  id: string;
  message: string;
  type?: 'info' | 'success' | 'warning' | 'error';
}

interface ScanContextType {
  uploadedFile: File | null;
  imagePreviewUrl: string | null;
  activeScanId: string | null;
  currentReport: PrivacyReport | null;
  comparisonData: ComparisonResponse | null;
  history: ScanHistoryItem[];
  isScanning: boolean;
  isRedacting: boolean;
  scanProgress: number;
  scanStatus: string;
  scanStepText: string;

  toast: Toast | null;
  settings: AppSettings;
  setUploadedFile: (file: File | null) => void;
  startScan: (params?: SimulationParams) => Promise<void>;
  triggerRedaction: (mode?: string) => Promise<void>;
  fetchReport: (id: string) => Promise<void>;
  fetchHistory: () => Promise<void>;
  deleteHistoryItem: (id: string) => void;
  clearHistory: () => void;
  updateSettings: (newSettings: Partial<AppSettings>) => void;
  showToast: (message: string, type?: Toast['type']) => void;
  postThreatAction: (threatId: string, action: 'confirm' | 'dismiss') => Promise<void>;
}

const DEFAULT_SETTINGS: AppSettings = {
  darkMode: true,
  highContrast: false,
  notifHigh: true,
  notifWeekly: true,
  retention: '7 Days',
};

const ScanContext = createContext<ScanContextType | undefined>(undefined);

export const ScanProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [uploadedFile, setUploadedFileState] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [currentReport, setCurrentReport] = useState<PrivacyReport | null>(null);
  const [comparisonData, setComparisonData] = useState<ComparisonResponse | null>(null);
  const [history, setHistory] = useState<ScanHistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem('privacy_simulator_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const saved = localStorage.getItem('privacy_simulator_settings');
      return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  });

  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [isRedacting, setIsRedacting] = useState<boolean>(false);
  const [scanProgress, setScanProgress] = useState<number>(0);
  const [scanStatus, setScanStatus] = useState<string>('idle');
  const [scanStepText, setScanStepText] = useState<string>('Initializing scan...');
  const [toast, setToast] = useState<Toast | null>(null);

  // Apply Theme & Settings to DOM & LocalStorage
  useEffect(() => {
    try {
      localStorage.setItem('privacy_simulator_settings', JSON.stringify(settings));
    } catch {}

    const root = document.documentElement;
    if (settings.darkMode) {
      root.classList.add('dark');
      root.style.colorScheme = 'dark';
    } else {
      root.classList.remove('dark');
      root.style.colorScheme = 'light';
    }

    if (settings.highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }
  }, [settings]);

  // Persist history changes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('privacy_simulator_history', JSON.stringify(history));
    } catch {}
  }, [history]);

  const showToast = (message: string, type: Toast['type'] = 'info') => {
    const id = Math.random().toString();
    setToast({ id, message, type });
    setTimeout(() => {
      setToast(null);
    }, 3500);
  };

  const updateSettings = (newSettings: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
  };

  const setUploadedFile = (file: File | null) => {
    setUploadedFileState(file);
    if (file && file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setImagePreviewUrl(url);
    } else {
      setImagePreviewUrl(null);
    }
  };

  const startScan = async (params?: SimulationParams) => {
    if (!uploadedFile) {
      showToast('Please select an image to scan first.', 'warning');
      return;
    }

    setIsScanning(true);
    setScanStatus('queued');
    setScanProgress(5);
    setScanStepText('Waiting in queue...');
    setCurrentReport(null);
    setComparisonData(null);

    try {
      const uploadRes = await scanService.uploadImage(uploadedFile, params);
      const scanId = uploadRes.scanId;
      setActiveScanId(scanId);

      // Poll real-time backend status
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await scanService.getScanStatus(scanId);
          const bStatus = statusRes.status || 'processing';
          setScanStatus(bStatus);
          setScanProgress(statusRes.progress ?? 0);

          if (bStatus === 'queued') {
            setScanStepText('Waiting in queue...');
          } else if (bStatus === 'processing') {
            setScanStepText(statusRes.currentStep || 'Scanning image...');
          } else if (bStatus === 'completed') {
            clearInterval(pollInterval);
            setScanProgress(100);
            setScanStepText('Analysis complete');
            setIsScanning(false);

            // Fetch completed report
            const report = await scanService.getReportById(scanId);
            setCurrentReport(report);
            showToast('Scan complete! Privacy report generated.', 'success');

            // Add to history
            const historyEntry: ScanHistoryItem = {
              id: scanId,
              name: report.targetName || uploadedFile.name,
              score: report.privacyScore ?? report.score ?? 50,
              riskLevel: (report.riskLevel || report.level || 'Medium').toString(),
              timestamp: new Date().toLocaleString(),
            };

            setHistory((prev) => [historyEntry, ...prev.filter((h) => h.id !== scanId)]);
          } else if (bStatus === 'failed') {
            clearInterval(pollInterval);
            setScanStepText('Analysis failed');
            setIsScanning(false);
            showToast(`Analysis failed: ${statusRes.errorMessage || 'Unknown error'}`, 'error');
          } else if (bStatus === 'cancelled') {
            clearInterval(pollInterval);
            setScanStepText('Analysis cancelled');
            setIsScanning(false);
          }
        } catch (err) {
          console.warn('Status poll warning:', err);
        }
      }, 500);
    } catch (err: any) {
      setIsScanning(false);
      setScanStatus('failed');
      showToast(`Upload failed: ${err.message || 'Server error'}`, 'error');
    }
  };


  const triggerRedaction = async (mode: string = 'blur') => {
    if (!activeScanId) {
      showToast('No active scan available for redaction.', 'warning');
      return;
    }

    setIsRedacting(true);
    showToast(`Applying ${mode} redaction & scrubbing EXIF...`, 'info');

    try {
      const redactRes = await scanService.triggerRedact(activeScanId, mode);

      // If cached, the server responds with status=completed instantly — no polling needed
      if (redactRes?.cached === true || redactRes?.status === 'completed') {
        setIsRedacting(false);
        const report = await scanService.getReportById(activeScanId);
        const safeImageUrl = `/api/v1/redacted-image/${activeScanId}?mode=${mode}&t=${Date.now()}`;
        setCurrentReport({ ...report, safeImage: safeImageUrl });
        setComparisonData({
          scanId: activeScanId,
          originalImage: report.originalImage || `/api/v1/image/${activeScanId}`,
          annotatedImage: report.annotatedImage || `/api/v1/annotated-image/${activeScanId}`,
          redactedImage: safeImageUrl,
          safeImage: safeImageUrl,
          originalScore: report.originalScore ?? report.privacyScore ?? 50,
          safeScore: report.safeScore ?? 98,
          scoreImprovement: report.scoreImprovement ?? (98 - (report.privacyScore ?? 50)),
          redactionMode: mode,
        });
        showToast(`${mode.toUpperCase()} — loaded instantly from cache!`, 'success');
        return;
      }

      // Not cached — poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await scanService.getRedactionStatus(activeScanId);
          if (statusRes.status === 'completed') {
            clearInterval(pollInterval);
            setIsRedacting(false);

            const report = await scanService.getReportById(activeScanId);
            const safeImageUrl = `/api/v1/redacted-image/${activeScanId}?mode=${mode}&t=${Date.now()}`;
            setCurrentReport({ ...report, safeImage: safeImageUrl });
            setComparisonData({
              scanId: activeScanId,
              originalImage: report.originalImage || `/api/v1/image/${activeScanId}`,
              annotatedImage: report.annotatedImage || `/api/v1/annotated-image/${activeScanId}`,
              redactedImage: safeImageUrl,
              safeImage: safeImageUrl,
              originalScore: report.originalScore ?? report.privacyScore ?? 50,
              safeScore: report.safeScore ?? 98,
              scoreImprovement: report.scoreImprovement ?? (98 - (report.privacyScore ?? 50)),
              redactionMode: mode,
            });

            showToast(`Image redacted successfully using ${mode} mode!`, 'success');
          } else if (statusRes.status === 'failed') {
            clearInterval(pollInterval);
            setIsRedacting(false);
            showToast('Auto-redaction failed.', 'error');
          }
        } catch (err) {
          console.warn('Redaction status poll warning:', err);
        }
      }, 500);
    } catch (err: any) {
      setIsRedacting(false);
      showToast(`Redaction error: ${err.message || 'Server error'}`, 'error');
    }
  };


  const fetchReport = async (id: string) => {
    try {
      const report = await scanService.getReportById(id);
      setCurrentReport(report);
      setActiveScanId(id);
      if (report.redactionStatus === 'completed') {
        const comp = await scanService.getComparison(id);
        setComparisonData(comp);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHistory = async () => {
    try {
      const remoteHistory = await scanService.getHistory();
      if (remoteHistory && remoteHistory.length > 0) {
        setHistory(remoteHistory);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const deleteHistoryItem = async (id: string) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
    await scanService.deleteHistoryItem(id);
    showToast('Scan record deleted from history.');
  };

  const clearHistory = async () => {
    setHistory([]);
    await scanService.clearAllHistory();
    showToast('All scan history cleared permanently.');
  };

  const postThreatAction = async (threatId: string, action: 'confirm' | 'dismiss') => {
    if (!activeScanId) return;
    try {
      const updatedReport = await scanService.postThreatAction(activeScanId, threatId, action);
      setCurrentReport((prev) => prev ? {
        ...prev,
        privacyScore: updatedReport.privacyScore,
        riskLevel: updatedReport.riskLevel,
        safeToShare: updatedReport.safeToShare,
        scoreBreakdown: updatedReport.scoreBreakdown,
        threats: updatedReport.threats,
        annotatedImage: `/api/v1/annotated-image/${activeScanId}?t=${Date.now()}` // reload annotated heatmap
      } : null);
      
      // Update history score
      setHistory((prev) => prev.map((item) => {
        if (item.id === activeScanId) {
          return {
            ...item,
            score: updatedReport.privacyScore,
            riskLevel: updatedReport.riskLevel
          };
        }
        return item;
      }));

      showToast(`Finding successfully ${action === 'dismiss' ? 'dismissed' : 'confirmed'}. Privacy score updated!`, 'success');
    } catch (err: any) {
      showToast(`Action failed: ${err.message || 'Error'}`, 'error');
    }
  };



  return (
    <ScanContext.Provider
      value={{
        uploadedFile,
        imagePreviewUrl,
        activeScanId,
        currentReport,
        comparisonData,
        history,
        isScanning,
        isRedacting,
        scanProgress,
        scanStatus,
        scanStepText,

        toast,
        settings,
        setUploadedFile,
        startScan,
        triggerRedaction,
        fetchReport,
        fetchHistory,
        deleteHistoryItem,
        clearHistory,
        updateSettings,
        showToast,
        postThreatAction,
      }}
    >
      {children}
    </ScanContext.Provider>
  );
};

export const useScanContext = () => {
  const context = useContext(ScanContext);
  if (!context) throw new Error('useScanContext must be used within a ScanProvider');
  return context;
};
