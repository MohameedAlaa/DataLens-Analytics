import test from 'node:test';
import assert from 'node:assert/strict';

// Helper mimicking the current Filters.jsx logic
function getCurrentNumericBounds(rawData, col) {
  const vals = rawData.map((r) => Number(r[col])).filter((v) => !Number.isNaN(v));
  return vals.length ? [Math.min(...vals), Math.max(...vals)] : null;
}

function getCurrentTopValues(rawData, col) {
  const counts = {};
  rawData.forEach((row) => {
    const v = row[col];
    if (v != null) counts[v] = (counts[v] || 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15)
    .map(([k, cnt]) => ({ value: k, count: cnt }));
}

test('REPRODUCTION P1: filter controls miss values appearing after row 100 when derived only from preview', () => {
  // Construct a 120-row dataset
  const fullDataset = [];
  for (let i = 0; i < 100; i++) {
    fullDataset.push({
      id: i,
      score: 20 + (i % 30), // score in [20, 49]
      category: i % 2 === 0 ? 'Alpha' : 'Beta',
    });
  }

  // Row 105 has a new maximum (score: 100) and Row 106 has a new minimum (score: 5)
  fullDataset.push({ id: 105, score: 100, category: 'Alpha' });
  fullDataset.push({ id: 106, score: 5, category: 'Beta' });

  // Row 107 has a brand new category 'Omega'
  fullDataset.push({ id: 107, score: 35, category: 'Omega' });

  // Currently, upload returns preview = fullDataset.slice(0, 100)
  const preview = fullDataset.slice(0, 100);

  // Derive filter options using current Filters.jsx implementation:
  const numericBounds = getCurrentNumericBounds(preview, 'score');
  const categoricalOptions = getCurrentTopValues(preview, 'category');

  // Verify failure:
  // 1. Min/max bounds do NOT include 5 or 100
  assert.equal(numericBounds[0], 20, 'Current implementation reports min=20 instead of full dataset min=5');
  assert.equal(numericBounds[1], 49, 'Current implementation reports max=49 instead of full dataset max=100');

  // 2. 'Omega' is completely missing from categorical options
  const hasOmega = categoricalOptions.some((opt) => opt.value === 'Omega');
  assert.equal(hasOmega, false, 'Current implementation misses category "Omega" from row 107');
});

// Helper implementing the fixed Filters.jsx logic
function getFixedNumericBounds(datasetInfo, rawData, col) {
  const backendBounds = datasetInfo?.filter_options?.[col]?.bounds;
  if (
    Array.isArray(backendBounds) &&
    backendBounds.length === 2 &&
    backendBounds[0] !== null &&
    backendBounds[1] !== null &&
    !Number.isNaN(Number(backendBounds[0])) &&
    !Number.isNaN(Number(backendBounds[1]))
  ) {
    return [Number(backendBounds[0]), Number(backendBounds[1])];
  }
  const vals = rawData.map((r) => Number(r[col])).filter((v) => !Number.isNaN(v));
  return vals.length ? [Math.min(...vals), Math.max(...vals)] : null;
}

function getFixedTopValues(datasetInfo, rawData, filteredData, col) {
  const backendOptions = datasetInfo?.filter_options?.[col]?.top_values;
  if (Array.isArray(backendOptions) && backendOptions.length > 0) {
    return backendOptions;
  }
  const counts = {};
  const src = rawData.length ? rawData : filteredData;
  src.forEach((row) => {
    const v = row[col];
    if (v != null) counts[v] = (counts[v] || 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15)
    .map(([k, cnt]) => ({ value: k, count: cnt }));
}

test('FIX VERIFICATION P1: filter controls represent values outside first 100 rows when filter_options is provided', () => {
  const preview = [{ id: 0, score: 20, category: 'Alpha' }];
  const datasetInfo = {
    dataset_id: 'ds-test-120',
    shape: [120, 3],
    filter_options: {
      score: { bounds: [5, 100] },
      category: {
        top_values: [
          { value: 'Alpha', count: 54 },
          { value: 'Beta', count: 53 },
          { value: 'Omega', count: 1 },
        ],
      },
    },
  };

  const numericBounds = getFixedNumericBounds(datasetInfo, preview, 'score');
  const categoricalOptions = getFixedTopValues(datasetInfo, preview, preview, 'category');

  // Verify that full bounds [5, 100] are correctly represented:
  assert.deepEqual(numericBounds, [5, 100]);

  // Verify that 'Omega' is present and counts match:
  const omegaEntry = categoricalOptions.find((opt) => opt.value === 'Omega');
  assert.ok(omegaEntry, 'Category "Omega" from row 107 must be present in filter options');
  assert.equal(omegaEntry.count, 1);
});

test('FIX VERIFICATION P1: graceful fallback to rawData when filter_options is absent', () => {
  const rawData = [
    { score: 10, cat: 'A' },
    { score: 30, cat: 'B' },
  ];
  const datasetInfo = { dataset_id: 'ds-no-filter-opts' };

  const numericBounds = getFixedNumericBounds(datasetInfo, rawData, 'score');
  const categoricalOptions = getFixedTopValues(datasetInfo, rawData, rawData, 'cat');

  assert.deepEqual(numericBounds, [10, 30]);
  assert.equal(categoricalOptions.length, 2);
  assert.equal(categoricalOptions[0].value, 'A');
});
