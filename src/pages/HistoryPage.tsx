import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, ExternalLink, ShieldCheck, ShieldAlert } from 'lucide-react';
import { useScan } from '../hooks/useScan';

const getLevelConfig = (riskLevel: string) => {
  const lvl = riskLevel.toLowerCase();
  if (lvl.includes('safe') || lvl.includes('low')) {
    return { badge: 'badge-safe', label: 'Safe' };
  }
  if (lvl.includes('medium')) {
    return { badge: 'badge-medium', label: 'Medium' };
  }
  if (lvl.includes('critical')) {
    return { badge: 'badge-critical', label: 'Critical' };
  }
  return { badge: 'badge-high', label: 'High Risk' };
};

type FilterType = 'all' | 'safe' | 'medium' | 'high' | 'critical';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const { history, fetchReport, deleteHistoryItem, clearHistory } = useScan();
  const [filter, setFilter] = useState<FilterType>('all');

  const filtered = filter === 'all'
    ? history
    : history.filter((h) => {
        const lvl = h.riskLevel.toLowerCase();
        if (filter === 'safe') return lvl.includes('safe') || lvl.includes('low');
        if (filter === 'medium') return lvl.includes('medium');
        if (filter === 'high') return lvl.includes('high') && !lvl.includes('critical');
        if (filter === 'critical') return lvl.includes('critical');
        return true;
      });

  const stats = {
    total: history.length,
    safe: history.filter((h) => h.riskLevel.toLowerCase().includes('safe') || h.score >= 75).length,
    atRisk: history.filter((h) => h.score < 75).length,
  };

  const handleViewReport = async (id: string) => {
    await fetchReport(id);
    navigate('/results');
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-headline text-3xl font-bold text-on-surface">Scan History</h1>
          <p className="text-on-surface-variant text-sm mt-1">Review all previous image privacy analyses.</p>
        </div>
        <div className="flex items-center gap-3">
          {history.length > 0 && (
            <button
              onClick={() => {
                if (confirm('Are you sure you want to clear all scan history?')) {
                  clearHistory();
                }
              }}
              className="btn-outline flex items-center gap-2 text-xs py-2.5 px-4 text-error border-error/30 hover:bg-error/10"
            >
              <Trash2 className="w-4 h-4" /> Clear All History
            </button>
          )}
          <button onClick={() => navigate('/upload')} className="btn-primary flex items-center gap-2 text-sm">
            <Plus className="w-4 h-4" /> New Analysis
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Scans', value: stats.total },
          { label: 'Safe Images', value: stats.safe, accent: 'text-primary' },
          { label: 'At Risk', value: stats.atRisk, accent: 'text-error' },
        ].map((s) => (
          <div key={s.label} className="card text-center py-6">
            <p className={`font-headline text-3xl font-bold ${s.accent ?? 'text-on-surface'}`}>{s.value}</p>
            <p className="text-xs text-on-surface-variant mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'safe', 'medium', 'high', 'critical'] as FilterType[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-widest transition-colors ${
              filter === f
                ? 'bg-primary text-on-primary'
                : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            {f === 'all' ? 'All Scans' : f}
          </button>
        ))}
      </div>

      {/* History Table */}
      <div className="card overflow-hidden p-0">
        {filtered.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <ShieldAlert className="w-10 h-10 text-outline mx-auto" />
            <p className="text-on-surface-variant text-sm">No scan history recorded yet.</p>
            <button onClick={() => navigate('/upload')} className="btn-outline text-xs inline-flex items-center gap-2">
              <Plus className="w-3.5 h-3.5" /> Start First Scan
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-outline-variant/20 text-xs text-on-surface-variant uppercase tracking-widest">
                <th className="text-left px-5 py-3 font-semibold">Image / Target</th>
                <th className="text-left px-5 py-3 font-semibold hidden sm:table-cell">Date</th>
                <th className="text-left px-5 py-3 font-semibold">Privacy Score</th>
                <th className="text-left px-5 py-3 font-semibold">Risk Tier</th>
                <th className="text-right px-5 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, i) => {
                const cfg = getLevelConfig(item.riskLevel);
                return (
                  <tr
                    key={item.id || i}
                    className={`border-b border-outline-variant/10 hover:bg-surface-container transition-colors ${
                      i % 2 === 0 ? '' : 'bg-surface-container-low/40'
                    }`}
                  >
                    <td className="px-5 py-4">
                      <span className="font-medium text-on-surface truncate block max-w-[200px]">{item.name}</span>
                    </td>
                    <td className="px-5 py-4 text-on-surface-variant hidden sm:table-cell text-xs">{item.timestamp}</td>
                    <td className="px-5 py-4">
                      <span className="font-headline font-bold text-lg text-on-surface">{item.score}</span>
                      <span className="text-xs text-on-surface-variant">/100</span>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`badge ${cfg.badge}`}>{cfg.label}</span>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleViewReport(item.id)}
                          className="p-2 rounded-lg bg-surface-container hover:bg-surface-container-high transition-colors text-on-surface-variant hover:text-primary flex items-center gap-1 text-xs"
                          title="View report"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span className="hidden md:inline">Report</span>
                        </button>
                        <button
                          onClick={() => deleteHistoryItem(item.id)}
                          className="p-2 rounded-lg bg-surface-container hover:bg-error-container/30 transition-colors text-on-surface-variant hover:text-error"
                          title="Delete scan"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default HistoryPage;
