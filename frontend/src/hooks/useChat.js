import { useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';
import { useData } from '../context/DataContext';

// Hook to handle chat messages with the backend LLM endpoint
export const useChat = () => {
  const { datasetInfo } = useData();
  const [messages, setMessages] = useState([]); // {role: 'user'|'assistant', content: string, timestamp: Date}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesRef = useRef(messages);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const sendMessage = useCallback(
    async (question) => {
      const trimmedQuestion = question?.trim();
      if (!trimmedQuestion) return;
      if (!datasetInfo?.filename) {
        setError('No dataset loaded.');
        return;
      }

      const userMsg = { role: 'user', content: trimmedQuestion, timestamp: new Date() };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);

      try {
        const history = messagesRef.current.map((m) => ({ role: m.role, content: m.content }));
        const resp = await axios.post('/api/chat', {
          question: trimmedQuestion,
          filename: datasetInfo.filename,
          history,
        });
        const assistantMsg = {
          role: 'assistant',
          content: resp.data.answer,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (e) {
        setError(e.response?.data?.detail || e.message || 'Failed to send message');
      } finally {
        setLoading(false);
      }
    },
    [datasetInfo]
  );

  const resetChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sendMessage, resetChat, loading, error };
};
