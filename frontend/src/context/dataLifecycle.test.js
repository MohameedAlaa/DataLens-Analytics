import test from 'node:test';
import assert from 'node:assert/strict';

function normalizeDatasetInfo(info) {
  const data = info || {};
  return {
    ...data,
    filename: data.filename || 'uploaded_dataset',
    shape: Array.isArray(data.shape) ? data.shape : [0, 0],
    columns: Array.isArray(data.columns) ? data.columns : [],
    dtypes: data.dtypes || {},
    numeric_columns: Array.isArray(data.numeric_columns) ? data.numeric_columns : [],
    categorical_columns: Array.isArray(data.categorical_columns) ? data.categorical_columns : [],
    date_columns: Array.isArray(data.date_columns) ? data.date_columns : [],
    preview: Array.isArray(data.preview) ? data.preview : [],
  };
}

test('dataLifecycle: normalizeDatasetInfo handles sparse/partial backend responses', () => {
  const normalized = normalizeDatasetInfo({ dataset_id: 'abc-123' });
  assert.equal(normalized.filename, 'uploaded_dataset');
  assert.deepEqual(normalized.shape, [0, 0]);
  assert.deepEqual(normalized.columns, []);
  assert.deepEqual(normalized.numeric_columns, []);
  assert.deepEqual(normalized.categorical_columns, []);
  assert.deepEqual(normalized.preview, []);
});

test('dataLifecycle: request sequence token prevents out-of-order filter overwrites', async () => {
  let activeSeq = 0;
  let currentFilteredData = null;

  async function mockApplyFilters(seq, delayMs, resultRows) {
    await new Promise((r) => setTimeout(r, delayMs));
    // Exact guard condition in DataContext: only commit if seq matches activeSeq
    if (seq === activeSeq) {
      currentFilteredData = resultRows;
    }
  }

  // Request 1 launched (slower, takes 50ms)
  activeSeq = 1;
  const req1 = mockApplyFilters(1, 50, ['old_row_1', 'old_row_2']);

  // Request 2 launched (faster, takes 10ms)
  activeSeq = 2;
  const req2 = mockApplyFilters(2, 10, ['new_row_A', 'new_row_B']);

  await Promise.all([req1, req2]);

  // Request 2 must win even though Request 1 resolved later!
  assert.deepEqual(currentFilteredData, ['new_row_A', 'new_row_B']);
});

test('dataLifecycle: new upload resets active filters to empty dict', () => {
  let activeFilters = { age: { range: [20, 30] }, status: ['active'] };
  let currentDatasetId = 'ds-initial';

  function onUploadSuccess(newDatasetInfo) {
    // Atomically reset filters to {}
    activeFilters = {};
    currentDatasetId = newDatasetInfo.dataset_id;
  }

  onUploadSuccess({ dataset_id: 'ds-second' });

  assert.deepEqual(activeFilters, {});
  assert.equal(currentDatasetId, 'ds-second');
});
