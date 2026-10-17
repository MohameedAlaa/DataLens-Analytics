import test from 'node:test';
import assert from 'node:assert/strict';

// Helper implementing the display items resolution logic from Filters.jsx:
// - Pins selected values (preserving checked state) even when absent from current search results
// - Prioritizes search results when a search query is active
// - Falls back to precomputed top_values when no search query is active
function computeDisplayItems({
  _col,
  query,
  searchRes,
  precomputedValues = [],
  selectedValues = [],
}) {
  const isSearching = Boolean(query && query.trim());
  const activeItems = isSearching && searchRes ? (searchRes.values || []) : precomputedValues;
  const resultValSet = new Set(activeItems.map((x) => x.value));

  // Items currently selected in filters that are not in the active item list
  const pinnedItems = selectedValues
    .filter((v) => !resultValSet.has(v))
    .map((v) => ({ value: v, count: null, isPinned: true }));

  return [...pinnedItems, ...activeItems];
}

// Helper simulating debounced search with sequence token for out-of-order race protection
class CategorySearchSimulator {
  constructor(apiFn, debounceMs = 300) {
    this.apiFn = apiFn;
    this.debounceMs = debounceMs;
    this.currentSeq = 0;
    this.timers = {};
    this.controllers = {};
    this.results = {};
    this.errors = {};
    this.loading = {};
    this.callHistory = [];
  }

  handleSearch(col, text) {
    if (this.timers[col]) {
      clearTimeout(this.timers[col]);
    }

    const trimmed = text.trim();
    if (!trimmed) {
      if (this.controllers[col]) {
        this.controllers[col].aborted = true;
      }
      delete this.results[col];
      this.errors[col] = null;
      this.loading[col] = false;
      return;
    }

    this.loading[col] = true;
    this.errors[col] = null;

    return new Promise((resolve) => {
      this.timers[col] = setTimeout(async () => {
        if (this.controllers[col]) {
          this.controllers[col].aborted = true;
        }
        const controller = { aborted: false };
        this.controllers[col] = controller;

        const seq = ++this.currentSeq;
        this.callHistory.push({ col, query: trimmed, seq });

        try {
          const data = await this.apiFn(col, trimmed, controller);
          if (seq === this.currentSeq && !controller.aborted) {
            this.results[col] = data;
            this.errors[col] = null;
          }
        } catch (err) {
          if (!controller.aborted && seq === this.currentSeq) {
            this.errors[col] = err.message || 'Failed to search categories';
          }
        } finally {
          if (seq === this.currentSeq && !controller.aborted) {
            this.loading[col] = false;
          }
          resolve();
        }
      }, this.debounceMs);
    });
  }
}

test('categorySearch: selection pinning maintains active selections absent from search results', () => {
  const precomputed = [
    { value: 'Apple', count: 100 },
    { value: 'Banana', count: 50 },
  ];
  // User selected 'Pineapple' (which is outside the search result for 'ber')
  const selectedValues = ['Pineapple', 'Strawberry'];

  // User searches for 'ber'
  const searchRes = {
    column: 'fruit',
    query: 'ber',
    total_matches: 2,
    truncated: false,
    values: [
      { value: 'Blueberry', count: 30 },
      { value: 'Raspberry', count: 20 },
    ],
  };

  const displayItems = computeDisplayItems({
    col: 'fruit',
    query: 'ber',
    searchRes,
    precomputedValues: precomputed,
    selectedValues,
  });

  // Verify Pineapple and Strawberry are pinned at the top as active items
  assert.equal(displayItems.length, 4);
  assert.equal(displayItems[0].value, 'Pineapple');
  assert.equal(displayItems[0].isPinned, true);
  assert.equal(displayItems[1].value, 'Strawberry');
  assert.equal(displayItems[1].isPinned, true);

  // Search results follow
  assert.equal(displayItems[2].value, 'Blueberry');
  assert.equal(displayItems[3].value, 'Raspberry');
});

test('categorySearch: when search query is cleared, falls back to precomputed top values', () => {
  const precomputed = [
    { value: 'CatA', count: 10 },
    { value: 'CatB', count: 8 },
  ];
  const selectedValues = ['CatA'];

  const displayItems = computeDisplayItems({
    col: 'category',
    query: '',
    searchRes: null,
    precomputedValues: precomputed,
    selectedValues,
  });

  assert.equal(displayItems.length, 2);
  assert.equal(displayItems[0].value, 'CatA');
  assert.equal(displayItems[1].value, 'CatB');
});

test('categorySearch: debounced search fires after delay and cancels rapid preceding strokes', async () => {
  let apiCallCount = 0;
  const mockApi = async (col, q) => {
    apiCallCount++;
    return {
      column: col,
      query: q,
      total_matches: 1,
      truncated: false,
      values: [{ value: `Result_${q}`, count: 5 }],
    };
  };

  const sim = new CategorySearchSimulator(mockApi, 50);

  // Type quickly: "a", "ab", "abc"
  sim.handleSearch('col1', 'a');
  sim.handleSearch('col1', 'ab');
  await sim.handleSearch('col1', 'abc');

  // Only the final debounced call should execute
  assert.equal(apiCallCount, 1);
  assert.equal(sim.callHistory.length, 1);
  assert.equal(sim.callHistory[0].query, 'abc');
  assert.equal(sim.results['col1'].query, 'abc');
  assert.equal(sim.loading['col1'], false);
});

test('categorySearch: sequence token rejects stale out-of-order API responses', async () => {
  // Simulate slow response for earlier query and fast response for later query
  const mockApi = async (col, q) => {
    if (q === 'slow') {
      await new Promise((r) => setTimeout(r, 60));
      return { column: col, query: 'slow', values: [{ value: 'SLOW_RES', count: 1 }] };
    }
    // fast
    return { column: col, query: 'fast', values: [{ value: 'FAST_RES', count: 10 }] };
  };

  const sim = new CategorySearchSimulator(mockApi, 10);

  // Trigger 'slow' search
  const pSlow = sim.handleSearch('colA', 'slow');
  // 15ms later, user types 'fast'
  await new Promise((r) => setTimeout(r, 15));
  const pFast = sim.handleSearch('colA', 'fast');

  await Promise.all([pSlow, pFast]);

  // The latest result must be 'FAST_RES', NOT overwritten by the slow response
  assert.equal(sim.results['colA'].query, 'fast');
  assert.equal(sim.results['colA'].values[0].value, 'FAST_RES');
});

test('categorySearch: handles error state and loading lifecycle', async () => {
  const mockFailingApi = async () => {
    throw new Error('Network timeout during category search');
  };

  const sim = new CategorySearchSimulator(mockFailingApi, 10);
  await sim.handleSearch('colErr', 'broken');

  assert.equal(sim.loading['colErr'], false);
  assert.equal(sim.errors['colErr'], 'Network timeout during category search');
  assert.equal(sim.results['colErr'], undefined);
});
