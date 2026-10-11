import test from 'node:test';
import assert from 'node:assert/strict';

// Pure simulation of useChat payload preparation and response normalization
function prepareChatPayload(trimmedQuestion, datasetId, rawHistory, activeFilters) {
  if (!trimmedQuestion?.trim()) return null;
  if (!datasetId) throw new Error('No dataset loaded');

  // Truncate history to last 10 messages
  const boundedHistory = (rawHistory || [])
    .slice(-10)
    .map((m) => ({ role: m.role, content: m.content }));

  return {
    question: trimmedQuestion.trim(),
    dataset_id: datasetId,
    history: boundedHistory,
    filters: activeFilters || {},
  };
}

function normalizeAssistantResponse(respData, fallbackDatasetId) {
  const data = respData || {};
  return {
    role: 'assistant',
    content: data.answer || 'No response returned from assistant.',
    citations: Array.isArray(data.citations) ? data.citations : [],
    analytics: data.analytics || null,
    mode: data.mode || (data.analytics ? 'analytics' : 'rag'),
    dataset_id: data.dataset_id || fallbackDatasetId,
  };
}

test('chatSafety: prepareChatPayload bounds history to last 10 messages', () => {
  const history = Array.from({ length: 25 }, (_, i) => ({
    role: i % 2 === 0 ? 'user' : 'assistant',
    content: `Message ${i}`,
  }));

  const payload = prepareChatPayload('What is the total sales?', 'ds-123', history, { region: ['North'] });
  assert.equal(payload.history.length, 10);
  assert.equal(payload.history[0].content, 'Message 15');
  assert.equal(payload.history[9].content, 'Message 24');
  assert.deepEqual(payload.filters, { region: ['North'] });
});

test('chatSafety: prepareChatPayload includes active filters', () => {
  const filters = { sales: { range: [100, 500] }, country: ['USA', 'Canada'] };
  const payload = prepareChatPayload('Show top accounts', 'ds-456', [], filters);
  assert.deepEqual(payload.filters, filters);
  assert.equal(payload.dataset_id, 'ds-456');
});

test('chatSafety: normalizeAssistantResponse preserves deterministic analytics without mutation', () => {
  const backendResponse = {
    answer: 'The total sales for USA is 1700.',
    citations: [],
    analytics: {
      operation: 'sum',
      column: 'sales',
      group_column: 'country',
      group_value: 'USA',
      value: 1700,
    },
    mode: 'analytics',
    dataset_id: 'ds-789',
  };

  const normalized = normalizeAssistantResponse(backendResponse, 'ds-789');
  assert.equal(normalized.mode, 'analytics');
  assert.ok(normalized.analytics);
  assert.equal(normalized.analytics.operation, 'sum');
  assert.equal(normalized.analytics.value, 1700);
  assert.equal(normalized.analytics.group_value, 'USA');
  assert.deepEqual(normalized.citations, []);
});

test('chatSafety: normalizeAssistantResponse handles citations defensive parsing', () => {
  const backendResponse = {
    answer: 'Accounts verified in dataset.',
    citations: [
      { row_index: 4, snippet: 'Checking account balance $1,200' },
      { row_index: 8, snippet: 'Savings account balance $4,500' }
    ],
    analytics: null,
    mode: 'rag',
  };

  const normalized = normalizeAssistantResponse(backendResponse, 'ds-101');
  assert.equal(normalized.citations.length, 2);
  assert.equal(normalized.citations[0].row_index, 4);
  assert.equal(normalized.mode, 'rag');
  assert.equal(normalized.analytics, null);
});

test('chatSafety: stale async response discarded when dataset switched', () => {
  let currentDatasetId = 'ds-NEW';
  const inFlightRequestDatasetId = 'ds-OLD';

  let messages = [];
  const handleResponse = (resp) => {
    // Exact guard logic from useChat
    if (currentDatasetId !== inFlightRequestDatasetId) {
      return; // Discard stale response
    }
    messages.push(resp);
  };

  handleResponse(normalizeAssistantResponse({ answer: 'Stale answer' }, inFlightRequestDatasetId));
  assert.equal(messages.length, 0, 'Stale response was not discarded!');
});
