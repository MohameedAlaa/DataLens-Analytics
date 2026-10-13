import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useData } from '../../context/DataContext';
import { useFilters } from '../../hooks/useFilters';
import {
  RefreshCw,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Hash,
  Type,
  Calendar,
  Filter,
  X,
  Search,
  RotateCcw
} from 'lucide-react';

/**
 * Professional SaaS Dataset Filter Control Center
 * Features:
 * - Collapsible section with active filter count badge "[3 Active]"
 * - Quick "Clear all" action
 * - Immediate active-filter chips bar with individual "x" removal
 * - Column search filter for datasets with > 4 columns
 * - Column-type icons: Text (Type), Numeric (Hash), Date (Calendar)
 * - Restrained, clean SaaS card accordions with subtle hover and active states
 */
export default function Filters() {
  const { datasetInfo, rawData, filteredData } = useData();
  const { applyFilters, resetFilters, filters, loading, error } = useFilters();

  const [isSectionOpen, setIsSectionOpen] = useState(true);
  const [localFilters, setLocalFilters] = useState({});
  const [openSections, setOpenSections] = useState({});
  const [columnSearch, setColumnSearch] = useState('');
  const debounceRef = useRef(null);
  const initialised = useRef(false);

  // ── Numeric Bounds Helper ─────────────────────────────────────────────────
  const getNumericBounds = useCallback((col) => {
    const vals = rawData.map((r) => Number(r[col])).filter((v) => !Number.isNaN(v));
    return vals.length ? [Math.min(...vals), Math.max(...vals)] : null;
  }, [rawData]);

  // ── Categorical Top Values Cache ──────────────────────────────────────────
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
      .slice(0, 15)
      .map(([k, cnt]) => ({ value: k, count: cnt }));
    topValuesCache.current[col] = result;
    return result;
  }, [rawData, filteredData]);

  useEffect(() => {
    topValuesCache.current = {};
  }, [rawData, filteredData]);

  // ── Initialise localFilters helper ──────────────────────────────────────
  const getInitialFilters = useCallback(() => {
    if (!datasetInfo) return {};
    const init = {};
    (Array.isArray(datasetInfo?.numeric_columns) ? datasetInfo.numeric_columns : []).forEach((col) => {
      const b = getNumericBounds(col);
      if (b) init[col] = { range: [String(b[0]), String(b[1])] };
    });
    (Array.isArray(datasetInfo?.categorical_columns) ? datasetInfo.categorical_columns : []).forEach((col) => {
      init[col] = [];
    });
    (Array.isArray(datasetInfo?.date_columns) ? datasetInfo.date_columns : []).forEach((col) => {
      init[col] = { range: ['', ''] };
    });
    return init;
  }, [datasetInfo, getNumericBounds]);

  // ── Initialise when dataset changes ───────────────────────────────────────
  useEffect(() => {
    if (!datasetInfo) return;
    const init = getInitialFilters();
    const open = {};
    Object.keys(init).forEach((col) => {
      open[col] = false;
    });
    setLocalFilters(init);
    setOpenSections(open);
    initialised.current = false;
  }, [datasetInfo?.dataset_id]);

  // Handle explicit reset of filters
  const handleResetFilters = useCallback(async () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    initialised.current = false;
    setLocalFilters(getInitialFilters());
    await resetFilters();
  }, [getInitialFilters, resetFilters]);

  // Sync if external filters transitioned from non-empty to empty
  const prevFiltersRef = useRef(filters);
  useEffect(() => {
    if (datasetInfo && Object.keys(prevFiltersRef.current || {}).length > 0 && Object.keys(filters || {}).length === 0) {
      setLocalFilters(getInitialFilters());
    }
    prevFiltersRef.current = filters;
  }, [filters, datasetInfo, getInitialFilters]);

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
    if (!initialised.current) {
      initialised.current = true;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => applyFilters(buildPayload()), 350);
    return () => clearTimeout(debounceRef.current);
  }, [localFilters]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleSection = (col) => {
    setOpenSections((p) => ({ ...p, [col]: !p[col] }));
  };

  // ── Column Definitions ───────────────────────────────────────────────────
  const allColumns = useMemo(() => {
    if (!datasetInfo) return [];
    return [
      ...((Array.isArray(datasetInfo?.categorical_columns) ? datasetInfo.categorical_columns : []).map((c) => ({ col: c, type: 'cat' }))),
      ...((Array.isArray(datasetInfo?.numeric_columns) ? datasetInfo.numeric_columns : []).map((c) => ({ col: c, type: 'num' }))),
      ...((Array.isArray(datasetInfo?.date_columns) ? datasetInfo.date_columns : []).map((c) => ({ col: c, type: 'date' }))),
    ];
  }, [datasetInfo]);

  // ── Active Filters Computation ───────────────────────────────────────────
  const activeChips = useMemo(() => {
    if (!datasetInfo) return [];
    const chips = [];

    // Categorical active chips
    (Array.isArray(datasetInfo?.categorical_columns) ? datasetInfo.categorical_columns : []).forEach((col) => {
      const selected = localFilters[col];
      if (Array.isArray(selected) && selected.length > 0) {
        selected.forEach((val) => {
          chips.push({
            id: `cat-${col}-${val}`,
            col,
            type: 'cat',
            label: String(val),
            onRemove: () => {
              setLocalFilters((prev) => ({
                ...prev,
                [col]: (prev[col] || []).filter((item) => item !== val)
              }));
            }
          });
        });
      }
    });

    // Numeric active chips
    (Array.isArray(datasetInfo?.numeric_columns) ? datasetInfo.numeric_columns : []).forEach((col) => {
      const cur = localFilters[col]?.range;
      if (cur) {
        const bounds = getNumericBounds(col);
        const [lo, hi] = cur;
        const isModified = bounds && (
          (lo !== '' && Number(lo) !== bounds[0]) ||
          (hi !== '' && Number(hi) !== bounds[1])
        );
        if (isModified) {
          const display = `${lo || bounds[0]} – ${hi || bounds[1]}`;
          chips.push({
            id: `num-${col}`,
            col,
            type: 'num',
            label: display,
            onRemove: () => {
              setLocalFilters((prev) => ({
                ...prev,
                [col]: { range: bounds ? [String(bounds[0]), String(bounds[1])] : ['', ''] }
              }));
            }
          });
        }
      }
    });

    // Date active chips
    (Array.isArray(datasetInfo?.date_columns) ? datasetInfo.date_columns : []).forEach((col) => {
      const cur = localFilters[col]?.range;
      if (cur && (cur[0] || cur[1])) {
        const display = `${cur[0] || 'Start'} to ${cur[1] || 'End'}`;
        chips.push({
          id: `date-${col}`,
          col,
          type: 'date',
          label: display,
          onRemove: () => {
            setLocalFilters((prev) => ({
              ...prev,
              [col]: { range: ['', ''] }
            }));
          }
        });
      }
    });

    return chips;
  }, [datasetInfo, localFilters, getNumericBounds]);

  // Unique active columns count
  const activeColumnCount = useMemo(() => {
    const cols = new Set(activeChips.map((c) => c.col));
    return cols.size;
  }, [activeChips]);

  // Filter columns by search query
  const filteredColumns = useMemo(() => {
    if (!columnSearch.trim()) return allColumns;
    const query = columnSearch.toLowerCase().trim();
    return allColumns.filter(({ col }) => col.toLowerCase().includes(query));
  }, [allColumns, columnSearch]);

  return (
    <div className="space-y-2">
      {/* ── Section Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-1 py-0.5">
        <button
          type="button"
          onClick={() => setIsSectionOpen((prev) => !prev)}
          className="flex items-center gap-2 group text-left focus:outline-none"
          aria-expanded={isSectionOpen}
          aria-label="Toggle Dataset Filters Section"
        >
          <Filter className="w-3.5 h-3.5 text-brand-400 group-hover:text-brand-300 transition-colors shrink-0" />
          <span className="text-xs font-semibold text-content-primary group-hover:text-white transition-colors">
            Dataset Filters
          </span>
          <ChevronDown
            className={`w-3 h-3 text-content-muted group-hover:text-content-secondary shrink-0 transition-transform duration-200 motion-reduce:transition-none ${
              isSectionOpen ? 'rotate-0' : '-rotate-90'
            }`}
          />
        </button>

        <div className="flex items-center gap-1.5">
          {activeColumnCount > 0 && (
            <>
              <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold rounded-md bg-brand-500/15 text-brand-300 border border-brand-500/30">
                {activeColumnCount} Active
              </span>
              <button
                type="button"
                onClick={handleResetFilters}
                title="Clear all active filters"
                aria-label="Clear all active filters"
                className="text-[11px] text-content-muted hover:text-red-400 hover:underline px-1 py-0.5 font-medium transition-colors"
              >
                Clear all
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Collapsible Content Container with Smooth Height Transition ── */}
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-200 ease-out motion-reduce:transition-none ${
          isSectionOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0 pointer-events-none'
        }`}
      >
        <div className="overflow-hidden space-y-2">
          {!datasetInfo ? (
            <div className="rounded-xl border border-surface-border/60 bg-surface-card/30 p-3 text-center">
              <Filter className="w-4 h-4 text-content-muted mx-auto mb-1.5 opacity-60" />
              <p className="body-xs text-content-muted font-medium">No dataset active</p>
              <p className="text-[10px] text-content-muted/70 mt-0.5">Upload a dataset to activate filters</p>
            </div>
          ) : !allColumns.length ? (
            <div className="rounded-xl border border-surface-border/60 bg-surface-card/30 p-3 text-center">
              <p className="body-xs text-content-muted">No filterable columns found in dataset.</p>
            </div>
          ) : (
            <>
              {/* ── Active Filters Summary Bar (Visible when filters are active) ── */}
          {activeChips.length > 0 && (
            <div className="p-2 rounded-xl bg-surface-elevated/40 border border-surface-border space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase tracking-wider text-content-muted font-semibold">
                  Applied ({activeChips.length})
                </span>
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="flex items-center gap-1 text-[10px] text-brand-400 hover:text-brand-300 font-medium transition-colors"
                >
                  <RotateCcw className="w-2.5 h-2.5" />
                  Reset
                </button>
              </div>
              <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto custom-scrollbar pr-0.5">
                {activeChips.map((chip) => (
                  <span
                    key={chip.id}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md
                               bg-brand-500/10 border border-brand-500/25 text-[11px] text-brand-300 max-w-full"
                  >
                    <span className="text-content-muted text-[10px] truncate max-w-[70px]">{chip.col}:</span>
                    <span className="font-medium text-white truncate max-w-[90px]" title={chip.label}>
                      {chip.label}
                    </span>
                    <button
                      type="button"
                      onClick={chip.onRemove}
                      aria-label={`Remove filter ${chip.col} ${chip.label}`}
                      className="p-0.5 text-brand-400 hover:text-white hover:bg-brand-500/20 rounded transition-colors"
                    >
                      <X className="w-2.5 h-2.5" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── Column Search (for datasets with > 4 columns) ──────────────── */}
          {allColumns.length > 4 && (
            <div className="relative">
              <Search className="w-3 h-3 text-content-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="Search filter fields..."
                value={columnSearch}
                onChange={(e) => setColumnSearch(e.target.value)}
                aria-label="Search filter columns"
                className="w-full pl-7 pr-7 py-1 text-xs rounded-lg bg-surface-bg/80 border border-surface-border
                           text-content-primary placeholder:text-content-muted
                           focus:border-brand-500/60 focus:bg-surface-bg focus:outline-none transition-colors"
              />
              {columnSearch && (
                <button
                  type="button"
                  onClick={() => setColumnSearch('')}
                  aria-label="Clear column search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-content-muted hover:text-content-primary rounded"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              )}
            </div>
          )}

          {/* ── Column Filter Controls List ───────────────────────────────── */}
          <div className="space-y-1 max-h-[calc(100vh-28rem)] overflow-y-auto custom-scrollbar pr-0.5">
            {filteredColumns.length === 0 ? (
              <p className="body-xs text-content-muted py-2 text-center">No columns match &quot;{columnSearch}&quot;</p>
            ) : (
              filteredColumns.map(({ col, type }) => {
                const isOpen = !!openSections[col];
                const Icon = type === 'cat' ? Type : type === 'num' ? Hash : Calendar;

                // Check active state for this specific column
                let isColActive = false;
                let activeCount = 0;
                if (type === 'cat') {
                  const sel = localFilters[col];
                  if (Array.isArray(sel) && sel.length > 0) {
                    isColActive = true;
                    activeCount = sel.length;
                  }
                } else if (type === 'num') {
                  const cur = localFilters[col]?.range;
                  if (cur) {
                    const bounds = getNumericBounds(col);
                    if (bounds && ((cur[0] !== '' && Number(cur[0]) !== bounds[0]) || (cur[1] !== '' && Number(cur[1]) !== bounds[1]))) {
                      isColActive = true;
                    }
                  }
                } else if (type === 'date') {
                  const cur = localFilters[col]?.range;
                  if (cur && (cur[0] || cur[1])) {
                    isColActive = true;
                  }
                }

                return (
                  <div
                    key={col}
                    className={`rounded-lg border transition-all duration-150 overflow-hidden ${
                      isColActive
                        ? 'border-brand-500/35 bg-surface-elevated/30'
                        : 'border-surface-border/80 bg-surface-card/40 hover:border-surface-borderStrong'
                    }`}
                  >
                    {/* Collapsed Control Header */}
                    <button
                      type="button"
                      onClick={() => toggleSection(col)}
                      aria-expanded={isOpen}
                      aria-label={`Filter by ${col}`}
                      className="w-full flex items-center justify-between px-2.5 py-1.5 text-left
                                 hover:bg-surface-elevated/60 transition-colors focus:outline-none"
                    >
                      <span className="flex items-center gap-2 min-w-0">
                        <Icon className={`w-3 h-3 shrink-0 ${isColActive ? 'text-brand-400' : 'text-content-muted'}`} />
                        <span className="text-xs font-medium text-content-primary truncate" title={col}>
                          {col}
                        </span>
                      </span>

                      <div className="flex items-center gap-1.5 shrink-0 ml-1">
                        {isColActive && (
                          <span className="px-1.5 py-0.2 text-[9px] font-mono font-semibold rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">
                            {type === 'cat' ? activeCount : 'active'}
                          </span>
                        )}
                        <ChevronDown
                          className={`w-3 h-3 text-content-muted shrink-0 transition-transform duration-200 motion-reduce:transition-none ${
                            isOpen ? 'rotate-180' : 'rotate-0'
                          }`}
                        />
                      </div>
                    </button>

                    {/* Expanded Controls Body with Smooth Grid Transition */}
                    <div
                      className={`grid transition-[grid-template-rows,opacity] duration-200 ease-out motion-reduce:transition-none ${
                        isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                      }`}
                    >
                      <div className="overflow-hidden">
                        <div className="px-2.5 pb-2.5 pt-1.5 border-t border-surface-border/60 bg-surface-bg/40">
                        {/* Categorical Filter Control */}
                        {type === 'cat' && (() => {
                          const items = topValues(col);
                          const selected = localFilters[col] || [];
                          const allVals = items.map((it) => it.value);
                          const allSelected = allVals.length > 0 && allVals.every((v) => selected.includes(v));

                          return (
                            <div className="space-y-1">
                              {/* Quick Actions (Select all / Deselect) */}
                              <div className="flex items-center justify-between pb-1 border-b border-surface-border/50 text-[10px]">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setLocalFilters((prev) => {
                                      const cur = prev[col] || [];
                                      const isAll = allVals.length > 0 && allVals.every((x) => cur.includes(x));
                                      return {
                                        ...prev,
                                        [col]: isAll ? [] : allVals
                                      };
                                    });
                                  }}
                                  className="text-brand-400 hover:text-brand-300 font-medium transition-colors"
                                >
                                  {allSelected ? 'Deselect all' : 'Select all'}
                                </button>
                                {selected.length > 0 && (
                                  <span className="text-content-muted font-mono">
                                    {selected.length} of {allVals.length}
                                  </span>
                                )}
                              </div>

                              {/* Options List */}
                              <div className="space-y-0.5 max-h-36 overflow-y-auto custom-scrollbar pt-1 pr-0.5">
                                {items.map(({ value: v, count: cnt }) => {
                                  const isChecked = selected.includes(v);
                                  return (
                                    <label
                                      key={v}
                                      className={`flex items-center justify-between gap-2 px-1.5 py-1 rounded cursor-pointer transition-colors ${
                                        isChecked
                                          ? 'bg-brand-500/10 text-white font-medium'
                                          : 'text-content-secondary hover:bg-surface-elevated hover:text-content-primary'
                                      }`}
                                    >
                                      <span className="flex items-center gap-2 min-w-0">
                                        <input
                                          type="checkbox"
                                          checked={isChecked}
                                          onChange={(e) => {
                                            const isCheckedNow = e.target.checked;
                                            setLocalFilters((prev) => {
                                              const cur = prev[col] || [];
                                              return {
                                                ...prev,
                                                [col]: isCheckedNow
                                                  ? [...cur, v]
                                                  : cur.filter((x) => x !== v)
                                              };
                                            });
                                          }}
                                          className="w-3.5 h-3.5 rounded border-surface-border text-brand-400 accent-brand-400 focus:ring-brand-400 bg-surface-card"
                                        />
                                        <span className="text-xs truncate" title={v}>{v}</span>
                                      </span>
                                      <span className="text-[10px] font-mono text-content-muted shrink-0">
                                        {cnt.toLocaleString()}
                                      </span>
                                    </label>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Numeric Range Filter Control */}
                        {type === 'num' && (() => {
                          const cur = localFilters[col]?.range || ['', ''];
                          const bounds = getNumericBounds(col);

                          return (
                            <div className="space-y-1.5 pt-0.5">
                              <div className="flex items-center gap-1.5">
                                <input
                                  type="number"
                                  placeholder={bounds ? String(bounds[0]) : 'Min'}
                                  value={cur[0]}
                                  onChange={(e) =>
                                    setLocalFilters((p) => ({
                                      ...p,
                                      [col]: { range: [e.target.value, cur[1]] }
                                    }))
                                  }
                                  className="w-full min-w-0 px-2 py-1 rounded-md text-xs text-content-primary
                                             bg-surface-bg border border-surface-border
                                             focus:border-brand-500 focus:outline-none transition-colors"
                                />
                                <span className="text-content-muted text-xs shrink-0">–</span>
                                <input
                                  type="number"
                                  placeholder={bounds ? String(bounds[1]) : 'Max'}
                                  value={cur[1]}
                                  onChange={(e) =>
                                    setLocalFilters((p) => ({
                                      ...p,
                                      [col]: { range: [cur[0], e.target.value] }
                                    }))
                                  }
                                  className="w-full min-w-0 px-2 py-1 rounded-md text-xs text-content-primary
                                             bg-surface-bg border border-surface-border
                                             focus:border-brand-500 focus:outline-none transition-colors"
                                />
                              </div>
                              {bounds && (
                                <div className="flex items-center justify-between text-[10px] text-content-muted px-0.5">
                                  <span>Min: {bounds[0].toLocaleString()}</span>
                                  <span>Max: {bounds[1].toLocaleString()}</span>
                                </div>
                              )}
                            </div>
                          );
                        })()}

                        {/* Date Range Filter Control */}
                        {type === 'date' && (() => {
                          const cur = localFilters[col]?.range || ['', ''];

                          return (
                            <div className="space-y-1.5 pt-0.5">
                              <div className="grid grid-cols-2 gap-1.5">
                                <div>
                                  <label className="text-[10px] text-content-muted block mb-0.5">Start</label>
                                  <input
                                    type="date"
                                    value={cur[0]}
                                    onChange={(e) =>
                                      setLocalFilters((p) => ({
                                        ...p,
                                        [col]: { range: [e.target.value, cur[1]] }
                                      }))
                                    }
                                    className="w-full min-w-0 px-1.5 py-1 rounded-md text-xs text-content-primary
                                               bg-surface-bg border border-surface-border
                                               focus:border-brand-500 focus:outline-none transition-colors"
                                  />
                                </div>
                                <div>
                                  <label className="text-[10px] text-content-muted block mb-0.5">End</label>
                                  <input
                                    type="date"
                                    value={cur[1]}
                                    onChange={(e) =>
                                      setLocalFilters((p) => ({
                                        ...p,
                                        [col]: { range: [cur[0], e.target.value] }
                                      }))
                                    }
                                    className="w-full min-w-0 px-1.5 py-1 rounded-md text-xs text-content-primary
                                               bg-surface-bg border border-surface-border
                                               focus:border-brand-500 focus:outline-none transition-colors"
                                  />
                                </div>
                              </div>
                            </div>
                          );
                        })()}
                      </div>
                    </div>
                  </div>
                </div>
                );
              })
            )}
          </div>

          {/* ── Footer Status & Reset Action ──────────────────────────────── */}
          <div className="pt-1 flex items-center justify-between text-[11px] text-content-muted">
            <span className="flex items-center gap-1.5">
              {loading ? (
                <>
                  <RefreshCw className="w-3 h-3 text-brand-400 animate-spin" />
                  <span className="text-brand-300">Filtering dataset…</span>
                </>
              ) : (
                <span>{filteredData?.length ? `${filteredData.length.toLocaleString()} matching rows` : ''}</span>
              )}
            </span>

            {activeColumnCount > 0 && (
              <button
                type="button"
                onClick={handleResetFilters}
                disabled={loading}
                className="hover:text-red-400 transition-colors disabled:opacity-50"
              >
                Reset all
              </button>
            )}
          </div>

          {error && <p className="body-xs text-red-400 px-1">{error}</p>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
