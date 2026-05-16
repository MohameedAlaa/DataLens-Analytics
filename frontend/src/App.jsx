import React from 'react';
import Upload from './components/Upload/Upload';
import Dashboard from './components/Dashboard/Dashboard';
import Filters from './components/Filters/Filters';
import Chatbot from './components/Chatbot/Chatbot';
import { useData } from './context/DataContext';

export default function App() {
  const { datasetInfo, filteredData, filters } = useData();
  return (
    <div className="min-h-screen bg-[#020617] text-surface">
      <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur-xl px-6 py-6 shadow-sm shadow-slate-950/20">
        <div className="mx-auto flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between max-w-[1600px]">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-slate/60">DataLens Analytics</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-surface">System Overview</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate/500">Professional dataset insight, filtering, and conversational analysis in one responsive workspace.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-2xl bg-slate-900/80 px-4 py-2 text-sm text-surface/90 shadow-inner">
              {datasetInfo?.filename || 'No dataset selected'}
            </span>
            {filters && Object.keys(filters).length > 0 && (
              <span className="rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-3 py-1 text-xs font-semibold shadow-sm">
                {Object.keys(filters).length} filters active
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] gap-6 px-6 py-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="space-y-6 min-w-0">
          <div className="rounded-[2rem] border border-slate-800 bg-slate-950/75 p-5 shadow-xl shadow-slate-950/30">
            <div>
              <p className="text-sm uppercase tracking-[0.4em] text-slate/70">Current dataset</p>
              <h2 className="mt-3 text-xl font-semibold text-surface">{datasetInfo?.filename || 'No dataset loaded'}</h2>
            </div>
            <div className="mt-6 space-y-3 text-sm text-slate/80">
              <div className="rounded-3xl bg-white/5 p-3">
                <p className="text-surface font-semibold">Rows</p>
                <p className="mt-2 text-2xl font-semibold text-surface">{datasetInfo?.shape?.[0] ?? '—'}</p>
              </div>
              <div className="rounded-3xl bg-white/5 p-3">
                <p className="text-surface font-semibold">Columns</p>
                <p className="mt-2 text-2xl font-semibold text-surface">{datasetInfo?.shape?.[1] ?? '—'}</p>
              </div>
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-800 bg-slate-950/75 p-5 shadow-xl shadow-slate-950/30">
            <h2 className="text-sm uppercase tracking-[0.35em] text-slate/70">Quick actions</h2>
            <div className="mt-5 space-y-4">
              <Upload />
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-800 bg-slate-950/75 p-5 shadow-xl shadow-slate-950/30">
            <h2 className="text-sm uppercase tracking-[0.35em] text-slate/70">Filters</h2>
            <div className="mt-4">
              <Filters />
            </div>
          </div>
        </aside>

        <main className="space-y-6 min-w-0">
          <div className="grid gap-6 xl:grid-cols-[2fr_1fr] min-w-0">
            <div className="rounded-[2rem] border border-slate-800 bg-slate-950/80 p-6 shadow-xl shadow-slate-950/30 min-w-0">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm uppercase tracking-[0.35em] text-slate/70">Dataset summary</p>
                  <h3 className="mt-3 text-2xl font-semibold text-surface">Snapshot of your uploaded data</h3>
                </div>
                <span className="rounded-full bg-electric/15 px-3 py-1 text-xs font-semibold text-electric">
                  {datasetInfo?.filename ?? 'No file'}
                </span>
              </div>
              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                <div className="rounded-3xl bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate/60">Total rows</p>
                  <p className="mt-3 text-3xl font-semibold text-surface">{datasetInfo?.shape?.[0] ?? '—'}</p>
                  <p className="mt-2 text-sm text-slate/70">Rows in the uploaded dataset</p>
                </div>
                <div className="rounded-3xl bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate/60">Total columns</p>
                  <p className="mt-3 text-3xl font-semibold text-surface">{datasetInfo?.shape?.[1] ?? '—'}</p>
                  <p className="mt-2 text-sm text-slate/70">Columns available for analysis</p>
                </div>
                <div className="rounded-3xl bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate/60">Preview rows</p>
                  <p className="mt-3 text-3xl font-semibold text-emerald-300">{filteredData?.length ?? 0}</p>
                  <p className="mt-2 text-sm text-slate/70">Rows currently loaded into the dashboard</p>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-800 bg-slate-950/80 p-6 shadow-xl shadow-slate-950/30">
              <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70">Data composition</h3>
              <div className="mt-6 grid gap-4">
                <div className="rounded-3xl bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate/60">Numeric columns</p>
                  <p className="mt-3 text-xl font-semibold text-surface">{datasetInfo?.numeric_columns?.length ?? 0}</p>
                  <p className="mt-2 text-sm text-slate/70">Ready for numerical analysis</p>
                </div>
                <div className="rounded-3xl bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate/60">Categorical columns</p>
                  <p className="mt-3 text-xl font-semibold text-surface">{datasetInfo?.categorical_columns?.length ?? 0}</p>
                  <p className="mt-2 text-sm text-slate/70">Ideal for grouping and distribution checks</p>
                </div>
                <div className="rounded-3xl bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate/60">Date columns</p>
                  <p className="mt-3 text-xl font-semibold text-surface">{datasetInfo?.date_columns?.length ?? 0}</p>
                  <p className="mt-2 text-sm text-slate/70">Useful for trend and time-series views</p>
                </div>
              </div>
            </div>
          </div>

          <Dashboard />
        </main>
      </div>
      <Chatbot />
    </div>
  );
}
