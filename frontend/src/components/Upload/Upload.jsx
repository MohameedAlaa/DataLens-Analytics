import React, { useRef } from 'react';
import { useDataset } from '../../hooks/useDataset';
import { Upload as UploadIcon, AlertCircle, RefreshCw, FileText } from 'lucide-react';

export default function Upload() {
  const { handleUpload, loading, error, datasetInfo } = useDataset();
  const inputRef = useRef(null);

  const onFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (file) {
      await handleUpload(file);
    }
    // Always reset input value so re-uploading the exact same file works
    if (e.target) {
      e.target.value = '';
    }
  };

  const onDrop = async (e) => {
    e.preventDefault();
    if (loading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await handleUpload(file);
    }
  };

  const onDragOver = (e) => e.preventDefault();

  return (
    <section
      className="rounded-3xl border border-surface-border bg-surface-card p-6 shadow-xl"
      onDrop={onDrop}
      onDragOver={onDragOver}
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="space-y-1.5">
          <h3 className="heading-sm text-content-primary">Upload data</h3>
          <p className="body-xs text-content-secondary">
            Drag and drop a CSV or Excel file (.csv, .xlsx, .xls), or browse to upload.
          </p>
        </div>

        <button
          disabled={loading}
          aria-label="Browse files to upload"
          className="rounded-full bg-brand-500 px-5 py-2.5 body-xs font-semibold text-white shadow-lg shadow-brand-500/20 transition hover:bg-brand-600 disabled:opacity-50 flex items-center gap-2"
          onClick={() => inputRef.current && inputRef.current.click()}
        >
          {loading ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Uploading…</span>
            </>
          ) : (
            <>
              <UploadIcon className="w-3.5 h-3.5" />
              <span>Browse files</span>
            </>
          )}
        </button>

        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          ref={inputRef}
          aria-label="Select dataset file"
          style={{ display: 'none' }}
          onChange={onFileChange}
        />

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl body-xs text-left max-w-md">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {datasetInfo && (
          <div className="mt-2 rounded-2xl bg-surface-elevated/40 border border-surface-border px-4 py-3 text-left body-xs text-content-secondary space-y-1 w-full max-w-sm">
            <div className="flex items-center gap-2 font-semibold text-content-primary">
              <FileText className="w-3.5 h-3.5 text-brand-400" />
              <span className="truncate">{datasetInfo.filename}</span>
            </div>
            <p className="text-[11px] text-content-muted">
              Rows: {(datasetInfo?.shape?.[0] ?? 0).toLocaleString()} • Columns: {datasetInfo?.shape?.[1] ?? 0}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
