import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldCheck, FileText, User, QrCode, MapPin, Loader2 } from 'lucide-react';
import { useScan } from '../hooks/useScan';

const steps = [
  { icon: FileText, label: 'Extracting Metadata & EXIF Tags' },
  { icon: FileText, label: 'Running Multi-Language OCR (English + Hindi)' },
  { icon: User,     label: 'Biometric Face Detection' },
  { icon: QrCode,   label: 'QR Code & Payload Scanning' },
  { icon: MapPin,   label: 'Evaluating Privacy Risk Score' },
  { icon: ShieldCheck, label: 'Gemini AI Summary & Sharing Advice' },
];

export const ScanningPage: React.FC = () => {
  const navigate = useNavigate();
  const { uploadedFile, imagePreviewUrl, isScanning, scanProgress, scanStatus, scanStepText, currentReport } = useScan();

  // ONLY redirect when backend confirms completed AND progress === 100 AND report exists
  useEffect(() => {
    if (scanStatus === 'completed' && scanProgress === 100 && currentReport) {
      const timer = setTimeout(() => {
        navigate('/results');
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [scanStatus, scanProgress, currentReport, navigate]);

  const isComplete = (scanStatus === 'completed' && scanProgress === 100);
  const isFailed = (scanStatus === 'failed');

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
      <div>
        <h1 className="font-headline text-3xl font-bold text-on-surface">Analyzing Your Image</h1>
        <p className="text-on-surface-variant text-sm mt-1">
          Our AI privacy scanner is analyzing your image for sensitive information.
        </p>
      </div>

      {/* Image Preview + Animated Scan Line */}
      <div className="relative rounded-2xl overflow-hidden border border-outline-variant/20 bg-surface-container h-64 flex items-center justify-center">
        {imagePreviewUrl ? (
          <img
            src={imagePreviewUrl}
            alt="Scanning"
            className="w-full h-full object-contain opacity-70"
          />
        ) : uploadedFile ? (
          <img
            src={URL.createObjectURL(uploadedFile)}
            alt="Scanning"
            className="w-full h-full object-contain opacity-70"
          />
        ) : (
          <div className="text-on-surface-variant text-sm flex items-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-primary" /> Scanning uploaded asset...
          </div>
        )}

        {/* Animated Scan Line - active only during scan */}
        {isScanning && !isComplete && <div className="scan-line" />}
        <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent pointer-events-none" />

        <div className="absolute bottom-4 left-4 text-xs text-primary font-mono font-semibold bg-background/80 px-3 py-1.5 rounded-lg border border-primary/20 backdrop-blur-md flex items-center gap-2">
          {isComplete ? (
            <span>✓ Analysis complete! Redirecting to report...</span>
          ) : isFailed ? (
            <span className="text-error">✕ Analysis failed</span>
          ) : (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
              <span>{scanStepText || `Scanning… ${scanProgress}%`}</span>
            </>
          )}
        </div>
      </div>


      {/* Real-time Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-on-surface-variant">
          <span>Real-Time Scanning Progress</span>
          <span className="font-mono font-bold text-primary">{scanProgress}%</span>
        </div>
        <div className="w-full h-2.5 bg-surface-container-high rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary via-secondary to-tertiary rounded-full"
            animate={{ width: `${scanProgress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Step List */}
      <div className="card space-y-2">
        <h2 className="font-headline text-sm font-bold text-on-surface uppercase tracking-widest mb-4">Detection Steps</h2>
        {steps.map((step, i) => {
          const stepProgressThreshold = (i + 1) * (100 / steps.length);
          const done = scanProgress >= stepProgressThreshold;
          const active = isScanning && !done && scanProgress >= (i * (100 / steps.length));
          const Icon = step.icon;

          return (
            <div
              key={i}
              className={`flex items-center gap-3 p-3 rounded-lg transition-colors text-sm
                ${done ? 'text-primary' : active ? 'text-on-surface bg-surface-container-high' : 'text-on-surface-variant opacity-50'}`}
            >
              <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0
                ${done ? 'bg-primary-container' : active ? 'bg-surface-container-highest' : 'bg-surface-container'}`}>
                {done ? (
                  <ShieldCheck className="w-4 h-4 text-primary" />
                ) : active ? (
                  <Loader2 className="w-4 h-4 text-primary animate-spin" />
                ) : (
                  <Icon className="w-4 h-4 text-outline" />
                )}
              </div>
              <span className={done ? 'line-through opacity-70' : ''}>{step.label}</span>
              {active && (
                <span className="ml-auto text-xs text-primary font-mono animate-pulse">processing...</span>
              )}
              {done && <span className="ml-auto text-xs text-primary font-bold">✓</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ScanningPage;
