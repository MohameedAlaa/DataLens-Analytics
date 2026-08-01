import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useData } from '../../context/DataContext';
import { useFilters } from '../../hooks/useFilters';
import { RefreshCw, ChevronDown, ChevronUp, Hash, Type, Calendar } from 'lucide-react';

/**
 * Dynamic filter panel — categorical checkboxes, numeric range, date range.
 * Each column type is shown in a collapsible accordion card.
 * Uses the design token system — no hardcoded old colours.
 */
export default function Filters() {
  const { datasetInfo, rawData, filteredData } = useData();
  const { applyFilters, resetFilters, filters, loading, error } = useFilters();

  const [localFilters, setLocalFilters] = useState({});
  const [openSections, setOpenSections] = useState({});
  const debounceRef = useRef(null);
  const initialised = useRef(false);

  // ── Helpers ─────────────────────────────────────────────────────────────
  const getNumericBounds = useCallback((col) => {
    const vals = rawData.map((r) => Number(r[col])).filter((v) => !Number.isNaN(v));
    return vals.length ? [Math.min(...vals), Math.max(...vals)] : null;
  }, [rawData]);

  const topValuesCache = useRef({});
  const topValues = useCallback((col) => {
    if (topValuesCache.current[col]) return topValuesCache.current[col];
    const counts = {};
    const src = rawData.length ? rawData : filteredData;
    src.forEach((row) => {
      const v = row[col];
      if (v != null) counts[v] = (counts[v] || 0) + 1;
    });
    const result = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([k]) => k);
    topValuesCache.current[col] = result;
    return result;
  }, [rawData, filteredData]);

  useEffect(() => { topValuesCache.current = {}; }, [rawData, filteredData]);

  // ── Initialise localFilters when dataset changes ─────────────────────────
  useEffect(() => {
    if (!datasetInfo) return;
    const init = {};
    const open = {};
    datasetInfo.numeric_columns?.forEach((col) => {
      const b = getNumericBounds(col);
      if (b) init[col] = { range: [String(b[0]), String(b[1])] };
      open[col] = false;
    });
    datasetInfo.categorical_columns?.forEach((col) => {
      init[col] = [];
      open[col] = false;
    });
    datasetInfo.date_columns?.forEach((col) => {
      init[col] = { range: ['', ''] };
      open[col] = false;
    });
    setLocalFilters(init);
    setOpenSections(open);
    initialised.current = false;
  }, [datasetInfo, getNumericBounds]);

  // ── Build backend payload ─────────────────────────────────────────────────
  const buildPayload = useCallback(() => {
    const payload = {};
    Object.entries(localFilters).forEach(([col, val]) => {
      if (Array.isArray(val) && val.length) {
        payload[col] = val;
      } else if (val && val.range) {
        const [lo, hi] = val.range;
        if (datasetInfo?.numeric_columns?.includes(col)) {
          const bounds = getNumericBounds(col);
          const loN = lo !== '' ? Number(lo) : bounds?.[0];
          const hiN = hi !== '' ? Number(hi) : bounds?.[1];
          if (bounds && (loN !== bounds[0] || hiN !== bounds[1])) {
            payload[col] = { range: [loN, hiN] };
          }
        } else if (datasetInfo?.date_columns?.includes(col) && (lo || hi)) {
          payload[col] = { range: [lo, hi] };
        }
      }
    });
    return payload;
  }, [datasetInfo, localFilters, getNumericBounds]);

  // ── Debounced apply ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!initialised.current) { initialised.current = true; return; }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => applyFilters(buildPayload()), 350);
    return () => clearTimeout(debounceRef.current);
  }, [localFilters]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleSection = (col) =>
    setOpenSections((p) => ({ ...p, [col]: !p[col] }));

  // ── Empty state ────────────────────────────────────────────────────────────
  if (!datasetInfo) {
    return (
      <div className="px-2 py-4 text-center space-y-1">
        <p className="body-xs text-content-muted">Upload a dataset to see filters.</p>
      </div>
    );
  }

  const allColumns = [
    ...(datasetInfo.categorical_columns || []).map((c) => ({ col: c, type: 'cat' })),
    ...(datasetInfo.numeric_columns || []).map((c) => ({ col: c, type: 'num' })),
    ...(datasetInfo.date_columns || []).map((c) => ({ col: c, type: 'date' })),
  ];

  if (!allColumns.length) {
    return <p className="body-xs px-2 py-3 text-content-muted">No filterable columns found.</p>;
  }

  // ── Shared section wrapper ─────────────────────────────────────────────────
  const Section = ({ col, type, children }) => {
    const Icon = type === 'cat' ? Type : type === 'num' ? Hash : Calendar;
    const isOpen = openSections[col];
    return (
      <div className="rounded-lg border border-surface-border overflow-hidden mb-1.5">
        <button
          type="button"
          onClick={() => toggleSection(col)}
          className="w-full flex items-center justify-between px-2.5 py-2
                     hover:bg-surface-elevated transition-colors text-left"
        >
          <span className="flex items-center gap-2 body-xs font-semibold text-content-primary truncate">
            <Icon className="w-3 h-3 text-brand-400 shrink-0" />
            <span className="truncate">{col}</span>
          </span>
          {isOpen
            ? <ChevronUp className="w-3 h-3 text-content-muted shrink-0" />
            : <ChevronDown className="w-3 h-3 text-content-muted shrink-0" />
          }
        </button>
        {isOpen && <div className="px-2.5 pb-2.5 pt-1 border-t border-surface-border bg-surface-elevated/30">{children}</div>}
      </div>
    );
  };

  return (
    <div className="space-y-0.5">
      {allColumns.map(({ col, type }) => (
        <Section key={col} col={col} type={type}>

          {/* ── Categorical ─────────────────────────────── */}
          {type === 'cat' && (() => {
            const vals = topValues(col);
            const selected = localFilters[col] || [];
            const allSelected = vals.length > 0 && vals.every((v) => selected.includes(v));
            return (
              <div className="space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar pt-1">
                {/* Select all row */}
                <label className="flex items-center gap-2 px-1 py-0.5 rounded cursor-pointer hover:bg-surface-elevated transition-colors">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={(e) => {
                      setLocalFilters((p) => ({ ...p, [col]: e.target.checked ? vals : [] }));
                    }}
                  />
                  <span className="body-xs text-content-secondary font-medium">Select all</span>
                </label>
                <div className="w-full h-px bg-surface-border" />
                {vals.map((v) => (
                  <label key={v} className="flex items-center gap-2 px-1 py-0.5 rounded cursor-pointer hover:bg-surface-elevated transition-colors">
                    <input
                      type="checkbox"
                      checked={selected.includes(v)}
                      onChange={(e) => {
                        const cur = localFilters[col] || [];
                        setLocalFilters((p) => ({
                          ...p,
                          [col]: e.target.checked
                            ? [...cur, v]
                            : cur.filter((x) => x !== v),
                        }));
                      }}
                    />
                    <span className="body-xs text-content-secondary truncate" title={v}>{v}</span>
                  </label>
                ))}
              </div>
            );
          })()}

          {/* ── Numeric ─────────────────────────────────── */}
          {type === 'num' && (() => {
            const cur = localFilters[col]?.range || ['', ''];
            const bounds = getNumericBounds(col);
            return (
              <div className="pt-1 space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    placeholder={bounds ? String(bounds[0]) : 'Min'}
                    value={cur[0]}
                    onChange={(e) => setLocalFilters((p) => ({
                      ...p, [col]: { range: [e.target.value, cur[1]] }
                    }))}
                    className="flex-1 min-w-0 px-2 py-1.5 rounded-lg body-xs text-content-primary
                               bg-surface-bg border border-surface-border
                               focus:border-brand-500 focus:outline-none transition-colors"
                  />
                  <span className="body-xs text-content-muted shrink-0">–</span>
                  <input
                    type="number"
                    placeholder={bounds ? String(bounds[1]) : 'Max'}
                    value={cur[1]}
                    onChange={(e) => setLocalFilters((p) => ({
                      ...p, [col]: { range: [cur[0], e.target.value] }
                    }))}
                    className="flex-1 min-w-0 px-2 py-1.5 rounded-lg body-xs text-content-primary
                               bg-surface-bg border border-surface-border
                               focus:border-brand-500 focus:outline-none transition-colors"
                  />
                </div>
                {bounds && (
                  <p className="body-xs text-content-muted">
                    Range: {bounds[0].toLocaleString()} – {bounds[1].toLocaleString()}
                  </p>
                )}
              </div>
            );
          })()}

          {/* ── Date ────────────────────────────────────── */}
          {type === 'date' && (() => {
            const cur = localFilters[col]?.range || ['', ''];
            return (
              <div className="pt-1 flex items-center gap-2">
                <input
                  type="date"
                  value={cur[0]}
                  onChange={(e) => setLocalFilters((p) => ({
                    ...p, [col]: { range: [e.target.value, cur[1]] }
                  }))}
                  className="flex-1 min-w-0 px-2 py-1.5 rounded-lg body-xs text-content-primary
                             bg-surface-bg border border-surface-border
                             focus:border-brand-500 focus:outline-none transition-colors"
                />
                <span className="body-xs text-content-muted shrink-0">–</span>
                <input
                  type="date"
                  value={cur[1]}
                  onChange={(e) => setLocalFilters((p) => ({
                    ...p, [col]: { range: [cur[0], e.target.value] }
                  }))}
                  className="flex-1 min-w-0 px-2 py-1.5 rounded-lg body-xs text-content-primary
                             bg-surface-bg border border-surface-border
                             focus:border-brand-500 focus:outline-none transition-colors"
                />
              </div>
            );
          })()}

        </Section>
      ))}

      {/* ── Footer: Reset + status ───────────────────────────────────────── */}
      <div className="pt-2 space-y-1.5">
        <button
          onClick={resetFilters}
          disabled={loading}
          className="w-full flex items-center justify-center gap-1.5
                     px-3 py-1.5 rounded-lg body-xs font-semibold
                     border border-surface-border text-content-secondary
                     hover:bg-surface-elevated hover:text-content-primary
                     disabled:opacity-50 transition-all"
        >
          {loading && <RefreshCw className="w-3 h-3 animate-spin" />}
          Reset all filters
        </button>
        {error && <p className="body-xs text-red-400 px-1">{error}</p>}
      </div>
    </div>
  );
}
