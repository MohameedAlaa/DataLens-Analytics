import React, { useEffect, useState, useMemo } from 'react';
import { useData } from '../../context/DataContext';
import axios from 'axios';
import {
  Sparkles, TrendingUp, AlertTriangle, Lightbulb, Activity, ArrowRight,
  ShieldCheck, CheckCircle2, AlertCircle, XCircle, Database, Hash, Type,
  Calendar, Grid, BarChart3, Layers, ScatterChart, PieChart, LineChart,
  TrendingDown, Zap, Eye, HelpCircle, ChevronDown, ChevronUp, Flame,
  Droplets, Triangle, GitBranch
} from 'lucide-react';

// ─── Pure computation helpers (all memoized) ──────────────────────────────

function computeHealthScore({ rowCount, colCount, nullCols, totalCells, sampleSize, missingCount, duplicateCount }) {
  let score = 100;
  if (totalCells > 0) {
    const missingRatio = missingCount / Math.max(sampleSize * colCount, 1);
    score -= Math.min(30, Math.round(missingRatio * 150));
  }
  score -= Math.min(20, duplicateCount * 2);
  if (rowCount < 10) score -= 10;
  if (colCount < 2) score -= 15;
  score -= Math.min(10, nullCols * 5);
  return Math.max(0, Math.min(100, score));
}

function computeNullStats(numericSummary, rowCount) {
  const nullPerCol = {};
  let totalNull = 0;
  Object.entries(numericSummary).forEach(([col, s]) => {
    const nullCount = Math.max(0, rowCount - (s.count || 0));
    nullPerCol[col] = nullCount;
    totalNull += nullCount;
  });
  return { nullPerCol, totalNull };
}

function computeCorrelations(corrMatrix) {
  const pairs = [];
  Object.entries(corrMatrix).forEach(([colA, subDict]) => {
    Object.entries(subDict).forEach(([colB, val]) => {
      if (colA < colB) { // avoid duplicates
        pairs.push({ colA, colB, val: Number(val.toFixed(3)) });
      }
    });
  });
  pairs.sort((a, b) => Math.abs(b.val) - Math.abs(a.val));
  return {
    strong: pairs.filter(p => Math.abs(p.val) >= 0.7),
    moderate: pairs.filter(p => Math.abs(p.val) >= 0.4 && Math.abs(p.val) < 0.7),
    weak: pairs.filter(p => Math.abs(p.val) < 0.4),
    all: pairs,
  };
}

function computeDistributions(numericSummary) {
  return Object.entries(numericSummary).map(([col, s]) => {
    const mean = s.mean ?? 0;
    const median = s['50%'] ?? 0;
    const std = s.std ?? 0;
    const q1 = s['25%'] ?? 0;
    const q3 = s['75%'] ?? 0;
    const range = (s.max ?? 0) - (s.min ?? 0);
    const cv = mean !== 0 ? std / Math.abs(mean) : 0; // coefficient of variation

    // Skewness approximation via Pearson's 2nd skewness coefficient
    const skew = std > 0 ? (3 * (mean - median)) / std : 0;

    let shape = 'Normal';
    let shapeColor = 'text-brand-400';
    let shapeBg = 'bg-brand-500/10';
    if (Math.abs(skew) > 2) { shape = 'Highly Skewed'; shapeColor = 'text-red-400'; shapeBg = 'bg-red-500/10'; }
    else if (Math.abs(skew) > 0.75) { shape = 'Skewed'; shapeColor = 'text-amber-400'; shapeBg = 'bg-amber-500/10'; }

    let variance = 'Normal Variance';
    if (cv > 1) { variance = 'High Variance'; }
    else if (cv < 0.1) { variance = 'Low Variance'; }

    return { col, mean, median, std, q1, q3, range, skew, cv, shape, shapeColor, shapeBg, variance };
  });
}

function computeOutliers(numericSummary, rowCount) {
  return Object.entries(numericSummary).map(([col, s]) => {
    const q1 = s['25%'] ?? 0;
    const q3 = s['75%'] ?? 0;
    const iqr = q3 - q1;
    const lowerFence = q1 - 1.5 * iqr;
    const upperFence = q3 + 1.5 * iqr;
    // Estimate outlier count: rows outside fence relative to non-null count
    const count = s.count || rowCount;
    // Using min/max vs fences to estimate
    const likelyOutliers = ((s.min ?? 0) < lowerFence ? 1 : 0) + ((s.max ?? 0) > upperFence ? 1 : 0);
    // Estimated % based on IQR method heuristic
    const estimatedCount = Math.round((likelyOutliers / 2) * count * 0.05);
    const pct = count > 0 ? ((estimatedCount / count) * 100).toFixed(1) : 0;
    let severity = 'Low';
    let sevColor = 'text-emerald-400';
    let sevBg = 'bg-emerald-500/10';
    if (Number(pct) > 5) { severity = 'High'; sevColor = 'text-red-400'; sevBg = 'bg-red-500/10'; }
    else if (Number(pct) > 2) { severity = 'Medium'; sevColor = 'text-amber-400'; sevBg = 'bg-amber-500/10'; }
    return { col, estimatedCount, pct, severity, sevColor, sevBg, iqr, lowerFence, upperFence };
  }).sort((a, b) => b.estimatedCount - a.estimatedCount);
}

function recommendCharts(numericCols, catCols, dateColsCount, rowCount, corrStrong) {
  const recs = [];
  if (numericCols.length >= 2) {
    recs.push({ type: 'Scatter Plot', icon: '⚬', color: 'text-brand-400', bg: 'bg-brand-500/10', reason: `${numericCols[0]} vs ${numericCols[1]} — reveals linear or non-linear relationships between the two strongest numeric dimensions.`, cols: [numericCols[0], numericCols[1]] });
  }
  if (numericCols.length >= 1) {
    recs.push({ type: 'Histogram', icon: '▬', color: 'text-accent-400', bg: 'bg-accent-500/10', reason: `${numericCols[0]} — shows frequency distribution, identifies skewness and outlier clusters.`, cols: [numericCols[0]] });
  }
  if (numericCols.length >= 1) {
    recs.push({ type: 'Box Plot', icon: '▭', color: 'text-purple-400', bg: 'bg-purple-500/10', reason: `${numericCols.slice(0, 3).join(', ')} — visualizes IQR, median, and outlier spread for numeric columns side by side.`, cols: numericCols.slice(0, 3) });
  }
  if (catCols.length >= 1) {
    recs.push({ type: 'Bar Chart', icon: '▤', color: 'text-emerald-400', bg: 'bg-emerald-500/10', reason: `${catCols[0]} — compare frequency counts across categorical groups for immediate segment comparison.`, cols: [catCols[0]] });
  }
  if (catCols.length >= 1 && rowCount > 0) {
    recs.push({ type: 'Pie Chart', icon: '◔', color: 'text-amber-400', bg: 'bg-amber-500/10', reason: `${catCols[0]} — proportion view is clearest when there are fewer than 8 distinct segments.`, cols: [catCols[0]] });
  }
  if (dateColsCount > 0 || numericCols.length >= 1) {
    recs.push({ type: 'Line Chart', icon: '—', color: 'text-cyan-400', bg: 'bg-cyan-500/10', reason: `${numericCols[0] || 'row index'} — trace trend over index or time axis to see directional momentum.`, cols: numericCols.slice(0, 1) });
  }
  if (numericCols.length >= 3) {
    recs.push({ type: 'Correlation Heatmap', icon: '▦', color: 'text-red-400', bg: 'bg-red-500/10', reason: `All ${numericCols.length} numeric columns — heatmap highlights pairwise statistical dependencies in a single glance.`, cols: numericCols });
  }
  return recs;
}

function generateSuggestedQuestions(datasetInfo, numericCols, catCols, corrStrong, outlierCols) {
  const questions = [];
  questions.push({ text: `Summarize this dataset in plain language.`, category: 'Overview' });
  if (corrStrong.length > 0) {
    questions.push({ text: `Explain the relationship between ${corrStrong[0].colA} and ${corrStrong[0].colB}.`, category: 'Correlation' });
  }
  if (outlierCols.length > 0) {
    questions.push({ text: `Find and explain anomalies in ${outlierCols[0].col}.`, category: 'Outliers' });
  }
  if (catCols.length > 0) {
    questions.push({ text: `What are the top segments in ${catCols[0]}?`, category: 'Categories' });
  }
  if (numericCols.length > 0) {
    questions.push({ text: `What is the statistical distribution of ${numericCols[0]}?`, category: 'Distribution' });
  }
  questions.push({ text: `What data quality issues should I fix first?`, category: 'Quality' });
  questions.push({ text: `Recommend the best visualizations for this dataset.`, category: 'Charts' });
  questions.push({ text: `Are there missing values that could skew my analysis?`, category: 'Quality' });
  return questions.slice(0, 8);
}

// ─── Sub-Components ────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, badge, badgeColor = 'text-brand-400 bg-brand-500/10 border-brand-500/30' }) {
  return (
    <div className="flex items-center gap-2.5 mb-4">
      <div className="p-1.5 rounded-lg bg-surface-elevated text-content-secondary border border-surface-border">
        <Icon className="w-4 h-4" />
      </div>
      <h3 className="text-xs font-bold text-content-primary uppercase tracking-wide">{title}</h3>
      {badge && (
        <span className={`ml-auto px-2 py-0.5 text-[10px] font-bold rounded-full border ${badgeColor}`}>{badge}</span>
      )}
    </div>
  );
}

function MetricCard({ icon: Icon, iconColor, title, value, desc, severity, bg, border, onClick, loading }) {
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl border ${border || 'border-surface-border'} ${bg || 'bg-surface-elevated/40'} 
        space-y-1.5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg
        ${onClick ? 'cursor-pointer hover:border-brand-500/40' : ''}`}
    >
      <div className="flex items-center justify-between">
        <div className={`p-1.5 rounded-lg ${bg || 'bg-surface-elevated'} border ${border || 'border-surface-border'}`}>
          <Icon className={`w-3.5 h-3.5 ${iconColor || 'text-content-secondary'}`} />
        </div>
        {severity && (
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${severity}`}>{severity}</span>
        )}
      </div>
      <p className="text-[10px] uppercase font-bold text-content-muted tracking-wider">{title}</p>
      <p className={`text-lg font-extrabold ${iconColor || 'text-content-primary'}`}>{value}</p>
      {desc && <p className="text-[11px] text-content-secondary leading-relaxed">{desc}</p>}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {[1, 2, 3].map(i => (
        <div key={i} className="p-5 rounded-2xl border border-surface-border bg-surface-card space-y-3">
          <div className="h-4 w-36 bg-surface-elevated rounded"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(j => <div key={j} className="h-20 bg-surface-elevated rounded-xl"></div>)}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────

export default function AIInsightsSection({ onPromptSelect }) {
  const { datasetInfo, rawData, setDatasetInfo } = useData();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    health: true, quality: true, correlation: true, outliers: true,
    distribution: true, charts: true, questions: true,
  });

  const toggleSection = (key) => setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));

  useEffect(() => {
    if (!datasetInfo?.dataset_id) { setStats(null); return; }
    let cancelled = false;
    const fetchStats = async () => {
      setLoading(true); setError(null);
      try {
        const resp = await axios.get(`/api/stats/${datasetInfo.dataset_id}`);
        if (!cancelled) setStats(resp.data);
      } catch (err) {
        if (cancelled) return;
        if (err.response?.status === 404) {
          // Dataset no longer exists in backend (server restarted and wiped in-memory store).
          // Clear the stale datasetInfo so the user is prompted to re-upload.
          setDatasetInfo(null);
          setStats(null);
          setError(null);
        } else {
          setError('Could not load dataset statistics from the backend.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchStats();
    return () => { cancelled = true; };
  }, [datasetInfo]);

  // ── All computations memoized ──────────────────────────────────────────
  const derived = useMemo(() => {
    if (!datasetInfo || !stats) return null;

    const rowCount = stats.row_count ?? datasetInfo.shape?.[0] ?? 0;
    const colCount = stats.column_count ?? datasetInfo.shape?.[1] ?? 0;
    const totalCells = rowCount * colCount;
    const numericSummary = stats.numeric_summary || {};
    const catSummary = stats.categorical_summary || {};
    const corrMatrix = stats.correlation_matrix || {};
    const numericCols = datasetInfo.numeric_columns || Object.keys(numericSummary);
    const catCols = datasetInfo.categorical_columns || Object.keys(catSummary);
    const dateColsCount = datasetInfo.date_columns?.length || 0;

    // Null stats from numeric summary (count vs rowCount)
    const { nullPerCol, totalNull } = computeNullStats(numericSummary, rowCount);
    const nullCols = Object.values(nullPerCol).filter(n => n === rowCount).length; // fully null cols
    const completePct = totalCells > 0 ? Math.round(((totalCells - totalNull) / totalCells) * 100) : 100;
    const missingPct = totalCells > 0 ? (100 - completePct).toFixed(1) : '0.0';
    const topMissingCols = Object.entries(nullPerCol)
      .sort((a, b) => b[1] - a[1])
      .filter(([, n]) => n > 0)
      .slice(0, 5)
      .map(([col, n]) => ({ col, count: n, pct: ((n / rowCount) * 100).toFixed(1) }));

    // Duplicate count from raw sample
    let duplicateCount = 0;
    if (rawData?.length > 0) {
      const seen = new Set();
      rawData.forEach(row => {
        const str = JSON.stringify(row);
        if (seen.has(str)) duplicateCount++;
        else seen.add(str);
      });
    }
    const duplicatePct = rawData?.length > 0 ? ((duplicateCount / rawData.length) * 100).toFixed(1) : '0.0';

    // Memory usage estimate in KB (4 bytes per numeric cell, 50 bytes avg per string cell)
    const memKB = Math.round((numericCols.length * rowCount * 4 + catCols.length * rowCount * 50) / 1024);
    const memLabel = memKB > 1024 ? `${(memKB / 1024).toFixed(1)} MB` : `${memKB} KB`;

    // Health score
    const healthScore = computeHealthScore({
      rowCount, colCount, nullCols, totalCells,
      sampleSize: rawData?.length || rowCount,
      missingCount: totalNull, duplicateCount,
    });
    let healthStatus;
    if (healthScore >= 90) healthStatus = { label: 'Excellent', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', Icon: CheckCircle2 };
    else if (healthScore >= 75) healthStatus = { label: 'Good', color: 'text-brand-400', bg: 'bg-brand-500/10', border: 'border-brand-500/30', Icon: AlertCircle };
    else if (healthScore >= 50) healthStatus = { label: 'Warning', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', Icon: AlertTriangle };
    else healthStatus = { label: 'Poor', color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', Icon: XCircle };

    // Correlations
    const correlations = computeCorrelations(corrMatrix);

    // Distributions
    const distributions = computeDistributions(numericSummary);

    // Outliers
    const outliers = computeOutliers(numericSummary, rowCount);
    const topOutliers = outliers.slice(0, 5);

    // Chart recommendations
    const chartRecs = recommendCharts(numericCols, catCols, dateColsCount, rowCount, correlations.strong);

    // Suggested questions
    const suggestedQs = generateSuggestedQuestions(datasetInfo, numericCols, catCols, correlations.strong, topOutliers);

    return {
      rowCount, colCount, totalCells, numericCols, catCols, dateColsCount,
      nullPerCol, totalNull, nullCols, completePct, missingPct, topMissingCols,
      duplicateCount, duplicatePct, memLabel, healthScore, healthStatus,
      correlations, distributions, outliers: topOutliers, chartRecs, suggestedQs,
      numericSummary, catSummary,
    };
  }, [datasetInfo, stats, rawData]);

  // ── Empty / Loading / Error states ────────────────────────────────────
  if (!datasetInfo) {
    return (
      <div className="p-8 rounded-2xl border border-surface-border bg-surface-card text-center space-y-3">
        <Sparkles className="w-8 h-8 text-brand-400 mx-auto opacity-40" />
        <h3 className="text-sm font-semibold text-content-primary">AI Insights Engine</h3>
        <p className="text-xs text-content-secondary max-w-sm mx-auto">
          Upload a CSV or Excel dataset to unlock automated health scores, correlation analysis, outlier detection, and AI-powered recommendations.
        </p>
      </div>
    );
  }

  if (loading) return <Skeleton />;

  if (error) {
    return (
      <div className="p-5 rounded-2xl border border-red-500/20 bg-red-500/5 space-y-2">
        <AlertTriangle className="w-5 h-5 text-red-400" />
        <p className="text-xs font-semibold text-red-400">{error}</p>
        <p className="text-xs text-content-secondary">Check backend connectivity and retry by refreshing the page.</p>
      </div>
    );
  }

  if (!derived) return null;

  const {
    rowCount, colCount, totalCells, numericCols, catCols, dateColsCount,
    totalNull, nullCols, completePct, missingPct, topMissingCols,
    duplicateCount, duplicatePct, memLabel, healthScore, healthStatus,
    correlations, distributions, outliers, chartRecs, suggestedQs,
  } = derived;

  const StatusIcon = healthStatus.Icon;

  // ── Section toggle header ──────────────────────────────────────────────
  const SectionToggle = ({ id, title, icon: Icon, badge, children }) => (
    <div className="rounded-2xl border border-surface-border bg-surface-card overflow-hidden shadow-sm">
      <button
        onClick={() => toggleSection(id)}
        className="w-full flex items-center justify-between p-5 hover:bg-surface-elevated/30 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-surface-elevated border border-surface-border">
            <Icon className="w-4 h-4 text-content-secondary" />
          </div>
          <span className="text-xs font-bold text-content-primary uppercase tracking-wide">{title}</span>
          {badge && <span className="px-2 py-0.5 text-[10px] font-bold bg-brand-500/10 text-brand-400 rounded-full border border-brand-500/20">{badge}</span>}
        </div>
        {expandedSections[id] ? <ChevronUp className="w-4 h-4 text-content-muted" /> : <ChevronDown className="w-4 h-4 text-content-muted" />}
      </button>
      {expandedSections[id] && <div className="px-5 pb-5">{children}</div>}
    </div>
  );

  return (
    <div className="space-y-4">

      {/* ── SECTION 1: Dataset Health Score ─────────────────────────────── */}
      <SectionToggle id="health" title="Dataset Health" icon={Activity} badge={`${healthScore}/100`}>
        <div className="space-y-4">
          {/* Score Banner */}
          <div className={`flex items-center gap-3 p-4 rounded-xl ${healthStatus.bg} border ${healthStatus.border}`}>
            <StatusIcon className={`w-6 h-6 ${healthStatus.color}`} />
            <div className="flex-1">
              <p className={`text-sm font-bold ${healthStatus.color}`}>{healthStatus.label} Health — {healthScore}/100</p>
              <p className="text-[11px] text-content-secondary mt-0.5">
                {rowCount.toLocaleString()} rows × {colCount} columns · {totalCells.toLocaleString()} total cells
              </p>
            </div>
            {/* Health bar */}
            <div className="w-28 h-2 bg-surface-elevated rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  healthScore >= 90 ? 'bg-emerald-400' : healthScore >= 75 ? 'bg-brand-400' : healthScore >= 50 ? 'bg-amber-400' : 'bg-red-400'
                }`}
                style={{ width: `${healthScore}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
            <MetricCard icon={Activity} iconColor={healthStatus.color} title="Health Score" value={`${healthScore}%`} bg={healthStatus.bg} border={healthStatus.border} />
            <MetricCard icon={AlertTriangle} iconColor={totalNull > 0 ? 'text-amber-400' : 'text-emerald-400'} title="Missing Values" value={totalNull} bg={totalNull > 0 ? 'bg-amber-500/10' : 'bg-emerald-500/10'} border={totalNull > 0 ? 'border-amber-500/30' : 'border-emerald-500/30'} />
            <MetricCard icon={Layers} iconColor={duplicateCount > 0 ? 'text-amber-400' : 'text-emerald-400'} title="Duplicates" value={duplicateCount} bg={duplicateCount > 0 ? 'bg-amber-500/10' : 'bg-emerald-500/10'} border={duplicateCount > 0 ? 'border-amber-500/30' : 'border-emerald-500/30'} />
            <MetricCard icon={Hash} iconColor="text-brand-400" title="Numeric" value={numericCols.length} bg="bg-brand-500/10" border="border-brand-500/20" />
            <MetricCard icon={Type} iconColor="text-emerald-400" title="Categorical" value={catCols.length} bg="bg-emerald-500/10" border="border-emerald-500/20" />
            <MetricCard icon={Calendar} iconColor="text-accent-400" title="Date" value={dateColsCount} bg="bg-accent-500/10" border="border-accent-500/20" />
            <MetricCard icon={Grid} iconColor="text-content-secondary" title="Total Cells" value={totalCells.toLocaleString()} />
          </div>
        </div>
      </SectionToggle>

      {/* ── SECTION 2: Data Quality ─────────────────────────────────────── */}
      <SectionToggle id="quality" title="Data Quality Analysis" icon={ShieldCheck}
        badge={completePct === 100 ? '100% Complete' : `${completePct}% Complete`}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard icon={Droplets} iconColor={Number(missingPct) > 5 ? 'text-red-400' : Number(missingPct) > 0 ? 'text-amber-400' : 'text-emerald-400'}
              title="Missing %" value={`${missingPct}%`}
              desc={`${totalNull} cells across numeric cols`}
              bg={Number(missingPct) > 5 ? 'bg-red-500/10' : Number(missingPct) > 0 ? 'bg-amber-500/10' : 'bg-emerald-500/10'}
              border={Number(missingPct) > 5 ? 'border-red-500/30' : Number(missingPct) > 0 ? 'border-amber-500/30' : 'border-emerald-500/30'}
            />
            <MetricCard icon={CheckCircle2} iconColor="text-emerald-400"
              title="Completeness %" value={`${completePct}%`}
              desc={`${(totalCells - totalNull).toLocaleString()} of ${totalCells.toLocaleString()} cells`}
              bg="bg-emerald-500/10" border="border-emerald-500/20"
            />
            <MetricCard icon={Layers} iconColor={Number(duplicatePct) > 2 ? 'text-amber-400' : 'text-emerald-400'}
              title="Duplicate %" value={`${duplicatePct}%`}
              desc={`${duplicateCount} duplicate rows in sample`}
              bg={Number(duplicatePct) > 2 ? 'bg-amber-500/10' : 'bg-emerald-500/10'}
              border={Number(duplicatePct) > 2 ? 'border-amber-500/30' : 'border-emerald-500/20'}
            />
            <MetricCard icon={Database} iconColor="text-brand-400"
              title="Memory Usage" value={memLabel}
              desc={`Estimated in-memory footprint`}
              bg="bg-brand-500/10" border="border-brand-500/20"
            />
          </div>

          {/* Null Columns & Top Missing Columns */}
          {topMissingCols.length > 0 ? (
            <div className="space-y-2">
              <p className="text-[10px] font-bold uppercase text-content-muted">Columns With Highest Missing Values</p>
              <div className="space-y-1.5">
                {topMissingCols.map(({ col, count, pct }) => (
                  <div key={col} className="flex items-center gap-3 p-2.5 rounded-lg bg-surface-elevated/40 border border-surface-border">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-content-primary truncate">{col}</p>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className={`font-bold ${Number(pct) > 10 ? 'text-red-400' : 'text-amber-400'}`}>{count} missing</span>
                      <span className="text-content-muted">({pct}%)</span>
                    </div>
                    {/* Mini bar */}
                    <div className="w-16 h-1.5 bg-surface-elevated rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${Number(pct) > 10 ? 'bg-red-400' : 'bg-amber-400'}`}
                        style={{ width: `${Math.min(100, Number(pct))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <p className="text-xs text-emerald-400 font-medium">No missing values detected in numeric columns — excellent data completeness.</p>
            </div>
          )}
        </div>
      </SectionToggle>

      {/* ── SECTION 3: Correlation Insights ────────────────────────────── */}
      <SectionToggle id="correlation" title="Correlation Insights" icon={GitBranch}
        badge={correlations.strong.length > 0 ? `${correlations.strong.length} strong` : 'None'}>
        {correlations.all.length === 0 ? (
          <div className="p-4 rounded-xl bg-surface-elevated/40 border border-surface-border text-center space-y-2">
            <GitBranch className="w-5 h-5 text-content-muted mx-auto" />
            <p className="text-xs text-content-secondary">Correlation analysis requires at least 2 numeric columns. This dataset has {numericCols.length} numeric column(s).</p>
          </div>
        ) : (
          <div className="space-y-3">
            {correlations.strong.length === 0 && correlations.moderate.length === 0 ? (
              <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
                <p className="text-xs text-amber-400 font-medium">No strong correlations detected (|r| ≥ 0.7). This may indicate independent variables, which is actually desirable for modeling tasks.</p>
              </div>
            ) : null}
            {[...correlations.strong, ...correlations.moderate].slice(0, 8).map((pair, i) => {
              const isPositive = pair.val > 0;
              const absVal = Math.abs(pair.val);
              const isStrong = absVal >= 0.7;
              return (
                <div key={i} className={`p-3.5 rounded-xl border transition-all hover:border-brand-500/30 cursor-pointer
                  ${isStrong ? 'border-brand-500/20 bg-brand-500/5' : 'border-surface-border bg-surface-elevated/40'}`}
                  onClick={() => onPromptSelect && onPromptSelect(`Explain the relationship between ${pair.colA} and ${pair.colB}`)}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-xs font-semibold text-content-primary truncate">{pair.colA}</span>
                      {isPositive ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" /> : <TrendingDown className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />}
                      <span className="text-xs font-semibold text-content-primary truncate">{pair.colB}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className={`w-16 h-1.5 rounded-full overflow-hidden ${isPositive ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
                        <div className={`h-full rounded-full ${isPositive ? 'bg-emerald-400' : 'bg-red-400'}`} style={{ width: `${Math.abs(pair.val) * 100}%` }} />
                      </div>
                      <span className={`text-xs font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>{pair.val}</span>
                      {isStrong && <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-brand-500 text-white">Strong</span>}
                    </div>
                  </div>
                  <p className="text-[11px] text-content-muted mt-1.5">
                    {isStrong ? `Strong ${isPositive ? 'positive' : 'negative'} correlation — click to ask AI for deeper analysis.` : `Moderate ${isPositive ? 'positive' : 'negative'} relationship detected.`}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </SectionToggle>

      {/* ── SECTION 4: Outlier Detection ───────────────────────────────── */}
      <SectionToggle id="outliers" title="Outlier Detection (IQR Method)" icon={Flame}
        badge={`Top ${Math.min(5, outliers.length)} columns`}>
        {outliers.length === 0 ? (
          <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
            <p className="text-xs text-emerald-400 font-medium">No numeric columns available for IQR-based outlier detection.</p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-[10px] text-content-muted mb-3">Fence boundaries computed as Q1 − 1.5×IQR and Q3 + 1.5×IQR. Counts are estimates from quartile analysis.</p>
            {outliers.map((o) => (
              <div key={o.col} className={`p-3.5 rounded-xl border ${o.sevBg} ${o.sevBg.replace('bg-', 'border-').replace('/10', '/20')} transition-all hover:opacity-90 cursor-pointer`}
                onClick={() => onPromptSelect && onPromptSelect(`Find and explain outliers in the ${o.col} column`)}>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-content-primary truncate">{o.col}</p>
                    <p className="text-[10px] text-content-secondary mt-0.5">
                      Fence: [{o.lowerFence.toFixed(2)}, {o.upperFence.toFixed(2)}] · IQR: {o.iqr.toFixed(2)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs flex-shrink-0">
                    <span className="text-content-muted">{o.pct}%</span>
                    <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${o.sevColor} ${o.sevBg} border ${o.sevBg.replace('bg-', 'border-').replace('/10', '/30')}`}>{o.severity}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionToggle>

      {/* ── SECTION 5: Distribution Summary ────────────────────────────── */}
      <SectionToggle id="distribution" title="Distribution Summary" icon={BarChart3}
        badge={`${distributions.length} numeric columns`}>
        {distributions.length === 0 ? (
          <div className="p-4 rounded-xl bg-surface-elevated/40 border border-surface-border">
            <p className="text-xs text-content-secondary text-center">No numeric columns found for distribution analysis.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {distributions.map(d => (
              <div key={d.col}
                onClick={() => onPromptSelect && onPromptSelect(`Describe the statistical distribution of ${d.col}`)}
                className="p-4 rounded-xl border border-surface-border bg-surface-elevated/40 space-y-2.5 hover:border-brand-500/30 cursor-pointer transition-all hover:-translate-y-0.5">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-content-primary truncate max-w-[70%]">{d.col}</p>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${d.shapeBg} ${d.shapeColor}`}>{d.shape}</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                  <div className="p-1.5 rounded bg-surface-elevated">
                    <p className="text-content-muted">Mean</p>
                    <p className="font-semibold text-content-primary">{d.mean?.toFixed(2) ?? '—'}</p>
                  </div>
                  <div className="p-1.5 rounded bg-surface-elevated">
                    <p className="text-content-muted">Median</p>
                    <p className="font-semibold text-content-primary">{d.median?.toFixed(2) ?? '—'}</p>
                  </div>
                  <div className="p-1.5 rounded bg-surface-elevated">
                    <p className="text-content-muted">Std Dev</p>
                    <p className="font-semibold text-content-primary">{d.std?.toFixed(2) ?? '—'}</p>
                  </div>
                  <div className="p-1.5 rounded bg-surface-elevated">
                    <p className="text-content-muted">Skew</p>
                    <p className={`font-semibold ${Math.abs(d.skew) > 1 ? 'text-amber-400' : 'text-content-primary'}`}>{d.skew?.toFixed(2)}</p>
                  </div>
                </div>
                <p className="text-[10px] text-content-muted">{d.variance}</p>
              </div>
            ))}
          </div>
        )}
      </SectionToggle>

      {/* ── SECTION 6: Recommended Charts ──────────────────────────────── */}
      <SectionToggle id="charts" title="Recommended Visualizations" icon={Eye}
        badge={`${chartRecs.length} suggestions`}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {chartRecs.map((rec, i) => (
            <div key={i}
              onClick={() => onPromptSelect && onPromptSelect(`Create a ${rec.type} for ${rec.cols.join(' and ')}`)}
              className={`p-4 rounded-xl border border-surface-border ${rec.bg} hover:border-brand-500/30 cursor-pointer transition-all hover:-translate-y-0.5 space-y-2`}>
              <div className="flex items-center gap-2.5">
                <span className={`text-xl ${rec.color}`}>{rec.icon}</span>
                <p className={`text-xs font-bold ${rec.color}`}>{rec.type}</p>
              </div>
              <p className="text-[11px] text-content-secondary leading-relaxed">{rec.reason}</p>
              <p className="text-[10px] text-content-muted flex items-center gap-1">
                <ArrowRight className="w-3 h-3 text-brand-400" /> Click to ask AI
              </p>
            </div>
          ))}
        </div>
      </SectionToggle>

      {/* ── SECTION 7: Suggested Questions ─────────────────────────────── */}
      <SectionToggle id="questions" title="Suggested AI Questions" icon={HelpCircle}
        badge={`${suggestedQs.length} prompts`}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {suggestedQs.map((q, i) => (
            <button key={i}
              onClick={() => onPromptSelect && onPromptSelect(q.text)}
              className="flex items-start gap-2.5 p-3 rounded-xl border border-surface-border bg-surface-elevated/40 text-left hover:bg-surface-elevated hover:border-brand-500/30 transition-all group">
              <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-brand-500/10 text-brand-400 border border-brand-500/20 flex-shrink-0 mt-0.5">{q.category}</span>
              <p className="text-xs text-content-secondary group-hover:text-content-primary transition-colors">{q.text}</p>
              <ChevronRight className="w-3.5 h-3.5 text-content-muted group-hover:text-brand-400 transition-colors ml-auto flex-shrink-0 mt-0.5" />
            </button>
          ))}
        </div>
      </SectionToggle>

    </div>
  );
}
