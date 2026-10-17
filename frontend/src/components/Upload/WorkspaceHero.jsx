import React, { useState, useRef } from 'react';
import { useDataset } from '../../hooks/useDataset';
import DataLensLogo from '../Brand/DataLensLogo';
import {
  Upload as UploadIcon, FileSpreadsheet, Sparkles,
  BarChart3, ShieldCheck, Zap, AlertCircle, RefreshCw,
  ArrowRight, FileText, CheckCircle2
} from 'lucide-react';

export default function WorkspaceHero() {
  const { handleUpload, loading, error } = useDataset();
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const sampleDatasets = [
    {
      name: 'Global Sales & Operations',
      filename: 'sample_sales_analytics.csv',
      rows: '4 rows • 5 columns',
      data: `country,product,sales,customers,date
USA,Laptop,1200,10,2026-01-01
USA,Phone,800,8,2026-01-02
Egypt,Laptop,900,7,2026-01-03
Egypt,Phone,600,6,2026-01-04`,
    },
    {
      name: 'Enterprise Revenue & Tiers',
      filename: 'sample_enterprise_tiers.csv',
      rows: '4 rows • 5 columns',
      data: `region,tier,revenue,units,quarter
North,Enterprise,5000,20,Q1
South,SMB,3000,15,Q2
East,Mid-Market,4200,18,Q1
West,Enterprise,6100,25,Q2`,
    },
  ];

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (file) {
      await handleUpload(file);
    }
    if (e.target) e.target.value = '';
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (loading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await handleUpload(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!isDragOver) setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const loadSampleDataset = async (sample) => {
    if (loading) return;
    const blob = new Blob([sample.data], { type: 'text/csv' });
    const file = new File([blob], sample.filename, { type: 'text/csv' });
    await handleUpload(file);
  };

  return (
    <div className="py-6 sm:py-10 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* ── Brand Header & Value Proposition ─────────────────── */}
      <div className="text-center space-y-3.5">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-medium">
          <Sparkles className="w-3.5 h-3.5 text-brand-400" />
          <span>Intelligent Multi-Dimensional Analytics</span>
        </div>

        <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-content-primary">
          Turn Raw Datasets into{' '}
          <span className="text-brand-400">
            Actionable Intelligence
          </span>
        </h1>

        <p className="text-sm sm:text-base text-content-secondary max-w-2xl mx-auto leading-relaxed">
          Upload any CSV or Excel file to unlock automated health checks, distribution curves,
          correlation matrices, and conversational queries powered by Google Gemini 2.5 Flash.
        </p>
      </div>

      {/* ── Interactive Drag & Drop Area ──────────────────────── */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !loading && inputRef.current?.click()}
        className={`
          relative rounded-3xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200
          border-2 border-dashed
          ${isDragOver
            ? 'border-brand-400 bg-brand-500/10 shadow-glow-brand scale-[1.01]'
            : 'border-surface-border hover:border-brand-500/50 bg-surface-card/60 hover:bg-surface-card/90 shadow-card'
          }
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-bg
        `}
        role="button"
        tabIndex={0}
        aria-label="Upload dataset dropzone"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        <input
          type="file"
          ref={inputRef}
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="hidden"
          aria-hidden="true"
        />

        <div className="flex flex-col items-center gap-4">
          <div className={`
            w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-200
            ${loading
              ? 'bg-brand-500/20 text-brand-400 animate-pulse'
              : 'bg-brand-500/10 border border-brand-500/20 text-brand-400 shadow-inner'
            }
          `}>
            {loading ? (
              <RefreshCw className="w-8 h-8 animate-spin" />
            ) : (
              <UploadIcon className="w-8 h-8 transition-transform group-hover:-translate-y-1" />
            )}
          </div>

          <div className="space-y-1.5">
            <h2 className="text-base sm:text-lg font-bold text-content-primary">
              {loading ? 'Processing & Vectorizing Dataset…' : 'Drop your dataset file here, or click to browse'}
            </h2>
            <p className="body-xs text-content-secondary max-w-md mx-auto">
              Supports standard tabular formats: <span className="font-semibold text-content-primary">CSV</span>,{' '}
              <span className="font-semibold text-content-primary">Excel (.xlsx, .xls)</span> up to 50MB
            </p>
          </div>

          {/* Supported Format Pills */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
            <span className="px-2.5 py-1 rounded-lg bg-surface-elevated/70 border border-surface-border body-xs text-content-secondary flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-brand-400" /> CSV
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-surface-elevated/70 border border-surface-border body-xs text-content-secondary flex items-center gap-1.5">
              <FileSpreadsheet className="w-3.5 h-3.5 text-brand-400" /> Excel
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-surface-elevated/70 border border-surface-border body-xs text-content-secondary flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-terracotta-400" /> Isolated & Secure
            </span>
          </div>

          <button
            type="button"
            disabled={loading}
            className="btn-primary mt-3 px-6 py-2.5 text-sm"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Ingesting Data…</span>
              </>
            ) : (
              <>
                <UploadIcon className="w-4 h-4" />
                <span>Select File from Computer</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Error Feedback Banner ────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/25 flex items-start gap-3 text-red-300 text-xs animate-in slide-in-from-top-2">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-red-300">Upload Encountered An Issue</p>
            <p className="text-red-400/90 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* ── One-Click Sample Datasets ─────────────────────────── */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <p className="label-caps">Or explore with curated sample datasets</p>
          <span className="text-[11px] text-content-muted">Instant 1-Click Load</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {sampleDatasets.map((sample) => (
            <button
              key={sample.name}
              type="button"
              disabled={loading}
              onClick={(e) => {
                e.stopPropagation();
                loadSampleDataset(sample);
              }}
              className="p-4 rounded-2xl border border-surface-border bg-surface-card/70 hover:bg-surface-elevated/80
                         hover:border-brand-500/30 text-left transition-all duration-150 active:scale-[0.98] group flex items-center justify-between
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-brand-400 shrink-0" />
                  <span className="text-xs font-bold text-content-primary group-hover:text-brand-300 transition-colors">
                    {sample.name}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-content-muted">{sample.rows}</p>
              </div>
              <div className="p-2 rounded-xl bg-surface-elevated text-content-muted group-hover:text-brand-400 group-hover:bg-brand-500/10 transition-colors">
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Feature Highlights Grid ───────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-surface-border/60">
        <div className="p-4 rounded-2xl bg-surface-card/60 border border-surface-border space-y-2">
          <div className="w-8 h-8 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
            <BarChart3 className="w-4 h-4" />
          </div>
          <h3 className="text-xs font-bold text-content-primary">Deterministic Math</h3>
          <p className="text-[11px] text-content-secondary leading-relaxed">
            Exact mathematical aggregates, variance calculations, and outlier bounds computed with zero hallucination.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-surface-card/60 border border-surface-border space-y-2">
          <div className="w-8 h-8 rounded-xl bg-terracotta-500/10 border border-terracotta-500/20 flex items-center justify-center text-terracotta-400">
            <Zap className="w-4 h-4" />
          </div>
          <h3 className="text-xs font-bold text-content-primary">ChromaDB Vector RAG</h3>
          <p className="text-[11px] text-content-secondary leading-relaxed">
            Semantic row indexing with Google Gemini embeddings and verifiable row-level citations for every insight.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-surface-card/60 border border-surface-border space-y-2">
          <div className="w-8 h-8 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h3 className="text-xs font-bold text-content-primary">Dataset Isolation</h3>
          <p className="text-[11px] text-content-secondary leading-relaxed">
            Strict session encapsulation guarantees zero cross-dataset leakage between uploads or model turns.
          </p>
        </div>
      </div>
    </div>
  );
}
