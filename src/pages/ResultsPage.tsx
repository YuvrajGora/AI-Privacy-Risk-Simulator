import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck,
  AlertTriangle,
  User,
  FileText,
  QrCode,
  MapPin,
  Eye,
  Sparkles,
  DownloadCloud,
  Wand2,
  CheckCircle,
  SlidersHorizontal,
  ArrowRight,
  Shield,
  Loader2,
  Lock,
} from 'lucide-react';
import { useScan } from '../hooks/useScan';
import PrivacyGauge from '../components/common/PrivacyGauge';
import scanService from '../services/scanService';

const severityConfig: Record<string, { cls: string; dot: string; badge: string }> = {
  critical: { cls: 'border-error/40 bg-error-container/20', dot: 'bg-error', badge: 'badge-critical' },
  Critical: { cls: 'border-error/40 bg-error-container/20', dot: 'bg-error', badge: 'badge-critical' },
  high: { cls: 'border-error/30 bg-error-container/10', dot: 'bg-error', badge: 'badge-high' },
  High: { cls: 'border-error/30 bg-error-container/10', dot: 'bg-error', badge: 'badge-high' },
  medium: { cls: 'border-tertiary/30 bg-tertiary-container/10', dot: 'bg-tertiary', badge: 'badge-medium' },
  Medium: { cls: 'border-tertiary/30 bg-tertiary-container/10', dot: 'bg-tertiary', badge: 'badge-medium' },
  safe: { cls: 'border-primary/20 bg-primary-container/10', dot: 'bg-primary', badge: 'badge-safe' },
  Safe: { cls: 'border-primary/20 bg-primary-container/10', dot: 'bg-primary', badge: 'badge-safe' },
};

export const ResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { currentReport, activeScanId, fetchReport, triggerRedaction, isRedacting, comparisonData, showToast, postThreatAction } = useScan();

  const [redactionMode, setRedactionMode] = useState<'blur' | 'pixelate' | 'blackbox' | 'solid'>('blur');
  const [sliderPosition, setSliderPosition] = useState<number>(50);
  const [activeTab, setActiveTab] = useState<'annotated' | 'comparison'>('annotated');
  const [expandedThreatId, setExpandedThreatId] = useState<string | null>(null);
  const [autopilotStep, setAutopilotStep] = useState<string | null>(null);

  const runAutopilotDemo = async () => {
    if (!currentReport || !activeScanId) return;
    
    // Step 1: Analyze & Show Findings
    setAutopilotStep("Step 1/4: Highlighting detected privacy risks...");
    showToast("Autopilot: Expanding first critical finding...", "info");
    setActiveTab('annotated');
    if (currentReport.threats && currentReport.threats.length > 0) {
      setExpandedThreatId(currentReport.threats[0].id || "threat_0");
    }
    
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    // Step 2: Dismiss False Positive (if multiple findings)
    if (currentReport.threats && currentReport.threats.length > 1) {
      setAutopilotStep("Step 2/4: Simulating false-positive override...");
      showToast("Autopilot: Dismissing face / lower risk finding...", "info");
      const targetThreat = currentReport.threats.find(t => t.type === "Visible Face" || t.severity === "Low" || t.severity === "Medium") || currentReport.threats[1];
      if (targetThreat && targetThreat.id) {
        await postThreatAction(targetThreat.id, 'dismiss');
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    
    // Step 3: Run Remediation Engine
    setAutopilotStep("Step 3/4: Applying OpenCV Blur Redaction & scrubbing EXIF...");
    showToast("Autopilot: Obscuring PII threats...", "info");
    await triggerRedaction("blur");
    setActiveTab('comparison');
    
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    // Step 4: Export PDF Package
    setAutopilotStep("Step 4/4: Downloading PDF audit report package...");
    showToast("Autopilot: Packing PDF export...", "success");
    handleExportPdf();
    
    await new Promise((resolve) => setTimeout(resolve, 1500));
    
    setAutopilotStep(null);
    showToast("Autopilot Walkthrough complete! Report saved, metadata sanitized.", "success");
  };

  // Modes that have already been generated (served from cache instantly)
  const cachedModes: string[] = (currentReport as any)?.cachedRedactionModes || [];

  useEffect(() => {
    if (id && id !== activeScanId) {
      fetchReport(id);
    }
  }, [id, activeScanId, fetchReport]);

  if (!currentReport) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center space-y-4">
        <Shield className="w-12 h-12 text-primary mx-auto animate-pulse" />
        <h2 className="font-headline text-2xl font-bold text-on-surface">No Active Privacy Report</h2>
        <p className="text-on-surface-variant text-sm">Please upload an image to run a privacy scan first.</p>
      </div>
    );
  }

  const score = currentReport.privacyScore ?? currentReport.score ?? 50;
  const riskLevel = currentReport.riskLevel || currentReport.level || 'Medium';
  const threats = currentReport.threats || [];
  const detections = currentReport.detections || {
    facesDetected: 0,
    piiFound: [],
    qrCodesFound: 0,
    gpsExposed: false,
  };
  const recommendations = currentReport.recommendations || [];
  const sharingAdvice = currentReport.sharingAdvice;

  const isRedacted = currentReport.redactionStatus === 'completed' || !!currentReport.safeImage;
  const safeImage = currentReport.safeImage || comparisonData?.safeImage;
  const annotatedImage = currentReport.annotatedImage || comparisonData?.annotatedImage;
  const originalImage = currentReport.originalImage || comparisonData?.originalImage;
  const originalScore = currentReport.originalScore ?? score;
  const safeScore = currentReport.safeScore ?? comparisonData?.safeScore ?? 98;
  const improvement = currentReport.scoreImprovement ?? comparisonData?.scoreImprovement ?? (safeScore - originalScore);

  const handleExportPdf = () => {
    if (!activeScanId && !currentReport.scanId) {
      showToast('Scan ID missing for PDF export.', 'warning');
      return;
    }
    const id = activeScanId || currentReport.scanId;
    const url = scanService.getPdfExportUrl(id);
    window.open(url, '_blank');
    showToast('Downloading official PDF report...', 'info');
  };

  const handleDownloadSafeImage = () => {
    const url = safeImage || `/api/v1/redacted-image/${activeScanId || currentReport.scanId}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `safe_sanitized_${currentReport.targetName || 'image'}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast('Downloading safe sanitized image!', 'success');
  };

  const handleRedactClick = async () => {
    await triggerRedaction(redactionMode);
    setActiveTab('comparison');
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-8">
      {/* Floating Autopilot Status Banner */}
      {autopilotStep && (
        <div className="bg-primary text-on-primary font-bold text-xs p-4 rounded-xl flex items-center justify-between shadow-lg animate-pulse border border-primary/20">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 animate-spin text-white" />
            <span>{autopilotStep}</span>
          </div>
          <span className="text-[9px] uppercase bg-on-primary/20 px-2 py-0.5 rounded font-black tracking-wider">
            Autopilot Active
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-headline text-3xl font-bold text-on-surface">Privacy Assessment Report</h1>
            {isRedacted && (
              <span className="badge badge-safe flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" /> Redacted & Safe
              </span>
            )}
          </div>
          <p className="text-on-surface-variant text-sm mt-1">
            Target: <span className="font-semibold text-on-surface">{currentReport.targetName || 'Uploaded Image'}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={runAutopilotDemo}
            disabled={!!autopilotStep}
            className="px-5 py-2.5 bg-gradient-to-r from-primary via-tertiary to-primary hover:brightness-110 text-on-primary font-bold text-xs uppercase tracking-widest rounded-xl transition-all hover:scale-[1.02] flex items-center gap-2 shadow-lg"
          >
            🚀 Autopilot Demo Run
          </button>
          <button onClick={handleExportPdf} className="btn-outline flex items-center gap-2 text-xs font-bold uppercase tracking-widest py-2.5 px-5">
            <DownloadCloud className="w-4 h-4" /> Download PDF Report
          </button>
        </div>
      </div>

      {/* ── Score & AI Assessment Row ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Audit stats column */}
        <div className="flex flex-col gap-6">
          {/* Gauge Card */}
          <div className="card flex flex-col items-center justify-center gap-4 py-8">
            <PrivacyGauge score={score} />
            <div className="text-center">
              <p className="font-headline text-2xl font-bold text-on-surface">{riskLevel} Risk</p>
              <p className="text-xs text-on-surface-variant mt-1">Privacy Safety Score: {score}/100</p>
            </div>
          </div>

          {/* Privacy Score Impact Breakdown */}
          {currentReport.scoreBreakdown && Object.keys(currentReport.scoreBreakdown).length > 0 && (
            <div className="card p-5 space-y-3">
              <h3 className="font-headline text-xs font-bold text-primary uppercase tracking-widest">Privacy Impact Breakdown</h3>
              <div className="space-y-2">
                {Object.entries(currentReport.scoreBreakdown).map(([category, value]) => (
                  <div key={category} className="flex justify-between items-center text-xs text-on-surface-variant">
                    <span>{category}</span>
                    <span className="font-mono text-error font-bold">{value} pts</span>
                  </div>
                ))}
                <div className="border-t border-outline-variant/30 pt-2 flex justify-between text-xs font-bold text-on-surface">
                  <span>Total Deductions</span>
                  <span className="text-error">{score - 100} pts</span>
                </div>
              </div>
            </div>
          )}

          {/* Scan Quality & Assessment Card */}
          {currentReport.scanReliability !== undefined && (
            <div className="card p-5 space-y-3">
              <h3 className="font-headline text-xs font-bold text-primary uppercase tracking-widest">Auditor Scan Quality</h3>
              <div className="flex items-center justify-between">
                <span className="text-xs text-on-surface-variant">Scan Reliability Rating</span>
                <span className={`font-headline text-sm font-bold ${currentReport.scanReliability >= 80 ? 'text-primary' : 'text-error'}`}>
                  {currentReport.scanReliability}%
                </span>
              </div>
              {currentReport.scanQuality && (
                <div className="text-[11px] text-on-surface-variant space-y-1.5 border-t border-outline-variant/20 pt-2">
                  <div className="flex justify-between">
                    <span>Resolution:</span>
                    <span className="font-semibold text-on-surface">{(currentReport.scanQuality as any).resolution}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Blur Focus:</span>
                    <span className="font-semibold text-on-surface">{(currentReport.scanQuality as any).blurLevel}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Exposure Level:</span>
                    <span className="font-semibold text-on-surface">{(currentReport.scanQuality as any).exposureLevel}</span>
                  </div>
                </div>
              )}
              {(currentReport.scanQuality as any)?.warning && (
                <div className="p-3 bg-error-container/20 border border-error/30 rounded-xl text-error text-[10px] font-bold mt-2">
                  ⚠️ {(currentReport.scanQuality as any).warning}
                </div>
              )}
            </div>
          )}

          {/* Accuracy Diagnostics Section */}
          <div className="card p-5 space-y-3">
            <h3 className="font-headline text-xs font-bold text-primary uppercase tracking-widest">Detection Accuracy Diagnostics</h3>
            <div className="text-xs text-on-surface-variant space-y-2">
              <div className="flex justify-between">
                <span>Total Findings:</span>
                <span className="font-bold text-on-surface">{threats.length}</span>
              </div>
              <div className="flex justify-between">
                <span>High Confidence:</span>
                <span className="font-semibold text-primary">{threats.filter((t: any) => t.confidenceLabel === "High Confidence").length}</span>
              </div>
              <div className="flex justify-between">
                <span>Medium Confidence:</span>
                <span className="font-semibold text-tertiary">{threats.filter((t: any) => t.confidenceLabel === "Medium Confidence").length}</span>
              </div>
              <div className="flex justify-between">
                <span>Low Confidence:</span>
                <span className="font-semibold text-on-surface-variant">{threats.filter((t: any) => t.confidenceLabel === "Low Confidence").length}</span>
              </div>
              <div className="flex justify-between border-t border-outline-variant/20 pt-2 font-semibold">
                <span>Dismissed Findings:</span>
                <span className="text-on-surface-variant">{threats.filter((t: any) => t.dismissed).length}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Audit Content column */}
        <div className="md:col-span-2 flex flex-col gap-6">
          {/* Gemini AI Assessment */}
          <div className="card space-y-4 p-6 flex-1 flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-primary">
                <Sparkles className="w-5 h-5" />
                <h2 className="font-headline text-sm font-bold uppercase tracking-widest">Gemini AI Audit</h2>
              </div>
              <p className="text-on-surface-variant text-sm leading-relaxed">{currentReport.summary}</p>

              {sharingAdvice && (
                <div className="p-3 bg-surface-container-high rounded-xl border border-primary/20 text-xs text-on-surface space-y-1">
                  <span className="font-bold text-primary uppercase tracking-wider block">Social Media Advice:</span>
                  <p className="text-on-surface-variant">{sharingAdvice}</p>
                </div>
              )}
            </div>

            {/* Detections Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-outline-variant/20">
              <div className="bg-surface-container-high rounded-xl p-3 text-center">
                <p className="font-headline text-xl font-bold text-error">{detections.facesDetected}</p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">Faces</p>
              </div>
              <div className="bg-surface-container-high rounded-xl p-3 text-center">
                <p className="font-headline text-xl font-bold text-tertiary">{detections.piiFound?.length || 0}</p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">PII Found</p>
              </div>
              <div className="bg-surface-container-high rounded-xl p-3 text-center">
                <p className="font-headline text-xl font-bold text-tertiary">{detections.qrCodesFound}</p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">QR Codes</p>
              </div>
              <div className="bg-surface-container-high rounded-xl p-3 text-center">
                <p className={`font-headline text-xl font-bold ${detections.gpsExposed ? 'text-error' : 'text-primary'}`}>
                  {detections.gpsExposed ? 'Exposed' : 'Clean'}
                </p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">GPS EXIF</p>
              </div>
            </div>
          </div>

          {/* Analysis Timeline */}
          {currentReport.metrics?.timingMetrics && (
            <div className="card p-6 space-y-4">
              <h3 className="font-headline text-xs font-bold text-primary uppercase tracking-widest">Analysis Timeline</h3>
              <div className="space-y-2 font-mono text-xs text-on-surface-variant">
                {[
                  { key: 'metadataTime', label: 'Metadata Scan' },
                  { key: 'ocrTime', label: 'OCR Scan' },
                  { key: 'screenTime', label: 'Screen Analysis' },
                  { key: 'qrTime', label: 'QR Analysis' },
                  { key: 'idCardTime', label: 'Privacy Scoring' },
                  { key: 'geminiTime', label: 'Report Generation' },
                ].map((item) => {
                  const val = currentReport.metrics.timingMetrics[item.key];
                  if (val === undefined) return null;
                  return (
                    <div key={item.key} className="flex justify-between items-center">
                      <span>{item.label}</span>
                      <span className="flex-1 mx-2 border-b border-dotted border-outline-variant/50" />
                      <span className="font-bold text-on-surface">{val}s</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Visual Artifacts: Highlighted Overlay & Before/After Comparison ── */}
      <div className="card space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-outline-variant/20 pb-4">
          <div className="flex items-center gap-2">
            <Eye className="w-5 h-5 text-primary" />
            <h2 className="font-headline text-base font-bold text-on-surface">Visual Threat Analysis</h2>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('annotated')}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                activeTab === 'annotated' ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Highlighted Threats
            </button>
            <button
              onClick={() => setActiveTab('comparison')}
              disabled={!isRedacted && !safeImage}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                activeTab === 'comparison'
                  ? 'bg-primary text-on-primary'
                  : isRedacted || safeImage
                  ? 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
                  : 'bg-surface-container/50 text-outline cursor-not-allowed'
              }`}
            >
              Before / After Comparison
            </button>
          </div>
        </div>

        {/* Tab 1: Annotated Overlay */}
        {activeTab === 'annotated' && (
          <div className="space-y-4">
            <p className="text-xs text-on-surface-variant">
              Bounding box overlays highlighting detected faces, identity cards, phone numbers, emails, addresses, and QR codes directly on the image.
            </p>
            <div className="relative rounded-2xl overflow-hidden bg-surface-container-lowest border border-outline-variant/30 flex items-center justify-center max-h-[500px]">
              {annotatedImage ? (
                <img src={annotatedImage} alt="Highlighted Threats" className="w-full h-full object-contain max-h-[500px]" />
              ) : (
                <div className="p-12 text-center text-on-surface-variant text-sm">Annotated image generating...</div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Before / After Comparison Slider */}
        {activeTab === 'comparison' && (
          <div className="space-y-4">
            <div className="bg-primary-container/20 border border-primary/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold text-primary uppercase tracking-widest">Privacy Score Improvement</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="font-headline text-2xl font-bold text-error">{originalScore}</span>
                  <ArrowRight className="w-5 h-5 text-primary" />
                  <span className="font-headline text-3xl font-bold text-primary">{safeScore}</span>
                  {originalScore > 0 && (
                    <span className="badge badge-safe text-xs font-bold ml-2">
                      +{Math.round(((safeScore - originalScore) / originalScore) * 100)}% improvement
                    </span>
                  )}
                </div>
              </div>
              {safeImage && (
                <button onClick={handleDownloadSafeImage} className="btn-primary py-2.5 px-6 text-xs flex items-center gap-2">
                  <DownloadCloud className="w-4 h-4" /> Download Safe Image
                </button>
              )}
            </div>

            {/* Interactive Image Comparison Slider */}
            <div className="relative rounded-2xl overflow-hidden bg-surface-container-lowest border border-outline-variant/30 max-h-[500px] select-none">
              {/* After (Redacted) Image Base */}
              {safeImage && (
                <img src={safeImage} alt="Redacted Safe" className="w-full h-full object-contain max-h-[500px]" />
              )}

              {/* Before (Original/Annotated) Clip Layer */}
              {annotatedImage && (
                <div
                  className="absolute top-0 left-0 bottom-0 overflow-hidden"
                  style={{ width: `${sliderPosition}%` }}
                >
                  <img src={annotatedImage} alt="Original" className="w-full h-full object-contain max-h-[500px] max-w-none" />
                </div>
              )}

              {/* Slider Line Divider */}
              <div
                className="absolute top-0 bottom-0 w-1 bg-primary cursor-ew-resize z-30"
                style={{ left: `${sliderPosition}%` }}
              >
                <div className="w-7 h-7 rounded-full bg-primary text-on-primary font-bold text-xs flex items-center justify-center -translate-x-3.5 translate-y-[220px] shadow-lg">
                  ↔
                </div>
              </div>

              {/* Range Input for Dragging */}
              <input
                type="range"
                min="0"
                max="100"
                value={sliderPosition}
                onChange={(e) => setSliderPosition(Number(e.target.value))}
                className="absolute inset-0 opacity-0 cursor-ew-resize w-full h-full z-40"
              />
            </div>
            <p className="text-center text-xs text-on-surface-variant">Drag the slider horizontally to compare Original vs Redacted Safe image.</p>
          </div>
        )}
      </div>

      {/* ── AI Privacy Remediation Control Panel ("Make Safe") ── */}
      <div className="card space-y-5 bg-gradient-to-br from-surface-container via-surface-container-high to-surface-container border-primary/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-primary">
              <Wand2 className="w-5 h-5" />
              <h2 className="font-headline text-lg font-bold text-on-surface">AI Privacy Remediation Engine</h2>
            </div>
            <p className="text-xs text-on-surface-variant">
              Automatically redact faces, identity cards, phone numbers, emails, addresses, QR codes, and vehicle license plates while stripping all EXIF location metadata.
            </p>
          </div>

          {/* Mode Selector */}
          <div className="flex items-center gap-2 bg-surface-container-highest p-1 rounded-xl border border-outline-variant/30 shrink-0">
            {(['blur', 'pixelate', 'blackbox', 'solid'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setRedactionMode(m)}
                className={`relative px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                  redactionMode === m ? 'bg-primary text-on-primary shadow-md' : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {m}
                {cachedModes.includes(m) && (
                  <span className="absolute -top-1.5 -right-1.5 text-[8px] bg-primary text-on-primary rounded-full px-1 font-black leading-none py-0.5">
                    ⚡
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-4 pt-2">
          <button
            onClick={handleRedactClick}
            disabled={isRedacting}
            className="btn-primary w-full sm:w-auto py-3 px-8 flex items-center justify-center gap-2 text-sm shadow-xl"
          >
            {isRedacting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" /> Redacting & Scrubbing EXIF...
              </>
            ) : (
              <>
                <Wand2 className="w-5 h-5" /> Auto-Redact & Make Safe ({redactionMode.toUpperCase()})
              </>
            )}
          </button>

          {isRedacted && (
            <button onClick={handleDownloadSafeImage} className="btn-outline w-full sm:w-auto py-3 px-6 flex items-center justify-center gap-2 text-sm">
              <DownloadCloud className="w-4 h-4" /> Download Safe Image
            </button>
          )}
        </div>
      </div>

      {/* ── Threat Breakdown List ── */}
      <div className="card space-y-4">
        <h2 className="font-headline text-sm font-bold text-on-surface uppercase tracking-widest">Detected Threats Breakdown</h2>
        {threats.length === 0 ? (
          <p className="text-xs text-on-surface-variant">No explicit threat items identified.</p>
        ) : (
          <div className="space-y-3">
            {threats.map((t: any, i: number) => {
              const cfg = severityConfig[t.severity] || severityConfig.Medium;
              const isExpanded = expandedThreatId === t.id;
              const isDismissed = t.dismissed === true;
              
              return (
                <motion.div
                  key={t.id || i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className={`flex flex-col p-4 rounded-xl border transition-all ${isDismissed ? 'bg-surface-container/40 border-outline-variant/20 opacity-70' : cfg.cls} cursor-pointer`}
                  onClick={() => setExpandedThreatId(isExpanded ? null : t.id)}
                >
                  <div className="flex items-start gap-4 w-full">
                    <div className="w-9 h-9 rounded-lg bg-surface-container flex items-center justify-center shrink-0">
                      <AlertTriangle className="w-4 h-4 text-on-surface-variant" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center flex-wrap gap-2 mb-0.5">
                        <span className={`text-sm font-semibold text-on-surface ${isDismissed ? 'line-through text-on-surface-variant' : ''}`}>
                          {t.type}
                        </span>
                        <span className={`badge ${isDismissed ? 'bg-surface-container-highest text-on-surface-variant' : cfg.badge}`}>
                          {t.severity}
                        </span>
                        {t.confidenceLabel && (
                          <span className="badge badge-info text-[9px] font-mono px-1.5 py-0.5">
                            {t.confidenceLabel}
                          </span>
                        )}
                        {t.deduction && (
                          <span className="badge badge-error text-[9px] font-mono px-1.5 py-0.5 bg-error/15 text-error">
                            -{t.deduction} pts
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-on-surface-variant">{t.description}</p>
                    </div>
                    <div className="flex items-center gap-3 self-center shrink-0">
                      {/* Confirm/Dismiss override action buttons */}
                      <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        {isDismissed ? (
                          <button
                            onClick={() => postThreatAction(t.id, 'confirm')}
                            className="px-2.5 py-1 bg-primary text-on-primary text-[10px] font-bold rounded-lg uppercase tracking-wider hover:brightness-110 active:scale-95 transition-all"
                          >
                            Restore Finding
                          </button>
                        ) : (
                          <>
                            <button
                              onClick={() => postThreatAction(t.id, 'confirm')}
                              className="px-2.5 py-1 bg-surface-container text-on-surface border border-outline-variant/30 text-[10px] font-bold rounded-lg uppercase tracking-wider hover:bg-surface-container-high active:scale-95 transition-all"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => postThreatAction(t.id, 'dismiss')}
                              className="px-2.5 py-1 bg-error-container/20 text-error border border-error/20 text-[10px] font-bold rounded-lg uppercase tracking-wider hover:bg-error-container/30 active:scale-95 transition-all"
                            >
                              Dismiss FP
                            </button>
                          </>
                        )}
                      </div>
                      <span className={`w-2 h-2 rounded-full shrink-0 ${isDismissed ? 'bg-on-surface-variant/30' : cfg.dot}`} />
                    </div>
                  </div>

                  {/* Expandable explainable details block */}
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      className="border-t border-outline-variant/30 mt-3 pt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="space-y-1">
                        <span className="font-bold text-[10px] text-primary uppercase tracking-widest block">What was detected?</span>
                        <p className="text-on-surface-variant leading-relaxed">{t.whatWasDetected || t.description}</p>
                      </div>
                      <div className="space-y-1">
                        <span className="font-bold text-[10px] text-primary uppercase tracking-widest block">Why is it risky?</span>
                        <p className="text-on-surface-variant leading-relaxed">{t.whyIsItRisky || 'Exposing personal elements increases profiling footprint.'}</p>
                      </div>
                      <div className="space-y-1">
                        <span className="font-bold text-[10px] text-primary uppercase tracking-widest block">How serious is it?</span>
                        <p className="text-on-surface-variant leading-relaxed">{t.howSeriousIsIt || `${t.severity} severity finding.`}</p>
                      </div>
                      <div className="space-y-1">
                        <span className="font-bold text-[10px] text-primary uppercase tracking-widest block">How can it be fixed?</span>
                        <p className="text-on-surface-variant leading-relaxed">{t.howCanItBeFixed || 'Scrub or overlay blur/black-box filters.'}</p>
                      </div>
                      {t.bbox && (
                        <div className="col-span-1 sm:col-span-2 text-[10px] text-on-surface-variant/80 bg-surface-container-high/50 p-2 rounded-lg font-mono">
                          Bounding Box: X:{t.bbox[0]}, Y:{t.bbox[1]}, W:{t.bbox[2]}, H:{t.bbox[3]}
                        </div>
                      )}
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Actionable Recommendations ── */}
      <div className="card space-y-4">
        <div className="flex items-center gap-2 text-primary">
          <ShieldCheck className="w-5 h-5" />
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest">Privacy Mitigation Steps</h2>
        </div>
        <ul className="space-y-3">
          {recommendations.map((rec: string, i: number) => (
            <li key={i} className="flex items-start gap-3 text-sm text-on-surface-variant">
              <span className="w-5 h-5 rounded-full bg-primary-container text-primary text-xs flex items-center justify-center font-bold shrink-0 mt-0.5">
                {i + 1}
              </span>
              {rec}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default ResultsPage;
