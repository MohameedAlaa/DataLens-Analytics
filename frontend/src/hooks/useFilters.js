import { useCallback } from 'react';
import { useData } from '../context/DataContext';

// Hook for managing filters UI and applying them via the backend
export const useFilters = () => {
  const { filters, applyFilters, resetFilters, loading, error } = useData();

  const setFilter = useCallback(
    (columnOrPayload, condition) => {
      const newFilters =
        typeof columnOrPayload === 'object' && columnOrPayload !== null && !Array.isArray(columnOrPayload)
          ? columnOrPayload
          : { ...filters, [columnOrPayload]: condition };
      applyFilters(newFilters);
    },
    [filters, applyFilters]
  );

  const clearFilter = useCallback(
    (column) => {
      const { [column]: _, ...rest } = filters;
      applyFilters(rest);
    },
    [filters, applyFilters]
  );

  return { filters, setFilter, clearFilter, resetFilters, loading, error, applyFilters };
};
