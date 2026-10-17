import test, { describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { preview } from 'vite';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, '..');

// ── Deterministic Test Fixtures ─────────────────────────────────────────────
const MOCK_DATASET_PAYLOAD = {
  dataset_id: 'e2e-sales-dataset-001',
  filename: 'sample_sales_analytics.csv',
  shape: [4, 5],
  columns: ['country', 'product', 'sales', 'customers', 'date'],
  preview: [
    { country: 'USA', product: 'Laptop', sales: 1200, customers: 10, date: '2026-01-01' },
    { country: 'USA', product: 'Phone', sales: 800, customers: 8, date: '2026-01-02' },
    { country: 'Egypt', product: 'Laptop', sales: 900, customers: 7, date: '2026-01-03' },
    { country: 'Egypt', product: 'Phone', sales: 600, customers: 6, date: '2026-01-04' },
  ],
  summary: {
    total_rows: 4,
    total_columns: 5,
    missing_cells: 0,
    missing_percentage: 0.0,
    memory_usage_mb: 0.001,
    columns: [
      { name: 'country', dtype: 'string', missing: 0, unique: 2 },
      { name: 'product', dtype: 'string', missing: 0, unique: 2 },
      { name: 'sales', dtype: 'integer', missing: 0, unique: 4, mean: 875, min: 600, max: 1200 },
      { name: 'customers', dtype: 'integer', missing: 0, unique: 4, mean: 7.75, min: 6, max: 10 },
      { name: 'date', dtype: 'datetime', missing: 0, unique: 4 },
    ],
  },
  insights: [
    {
      title: 'Dataset Ingestion Health',
      description: '4 clean records ingested with zero null values across 5 attributes.',
      confidence: 1.0,
      type: 'overview',
    },
  ],
  health_score: 100,
  quality_grade: 'A',
  filter_options: {
    country: ['USA', 'Egypt'],
    product: ['Laptop', 'Phone'],
  },
};

describe('TEST-01: End-to-End Browser Verification Suite', { timeout: 60000 }, () => {
  let previewServer;
  let baseUrl;
  let browser;

  before(async () => {
    // 1. Verify that production build directory exists
    const distPath = path.join(FRONTEND_DIR, 'dist');
    assert.ok(
      fs.existsSync(distPath),
      `Production build directory not found at ${distPath}. Run 'npm run build' before executing E2E tests.`
    );

    // 2. Start Vite production preview server programmatically
    previewServer = await preview({
      root: FRONTEND_DIR,
      preview: {
        port: Number(process.env.E2E_PORT) || 4199,
        strictPort: false,
      },
    });

    baseUrl = previewServer.resolvedUrls.local[0];
    console.log(`[E2E] Vite production preview listening at: ${baseUrl}`);

    // 3. Launch headless browser
    const launchOptions = { headless: true };
    if (process.env.PLAYWRIGHT_CHANNEL) {
      launchOptions.channel = process.env.PLAYWRIGHT_CHANNEL;
    }

    browser = await chromium.launch(launchOptions);
    console.log(`[E2E] Headless Chromium launched successfully (version: ${browser.version()})`);
  });

  after(async () => {
    if (browser) {
      await browser.close();
      console.log('[E2E] Browser closed cleanly.');
    }
    if (previewServer) {
      await previewServer.close();
      console.log('[E2E] Vite preview server closed cleanly.');
    }
  });

  test('Scenario A: Application loads successfully with expected title, brand logo, and hero elements', async () => {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const uncaughtErrors = [];

    page.on('pageerror', (err) => uncaughtErrors.push(err.message));

    try {
      await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 15000 });

      // Verify page title
      const title = await page.title();
      assert.match(title, /DataLens Analytics/, `Expected page title to mention DataLens Analytics, got "${title}"`);

      // Verify Brand Logo in Navbar
      const logo = page.locator('text=DataLens').first();
      await logo.waitFor({ state: 'visible', timeout: 5000 });
      assert.ok(await logo.isVisible(), 'DataLens logo must be visible in navbar');

      // Verify Main Value Proposition Headline
      const heroHeading = page.locator('h1').first();
      await heroHeading.waitFor({ state: 'visible', timeout: 5000 });
      const headingText = await heroHeading.textContent();
      assert.match(headingText, /Actionable Intelligence/, 'Hero heading must render value proposition');

      // Verify Upload Dropzone interactive button
      const dropzone = page.locator('div[role="button"][aria-label="Upload dataset dropzone"]').first();
      await dropzone.waitFor({ state: 'visible', timeout: 5000 });
      assert.ok(await dropzone.isVisible(), 'Upload dropzone must be present and visible');

      // Verify Curated Sample Datasets are displayed
      const sampleBtn = page.locator('text=Global Sales & Operations').first();
      await sampleBtn.waitFor({ state: 'visible', timeout: 5000 });
      assert.ok(await sampleBtn.isVisible(), 'Curated sample dataset button must be visible');

      // Assert zero uncaught JavaScript errors during startup
      assert.equal(
        uncaughtErrors.length,
        0,
        `Uncaught runtime exceptions detected on page load: ${uncaughtErrors.join('; ')}`
      );
    } finally {
      await context.close();
    }
  });

  test('Scenario B: Dataset ingestion transitions workspace to active dashboard and displays dataset metrics', async () => {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const uncaughtErrors = [];

    page.on('pageerror', (err) => uncaughtErrors.push(err.message));

    // Intercept upload request with deterministic mock contract
    await page.route('**/api/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_DATASET_PAYLOAD),
      });
    });

    try {
      await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 15000 });

      // Click the curated sample dataset button to trigger ingestion
      const sampleBtn = page.locator('text=Global Sales & Operations').first();
      await sampleBtn.waitFor({ state: 'visible', timeout: 5000 });
      await sampleBtn.click();

      // Verify that the active dataset pill appears in the top navigation bar
      const datasetPill = page.locator('text=sample_sales_analytics.csv').first();
      await datasetPill.waitFor({ state: 'visible', timeout: 8000 });
      assert.ok(await datasetPill.isVisible(), 'Dataset pill must display active filename in navbar');

      // Verify shape badge displays row and column totals
      const shapeBadge = page.locator('text=4 rows • 5 cols').first();
      await shapeBadge.waitFor({ state: 'visible', timeout: 5000 });
      assert.ok(await shapeBadge.isVisible(), 'Shape badge must display 4 rows • 5 cols');

      // Verify workspace transitioned from hero to analytics dashboard
      const tableRows = page.locator('text=USA').first();
      await tableRows.waitFor({ state: 'visible', timeout: 8000 });
      assert.ok(await tableRows.isVisible(), 'Data table must render records from ingested dataset');

      assert.equal(
        uncaughtErrors.length,
        0,
        `Uncaught runtime exceptions during dataset ingestion: ${uncaughtErrors.join('; ')}`
      );
    } finally {
      await context.close();
    }
  });

  test('Scenario C: Table search and row controls dynamically update displayed records and count', async () => {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    await page.route('**/api/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_DATASET_PAYLOAD),
      });
    });

    try {
      await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 15000 });

      // Ingest sample dataset
      await page.locator('text=Global Sales & Operations').first().click();
      await page.locator('text=sample_sales_analytics.csv').first().waitFor({ state: 'visible', timeout: 8000 });

      // Locate table search input in AdvancedDataTable
      const searchInput = page.locator('input[placeholder="Search table rows..."]').first();
      await searchInput.waitFor({ state: 'visible', timeout: 5000 });

      // Type "Egypt" to filter records
      await searchInput.fill('Egypt');

      // Assert row count updates to "2 rows"
      const rowCountSpan = page.locator('text=2 rows').first();
      await rowCountSpan.waitFor({ state: 'visible', timeout: 5000 });
      assert.ok(await rowCountSpan.isVisible(), 'Row counter must update to 2 rows when filtered by Egypt');

      // Verify Egypt rows are displayed
      const egyptCell = page.locator('td:has-text("Egypt"), div:has-text("Egypt")').first();
      assert.ok(await egyptCell.isVisible(), 'Filtered results must show Egypt rows');

      // Clear search and verify restoration to 4 rows
      await searchInput.fill('');
      const fullCountSpan = page.locator('text=4 rows').first();
      await fullCountSpan.waitFor({ state: 'visible', timeout: 5000 });
      assert.ok(await fullCountSpan.isVisible(), 'Row counter must restore to 4 rows after clearing search');

      // Verify Rows Per Page selector is accessible and functional
      const pageSizeSelect = page.locator('select[aria-label="Rows per page"]').first();
      await pageSizeSelect.waitFor({ state: 'visible', timeout: 5000 });
      await pageSizeSelect.selectOption('25');
      assert.equal(await pageSizeSelect.inputValue(), '25', 'Page size selector must update value to 25');
    } finally {
      await context.close();
    }
  });

  test('Scenario D: Keyboard navigation highlights interactive controls with visible focus indicators', async () => {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    try {
      await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 15000 });

      // Ensure main interactive dropzone element is loaded and visible
      const dropzone = page.locator('div[role="button"][aria-label="Upload dataset dropzone"]').first();
      await dropzone.waitFor({ state: 'visible', timeout: 5000 });

      // Exercise real keyboard navigation via Tab key (avoiding programmatic locator.focus())
      // Sequentially Tab through the document until the upload dropzone receives focus
      const MAX_TABS = 15;
      let tabsCount = 0;
      let dropzoneFocused = false;

      while (tabsCount < MAX_TABS) {
        await page.keyboard.press('Tab');
        tabsCount += 1;

        const isDropzone = await page.evaluate(() => {
          return document.activeElement?.getAttribute('aria-label') === 'Upload dataset dropzone';
        });

        if (isDropzone) {
          dropzoneFocused = true;
          break;
        }
      }

      assert.ok(
        dropzoneFocused,
        `Expected upload dropzone to receive focus via Tab navigation within ${MAX_TABS} presses (took ${tabsCount} tabs)`
      );

      // Verify that the dropzone is activeElement, matches :focus-visible, and has a visible computed focus indicator
      const focusState = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el) return null;

        const isFocusVisible = el.matches(':focus-visible');
        const comp = window.getComputedStyle(el);
        const outlineWidth = parseFloat(comp.outlineWidth) || 0;
        const outlineStyle = comp.outlineStyle;
        const outlineColor = comp.outlineColor;
        const boxShadow = comp.boxShadow;

        const hasVisibleOutline = outlineWidth > 0 && outlineStyle !== 'none' && outlineColor !== 'transparent' && outlineColor !== 'rgba(0, 0, 0, 0)';
        const hasVisibleRing = Boolean(boxShadow && boxShadow !== 'none' && !boxShadow.includes('0px 0px 0px 0px'));

        return {
          tagName: el.tagName.toLowerCase(),
          role: el.getAttribute('role'),
          ariaLabel: el.getAttribute('aria-label'),
          isFocusVisible,
          outlineWidth,
          outlineStyle,
          outlineColor,
          boxShadow,
          hasVisibleFocusIndicator: hasVisibleOutline || hasVisibleRing,
        };
      });

      assert.ok(focusState, 'An active element must be present in the document');
      assert.equal(
        focusState.ariaLabel,
        'Upload dataset dropzone',
        'Upload dropzone must be document.activeElement'
      );
      assert.equal(
        focusState.isFocusVisible,
        true,
        'Upload dropzone must match :focus-visible pseudo-class after keyboard Tab navigation'
      );
      assert.ok(
        focusState.hasVisibleFocusIndicator,
        `Dropzone must display a visible focus indicator (computed outline: ${focusState.outlineWidth}px ${focusState.outlineStyle} ${focusState.outlineColor}, boxShadow: ${focusState.boxShadow})`
      );

      // Verify that focus-visible ring styles class is applied on the element
      const classList = await dropzone.getAttribute('class');
      assert.match(
        classList,
        /focus-visible:ring-brand-400/,
        'Dropzone must have focus-visible:ring-brand-400 styling applied'
      );

      // Verify bidirectional keyboard navigation: Shift+Tab moves focus back to previous element and Tab returns
      await page.keyboard.press('Shift+Tab');
      const prevActiveAriaLabel = await page.evaluate(() => document.activeElement?.getAttribute('aria-label') || document.activeElement?.tagName.toLowerCase());
      assert.notEqual(
        prevActiveAriaLabel,
        'Upload dataset dropzone',
        'Shift+Tab must move focus backwards away from the dropzone'
      );

      await page.keyboard.press('Tab');
      const returnedToDropzone = await page.evaluate(
        () => document.activeElement?.getAttribute('aria-label') === 'Upload dataset dropzone'
      );
      assert.ok(
        returnedToDropzone,
        'Pressing Tab must return focus back to the upload dropzone'
      );
    } finally {
      await context.close();
    }
  });

  test('Scenario E: API rejection presents a clean, non-disruptive user-visible error banner', async () => {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const uncaughtErrors = [];

    page.on('pageerror', (err) => uncaughtErrors.push(err.message));

    // Mock API rejection (e.g. empty file or invalid schema)
    await page.route('**/api/upload', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Upload rejected: Dataset contains 0 data rows',
        }),
      });
    });

    try {
      await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 15000 });

      // Attempt upload via sample button
      const sampleBtn = page.locator('text=Global Sales & Operations').first();
      await sampleBtn.waitFor({ state: 'visible', timeout: 5000 });
      await sampleBtn.click();

      // Verify Error Feedback Banner is displayed
      const errorBanner = page.locator('text=Upload Encountered An Issue').first();
      await errorBanner.waitFor({ state: 'visible', timeout: 8000 });
      assert.ok(await errorBanner.isVisible(), 'Error banner title must be visible');

      // Verify exact error message string is rendered
      const errorDetails = page.locator('text=Upload rejected: Dataset contains 0 data rows').first();
      await errorDetails.waitFor({ state: 'visible', timeout: 5000 });
      assert.ok(await errorDetails.isVisible(), 'Error detail string must be displayed to user');

      // Assert no unhandled React rendering crash or uncaught exceptions occurred
      assert.equal(
        uncaughtErrors.length,
        0,
        `Unexpected runtime error during error handling: ${uncaughtErrors.join('; ')}`
      );
    } finally {
      await context.close();
    }
  });
});
