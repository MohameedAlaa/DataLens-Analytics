import { useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';
import { useData } from '../context/DataContext';
import { apiClient, extractErrorMessage } from '../utils/apiClient';

// Hook to handle chat messages with the backend LLM endpoint
export const useChat = () => {
  const { datasetInfo, filters } = useData();
  const [messages, setMessages] = useState([]); // {role: 'user'|'assistant', content: string, citations?: [], analytics?: {}, mode?: string, timestamp: Date}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const messagesRef = useRef(messages);
  const loadingRef = useRef(loading);
  const abortControllerRef = useRef(null);
  const currentDatasetIdRef = useRef(datasetInfo?.dataset_id);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);

  // Clean isolation: When dataset changes or is cleared, abort pending chat & reset conversation
  useEffect(() => {
    const prevDatasetId = currentDatasetIdRef.current;
    const nextDatasetId = datasetInfo?.dataset_id;

    if (prevDatasetId !== nextDatasetId) {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      currentDatasetIdRef.current = nextDatasetId;
      setMessages([]);
      setError(null);
      setLoading(false);
    }
  }, [datasetInfo?.dataset_id]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const sendMessage = useCallback(
    async (question) => {
      const trimmedQuestion = question?.trim();
      if (!trimmedQuestion) return;

      // Duplicate submission protection
      if (loadingRef.current) return;

      if (!datasetInfo?.dataset_id) {
        setError('No dataset loaded. Please upload a dataset first.');
        return;
      }

      // Abort any previous pending request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      const requestDatasetId = datasetInfo.dataset_id;

      const userMsg = {
        role: 'user',
        content: trimmedQuestion,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);

      try {
        // Send up to the last 10 messages for bounded prompt context
        const history = messagesRef.current
          .slice(-10)
          .map((m) => ({ role: m.role, content: m.content }));

        const resp = await apiClient.post(
          '/chat',
          {
            question: trimmedQuestion,
            dataset_id: requestDatasetId,
            history,
            filters: filters || {},
          },
          { signal: abortController.signal }
        );

        // Discard response if dataset switched while request was in-flight
        if (currentDatasetIdRef.current !== requestDatasetId) {
          return;
        }

        const data = resp.data || {};
        const assistantMsg = {
          role: 'assistant',
          content: data.answer || 'No response returned from assistant.',
          citations: Array.isArray(data.citations) ? data.citations : [],
          analytics: data.analytics || null,
          mode: data.mode || (data.analytics ? 'analytics' : 'rag'),
          dataset_id: data.dataset_id || requestDatasetId,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (e) {
        if (axios.isCancel(e) || e.name === 'CanceledError' || e.name === 'AbortError') {
          // Request was cancelled intentionally (reset or dataset switch)
          return;
        }
        if (currentDatasetIdRef.current === requestDatasetId) {
          setError(extractErrorMessage(e, 'Failed to send message'));
        }
      } finally {
        if (currentDatasetIdRef.current === requestDatasetId) {
          setLoading(false);
        }
      }
    },
    [datasetInfo, filters]
  );

  const resetChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setMessages([]);
    setError(null);
    setLoading(false);
  }, []);

  return { messages, sendMessage, resetChat, loading, error };
};
