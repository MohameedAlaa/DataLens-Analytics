import React, { useRef } from 'react';
import { useDataset } from '../../hooks/useDataset';

export default function Upload() {
  const { handleUpload, loading, error, datasetInfo } = useDataset();
  const inputRef = useRef(null);

  const onFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) await handleUpload(file);
  };

  const onDrop = async (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) await handleUpload(file);
  };

  const onDragOver = (e) => e.preventDefault();

  return (
    <section
      className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-xl shadow-slate-950/30"
      onDrop={onDrop}
      onDragOver={onDragOver}
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-surface">Upload data</h3>
          <p className="text-sm text-slate/70">Drag and drop a CSV or Excel file, or browse to upload.</p>
        </div>

        <button
          className="rounded-full bg-electric px-5 py-3 text-sm font-semibold text-navy shadow-lg shadow-electric/20 transition hover:bg-electric/90"
          onClick={() => inputRef.current && inputRef.current.click()}
        >
          Browse files
        </button>

        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          ref={inputRef}
          style={{ display: 'none' }}
          onChange={onFileChange}
        />

        {loading && <p className="text-sm text-slate/70">Uploading…</p>}
        {error && <p className="text-sm text-red-400">{error}</p>}

        {datasetInfo && (
          <div className="mt-4 rounded-3xl bg-white/5 px-4 py-3 text-left text-sm text-slate/80">
            <p className="font-semibold text-surface">Current file</p>
            <p className="mt-2">{datasetInfo.filename}</p>
            <p className="mt-1">Rows: {datasetInfo.shape[0]}, Columns: {datasetInfo.shape[1]}</p>
          </div>
        )}
      </div>
    </section>
  );
}
