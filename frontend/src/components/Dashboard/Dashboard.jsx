import React, { useMemo } from 'react';
import { useData } from '../../context/DataContext';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  Legend,
} from 'recharts';

export default function Dashboard() {
  const { datasetInfo, filteredData } = useData();
  const previewRows = filteredData || [];
  const previewColumns = previewRows[0] ? Object.keys(previewRows[0]) : datasetInfo?.columns || [];
  const numericColumns = datasetInfo?.numeric_columns || [];
  const categoricalColumns = datasetInfo?.categorical_columns || [];

  const categoryCounts = useMemo(() => {
    if (categoricalColumns.length === 0 || previewRows.length === 0) {
      return [];
    }
    const key = categoricalColumns[0];
    const counts = previewRows.reduce((acc, row) => {
      const label = row[key] ?? 'Unknown';
      acc[label] = (acc[label] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10);
  }, [categoricalColumns, previewRows]);

  const scatterData = useMemo(() => {
    if (numericColumns.length < 2 || previewRows.length === 0) return [];
    const [xKey, yKey] = numericColumns;
    return previewRows
      .map((row, index) => ({
        x: Number(row[xKey]),
        y: Number(row[yKey]),
        label: row[categoricalColumns?.[0]] ?? `Row ${index + 1}`,
      }))
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
  }, [numericColumns, categoricalColumns, previewRows]);

  const lineData = useMemo(() => {
    if (numericColumns.length === 0 || previewRows.length === 0) return [];
    const key = numericColumns[0];
    return previewRows
      .map((row, index) => ({
        index: index + 1,
        value: Number(row[key]),
      }))
      .filter((item) => Number.isFinite(item.value));
  }, [numericColumns, previewRows]);

  if (!datasetInfo) {
    return (
      <section className="rounded-[2rem] border border-slate-800 bg-slate-950/75 p-6 shadow-xl shadow-slate-950/30">
        <p className="text-slate">No dataset loaded yet. Upload a file to view dashboard details.</p>
      </section>
    );
  }

  return (
    <section className="rounded-[2rem] border border-slate-800 bg-slate-950/75 p-6 shadow-xl shadow-slate-950/30">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-slate/70">Dataset dashboard</p>
          <h2 className="mt-3 text-2xl font-semibold text-surface">Interactive analytics</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 text-slate/80 text-sm">
          <div className="rounded-3xl bg-white/5 p-4">
            <p className="text-xs uppercase tracking-[0.35em]">Rows</p>
            <p className="mt-2 text-xl font-semibold text-surface">{datasetInfo.shape?.[0] ?? 'n/a'}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-4">
            <p className="text-xs uppercase tracking-[0.35em]">Columns</p>
            <p className="mt-2 text-xl font-semibold text-surface">{datasetInfo.shape?.[1] ?? 'n/a'}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2 min-w-0">
        <div className="rounded-3xl border border-slate-800 bg-[#111827]/80 p-5 min-w-0">
          <h3 className="mb-4 text-sm uppercase tracking-[0.35em] text-slate/70">Columns</h3>
          <div className="grid gap-3 sm:grid-cols-2 min-w-0">
            {datasetInfo.columns.map((column) => (
              <div key={column} className="rounded-3xl bg-slate-900/80 px-4 py-3 text-sm text-surface/90 break-words min-w-0">
                {column}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-[#111827]/80 p-5 min-w-0">
          <h3 className="mb-4 text-sm uppercase tracking-[0.35em] text-slate/70">Data types</h3>
          <div className="space-y-3 text-sm text-slate/80 min-w-0">
            {Object.entries(datasetInfo.dtypes).map(([column, dtype]) => (
              <div key={column} className="rounded-3xl bg-white/5 p-3 break-words min-w-0">
                <p className="font-medium text-surface">{column}</p>
                <p>{dtype}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        {scatterData.length > 0 ? (
          <div className="rounded-3xl border border-slate-800 bg-[#111827]/80 p-5">
            <h3 className="mb-4 text-sm uppercase tracking-[0.35em] text-slate/70">
              Scatter: {numericColumns[0]} vs {numericColumns[1]}
            </h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <CartesianGrid stroke="#334155" />
                  <XAxis type="number" dataKey="x" name={numericColumns[0]} />
                  <YAxis type="number" dataKey="y" name={numericColumns[1]} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter name="Data points" data={scatterData} fill="#38bdf8" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : numericColumns.length > 0 ? (
          <div className="rounded-3xl border border-slate-800 bg-[#111827]/80 p-5">
            <h3 className="mb-4 text-sm uppercase tracking-[0.35em] text-slate/70">
              Line: {numericColumns[0]}
            </h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lineData}>
                  <CartesianGrid stroke="#334155" />
                  <XAxis dataKey="index" name="Row" />
                  <YAxis dataKey="value" name={numericColumns[0]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="value" stroke="#38bdf8" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : null}

        {categoryCounts.length > 0 ? (
          <div className="rounded-3xl border border-slate-800 bg-[#111827]/80 p-5">
            <h3 className="mb-4 text-sm uppercase tracking-[0.35em] text-slate/70">
              Top values: {categoricalColumns[0]}
            </h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryCounts} layout="vertical" margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
                  <CartesianGrid stroke="#334155" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="name" width={120} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#60a5fa" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : null}
      </div>

      <div className="mt-6 rounded-3xl border border-slate-800 bg-[#111827]/80 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70">Preview</h3>
          <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs text-slate/70">Showing top 6 rows</span>
        </div>
        {previewRows.length === 0 ? (
          <p className="text-slate">No preview rows available.</p>
        ) : (
          <div className="overflow-x-auto rounded-3xl border border-slate-800 bg-slate-950/70 min-w-0">
            <table className="min-w-full max-w-full table-auto border-collapse text-left text-sm">
              <thead>
                <tr>
                  {previewColumns.map((column) => (
                    <th key={column} className="border-b border-slate-800 px-3 py-3 text-left text-xs uppercase tracking-[0.2em] text-slate/60 break-words">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.slice(0, 6).map((row, rowIndex) => (
                  <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-slate-900/60' : 'bg-slate-950/60'}>
                    {previewColumns.map((column) => (
                      <td key={column} className="border-b border-slate-800 px-3 py-3 text-surface break-words">
                        {String(row[column] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
