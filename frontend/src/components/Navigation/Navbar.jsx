import React from 'react';
import { useData } from '../../context/DataContext';
import { useDataset } from '../../hooks/useDataset';
import { BarChart3, Database, Filter, Upload, RefreshCw, Menu, Bot } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, onToggleMobileSidebar, onToggleMobileCopilot }) {
  const { datasetInfo, filters } = useData();
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
        className="md:hidden p-2 rounded-xl border border-surface-border bg-surface-card text-content-secondary hover:text-content-primary hover:bg-surface-elevated transition-colors"
        aria-label="Toggle navigation menu"
      >
        <Menu className="w-4 h-4" />
      </button>

      {/* ── Brand ──────────────────────────────────────── */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-brand-600 to-accent-400
                        flex items-center justify-center text-white shadow-sm shadow-brand-500/30">
          <BarChart3 className="w-4 h-4" />
        </div>
        <div className="leading-none">
          <p className="text-sm font-bold text-content-primary tracking-tight">DataLens</p>
          <p className="label-caps mt-0.5 text-brand-400">Analytics AI</p>
        </div>
      </div>

      {/* ── Divider ────────────────────────────────────── */}
      <div className="hidden md:block h-5 w-px bg-surface-border shrink-0" />

      {/* ── Dataset pill (flexible, truncates) ─────────── */}
      <div className="hidden sm:flex items-center gap-2 min-w-0 flex-1
                      px-3 py-1.5 rounded-full bg-surface-card border border-surface-border">
        <Database className="w-3.5 h-3.5 text-brand-400 shrink-0" />
        <span className="body-xs font-medium text-content-primary truncate">
          {datasetInfo?.filename || 'No dataset loaded'}
        </span>
        {datasetInfo && (
          <span className="ml-auto shrink-0 px-2 py-0.5 text-[10px] font-semibold
                           bg-brand-500/10 text-brand-400 rounded-full border border-brand-500/20">
            {datasetInfo.shape?.[0]?.toLocaleString()} rows
          </span>
        )}
      </div>

      {/* ── Right actions ──────────────────────────────── */}
      <div className="flex items-center gap-2 shrink-0 ml-auto">
        {activeFilterCount > 0 && (
          <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full
                           bg-emerald-500/10 border border-emerald-500/25 body-xs text-emerald-400 font-semibold">
            <Filter className="w-3 h-3" />
            {activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''}
          </span>
        )}

        {/* Mobile AI Copilot Toggle Button (< lg) */}
        <button
          type="button"
          onClick={onToggleMobileCopilot}
          className="lg:hidden inline-flex items-center gap-1.5 px-3 py-2 body-xs font-semibold rounded-xl
                     border border-brand-500/30 bg-brand-500/10 text-brand-400 hover:bg-brand-500/20 transition-all"
          aria-label="Open AI Copilot"
        >
          <Bot className="w-4 h-4" />
          <span className="hidden xs:inline">Copilot</span>
        </button>

        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept=".csv,.xlsx,.xls"
          aria-label="Upload dataset file input"
          onChange={onFileSelect}
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          aria-label="Upload Dataset"
          className="inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 body-xs font-semibold rounded-xl
                     bg-gradient-to-r from-brand-600 to-accent-500 text-white
                     shadow-sm shadow-brand-500/25 hover:opacity-90 active:scale-95
                     transition-all disabled:opacity-50 whitespace-nowrap"
        >
          {loading
            ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Uploading…</>
            : <><Upload className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Upload Dataset</span><span className="sm:hidden">Upload</span></>
          }
        </button>
      </div>
    </header>
  );
}
