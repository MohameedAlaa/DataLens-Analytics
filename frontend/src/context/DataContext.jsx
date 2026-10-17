import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import axios from 'axios';
import { apiClient, extractErrorMessage } from '../utils/apiClient';

// Create Context
const DataContext = createContext(null);

export const useData = () => useContext(DataContext);

export const DataProvider = ({ children }) => {
  const [datasetInfo, setDatasetInfo] = useState(null); // includes columns, dtypes, preview, etc.
  const [rawData, setRawData] = useState([]); // full rows (limited to 20000 for UI)
  const [filteredData, setFilteredData] = useState([]);
  const [filteredTotal, setFilteredTotal] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [filters, setFilters] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const filterAbortControllerRef = useRef(null);
  const filterRequestSeqRef = useRef(0);

  // Clear dataset and reset all dependent states
  const clearDataset = useCallback(() => {
    if (filterAbortControllerRef.current) {
      filterAbortControllerRef.current.abort();
    }
    setDatasetInfo(null);
    setRawData([]);
    setFilteredData([]);
    setFilteredTotal(null);
    setHasMore(false);
    setFilters({});
    setError(null);
    setLoading(false);
  }, []);

  // Upload handler – called from useDataset hook
  const uploadFile = useCallback(async (file) => {
    setLoading(true);
    setError(null);
    try {
      // Abort any pending filter request from previous dataset
      if (filterAbortControllerRef.current) {
        filterAbortControllerRef.current.abort();
      }

      const form = new FormData();
      form.append('file', file);
      // Let the browser set the Content-Type (and boundary) automatically.
      const resp = await apiClient.post('/upload', form);
      const info = resp.data || {};
      const normalizedInfo = {
        ...info,
        filename: info.filename || 'uploaded_dataset',
        shape: Array.isArray(info.shape) ? info.shape : [0, 0],
        columns: Array.isArray(info.columns) ? info.columns : [],
        dtypes: info.dtypes || {},
        numeric_columns: Array.isArray(info.numeric_columns) ? info.numeric_columns : [],
        categorical_columns: Array.isArray(info.categorical_columns) ? info.categorical_columns : [],
        date_columns: Array.isArray(info.date_columns) ? info.date_columns : [],
        preview: Array.isArray(info.preview) ? info.preview : [],
        filter_options: (info.filter_options && typeof info.filter_options === 'object') ? info.filter_options : {},
      };

      // Reset filters and establish new dataset state atomically
      setFilters({});
      setDatasetInfo(normalizedInfo);
      const previewRows = normalizedInfo.preview;
      setRawData(previewRows);
      setFilteredData(previewRows);
      setFilteredTotal(normalizedInfo.shape[0] ?? previewRows.length);
      setHasMore((normalizedInfo.shape[0] ?? 0) > previewRows.length);
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to upload dataset'));
    } finally {
      setLoading(false);
    }
  }, []);

  // Apply filters – called from useFilters hook with out-of-order protection
  const applyFilters = useCallback(async (newFilters) => {
    if (!datasetInfo?.dataset_id) return;

    // Abort previous filter request if still in flight
    if (filterAbortControllerRef.current) {
      filterAbortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    filterAbortControllerRef.current = abortController;
    const requestSeq = ++filterRequestSeqRef.current;

    setLoading(true);
    setError(null);
    try {
      const resp = await apiClient.post(
        '/filter',
        {
          dataset_id: datasetInfo.dataset_id,
          filters: newFilters,
          limit: 20000,
          offset: 0,
        },
        { signal: abortController.signal }
      );

      // Only update state if this is still the latest request
      if (requestSeq === filterRequestSeqRef.current) {
        const rows = resp.data.filtered_data || [];
        const total = resp.data.total ?? resp.data.row_count ?? rows.length;
        const more = Boolean(resp.data.has_more);
        setFilters(newFilters);
        setFilteredData(rows.slice(0, 20000)); // cap for UI
        setFilteredTotal(total);
        setHasMore(more);
      }
    } catch (e) {
      if (axios.isCancel(e) || e.name === 'CanceledError' || e.name === 'AbortError') {
        // Request was cancelled intentionally, do not set error
        return;
      }
      if (requestSeq === filterRequestSeqRef.current) {
        setError(extractErrorMessage(e, 'Failed to apply filters'));
      }
    } finally {
      if (requestSeq === filterRequestSeqRef.current) {
        setLoading(false);
      }
    }
  }, [datasetInfo?.dataset_id]);

  // Reset all filters
  const resetFilters = useCallback(async () => {
    if (!datasetInfo?.dataset_id) return;
    setFilters({});
    if (rawData.length) {
      setFilteredData(rawData);
    }
    setFilteredTotal(datasetInfo?.shape?.[0] ?? rawData.length);
    setHasMore(false);
    await applyFilters({});
  }, [datasetInfo?.dataset_id, datasetInfo?.shape, rawData, applyFilters]);

  // Effect to keep filteredData in sync when raw data changes and no filters
  useEffect(() => {
    if (Object.keys(filters).length === 0 && rawData.length) {
      setFilteredData(rawData);
      setFilteredTotal(datasetInfo?.shape?.[0] ?? rawData.length);
      setHasMore(false);
    }
  }, [rawData, filters, datasetInfo?.shape]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (filterAbortControllerRef.current) {
        filterAbortControllerRef.current.abort();
      }
    };
  }, []);

  const contextValue = useMemo(() => ({
    datasetInfo,
    rawData,
    filteredData,
    filteredTotal,
    hasMore,
    filters,
    loading,
    error,
    uploadFile,
    applyFilters,
    resetFilters,
    setDatasetInfo,
    clearDataset,
  }), [
    datasetInfo,
    rawData,
    filteredData,
    filteredTotal,
    hasMore,
    filters,
    loading,
    error,
    uploadFile,
    applyFilters,
    resetFilters,
    clearDataset,
  ]);

  return (
    <DataContext.Provider value={contextValue}>
      {children}
    </DataContext.Provider>
  );
};
