import React, { useMemo, memo, useState, useCallback } from 'react';
import { useData } from '../../context/DataContext';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, AreaChart, Area, ScatterChart, Scatter, ZAxis,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ComposedChart,
} from 'recharts';
import {
  TrendingUp, PieChart as PieIcon, BarChart3, ScatterChart as ScatterIcon,
  Table as TableIcon, Layers, Activity, GitBranch, Grid3x3, Sigma,
  ChevronDown,
} from 'lucide-react';
import AdvancedDataTable from './AdvancedDataTable';

// ── Palette ──────────────────────────────────────────────────────────────────
const PALETTE = [
  '#0ea5e9', '#06b6d4', '#10b981', '#f59e0b',
  '#8b5cf6', '#ec4899', '#3b82f6', '#f97316',
];

const TOOLTIP_STYLE = {
  backgroundColor: '#0f172a',
  borderColor: '#334155',
  borderRadius: '0.75rem',
  fontSize: '11px',
  color: '#f8fafc',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Down-sample rows for trend charts to avoid overplotting */
function sampleRows(rows, maxPts = 300) {
  if (rows.length <= maxPts) return rows;
  const step = Math.ceil(rows.length / maxPts);
  return rows.filter((_, i) => i % step === 0);
}

/** Build histogram bins for a numeric column */
function buildHistogram(rows, col, bins = 20) {
  const vals = rows.map(r => Number(r[col])).filter(v => Number.isFinite(v));
  if (!vals.length) return [];
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const binSize = (max - min) / bins || 1;
  const counts = Array.from({ length: bins }, (_, i) => ({
    bin: `${(min + i * binSize).toFixed(1)}`,
    count: 0,
    range: [min + i * binSize, min + (i + 1) * binSize],
  }));
  vals.forEach(v => {
    const idx = Math.min(bins - 1, Math.floor((v - min) / binSize));
    counts[idx].count++;
  });
  return counts;
}

/** Build box-plot stat for a column */
function boxStats(rows, col) {
  const vals = rows.map(r => Number(r[col])).filter(v => Number.isFinite(v)).sort((a, b) => a - b);
  if (vals.length < 4) return null;
  const q1 = vals[Math.floor(vals.length * 0.25)];
  const median = vals[Math.floor(vals.length * 0.5)];
  const q3 = vals[Math.floor(vals.length * 0.75)];
  const iqr = q3 - q1;
  return {
    col,
    min: Math.max(vals[0], q1 - 1.5 * iqr),
    q1, median, q3,
    max: Math.min(vals[vals.length - 1], q3 + 1.5 * iqr),
    lowerFence: q1 - 1.5 * iqr,
    upperFence: q3 + 1.5 * iqr,
  };
}

/** Build correlation heatmap cells */
function buildHeatmapCells(rows, numericCols) {
  if (numericCols.length < 2) return [];
  // Precompute numeric arrays once per column instead of N*N times
  const colData = {};
  for (const c of numericCols) {
    colData[c] = rows.map(r => Number(r[c])).filter(v => Number.isFinite(v));
  }

  const cells = [];
  for (let i = 0; i < numericCols.length; i++) {
    for (let j = 0; j < numericCols.length; j++) {
      const a = numericCols[i], b = numericCols[j];
      const pairsA = colData[a];
      const pairsB = colData[b];
      const n = Math.min(pairsA.length, pairsB.length);
      let corr = i === j ? 1 : 0;
      if (n > 2 && i !== j) {
        const meanA = pairsA.slice(0, n).reduce((s, v) => s + v, 0) / n;
        const meanB = pairsB.slice(0, n).reduce((s, v) => s + v, 0) / n;
        let cov = 0, varA = 0, varB = 0;
        for (let k = 0; k < n; k++) {
          const da = pairsA[k] - meanA, db = pairsB[k] - meanB;
          cov += da * db; varA += da * da; varB += db * db;
        }
        const denom = Math.sqrt(varA * varB);
        corr = denom > 0 ? Number((cov / denom).toFixed(2)) : 0;
      }
      cells.push({ x: a, y: b, corr });
    }
  }
  return cells;
}

/** Interpolate red-green for correlation values [-1, 1] */
function corrColor(val) {
  if (val >= 0) {
    const t = val;
    return `rgba(16,185,129,${0.15 + t * 0.65})`;   // emerald
  }
  const t = -val;
  return `rgba(239,68,68,${0.15 + t * 0.65})`;       // red
}

// ── Shared card wrapper ───────────────────────────────────────────────────────
function ChartCard({ id, title, icon: Icon, iconColor, badge, accentClass, children, selector }) {
  return (
    <div
      id={id}
      className={`p-4 sm:p-5 rounded-2xl border border-surface-border bg-surface-card
        flex flex-col space-y-3 shadow-sm transition-all duration-200
        hover:shadow-md ${accentClass || 'hover:border-brand-500/20'}`}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 body-xs font-bold text-content-primary">
          <div className={`p-1.5 rounded-lg border ${iconColor || 'bg-brand-500/10 text-brand-400 border-brand-500/20'}`}>
            <Icon className="w-4 h-4" />
          </div>
          <span>{title}</span>
          {badge && (
            <span className="ml-1 text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              {badge}
            </span>
          )}
        </div>
        {selector}
      </div>
      {children}
    </div>
  );
}

// ── Col selector ──────────────────────────────────────────────────────────────
function ColSelect({ value, options, onChange, accent = 'brand' }) {
  if (!options || options.length <= 1) return null;
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className={`bg-surface-elevated border border-surface-border body-xs text-content-primary
        rounded-lg px-2.5 py-1 focus:outline-none focus:border-${accent}-500 transition-colors`}
    >
      {options.map(c => <option key={c} value={c}>{c}</option>)}
    </select>
  );
}

// ── Empty chart placeholder ───────────────────────────────────────────────────
function EmptyChart({ message }) {
  return (
    <div className="h-56 flex items-center justify-center body-xs text-content-secondary italic">
      {message}
    </div>
  );
}

// ── CHART 1 — Numeric Trend (sampled area chart) ──────────────────────────────
function NumericTrendChart({ rows, numericColumns }) {
  const [col, setCol] = useState(numericColumns[0] || '');
  const active = col || numericColumns[0];

  const data = useMemo(() => {
    if (!active || !rows.length) return [];
    const sampled = sampleRows(rows, 300);
    return sampled
      .map((r, i) => ({ i: i + 1, v: Number(r[active]) }))
      .filter(d => Number.isFinite(d.v));
  }, [active, rows]);

  return (
    <ChartCard
      title={`Trend — ${active || 'N/A'}`}
      icon={TrendingUp}
      iconColor="bg-brand-500/10 text-brand-400 border-brand-500/20"
      accentClass="hover:border-brand-500/20"
      selector={<ColSelect value={active} options={numericColumns} onChange={setCol} />}
    >
      <div className="h-56 w-full">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
              <defs>
                <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.7} />
                  <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="i" stroke="#64748b" fontSize={9} tickLine={false} label={{ value: `row (sampled)`, position: 'insideBottomRight', offset: -4, fontSize: 8, fill: '#64748b' }} />
              <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => [v.toFixed(2), active]} />
              <Area type="monotone" dataKey="v" stroke="#0ea5e9" strokeWidth={1.5} fillOpacity={1} fill="url(#trendGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : <EmptyChart message="No numeric data available." />}
      </div>
    </ChartCard>
  );
}

// ── CHART 2 — Histogram ───────────────────────────────────────────────────────
function HistogramChart({ rows, numericColumns }) {
  const [col, setCol] = useState(numericColumns[0] || '');
  const active = col || numericColumns[0];

  const bins = useMemo(() => buildHistogram(rows, active, 20), [active, rows]);

  return (
    <ChartCard
      title={`Histogram — ${active || 'N/A'}`}
      icon={BarChart3}
      iconColor="bg-purple-500/10 text-purple-400 border-purple-500/20"
      accentClass="hover:border-purple-500/20"
      selector={<ColSelect value={active} options={numericColumns} onChange={setCol} accent="purple" />}
    >
      <div className="h-56 w-full">
        {bins.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bins} margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="bin" stroke="#64748b" fontSize={8} tickLine={false} interval="preserveStartEnd" />
              <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n, p) => [v, `freq [${Number(p.payload.range?.[0]).toFixed(1)}, ${Number(p.payload.range?.[1]).toFixed(1)})`]} />
              <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} maxBarSize={32} />
            </BarChart>
          </ResponsiveContainer>
        ) : <EmptyChart message="Insufficient numeric data for histogram." />}
      </div>
    </ChartCard>
  );
}

// ── CHART 3 — Scatter Plot ────────────────────────────────────────────────────
function ScatterPlotChart({ rows, numericColumns }) {
  const [colX, setColX] = useState(numericColumns[0] || '');
  const [colY, setColY] = useState(numericColumns[1] || numericColumns[0] || '');
  const activeX = colX || numericColumns[0];
  const activeY = colY || numericColumns[1] || numericColumns[0];

  const data = useMemo(() => {
    if (!activeX || !activeY || !rows.length) return [];
    return sampleRows(rows, 400)
      .map(r => ({ x: Number(r[activeX]), y: Number(r[activeY]) }))
      .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
  }, [activeX, activeY, rows]);

  return (
    <ChartCard
      title={`Scatter — ${activeX} vs ${activeY}`}
      icon={ScatterIcon}
      iconColor="bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
      accentClass="hover:border-cyan-500/20"
      selector={
        <div className="flex items-center gap-1.5 flex-wrap">
          <ColSelect value={activeX} options={numericColumns} onChange={setColX} accent="cyan" />
          <span className="body-xs text-content-muted">vs</span>
          <ColSelect value={activeY} options={numericColumns} onChange={setColY} accent="cyan" />
        </div>
      }
    >
      <div className="h-56 w-full">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="x" type="number" name={activeX} stroke="#64748b" fontSize={9} tickLine={false} />
              <YAxis dataKey="y" type="number" name={activeY} stroke="#64748b" fontSize={9} tickLine={false} />
              <ZAxis range={[12, 12]} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ strokeDasharray: '3 3' }} formatter={(v, n) => [Number(v).toFixed(2), n]} />
              <Scatter data={data} fill="#06b6d4" fillOpacity={0.65} />
            </ScatterChart>
          </ResponsiveContainer>
        ) : <EmptyChart message="Select two different numeric columns." />}
      </div>
    </ChartCard>
  );
}

// ── CHART 4 — Categorical Bar ─────────────────────────────────────────────────
function CategoricalBarChart({ rows, catColumns }) {
  const [col, setCol] = useState(catColumns[0] || '');
  const active = col || catColumns[0];

  const data = useMemo(() => {
    if (!active || !rows.length) return [];
    const counts = {};
    rows.forEach(r => { const v = String(r[active] ?? 'null'); counts[v] = (counts[v] || 0) + 1; });
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 15);
  }, [active, rows]);

  return (
    <ChartCard
      title={`Distribution — ${active || 'N/A'}`}
      icon={BarChart3}
      iconColor="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      accentClass="hover:border-emerald-500/20"
      selector={<ColSelect value={active} options={catColumns} onChange={setCol} accent="emerald" />}
    >
      <div className="h-56 w-full">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 4, bottom: 0 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" stroke="#64748b" fontSize={9} tickLine={false} />
              <YAxis type="category" dataKey="name" stroke="#64748b" fontSize={8} tickLine={false} width={90} tick={{ fill: '#94a3b8' }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={20}>
                {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : <EmptyChart message="No categorical data available." />}
      </div>
    </ChartCard>
  );
}

// ── CHART 5 — Pie Chart ───────────────────────────────────────────────────────
function PieChartCard({ rows, catColumns }) {
  const [col, setCol] = useState(catColumns[0] || '');
  const active = col || catColumns[0];

  const data = useMemo(() => {
    if (!active || !rows.length) return [];
    const counts = {};
    rows.forEach(r => { const v = String(r[active] ?? 'null'); counts[v] = (counts[v] || 0) + 1; });
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [active, rows]);

  const RADIAN = Math.PI / 180;
  const renderLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
    if (percent < 0.05) return null;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.6;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={9} fontWeight="600">{`${(percent * 100).toFixed(0)}%`}</text>;
  };

  return (
    <ChartCard
      title={`Segments — ${active || 'N/A'}`}
      icon={PieIcon}
      iconColor="bg-amber-500/10 text-amber-400 border-amber-500/20"
      accentClass="hover:border-amber-500/20"
      selector={<ColSelect value={active} options={catColumns} onChange={setCol} accent="amber" />}
    >
      <div className="h-56 w-full">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} cx="50%" cy="50%" outerRadius={80} dataKey="value" labelLine={false} label={renderLabel}>
                {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, name) => [v, name]} />
            </PieChart>
          </ResponsiveContainer>
        ) : <EmptyChart message="No categorical data for pie chart." />}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
        {data.slice(0, 6).map((d, i) => (
          <div key={i} className="flex items-center gap-1 body-xs text-content-secondary">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: PALETTE[i % PALETTE.length] }} />
            <span className="truncate max-w-[80px]">{d.name}</span>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

// ── CHART 6 — Box Plot (custom via ComposedChart) ─────────────────────────────
function BoxPlotChart({ rows, numericColumns }) {
  const cols = numericColumns.slice(0, 6);

  const data = useMemo(() =>
    cols.map(c => boxStats(rows, c)).filter(Boolean),
  [rows, cols]);

  return (
    <ChartCard
      title="Box Plot — IQR Distribution"
      icon={Activity}
      iconColor="bg-rose-500/10 text-rose-400 border-rose-500/20"
      accentClass="hover:border-rose-500/20"
      badge={`${data.length} columns`}
    >
      <div className="h-56 w-full">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={data}
              margin={{ top: 8, right: 8, left: -22, bottom: 20 }}
            >
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="col" stroke="#64748b" fontSize={8} tickLine={false} interval={0} angle={-30} textAnchor="end" />
              <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0]?.payload;
                  if (!d) return null;
                  return (
                    <div style={{ ...TOOLTIP_STYLE, padding: '8px 12px', border: '1px solid #334155' }}>
                      <p style={{ fontWeight: 700, marginBottom: 4 }}>{d.col}</p>
                      {[['Min', d.min], ['Q1', d.q1], ['Median', d.median], ['Q3', d.q3], ['Max', d.max]].map(([k, v]) => (
                        <p key={k} style={{ margin: '1px 0' }}><span style={{ color: '#94a3b8' }}>{k}: </span>{Number(v).toFixed(2)}</p>
                      ))}
                    </div>
                  );
                }}
              />
              {/* IQR box (q3 - q1) stacked on top of q1 baseline */}
              <Bar dataKey="q1" stackId="box" fill="transparent" stroke="transparent" />
              <Bar dataKey={() => null} stackId="box" fill="transparent">
                {data.map((d, i) => (
                  <Cell
                    key={i}
                    fill={PALETTE[i % PALETTE.length]}
                    fillOpacity={0.4}
                    stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1.5}
                  />
                ))}
              </Bar>
              {/* Median line */}
              <Bar
                dataKey="median"
                fill="transparent"
                stroke="transparent"
                label={{ position: 'top', fontSize: 8, fill: '#94a3b8', formatter: v => v?.toFixed(1) }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        ) : <EmptyChart message="Need at least 4 rows per numeric column for box stats." />}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {data.map((d, i) => (
          <div key={d.col} className="flex items-center gap-1.5 body-xs text-content-secondary">
            <span className="w-2 h-2 rounded-sm" style={{ background: PALETTE[i % PALETTE.length], opacity: 0.8 }} />
            <span className="truncate max-w-[80px]">{d.col}</span>
            <span className="text-content-muted">M={Number(d.median).toFixed(1)}</span>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

// ── CHART 7 — Correlation Heatmap ─────────────────────────────────────────────
function CorrelationHeatmap({ rows, numericColumns }) {
  const cols = numericColumns.slice(0, 8);
  const cells = useMemo(() => buildHeatmapCells(sampleRows(rows, 500), cols), [rows, cols]);

  if (cols.length < 2) return null;

  const cellSize = Math.min(56, Math.floor(360 / cols.length));

  return (
    <ChartCard
      title="Correlation Heatmap"
      icon={GitBranch}
      iconColor="bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
      accentClass="hover:border-indigo-500/20"
      badge={`${cols.length}×${cols.length}`}
    >
      <div className="overflow-x-auto custom-scrollbar">
        <div className="inline-block min-w-max">
          {/* Column headers */}
          <div className="flex" style={{ paddingLeft: cellSize + 4 }}>
            {cols.map(c => (
              <div key={c} className="text-[8px] text-content-muted text-center truncate font-medium"
                style={{ width: cellSize, maxWidth: cellSize }}>
                {c.length > 6 ? c.slice(0, 6) + '…' : c}
              </div>
            ))}
          </div>
          {/* Rows */}
          {cols.map((rowCol, ri) => (
            <div key={rowCol} className="flex items-center">
              <div className="text-[8px] text-content-muted text-right pr-1 shrink-0 truncate font-medium"
                style={{ width: cellSize, maxWidth: cellSize }}>
                {rowCol.length > 6 ? rowCol.slice(0, 6) + '…' : rowCol}
              </div>
              {cols.map((colCol, ci) => {
                const cell = cells.find(c => c.x === colCol && c.y === rowCol);
                const val = cell?.corr ?? 0;
                return (
                  <div
                    key={colCol}
                    title={`${rowCol} × ${colCol}: ${val}`}
                    className="flex items-center justify-center text-[9px] font-bold border border-surface-bg/30 transition-all hover:scale-105 cursor-default"
                    style={{
                      width: cellSize,
                      height: cellSize,
                      background: corrColor(val),
                      color: Math.abs(val) > 0.5 ? '#f8fafc' : '#94a3b8',
                    }}
                  >
                    {val.toFixed(2)}
                  </div>
                );
              })}
            </div>
          ))}
          {/* Color scale legend */}
          <div className="flex items-center gap-2 mt-2 px-1">
            <span className="text-[9px] text-red-400">−1</span>
            <div className="h-2 flex-1 rounded" style={{ background: 'linear-gradient(to right, rgba(239,68,68,0.8), rgba(30,41,59,0.4), rgba(16,185,129,0.8))' }} />
            <span className="text-[9px] text-emerald-400">+1</span>
          </div>
        </div>
      </div>
    </ChartCard>
  );
}

// ── CHART 8 — Radar (multi-column profile) ────────────────────────────────────
function RadarProfileChart({ rows, numericColumns }) {
  const cols = numericColumns.slice(0, 7);

  const data = useMemo(() => {
    if (!cols.length || !rows.length) return [];
    // Normalize each column to 0-100 for radar
    return cols.map(col => {
      const vals = rows.map(r => Number(r[col])).filter(v => Number.isFinite(v));
      if (!vals.length) return { col, mean: 0, pct: 0 };
      const mean = vals.reduce((s, v) => s + v, 0) / vals.length;
      const min = Math.min(...vals), max = Math.max(...vals);
      const pct = max > min ? Math.round(((mean - min) / (max - min)) * 100) : 50;
      return { col, mean: Number(mean.toFixed(2)), pct };
    });
  }, [rows, cols]);

  return (
    <ChartCard
      title="Numeric Profile (Radar)"
      icon={Sigma}
      iconColor="bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/20"
      accentClass="hover:border-fuchsia-500/20"
      badge="normalized"
    >
      <div className="h-56 w-full">
        {data.length >= 3 ? (
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data}>
              <PolarGrid stroke="#1e293b" />
              <PolarAngleAxis dataKey="col" tick={{ fill: '#64748b', fontSize: 9 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 8 }} />
              <Radar name="Mean %" dataKey="pct" stroke="#a855f7" fill="#a855f7" fillOpacity={0.3} strokeWidth={2} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, _, p) => [`${v}% (mean: ${p.payload.mean})`, p.payload.col]} />
            </RadarChart>
          </ResponsiveContainer>
        ) : <EmptyChart message="Need at least 3 numeric columns for radar chart." />}
      </div>
    </ChartCard>
  );
}

// ── EMPTY STATE ───────────────────────────────────────────────────────────────
function DashboardEmpty() {
  return (
    <div className="p-8 rounded-2xl border border-surface-border bg-surface-card text-center space-y-3">
      <Layers className="w-8 h-8 text-brand-400 mx-auto opacity-50" />
      <h3 className="heading-xs">Dashboard Inactive</h3>
      <p className="body-xs text-content-secondary max-w-sm mx-auto">
        Please upload a CSV or Excel dataset to render interactive visual charts and dynamic tables.
      </p>
    </div>
  );
}

// ── SECTION HEADER ─────────────────────────────────────────────────────────────
function SectionHeader({ icon: Icon, label }) {
  return (
    <div className="flex items-center gap-2">
      <div className="p-1.5 rounded-lg bg-surface-elevated text-content-secondary border border-surface-border">
        <Icon className="w-4 h-4" />
      </div>
      <h3 className="label-caps font-bold text-content-primary">{label}</h3>
    </div>
  );
}

function AnalyticsSummaryCards({ rows, numericColumns, catColumns }) {
  const stats = [
    {
      label: 'Rows analyzed',
      value: rows.length.toLocaleString(),
      hint: rows.length ? 'live filtered view' : 'no rows yet',
    },
    {
      label: 'Numeric fields',
      value: numericColumns.length.toString(),
      hint: numericColumns.length ? 'trend + distribution ready' : 'no numeric candidates',
    },
    {
      label: 'Categorical fields',
      value: catColumns.length.toString(),
      hint: catColumns.length ? 'segments + proportions ready' : 'fallback views enabled',
    },
    {
      label: 'Layout mode',
      value: '2 × 2',
      hint: 'responsive analytics grid',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="rounded-2xl border border-surface-border bg-surface-card p-3.5 shadow-sm">
          <p className="body-xs text-content-muted">{stat.label}</p>
          <p className="mt-1 text-lg font-semibold text-content-primary">{stat.value}</p>
          <p className="mt-1 body-xs text-content-secondary">{stat.hint}</p>
        </div>
      ))}
    </div>
  );
}

// ── MAIN DASHBOARD ────────────────────────────────────────────────────────────
export default memo(function Dashboard() {
  const { datasetInfo, filteredData } = useData();
  const rows = filteredData || [];

  const numericColumns = datasetInfo?.numeric_columns || [];
  const catColumns = datasetInfo?.categorical_columns || [];
  const hasNumeric = numericColumns.length > 0;
  const hasCat = catColumns.length > 0;
  const hasMultiNum = numericColumns.length >= 2;

  if (!datasetInfo) return <DashboardEmpty />;

  return (
    <div id="analytics" className="space-y-6">
      <div id="overview" className="h-0 w-full" />

      <div className="space-y-3">
        <SectionHeader icon={Grid3x3} label="Analytics Overview" />
        <AnalyticsSummaryCards rows={rows} numericColumns={numericColumns} catColumns={catColumns} />
      </div>

      <div id="visualizations" className="space-y-3">
        <SectionHeader icon={BarChart3} label="Core Visualizations" />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          {hasNumeric ? (
            <NumericTrendChart rows={rows} numericColumns={numericColumns} />
          ) : (
            <div className="p-5 rounded-2xl border border-surface-border bg-surface-card body-xs text-content-secondary flex items-center justify-center italic">
              No numeric columns available for trend analysis.
            </div>
          )}

          {hasNumeric ? (
            <HistogramChart rows={rows} numericColumns={numericColumns} />
          ) : (
            <div className="p-5 rounded-2xl border border-surface-border bg-surface-card body-xs text-content-secondary flex items-center justify-center italic">
              No numeric columns available for histograms.
            </div>
          )}

          {hasMultiNum ? (
            <ScatterPlotChart rows={rows} numericColumns={numericColumns} />
          ) : hasNumeric ? (
            <NumericTrendChart rows={rows} numericColumns={numericColumns} />
          ) : (
            <div className="p-5 rounded-2xl border border-surface-border bg-surface-card body-xs text-content-secondary flex items-center justify-center italic">
              No numeric columns available for scatter plot.
            </div>
          )}

          {hasCat ? (
            <CategoricalBarChart rows={rows} catColumns={catColumns} />
          ) : hasNumeric ? (
            <HistogramChart rows={rows} numericColumns={[...numericColumns].reverse()} />
          ) : (
            <div className="p-5 rounded-2xl border border-surface-border bg-surface-card body-xs text-content-secondary flex items-center justify-center italic">
              No categorical columns available.
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <SectionHeader icon={PieIcon} label="Proportions & Spread" />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          {hasCat ? (
            <PieChartCard rows={rows} catColumns={catColumns} />
          ) : hasNumeric ? (
            <BoxPlotChart rows={rows} numericColumns={numericColumns} />
          ) : null}

          {hasNumeric ? (
            <BoxPlotChart rows={rows} numericColumns={numericColumns} />
          ) : hasCat ? (
            <CategoricalBarChart rows={rows} catColumns={catColumns} />
          ) : null}
        </div>
      </div>

      {hasMultiNum && (
        <div className="space-y-3">
          <SectionHeader icon={GitBranch} label="Correlations & Profiles" />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <CorrelationHeatmap rows={rows} numericColumns={numericColumns} />
            <RadarProfileChart rows={rows} numericColumns={numericColumns} />
          </div>
        </div>
      )}

      <div id="dataset" className="space-y-3">
        <SectionHeader icon={TableIcon} label="Filtered Dataset Browser" />
        <AdvancedDataTable />
      </div>
    </div>
  );
});
