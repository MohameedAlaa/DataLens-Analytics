import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';

const PROD_URL = 'https://data-lens-analytics.vercel.app/';
const FIXTURES_DIR = path.resolve('../test_fixtures');
const SALES_CSV = path.join(FIXTURES_DIR, 'uat_sales.csv');
const SECOND_CSV = path.join(FIXTURES_DIR, 'uat_second.csv');
const EMPTY_CSV = path.join(FIXTURES_DIR, 'uat_empty.csv');
const HEADERS_ONLY_CSV = path.join(FIXTURES_DIR, 'uat_headers_only.csv');
const UNSUPPORTED_TXT = path.join(FIXTURES_DIR, 'uat_unsupported.txt');
const SCREENSHOT_DIR = path.resolve('C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runUAT() {
  console.log('================================================================');
  console.log('DATALENS ANALYTICS — PRODUCTION END-TO-END UAT');
  console.log(`Target URL: ${PROD_URL}`);
  console.log('================================================================');

  const report = {
    test1_initialLoad: {},
    test2_responsive: {},
    test3_upload: {},
    test4_analytics: {},
    test5_filtering: {},
    test6_aiCopilot: {},
    test7_rag: {},
    test8_isolation: {},
    test9_invalidInput: {},
    test10_connectivity: {},
    test12_performance: {},
    test13_security: {},
  };

  const consoleLogs = [];
  const networkRequests = [];
  const networkFailures = [];

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  page.on('console', msg => {
    const entry = { type: msg.type(), text: msg.text() };
    consoleLogs.push(entry);
    if (msg.type() === 'error' || msg.type() === 'warn') {
      console.log(`[Browser ${msg.type().toUpperCase()}]: ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    console.log(`[Page Error]: ${err.message}`);
    consoleLogs.push({ type: 'pageerror', text: err.message, stack: err.stack });
  });

  page.on('request', req => {
    networkRequests.push({
      url: req.url(),
      method: req.method(),
      resourceType: req.resourceType(),
    });
  });

  page.on('requestfailed', req => {
    networkFailures.push({
      url: req.url(),
      method: req.method(),
      failure: req.failure() ? req.failure().errorText : 'unknown',
    });
    console.log(`[Request Failed]: ${req.method()} ${req.url()}`);
  });

  page.on('response', res => {
    if (res.url().includes('/api/') || res.url().includes('/upload') || res.url().includes('/chat') || res.url().includes('/health') || res.url().includes('onrender')) {
      console.log(`[API Response]: ${res.status()} ${res.url()} (content-type: ${res.headers()['content-type'] || 'n/a'})`);
    }
  });

  // -------------------------------------------------------------
  // TEST 1: Initial Load
  // -------------------------------------------------------------
  console.log('\n--- TEST 1: Initial Load ---');
  const t0 = Date.now();
  const navResponse = await page.goto(PROD_URL, { waitUntil: 'networkidle', timeout: 30000 });
  const tNav = Date.now() - t0;
  console.log(`Navigation status: ${navResponse ? navResponse.status() : 'null'} in ${tNav}ms`);

  const title = await page.title();
  console.log(`Page title: "${title}"`);

  // Check for root rendering
  const rootHtml = await page.locator('#root').innerHTML();
  const isBlank = !rootHtml || rootHtml.trim().length === 0;
  console.log(`Root has content: ${!isBlank} (length: ${rootHtml ? rootHtml.length : 0})`);

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'uat_01_initial_load.png'), fullPage: true });

  report.test1_initialLoad = {
    status: navResponse ? navResponse.status() : null,
    navigationTimeMs: tNav,
    title,
    isBlank,
    consoleErrors: consoleLogs.filter(l => l.type === 'error' || l.type === 'pageerror'),
    consoleWarnings: consoleLogs.filter(l => l.type === 'warn'),
  };

  // -------------------------------------------------------------
  // TEST 2: Responsive UI
  // -------------------------------------------------------------
  console.log('\n--- TEST 2: Responsive UI ---');
  const viewports = [
    { name: 'desktop_1440', width: 1440, height: 900 },
    { name: 'tablet_768', width: 768, height: 1024 },
    { name: 'mobile_390', width: 390, height: 844 },
    { name: 'mobile_360', width: 360, height: 800 },
  ];

  for (const vp of viewports) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.waitForTimeout(500);
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    const hasHorizontalOverflow = scrollWidth > clientWidth;
    console.log(`Viewport ${vp.name} (${vp.width}x${vp.height}): client=${clientWidth}, scroll=${scrollWidth}, overflow=${hasHorizontalOverflow}`);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `uat_02_responsive_${vp.name}.png`) });
    report.test2_responsive[vp.name] = { hasHorizontalOverflow, scrollWidth, clientWidth };
  }

  // Restore 1440x900
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(500);

  // -------------------------------------------------------------
  // TEST 3: Upload Real Dataset
  // -------------------------------------------------------------
  console.log('\n--- TEST 3: Upload Real Dataset ---');
  console.log(`Uploading ${SALES_CSV}...`);
  const fileInput = page.locator('input[type="file"]').first();

  let uploadResponseReceived = null;
  const uploadPromise = page.waitForResponse(res => res.url().includes('/upload'), { timeout: 15000 }).catch(e => {
    console.log(`waitForResponse(/upload) timed out or failed: ${e.message}`);
    return null;
  });

  const tUploadStart = Date.now();
  await fileInput.setInputFiles(SALES_CSV);
  uploadResponseReceived = await uploadPromise;
  const tUploadDuration = Date.now() - tUploadStart;

  let uploadStatus = null;
  let uploadUrl = null;
  let uploadContentType = null;
  let uploadBodySnippet = null;

  if (uploadResponseReceived) {
    uploadStatus = uploadResponseReceived.status();
    uploadUrl = uploadResponseReceived.url();
    uploadContentType = uploadResponseReceived.headers()['content-type'];
    try {
      const text = await uploadResponseReceived.text();
      uploadBodySnippet = text.slice(0, 300);
    } catch {}
    console.log(`Upload Response URL: ${uploadUrl}`);
    console.log(`Upload Status: ${uploadStatus}`);
    console.log(`Upload Content-Type: ${uploadContentType}`);
    console.log(`Upload Body Snippet: ${uploadBodySnippet}`);
  }

  // Wait 3 seconds to see UI reaction (toasts, error alerts, dataset pills, dashboard)
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'uat_03_upload_result.png') });

  // Check visible error messages or toasts
  const toastText = await page.locator('[role="status"], [role="alert"], .toast, .text-red-500, .bg-red-500, .border-red-500').allTextContents().catch(() => []);
  console.log(`Visible alerts/toasts:`, toastText);

  // Check dataset pill or active dataset indicator
  const datasetPill = await page.locator('text=uat_sales.csv').count();
  console.log(`Dataset pill count for "uat_sales.csv": ${datasetPill}`);

  report.test3_upload = {
    durationMs: tUploadDuration,
    uploadStatus,
    uploadUrl,
    uploadContentType,
    uploadBodySnippet,
    datasetPillFound: datasetPill > 0,
    alerts: toastText,
  };

  // -------------------------------------------------------------
  // TEST 4 & 5: Deterministic Analytics & Filtering
  // -------------------------------------------------------------
  console.log('\n--- TEST 4 & 5: Analytics & Filtering ---');
  // Check if dashboard panels (charts, summary cards) are rendered
  const statCards = await page.locator('.stat-card, [data-testid="stat-card"], .grid .bg-navy-light').allTextContents().catch(() => []);
  console.log(`Dashboard cards found (${statCards.length}):`, statCards.slice(0, 5));

  report.test4_analytics = {
    statCardsFound: statCards.length,
    statCardsSnippet: statCards.slice(0, 5),
  };

  // -------------------------------------------------------------
  // TEST 6 & 7: AI Copilot & RAG
  // -------------------------------------------------------------
  console.log('\n--- TEST 6 & 7: AI Copilot & RAG ---');
  const chatInput = page.locator('input[aria-label="Ask AI Copilot about dataset"], input[placeholder*="Ask"], input[placeholder*="Copilot"]').first();
  const chatExists = await chatInput.count() > 0;
  console.log(`Chat input exists: ${chatExists}`);

  if (chatExists) {
    const isChatDisabled = await chatInput.isDisabled();
    console.log(`Chat input disabled: ${isChatDisabled}`);
    report.test6_aiCopilot = { chatExists, isChatDisabled };
  } else {
    report.test6_aiCopilot = { chatExists: false };
  }

  // -------------------------------------------------------------
  // TEST 9: Invalid Input Testing
  // -------------------------------------------------------------
  console.log('\n--- TEST 9: Invalid Input Testing ---');
  console.log(`Uploading empty CSV (${EMPTY_CSV})...`);
  await fileInput.setInputFiles(EMPTY_CSV);
  await page.waitForTimeout(2000);
  const emptyAlerts = await page.locator('[role="status"], [role="alert"], .text-red-500, .bg-red-500').allTextContents().catch(() => []);
  console.log(`Empty CSV alerts:`, emptyAlerts);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'uat_09_empty_csv.png') });

  console.log(`Uploading unsupported file (${UNSUPPORTED_TXT})...`);
  await fileInput.setInputFiles(UNSUPPORTED_TXT);
  await page.waitForTimeout(2000);
  const unsupportedAlerts = await page.locator('[role="status"], [role="alert"], .text-red-500, .bg-red-500').allTextContents().catch(() => []);
  console.log(`Unsupported file alerts:`, unsupportedAlerts);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'uat_09_unsupported_file.png') });

  report.test9_invalidInput = {
    emptyAlerts,
    unsupportedAlerts,
  };

  // -------------------------------------------------------------
  // TEST 10: Connectivity Audit
  // -------------------------------------------------------------
  console.log('\n--- TEST 10: Backend Connectivity Audit ---');
  const apiRequests = networkRequests.filter(r => r.url.includes('/api') || r.url.includes('onrender') || r.url.includes('localhost') || r.url.includes('/upload'));
  console.log(`Total API requests intercepted: ${apiRequests.length}`);
  for (const r of apiRequests) {
    console.log(` - ${r.method} ${r.url} (${r.resourceType})`);
  }
  report.test10_connectivity = {
    apiRequests,
    networkFailures,
  };

  // -------------------------------------------------------------
  // TEST 13: Security / Secrets Inspection
  // -------------------------------------------------------------
  console.log('\n--- TEST 13: Security / Exposure Inspection ---');
  const pageSource = await page.content();
  const hasGeminiKeyInSource = /AIzaSy[A-Za-z0-9_-]{33}/.test(pageSource);
  const hasSecretWordInSource = /GOOGLE_API_KEY\s*=\s*['"]?[A-Za-z0-9_-]+/.test(pageSource);
  console.log(`Secret patterns in HTML: GeminiKey=${hasGeminiKeyInSource}, GoogleApiKeyEnv=${hasSecretWordInSource}`);

  report.test13_security = {
    hasGeminiKeyInSource,
    hasSecretWordInSource,
    httpsUsed: PROD_URL.startsWith('https://'),
  };

  // Save full results JSON
  fs.writeFileSync('uat_report_data.json', JSON.stringify({ report, consoleLogs, networkRequests, networkFailures }, null, 2));
  console.log('\nUAT Run Complete! Results saved to uat_report_data.json');

  await browser.close();
}

runUAT().catch(err => {
  console.error('UAT Runner Failure:', err);
  process.exit(1);
});
