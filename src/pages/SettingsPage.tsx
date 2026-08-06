import React, { useState } from 'react';
import { Eye, Bell, Shield, Trash2, CheckCircle } from 'lucide-react';
import { useScan } from '../hooks/useScan';

export const SettingsPage: React.FC = () => {
  const { settings, updateSettings, clearHistory, showToast } = useScan();
  const [purged, setPurged] = useState(false);

  const handlePurge = () => {
    if (confirm('Permanently delete all scan history? This cannot be undone.')) {
      clearHistory();
      setPurged(true);
      showToast('Scan history permanently cleared.', 'success');
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-8">
      <div>
        <h1 className="font-headline text-3xl font-bold text-on-surface">Settings & Preferences</h1>
        <p className="text-on-surface-variant text-sm mt-1">Manage appearance, privacy notifications, and history retention.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Appearance */}
        <div className="card space-y-5">
          <div className="flex items-center gap-2">
            <Eye className="w-5 h-5 text-primary" />
            <h2 className="font-headline text-base font-bold text-on-surface">Appearance</h2>
          </div>

          {[
            {
              label: 'Dark Theme',
              sub: 'Sleek dark mode palette',
              state: settings.darkMode,
              toggle: () => {
                const next = !settings.darkMode;
                updateSettings({ darkMode: next });
                showToast(`Dark Mode ${next ? 'enabled' : 'disabled'}.`);
              },
            },
            {
              label: 'High Contrast',
              sub: 'Increases text and badge visibility',
              state: settings.highContrast,
              toggle: () => {
                const next = !settings.highContrast;
                updateSettings({ highContrast: next });
                showToast(`High Contrast ${next ? 'enabled' : 'disabled'}.`);
              },
            },
          ].map((item) => (
            <div key={item.label} className="flex items-center justify-between p-3 bg-surface-container rounded-xl border border-outline-variant/20">
              <div>
                <p className="text-sm font-semibold text-on-surface">{item.label}</p>
                <p className="text-xs text-on-surface-variant">{item.sub}</p>
              </div>
              <button
                onClick={item.toggle}
                className={`w-12 h-6 rounded-full relative flex items-center px-1 transition-colors ${
                  item.state ? 'bg-primary' : 'bg-surface-container-highest'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full bg-on-primary shadow transition-transform ${
                    item.state ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          ))}
        </div>

        {/* Notifications */}
        <div className="card space-y-5">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            <h2 className="font-headline text-base font-bold text-on-surface">Privacy Notifications</h2>
          </div>

          {[
            {
              label: 'High Risk Alerts',
              sub: 'Notify when critical PII or identity cards are detected',
              state: settings.notifHigh,
              toggle: () => {
                const next = !settings.notifHigh;
                updateSettings({ notifHigh: next });
                showToast(`High Risk Alerts ${next ? 'enabled' : 'disabled'}.`);
              },
            },
            {
              label: 'Weekly Summary',
              sub: 'A periodic recap of your scan history and safety score',
              state: settings.notifWeekly,
              toggle: () => {
                const next = !settings.notifWeekly;
                updateSettings({ notifWeekly: next });
                showToast(`Weekly Summary ${next ? 'enabled' : 'disabled'}.`);
              },
            },
          ].map((item) => (
            <label key={item.label} className="flex items-start gap-3 p-3 bg-surface-container rounded-xl border border-outline-variant/20 cursor-pointer">
              <input
                type="checkbox"
                checked={item.state}
                onChange={item.toggle}
                className="mt-0.5 w-4 h-4 rounded accent-primary cursor-pointer"
              />
              <div>
                <p className="text-sm font-semibold text-on-surface">{item.label}</p>
                <p className="text-xs text-on-surface-variant">{item.sub}</p>
              </div>
            </label>
          ))}
        </div>

        {/* Data Retention & Privacy */}
        <div className="md:col-span-2 card space-y-5">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            <h2 className="font-headline text-base font-bold text-on-surface">Data Retention & Storage</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-surface-container rounded-xl p-4 border border-outline-variant/20 space-y-2">
              <p className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">History Retention</p>
              <select
                value={settings.retention}
                onChange={(e) => {
                  updateSettings({ retention: e.target.value });
                  showToast(`Retention set to ${e.target.value}.`);
                }}
                className="w-full bg-surface-container-high border border-outline-variant/30 text-on-surface text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-primary cursor-pointer"
              >
                <option>24 Hours</option>
                <option>7 Days</option>
                <option>30 Days</option>
                <option>Forever</option>
              </select>
            </div>

            <div className="bg-surface-container rounded-xl p-4 border border-outline-variant/20 space-y-1">
              <p className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">Image Storage</p>
              <p className="text-primary font-bold text-sm">Redacted & Sterilized</p>
              <p className="text-xs text-on-surface-variant">Original image EXIF data is stripped during redaction</p>
            </div>

            <div className="bg-surface-container rounded-xl p-4 border border-outline-variant/20 space-y-1">
              <p className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">AI Engine</p>
              <p className="text-primary font-bold text-sm">Google Gemini 1.5</p>
              <p className="text-xs text-on-surface-variant">OCR & detection handled locally; structured findings audited by AI</p>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="bg-error-container/10 border border-error/20 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex-1">
              <p className="text-sm font-bold text-error uppercase tracking-widest mb-1">Clear All Scan History</p>
              <p className="text-xs text-on-surface-variant">Permanently remove all previous scan records and uploaded server images.</p>
            </div>
            <button
              onClick={handlePurge}
              disabled={purged}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-bold text-xs uppercase tracking-widest transition-all shrink-0 ${
                purged
                  ? 'bg-primary-container text-primary cursor-default'
                  : 'bg-error text-on-error hover:brightness-110 active:scale-95'
              }`}
            >
              {purged ? <><CheckCircle className="w-4 h-4" /> History Cleared</> : <><Trash2 className="w-4 h-4" /> Clear All History</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
