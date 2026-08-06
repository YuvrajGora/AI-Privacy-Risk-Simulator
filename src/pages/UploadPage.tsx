import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Image as ImageIcon, Shield, ArrowRight, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { useScan } from '../hooks/useScan';
import { SimulationParams } from '../types';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { setUploadedFile, startScan, showToast, uploadedFile } = useScan();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const [params, setParams] = useState<SimulationParams>({
    maxLatency: '120ms',
    scanMode: 'Deep Scan',
    privacyLevel: 'High Protection',
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setUploadedFile(file);
      showToast(`Selected: ${file.name}`);
    } else {
      showToast('Please upload a PNG, JPG, JPEG, or WEBP image.');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      showToast(`Selected: ${file.name}`);
    }
  };

  const handleSubmit = async () => {
    if (!uploadedFile) {
      showToast('Please select an image first.');
      return;
    }
    await startScan(params);
    navigate('/scanning');
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-headline text-3xl font-bold text-on-surface">Analyze Image</h1>
        <p className="text-on-surface-variant text-sm mt-1">
          Upload an image to check for privacy risks — faces, hidden text, GPS data, QR codes and more.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Drop Zone ── */}
        <div className="lg:col-span-2 space-y-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all min-h-[300px]
              ${dragging
                ? 'border-primary bg-primary-container/20 scale-[1.01]'
                : uploadedFile
                  ? 'border-primary/40 bg-primary-container/10'
                  : 'border-outline-variant/40 hover:border-primary/50 hover:bg-surface-container/40'
              }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleFileSelect}
            />

            {uploadedFile ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-3"
              >
                <div className="w-16 h-16 rounded-xl bg-primary-container/40 border border-primary/30 flex items-center justify-center mx-auto">
                  <ImageIcon className="w-8 h-8 text-primary" />
                </div>
                <div>
                  <p className="font-semibold text-on-surface">{uploadedFile.name}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    {(uploadedFile.size / 1024).toFixed(1)} KB · Ready for analysis
                  </p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setUploadedFile(null); }}
                  className="inline-flex items-center gap-1 text-xs text-error hover:text-error/80 transition-colors"
                >
                  <X className="w-3 h-3" /> Remove image
                </button>
              </motion.div>
            ) : (
              <div className="space-y-4">
                <div className="w-16 h-16 rounded-xl bg-surface-container border border-outline-variant/30 flex items-center justify-center mx-auto">
                  <UploadCloud className="w-8 h-8 text-on-surface-variant" />
                </div>
                <div>
                  <p className="text-on-surface font-semibold">Drag & drop your image here</p>
                  <p className="text-on-surface-variant text-sm mt-1">or click to browse files</p>
                </div>
                <div className="flex flex-wrap justify-center gap-2 pt-2">
                  {['PNG', 'JPG', 'JPEG', 'WEBP'].map((fmt) => (
                    <span key={fmt} className="badge badge-safe">{fmt}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!uploadedFile}
            className={`w-full py-4 rounded-xl font-bold text-sm uppercase tracking-widest flex items-center justify-center gap-2 transition-all
              ${uploadedFile
                ? 'bg-secondary text-on-secondary hover:brightness-110 active:scale-95 shadow-lg'
                : 'bg-surface-container text-on-surface-variant cursor-not-allowed'
              }`}
          >
            <Shield className="w-5 h-5" />
            Analyze Image
            {uploadedFile && <ArrowRight className="w-4 h-4" />}
          </button>
        </div>

        {/* ── Scan Options ── */}
        <div className="space-y-4">
          {/* Privacy Scan Mode */}
          <div className="card space-y-3">
            <h3 className="font-headline text-sm font-bold text-on-surface uppercase tracking-widest">Privacy Scan Mode</h3>
            <p className="text-on-surface-variant text-xs">Choose scan depth and speed.</p>
            <div className="space-y-2">
              {[
                { value: 'Deep Scan', label: 'Deep Scan', sub: 'Most thorough — recommended', recommended: true },
                { value: 'Quick Scan', label: 'Quick Scan', sub: 'Fast, basic checks only' },
              ].map((opt) => (
                <label key={opt.value} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${params.scanMode === opt.value ? 'border-primary/40 bg-primary-container/20' : 'border-outline-variant/20 hover:border-outline-variant/40'}`}>
                  <input
                    type="radio"
                    name="scanMode"
                    value={opt.value}
                    checked={params.scanMode === opt.value}
                    onChange={(e) => setParams({ ...params, scanMode: e.target.value })}
                    className="mt-0.5 accent-primary"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-on-surface">{opt.label}</span>
                      {opt.recommended && <span className="badge badge-safe text-[10px]">Recommended</span>}
                    </div>
                    <p className="text-xs text-on-surface-variant">{opt.sub}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Privacy Level */}
          <div className="card space-y-3">
            <h3 className="font-headline text-sm font-bold text-on-surface uppercase tracking-widest">Privacy Level</h3>
            <p className="text-on-surface-variant text-xs">How strict should risk scoring be?</p>
            <select
              value={params.privacyLevel}
              onChange={(e) => setParams({ ...params, privacyLevel: e.target.value })}
              className="w-full bg-surface-container-high border border-outline-variant/30 text-on-surface text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:border-primary"
            >
              <option>High Protection</option>
              <option>Standard Protection</option>
              <option>Minimal Protection</option>
            </select>
          </div>

          {/* Info */}
          <div className="card space-y-2 bg-primary-container/10 border-primary/20">
            <div className="flex items-center gap-2 text-primary">
              <Shield className="w-4 h-4" />
              <span className="text-xs font-bold uppercase tracking-widest">Privacy Guaranteed</span>
            </div>
            <p className="text-on-surface-variant text-xs leading-relaxed">
              Your image is analyzed in real-time and permanently deleted from our servers immediately after your report is generated.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
