import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useData } from '../../context/DataContext';
import { useFilters } from '../../hooks/useFilters';

/**
 * Dynamic filter panel that generates controls based on column types.
 * - Categorical: multi‑select checkboxes (top 10 values + Select all / Clear)
 * - Numeric: min / max number inputs (simple replacement for dual‑handle slider)
 * - Date: start / end date inputs
 * Filters are applied with a 300 ms debounce to the backend.
 */
export default function Filters() {
  const { datasetInfo, rawData, filteredData } = useData();
  const { clearFilter, resetFilters, filters, loading, error, applyFilters } = useFilters();

  const [localFilters, setLocalFilters] = useState({});
  const [debounceTimer, setDebounceTimer] = useState(null);
  const hasInitializedFilters = useRef(false);

  const getNumericBounds = useCallback(
    (col) => {
      const values = rawData
        .map((r) => Number(r[col]))
        .filter((v) => !Number.isNaN(v));
      if (!values.length) return null;
      return [Math.min(...values), Math.max(...values)];
    },
    [rawData]
  );

  // Initialise localFilters when datasetInfo changes
  useEffect(() => {
    if (!datasetInfo) return;
    const init = {};
    datasetInfo.numeric_columns?.forEach((col) => {
      const bounds = getNumericBounds(col);
      if (bounds) {
        init[col] = { range: bounds };
      }
    });
    datasetInfo.categorical_columns?.forEach((col) => {
      init[col] = [];
    });
    datasetInfo.date_columns?.forEach((col) => {
      init[col] = { range: ['', ''] };
    });
    setLocalFilters(init);
    hasInitializedFilters.current = false;
  }, [datasetInfo, getNumericBounds]);

  // Build backend filter payload format expected by /filter endpoint
  const buildPayload = useCallback(() => {
    const payload = {};
    Object.entries(localFilters).forEach(([col, val]) => {
      if (Array.isArray(val) && val.length) {
        payload[col] = val;
        return;
      }

      if (val && typeof val === 'object' && val.range) {
        const [lo, hi] = val.range;
        if (datasetInfo?.numeric_columns?.includes(col)) {
          const bounds = getNumericBounds(col);
          const loNum = lo !== '' ? Number(lo) : bounds?.[0];
          const hiNum = hi !== '' ? Number(hi) : bounds?.[1];
          if (bounds && (lo !== '' || hi !== '') && (loNum !== bounds[0] || hiNum !== bounds[1])) {
            payload[col] = { range: [loNum, hiNum] };
          }
        } else if (datasetInfo?.date_columns?.includes(col)) {
          if (lo || hi) {
            payload[col] = { range: [lo, hi] };
          }
        }
      }
    });
    return payload;
  }, [datasetInfo, localFilters, getNumericBounds]);

  const apply = useCallback(() => {
    if (!hasInitializedFilters.current) {
      hasInitializedFilters.current = true;
      return;
    }

    const payload = buildPayload();
    applyFilters(payload);
  }, [applyFilters, buildPayload]);

  // Debounce handling
  useEffect(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
    const timer = setTimeout(() => apply(), 300);
    setDebounceTimer(timer);
    return () => clearTimeout(timer);
  }, [localFilters, apply]);

  // Helper to compute top 10 categorical values from the original raw dataset
  const topValues = (col) => {
    const counts = {};
    const source = rawData.length ? rawData : filteredData;
    source.forEach((row) => {
      const v = row[col];
      if (v != null) counts[v] = (counts[v] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map((e) => e[0]);
  };

  if (!datasetInfo) return <p className="p-4 text-slate">No dataset loaded.</p>;

  return (
    <div className="h-full text-surface">
      <h2 className="text-lg font-medium mb-4 sr-only">Filters</h2>

      {/* Categorical filters */}
      {datasetInfo.categorical_columns?.map((col) => (
        <div key={col} className="mb-4">
          <label className="block font-medium mb-1">{col}</label>
          <div className="max-h-40 overflow-y-auto border border-slate rounded p-2 bg-navy">
            {/* Select all / Clear */}
            <div className="flex items-center mb-1">
              <input
                type="checkbox"
                checked={
                  localFilters[col] &&
                  topValues(col).every((v) => localFilters[col].includes(v))
                }
                onChange={(e) => {
                  const allVals = topValues(col);
                  setLocalFilters((prev) => ({
                    ...prev,
                    [col]: e.target.checked ? allVals : [],
                  }));
                }}
              />
              <span className="ml-2 text-xs">Select all / Clear</span>
            </div>
            {topValues(col).map((v) => (
              <div key={v} className="flex items-center">
                <input
                  type="checkbox"
                  checked={localFilters[col]?.includes(v) || false}
                  onChange={(e) => {
                    const cur = localFilters[col] || [];
                    setLocalFilters((prev) => ({
                      ...prev,
                      [col]: e.target.checked ? [...cur, v] : cur.filter((x) => x !== v),
                    }));
                  }}
                />
                <span className="ml-2 text-xs">{v}</span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Numeric filters */}
      {datasetInfo.numeric_columns?.map((col) => {
        const cur = localFilters[col]?.range || ['', ''];
        const values = filteredData.map((r) => Number(r[col])).filter((v) => !isNaN(v));
        const min = values.length ? Math.min(...values) : '';
        const max = values.length ? Math.max(...values) : '';
        return (
          <div key={col} className="mb-4">
            <label className="block font-medium mb-1">{col}</label>
            <div className="flex space-x-2 items-center">
              <input
                type="number"
                placeholder={min}
                value={cur[0]}
                onChange={(e) => {
                  const lo = e.target.value;
                  setLocalFilters((prev) => ({
                    ...prev,
                    [col]: { range: [lo, cur[1]] },
                  }));
                }}
                className="w-1/2 bg-navy border border-slate rounded p-1"
              />
              <span className="text-xs">–</span>
              <input
                type="number"
                placeholder={max}
                value={cur[1]}
                onChange={(e) => {
                  const hi = e.target.value;
                  setLocalFilters((prev) => ({
                    ...prev,
                    [col]: { range: [cur[0], hi] },
                  }));
                }}
                className="w-1/2 bg-navy border border-slate rounded p-1"
              />
            </div>
          </div>
        );
      })}

      {/* Date filters */}
      {datasetInfo.date_columns?.map((col) => {
        const cur = localFilters[col]?.range || ['', ''];
        return (
          <div key={col} className="mb-4">
            <label className="block font-medium mb-1">{col}</label>
            <div className="flex space-x-2 items-center">
              <input
                type="date"
                value={cur[0]}
                onChange={(e) => {
                  setLocalFilters((prev) => ({
                    ...prev,
                    [col]: { range: [e.target.value, cur[1]] },
                  }));
                }}
                className="w-1/2 bg-navy border border-slate rounded p-1"
              />
              <span className="text-xs">–</span>
              <input
                type="date"
                value={cur[1]}
                onChange={(e) => {
                  setLocalFilters((prev) => ({
                    ...prev,
                    [col]: { range: [cur[0], e.target.value] },
                  }));
                }}
                className="w-1/2 bg-navy border border-slate rounded p-1"
              />
            </div>
          </div>
        );
      })}

      <button
        className="mt-4 px-3 py-1 bg-electric text-navy rounded hover:bg-electric/80"
        onClick={resetFilters}
        disabled={loading}
      >
        Reset all filters
      </button>

      {loading && <p className="mt-2 text-sm">Applying filters…</p>}
      {error && <p className="mt-2 text-red-400">{error}</p>}
    </div>
  );
}
