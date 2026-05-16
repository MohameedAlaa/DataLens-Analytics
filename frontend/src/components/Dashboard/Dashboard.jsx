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
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { Hash, Type, Calendar, Tag, Zap, TrendingUp, PieChart as PieIcon } from 'lucide-react';

const getDataTypeInfo = (dtype) => {
  if (dtype.includes('int') || dtype.includes('float')) {
    return { icon: Hash, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Numeric' };
  }
  if (dtype.includes('object') || dtype.includes('str')) {
    return { icon: Type, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Text' };
  }
  if (dtype.includes('datetime') || dtype.includes('date')) {
    return { icon: Calendar, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Date' };
  }
  if (dtype.includes('bool')) {
    return { icon: Zap, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Boolean' };
  }
  return { icon: Tag, color: 'text-slate-400', bg: 'bg-slate-500/10', label: 'Other' };
};

const CHART_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6'];

const getStats = (values) => {
  const nums = values.filter(v => Number.isFinite(v));
  if (nums.length === 0) return { min: 0, max: 0, avg: 0 };
  return {
    min: Math.min(...nums).toFixed(2),
    max: Math.max(...nums).toFixed(2),
    avg: (nums.reduce((a, b) => a + b, 0) / nums.length).toFixed(2),
  };
};

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
        <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900/60 to-[#111827]/80 p-6 shadow-lg shadow-blue-500/5 min-w-0">
          <div className="flex items-center gap-2 mb-5">
            <div className="h-8 w-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Tag className="w-4 h-4 text-blue-400" />
            </div>
            <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70 font-semibold">Columns</h3>
            <span className="ml-auto text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded-lg">{datasetInfo.columns.length}</span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 min-w-0">
            {datasetInfo.columns.map((column, idx) => (
              <div
                key={column}
                className="group relative rounded-2xl bg-gradient-to-br from-slate-800/50 to-slate-700/30 hover:from-slate-700/80 hover:to-slate-600/40 px-4 py-3 text-sm text-surface/90 break-words min-w-0 transition-all duration-300 cursor-default border border-slate-700/30 hover:border-slate-600/50 shadow-sm hover:shadow-md"
              >
                <div className="flex items-center gap-2">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400/60 group-hover:bg-cyan-300" />
                  {column}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900/60 to-[#111827]/80 p-6 shadow-lg shadow-purple-500/5 min-w-0">
          <div className="flex items-center gap-2 mb-5">
            <div className="h-8 w-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Zap className="w-4 h-4 text-purple-400" />
            </div>
            <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70 font-semibold">Data types</h3>
            <span className="ml-auto text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded-lg">{Object.keys(datasetInfo.dtypes).length}</span>
          </div>
          <div className="space-y-2 text-sm text-slate/80 min-w-0">
            {Object.entries(datasetInfo.dtypes).map(([column, dtype]) => {
              const typeInfo = getDataTypeInfo(dtype);
              const IconComponent = typeInfo.icon;
              return (
                <div
                  key={column}
                  className="group rounded-2xl bg-gradient-to-r from-slate-800/40 to-slate-700/20 hover:from-slate-700/60 hover:to-slate-600/30 p-3 break-words min-w-0 transition-all duration-300 border border-slate-700/30 hover:border-slate-600/50"
                >
                  <div className="flex items-start gap-3">
                    <div className={`${typeInfo.bg} ${typeInfo.color} p-2 rounded-lg flex-shrink-0 group-hover:scale-110 transition-transform`}>
                      <IconComponent className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-surface text-sm">{column}</p>
                      <p className="text-xs text-slate/60 mt-1">
                        <span className={`${typeInfo.bg} ${typeInfo.color} px-2 py-0.5 rounded text-xs font-medium`}>
                          {typeInfo.label}
                        </span>
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        {scatterData.length > 0 ? (
          <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-[#1e293b]/50 to-[#111827]/80 p-6 shadow-lg shadow-blue-500/10">
            <div className="flex items-center gap-2 mb-5">
              <div className="h-8 w-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Hash className="w-4 h-4 text-blue-400" />
              </div>
              <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70 font-semibold">
                Scatter: {numericColumns[0]} vs {numericColumns[1]}
              </h3>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis type="number" dataKey="x" name={numericColumns[0]} stroke="#94a3b8" />
                  <YAxis type="number" dataKey="y" name={numericColumns[1]} stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.75rem' }} />
                  <Scatter name="Data points" data={scatterData} fill="#3b82f6" fillOpacity={0.7} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : numericColumns.length > 0 ? (
          <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-[#1e293b]/50 to-[#111827]/80 p-6 shadow-lg shadow-cyan-500/10">
            <div className="flex items-center gap-2 mb-5">
              <div className="h-8 w-8 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
              </div>
              <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70 font-semibold">
                Trend: {numericColumns[0]}
              </h3>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={lineData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis dataKey="index" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.75rem' }} />
                  <Area type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#colorValue)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : null}

        {categoryCounts.length > 0 && (
          <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-[#1e293b]/50 to-[#111827]/80 p-6 shadow-lg shadow-emerald-500/10">
            <div className="flex items-center gap-2 mb-5">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <PieIcon className="w-4 h-4 text-emerald-400" />
              </div>
              <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70 font-semibold">
                Distribution: {categoricalColumns[0]}
              </h3>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={categoryCounts} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ${value}`} outerRadius={100} fill="#8884d8" dataKey="value">
                    {categoryCounts.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.75rem' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {categoryCounts.length > 0 && (
        <div className="mt-6 rounded-3xl border border-slate-800 bg-gradient-to-br from-[#1e293b]/50 to-[#111827]/80 p-6 shadow-lg shadow-blue-500/10">
          <div className="flex items-center gap-2 mb-5">
            <div className="h-8 w-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Hash className="w-4 h-4 text-blue-400" />
            </div>
            <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70 font-semibold">
              Categories: {categoricalColumns[0]}
            </h3>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryCounts} margin={{ left: 0, right: 30, top: 20, bottom: 20 }}>
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#1e40af" />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="#94a3b8" angle={-45} textAnchor="end" height={100} />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.75rem' }} />
                <Bar dataKey="value" fill="url(#barGradient)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {numericColumns.length > 0 && (
        <div className="mt-6 grid gap-4 grid-cols-1 sm:grid-cols-3">
          {numericColumns.slice(0, 3).map((col) => {
            const values = previewRows.map(r => Number(r[col])).filter(v => Number.isFinite(v));
            const stats = getStats(values);
            return (
              <div key={col} className="rounded-3xl border border-slate-800 bg-gradient-to-br from-[#1e293b]/60 to-[#111827]/80 p-6 shadow-lg shadow-amber-500/10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-surface">{col}</h3>
                  <div className="h-6 w-6 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <TrendingUp className="w-3 h-3 text-amber-400" />
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="p-3 rounded-2xl bg-slate-700/30 border border-slate-600/20">
                    <p className="text-xs text-slate/60 uppercase tracking-wider">Average</p>
                    <p className="text-lg font-bold text-cyan-300 mt-1">{stats.avg}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-xl bg-slate-700/20 border border-slate-600/20">
                      <p className="text-xs text-slate/60">Min</p>
                      <p className="text-sm font-semibold text-blue-300">{stats.min}</p>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-700/20 border border-slate-600/20">
                      <p className="text-xs text-slate/60">Max</p>
                      <p className="text-sm font-semibold text-emerald-300">{stats.max}</p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-6 rounded-3xl border border-slate-800 bg-gradient-to-br from-[#1e293b]/50 to-[#111827]/80 p-6 shadow-lg shadow-purple-500/10">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Type className="w-4 h-4 text-purple-400" />
            </div>
            <h3 className="text-sm uppercase tracking-[0.35em] text-slate/70 font-semibold">Data Preview</h3>
          </div>
          <span className="rounded-full bg-purple-500/20 text-purple-300 px-3 py-1 text-xs font-medium">Showing top 6 rows</span>
        </div>
        {previewRows.length === 0 ? (
          <p className="text-slate/70">No preview rows available.</p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-700/40">
            <table className="min-w-full table-auto text-sm">
              <thead className="bg-gradient-to-r from-slate-800/60 to-slate-700/40">
                <tr>
                  {previewColumns.map((column) => (
                    <th key={column} className="px-4 py-3 text-left text-xs uppercase tracking-[0.2em] text-slate/60 font-semibold border-b border-slate-700/40">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.slice(0, 6).map((row, rowIndex) => (
                  <tr key={rowIndex} className={`border-b border-slate-700/30 transition-all duration-200 hover:bg-slate-800/40 ${rowIndex % 2 === 0 ? 'bg-slate-900/30' : 'bg-slate-950/20'}`}>
                    {previewColumns.map((column) => (
                      <td key={column} className="px-4 py-3 text-surface/90 break-words">
                        <span className="inline-block px-2 py-1 rounded-lg bg-slate-800/50 border border-slate-700/30">
                          {String(row[column] ?? '—')}
                        </span>
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
