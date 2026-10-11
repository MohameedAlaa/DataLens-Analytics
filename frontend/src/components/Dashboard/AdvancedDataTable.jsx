import React, { useState, useMemo } from 'react';
import { useData } from '../../context/DataContext';
import {
  Search,
  Download,
  Eye,
  Maximize2,
  Minimize2,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  Lock,
  Unlock
} from 'lucide-react';

export default function AdvancedDataTable() {
  const { datasetInfo, filteredData } = useData();
  const rows = filteredData || [];

  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [hiddenColumns, setHiddenColumns] = useState([]);
  const [freezeFirstCol, setFreezeFirstCol] = useState(true);
  const [selectedRows, setSelectedRows] = useState([]);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [copiedCell, setCopiedCell] = useState(null);
  const [showColMenu, setShowColMenu] = useState(false);

  const allColumns = useMemo(() => {
    if (rows.length > 0 && rows[0] && typeof rows[0] === 'object') {
      return Object.keys(rows[0]);
    }
    return Array.isArray(datasetInfo?.columns) ? datasetInfo.columns : [];
  }, [rows, datasetInfo]);

  const visibleColumns = useMemo(() => {
    return allColumns.filter(c => !hiddenColumns.includes(c));
  }, [allColumns, hiddenColumns]);

  // Filter by search term
  const searchedRows = useMemo(() => {
    if (!searchTerm.trim()) return rows;
    const term = searchTerm.toLowerCase();
    return rows.filter(r =>
      Object.values(r).some(val => String(val ?? '').toLowerCase().includes(term))
    );
  }, [rows, searchTerm]);

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortConfig.key) return searchedRows;
    const sorted = [...searchedRows].sort((a, b) => {
      const valA = a[sortConfig.key];
      const valB = b[sortConfig.key];

      if (valA == null) return 1;
      if (valB == null) return -1;

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortConfig.direction === 'asc' ? valA - valB : valB - valA;
      }
      return sortConfig.direction === 'asc'
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
    return sorted;
  }, [searchedRows, sortConfig]);

  // Paginate
  const totalPages = Math.ceil(sortedRows.length / pageSize) || 1;
  const currentPage = Math.min(page, totalPages);
  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, currentPage, pageSize]);

  const handleSort = (colKey) => {
    let direction = 'asc';
    if (sortConfig.key === colKey && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key: colKey, direction });
  };

  const toggleColumnVisibility = (col) => {
    setHiddenColumns(prev =>
      prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
    );
  };

  const toggleSelectRow = (idx) => {
    setSelectedRows(prev =>
      prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx]
    );
  };

  const toggleSelectAllPage = () => {
    const pageIndices = paginatedRows.map((_, i) => (currentPage - 1) * pageSize + i);
    const allSelected = pageIndices.every(i => selectedRows.includes(i));

    if (allSelected) {
      setSelectedRows(prev => prev.filter(i => !pageIndices.includes(i)));
    } else {
      setSelectedRows(prev => Array.from(new Set([...prev, ...pageIndices])));
    }
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(String(text ?? ''));
    setCopiedCell(key);
    setTimeout(() => setCopiedCell(null), 1500);
  };

  const exportCSV = () => {
    if (!sortedRows.length) return;
    const exportData = selectedRows.length > 0
      ? selectedRows.map(i => sortedRows[i]).filter(Boolean)
      : sortedRows;

    const headers = visibleColumns.join(',');
    const body = exportData.map(r => visibleColumns.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([`${headers}\n${body}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${datasetInfo?.filename || 'export'}_filtered.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!datasetInfo) {
    return (
      <div className="p-8 rounded-2xl border border-surface-border bg-surface-card text-center body-xs text-content-secondary">
        No dataset loaded yet. Upload a dataset to inspect formatted data rows.
      </div>
    );
  }

  return (
    <div className={`rounded-2xl border border-surface-border bg-surface-card flex flex-col transition-all ${
      isFullScreen ? 'fixed inset-4 z-50 shadow-2xl bg-surface-bg' : 'relative'
    }`}>
      {/* ── Toolbar: Responsive wrapping layout (Task 5) ── */}
      <div className="p-3.5 border-b border-surface-border flex flex-wrap items-center justify-between gap-3">
        {/* Left: Search input & Row Counter */}
        <div className="flex items-center gap-3 flex-wrap flex-1 min-w-[240px]">
          <div className="relative flex-1 min-w-[180px] max-w-md">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-content-muted" />
            <input
              type="text"
              placeholder="Search table rows..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
              className="w-full pl-8 pr-3 py-1.5 bg-surface-elevated border border-surface-border rounded-xl body-xs text-content-primary placeholder:text-content-muted focus:outline-none focus:border-brand-500"
            />
          </div>
          <span className="body-xs text-content-secondary shrink-0 font-medium">
            {sortedRows.length.toLocaleString()} row{sortedRows.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Right: Table Action Buttons (Wrap gracefully) */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          {/* Column Toggle Menu */}
          <div className="relative">
            <button
              onClick={() => setShowColMenu(!showColMenu)}
              aria-label="Toggle column visibility menu"
              className="px-3 py-1.5 rounded-xl border border-surface-border bg-surface-elevated body-xs text-content-secondary hover:text-content-primary flex items-center gap-1.5 transition-colors"
            >
              <Eye className="w-3.5 h-3.5 text-brand-400" />
              <span>Columns</span>
            </button>
            {showColMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-surface-elevated border border-surface-border rounded-xl p-2 shadow-xl z-30 max-h-56 overflow-y-auto custom-scrollbar">
                <p className="label-caps px-2 mb-1">Toggle Columns</p>
                {allColumns.map(col => (
                  <label key={col} className="flex items-center gap-2 px-2 py-1 hover:bg-surface-card rounded body-xs text-content-primary cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!hiddenColumns.includes(col)}
                      onChange={() => toggleColumnVisibility(col)}
                      className="rounded border-surface-border text-brand-500 focus:ring-0"
                    />
                    <span className="truncate">{col}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Freeze First Column Toggle */}
          <button
            onClick={() => setFreezeFirstCol(!freezeFirstCol)}
            aria-label={freezeFirstCol ? "Unfreeze first column" : "Freeze first column"}
            className={`px-3 py-1.5 rounded-xl border body-xs flex items-center gap-1.5 transition-all ${
              freezeFirstCol
                ? 'border-brand-500/40 bg-brand-500/10 text-brand-400 font-semibold'
                : 'border-surface-border bg-surface-elevated text-content-secondary'
            }`}
          >
            {freezeFirstCol ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
            <span>Freeze Col 1</span>
          </button>

          {/* CSV Export */}
          <button
            onClick={exportCSV}
            aria-label="Export filtered data to CSV"
            className="px-3 py-1.5 rounded-xl border border-surface-border bg-surface-elevated body-xs text-content-primary hover:bg-brand-500/10 hover:border-brand-500/30 flex items-center gap-1.5 transition-colors font-medium"
          >
            <Download className="w-3.5 h-3.5 text-brand-400" />
            <span>Export CSV</span>
          </button>

          {/* Full Screen Toggle */}
          <button
            onClick={() => setIsFullScreen(!isFullScreen)}
            aria-label={isFullScreen ? "Exit full screen view" : "Open full screen view"}
            className="p-1.5 rounded-xl border border-surface-border bg-surface-elevated text-content-secondary hover:text-content-primary transition-colors"
            title={isFullScreen ? "Exit Full Screen" : "Full Screen"}
          >
            {isFullScreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Main Scrollable Table Area */}
      <div className="flex-1 overflow-auto custom-scrollbar max-h-[500px]">
        {paginatedRows.length === 0 ? (
          <div className="p-12 text-center body-xs text-content-secondary">
            No rows match the search query or active filter criteria.
          </div>
        ) : (
          <table className="w-full text-left border-collapse body-xs">
            <thead className="sticky top-0 bg-surface-elevated border-b border-surface-border z-10">
              <tr>
                <th className="p-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={paginatedRows.length > 0 && paginatedRows.every((_, i) => selectedRows.includes((currentPage - 1) * pageSize + i))}
                    onChange={toggleSelectAllPage}
                    className="rounded border-surface-border text-brand-500 focus:ring-0"
                  />
                </th>
                {visibleColumns.map((col, idx) => (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    className={`p-3 font-semibold text-content-secondary cursor-pointer hover:text-content-primary select-none whitespace-nowrap ${
                      freezeFirstCol && idx === 0 ? 'sticky left-0 bg-surface-elevated z-20 border-r border-surface-border' : ''
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col}</span>
                      <ArrowUpDown className="w-3 h-3 opacity-50" />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedRows.map((row, rIdx) => {
                const globalIdx = (currentPage - 1) * pageSize + rIdx;
                const isSelected = selectedRows.includes(globalIdx);
                return (
                  <tr
                    key={globalIdx}
                    className={`border-b border-surface-border/50 hover:bg-surface-elevated/50 transition-colors ${
                      isSelected ? 'bg-brand-500/10' : ''
                    }`}
                  >
                    <td className="p-3 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectRow(globalIdx)}
                        className="rounded border-surface-border text-brand-500 focus:ring-0"
                      />
                    </td>
                    {visibleColumns.map((col, cIdx) => {
                      const cellVal = row[col] ?? '—';
                      const cellKey = `${globalIdx}-${col}`;
                      const isCopied = copiedCell === cellKey;
                      return (
                        <td
                          key={col}
                          className={`p-3 text-content-primary whitespace-nowrap max-w-[240px] truncate relative group ${
                            freezeFirstCol && cIdx === 0 ? 'sticky left-0 bg-surface-card z-10 border-r border-surface-border font-medium' : ''
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="truncate">{String(cellVal)}</span>
                            <button
                              onClick={() => copyToClipboard(cellVal, cellKey)}
                              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-surface-elevated rounded text-content-muted hover:text-content-primary transition-opacity"
                              title="Copy cell value"
                            >
                              {isCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            </button>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Footer */}
      <div className="p-3 border-t border-surface-border flex flex-wrap items-center justify-between gap-3 body-xs text-content-secondary">
        <div className="flex items-center gap-2 flex-wrap">
          <span>Rows per page:</span>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
            className="bg-surface-elevated border border-surface-border rounded-lg px-2 py-1 text-content-primary focus:outline-none"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          {selectedRows.length > 0 && (
            <span className="px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 font-semibold border border-brand-500/20">
              {selectedRows.length} row{selectedRows.length > 1 ? 's' : ''} selected
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span>Page {currentPage} of {totalPages}</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={currentPage === 1}
              aria-label="Go to first page"
              className="p-1 rounded-lg border border-surface-border bg-surface-elevated disabled:opacity-40"
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              aria-label="Go to previous page"
              className="p-1 rounded-lg border border-surface-border bg-surface-elevated disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              aria-label="Go to next page"
              className="p-1 rounded-lg border border-surface-border bg-surface-elevated disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={currentPage === totalPages}
              aria-label="Go to last page"
              className="p-1 rounded-lg border border-surface-border bg-surface-elevated disabled:opacity-40"
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
