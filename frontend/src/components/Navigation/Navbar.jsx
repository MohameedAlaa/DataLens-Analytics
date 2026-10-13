import React from 'react';
import { useData } from '../../context/DataContext';
import { useDataset } from '../../hooks/useDataset';
import DataLensLogo from '../Brand/DataLensLogo';
import { Database, Filter, Upload, RefreshCw, Menu, Bot, X, Sparkles } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, onToggleMobileSidebar, onToggleMobileCopilot }) {
  const { datasetInfo, filters, clearDataset } = useData();
  const { handleUpload, loading } = useDataset();
  const fileInputRef = React.useRef(null);

  const activeFilterCount = filters ? Object.keys(filters).length : 0;

  const onFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (file) {
      await handleUpload(file);
    }
    // Reset input so same file can be re-uploaded
    if (e.target) {
      e.target.value = '';
    }
  };

  return (
    <header
      className="sticky top-0 z-40 h-16 w-full shrink-0
                 border-b border-surface-border bg-surface-bg/95 backdrop-blur-md
                 px-4 md:px-6 flex items-center gap-3 sm:gap-4"
    >
      {/* ── Mobile Menu Toggle Button (< md) ── */}
      <button
        type="button"
        onClick={onToggleMobileSidebar}
        className="md:hidden p-2 rounded-xl border border-surface-border bg-surface-card/80 text-content-secondary hover:text-content-primary hover:bg-surface-elevated transition-colors focus-visible:ring-2 focus-visible:ring-brand-400"
        aria-label="Toggle navigation menu"
      >
        <Menu className="w-4 h-4" />
      </button>

      {/* ── Brand Identity Logo ────────────────────────── */}
      <div className="shrink-0">
        <DataLensLogo size="md" variant="full" />
      </div>

      {/* ── Divider ────────────────────────────────────── */}
      <div className="hidden md:block h-6 w-px bg-surface-border/80 shrink-0 mx-1" />

      {/* ── Dataset Pill / Active Context Indicator ────── */}
      <div className="hidden sm:flex items-center gap-2.5 min-w-0 max-w-md flex-1
                      px-3.5 py-1.5 rounded-xl bg-surface-card/70 border border-surface-border shadow-inner">
        <Database className={`w-3.5 h-3.5 shrink-0 ${datasetInfo ? 'text-brand-400' : 'text-content-muted'}`} />
        {datasetInfo ? (
          <>
            <span className="body-xs font-medium text-content-primary truncate select-all" title={datasetInfo.filename}>
              {datasetInfo.filename}
            </span>
            <div className="ml-auto flex items-center gap-1.5 shrink-0">
              <span className="px-2 py-0.5 text-[10px] font-mono font-semibold
                               bg-brand-500/10 text-brand-300 rounded-md border border-brand-500/20">
                {(datasetInfo.shape?.[0] ?? 0).toLocaleString()} rows • {datasetInfo.shape?.[1] ?? 0} cols
              </span>
              <button
                type="button"
                onClick={clearDataset}
                title="Clear current dataset"
                aria-label="Clear current dataset"
                className="p-1 rounded-md text-content-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </>
        ) : (
          <span className="body-xs text-content-muted truncate">
            No dataset loaded • <span className="text-content-secondary">Upload CSV or Excel</span>
          </span>
        )}
      </div>

      {/* ── Right Action Controls ──────────────────────── */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 ml-auto">
        {activeFilterCount > 0 && (
          <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg
                           bg-emerald-500/10 border border-emerald-500/25 body-xs text-emerald-400 font-semibold font-mono">
            <Filter className="w-3 h-3" />
            {activeFilterCount} active filter{activeFilterCount > 1 ? 's' : ''}
          </span>
        )}

        {/* Mobile AI Copilot Drawer Toggle (< lg) */}
        <button
          type="button"
          onClick={onToggleMobileCopilot}
          className="lg:hidden inline-flex items-center gap-1.5 px-3 py-2 body-xs font-semibold rounded-xl
                     border border-brand-500/30 bg-brand-500/10 text-brand-400 hover:bg-brand-500/20
                     active:scale-95 transition-all"
          aria-label="Toggle AI Copilot"
        >
          <Bot className="w-4 h-4" />
          <span className="hidden xs:inline">Copilot</span>
        </button>

        {/* Hidden File Input */}
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept=".csv,.xlsx,.xls"
          aria-label="Upload dataset file input"
          onChange={onFileSelect}
        />

        {/* Upload Action Button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          aria-label="Upload Dataset"
          className="btn-primary"
        >
          {loading ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Uploading…</span>
            </>
          ) : (
            <>
              <Upload className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Upload Dataset</span>
              <span className="sm:hidden">Upload</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
