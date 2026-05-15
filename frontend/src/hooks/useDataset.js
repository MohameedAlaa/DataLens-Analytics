import { useCallback } from 'react';
import { useData } from '../context/DataContext';

// Hook exposing upload and dataset state
export const useDataset = () => {
  const {
    datasetInfo,
    rawData,
    filteredData,
    loading,
    error,
    uploadFile,
    setDatasetInfo,
  } = useData();

  const handleUpload = useCallback(
    async (file) => {
      await uploadFile(file);
    },
    [uploadFile]
  );

  return {
    datasetInfo,
    rawData,
    filteredData,
    loading,
    error,
    handleUpload,
    setDatasetInfo,
  };
};
