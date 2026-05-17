import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

// Create Context
const DataContext = createContext(null);

export const useData = () => useContext(DataContext);

export const DataProvider = ({ children }) => {
  const [datasetInfo, setDatasetInfo] = useState(null); // includes columns, dtypes, preview, etc.
  const [rawData, setRawData] = useState([]); // full rows (limited to 1000 for UI)
  const [filteredData, setFilteredData] = useState([]);
  const [filters, setFilters] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Upload handler – called from useDataset hook
  const uploadFile = async (file) => {
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      // Let the browser set the Content-Type (and boundary) automatically.
      const resp = await axios.post('/api/upload', form);
      const info = resp.data;
      setDatasetInfo(info);
      // Store first 1000 rows for UI
      const previewRows = info.preview || [];
      setRawData(previewRows);
      setFilteredData(previewRows);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  // Apply filters – called from useFilters hook
  const applyFilters = async (newFilters) => {
    if (!datasetInfo?.filename || !rawData.length) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await axios.post('/api/filter', {
        filters: newFilters,
        data: rawData,
      });
      const rows = resp.data.filtered_data || [];
      setFilters(newFilters);
      setFilteredData(rows.slice(0, 1000)); // cap for UI
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  // Reset all filters
  const resetFilters = async () => {
    if (!datasetInfo?.filename) return;
    await applyFilters({});
  };

  // Effect to keep filteredData in sync when raw data changes and no filters
  useEffect(() => {
    if (Object.keys(filters).length === 0 && rawData.length) {
      setFilteredData(rawData);
    }
  }, [rawData, filters]);

  return (
    <DataContext.Provider
      value={{
        datasetInfo,
        rawData,
        filteredData,
        filters,
        loading,
        error,
        uploadFile,
        applyFilters,
        resetFilters,
        setDatasetInfo,
      }}
    >
      {children}
    </DataContext.Provider>
  );
};
