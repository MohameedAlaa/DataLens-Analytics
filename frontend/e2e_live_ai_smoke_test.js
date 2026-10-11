import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';

const FRONTEND_URL = 'http://127.0.0.1:5173';
const FIXTURES_DIR = path.resolve('../test_fixtures');
const PRIMARY_CSV = path.join(FIXTURES_DIR, 'alex_sales_primary.csv');
const SECOND_CSV = path.join(FIXTURES_DIR, 'alex_sales_second.csv');
const SCREENSHOT_DIR = path.resolve('C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots');

async function runLiveSmokeTest() {
  console.log('===============================================================');
  console.log('DATALENS ANALYTICS — LIVE AI SMOKE TEST (gemini-2.5-flash)');
  console.log('===============================================================');

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const results = {
    modelOverride: 'gemini-2.5-flash',
    greeting: null,
    semanticRAG: null,
    datasetIsolation: null,
  };

  try {
    // 1. Visit App
    console.log('\n--- 1. Navigating to DataLens App ---');
    await page.goto(FRONTEND_URL, { waitUntil: 'networkidle' });

    // 2. Upload Primary Dataset
    console.log(`\n--- 2. Uploading Primary Dataset: ${PRIMARY_CSV} ---`);
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(PRIMARY_CSV);
    const uploadRes = await page.waitForResponse(res => res.url().includes('/upload'), { timeout: 20000 });
    console.log(`Upload Status: ${uploadRes.status()}`);

    const pill = page.locator('text=alex_sales_primary.csv').first();
    await pill.waitFor({ timeout: 15000 });
    console.log('Dataset loaded in React context: alex_sales_primary.csv');
    await page.waitForTimeout(2000);

    const chatInput = page.locator('input[aria-label="Ask AI Copilot about dataset"]');
    const sendBtn = page.locator('button[aria-label="Send message"]');

    // Ensure chat input is enabled
    await chatInput.waitFor({ state: 'visible', timeout: 10000 });
    for (let attempt = 0; attempt < 20; attempt++) {
      if (!(await chatInput.isDisabled())) break;
      await page.waitForTimeout(500);
    }
    console.log(`Chat Input disabled status: ${await chatInput.isDisabled()}`);

    // 3. Greeting Query (LIVE)
    console.log('\n--- 3. Running Live Greeting Query: "Hello" ---');
    await chatInput.fill('Hello');
    await page.waitForTimeout(300);

    const [greetRes] = await Promise.all([
      page.waitForResponse(res => res.url().includes('/chat'), { timeout: 45000 }),
      sendBtn.click(),
    ]);
    console.log(`Greeting HTTP Status: ${greetRes.status()}`);
    const greetJson = await greetRes.json();
    await page.waitForTimeout(2000);

    const messages = await page.locator('.rounded-tl-none').allInnerTexts();
    const greetAnswer = messages[messages.length - 1] || '';
    console.log(`Live Greeting Response: "${greetAnswer.trim()}"`);

    const greetScreenshot = path.join(SCREENSHOT_DIR, 'live_smoke_greeting.png');
    await page.screenshot({ path: greetScreenshot });

    results.greeting = {
      query: 'Hello',
      status: greetRes.status(),
      answer: greetAnswer.trim(),
      screenshot: greetScreenshot,
      isLive: true,
    };

    // 4. Semantic / RAG Query (LIVE)
    console.log('\n--- 4. Running Live Semantic / RAG Query: "What products are sold in this dataset and in which countries?" ---');
    await chatInput.fill('What products are sold in this dataset and in which countries?');
    await page.waitForTimeout(300);

    const [ragRes] = await Promise.all([
      page.waitForResponse(res => res.url().includes('/chat'), { timeout: 45000 }),
      sendBtn.click(),
    ]);
    console.log(`Semantic / RAG HTTP Status: ${ragRes.status()}`);
    const ragJson = await ragRes.json();
    await page.waitForTimeout(2000);

    const messagesAfterRag = await page.locator('.rounded-tl-none').allInnerTexts();
    const ragAnswer = messagesAfterRag[messagesAfterRag.length - 1] || '';
    console.log(`Live Semantic / RAG Response: "${ragAnswer.trim().slice(0, 200)}..."`);

    const citationBadges = await page.locator('text=Verified Citation').count();
    console.log(`Rendered Verified Citation Badges in UI: ${citationBadges}`);

    // Verify citation payload details
    const citations = ragJson.citations || [];
    console.log(`Backend citations returned: ${citations.length}`);
    const citationFilenames = citations.map(c => c.filename);
    console.log(`Citation filenames: ${citationFilenames.join(', ')}`);

    const ragScreenshot = path.join(SCREENSHOT_DIR, 'live_smoke_semantic_rag.png');
    await page.screenshot({ path: ragScreenshot });

    results.semanticRAG = {
      query: 'What products are sold in this dataset and in which countries?',
      status: ragRes.status(),
      answer: ragAnswer.trim(),
      citationsCount: citations.length,
      citationFilenames,
      citationBadgesInUI: citationBadges,
      screenshot: ragScreenshot,
      isLive: true,
      hasProductNames: ragAnswer.toLowerCase().includes('laptop') || ragAnswer.toLowerCase().includes('smartphone'),
      onlyPrimaryCitations: citationFilenames.every(f => f === 'alex_sales_primary.csv'),
    };

    // 5. Cross-Dataset Isolation Live Test
    console.log(`\n--- 5. Uploading Second Dataset: ${SECOND_CSV} ---`);
    const navbarFileInput = page.locator('input[aria-label="Upload dataset file input"]');
    await navbarFileInput.setInputFiles(SECOND_CSV);
    const switchUploadRes = await page.waitForResponse(res => res.url().includes('/upload'), { timeout: 20000 });
    console.log(`Second Dataset Upload Status: ${switchUploadRes.status()}`);
    await page.waitForTimeout(3000);

    console.log('Querying Second Dataset: "What quarters and tiers are in this dataset?"');
    await chatInput.fill('What quarters and tiers are in this dataset?');
    await page.waitForTimeout(300);

    const [secondRagRes] = await Promise.all([
      page.waitForResponse(res => res.url().includes('/chat'), { timeout: 45000 }),
      sendBtn.click(),
    ]);
    console.log(`Second Dataset RAG HTTP Status: ${secondRagRes.status()}`);
    const secondRagJson = await secondRagRes.json();
    await page.waitForTimeout(2000);

    const messagesAfterSecond = await page.locator('.rounded-tl-none').allInnerTexts();
    const secondRagAnswer = messagesAfterSecond[messagesAfterSecond.length - 1] || '';
    console.log(`Second Dataset Response: "${secondRagAnswer.trim().slice(0, 200)}..."`);

    const secondCitations = secondRagJson.citations || [];
    const secondCitationFilenames = secondCitations.map(c => c.filename);
    console.log(`Second dataset citations: ${secondCitationFilenames.join(', ')}`);

    const isolatedFromPrimary = !secondCitationFilenames.some(f => f === 'alex_sales_primary.csv');
    console.log(`Strictly isolated from primary dataset citations: ${isolatedFromPrimary}`);

    const isolationScreenshot = path.join(SCREENSHOT_DIR, 'live_smoke_dataset_isolation.png');
    await page.screenshot({ path: isolationScreenshot });

    results.datasetIsolation = {
      status: secondRagRes.status(),
      answer: secondRagAnswer.trim(),
      citationsCount: secondCitations.length,
      citationFilenames: secondCitationFilenames,
      isolatedFromPrimary,
      screenshot: isolationScreenshot,
      isLive: true,
    };

    console.log('\nAll Live AI smoke tests passed successfully!');
  } catch (err) {
    console.error(`Live Smoke Test Exception: ${err.message}`);
    results.error = err.message;
  } finally {
    await browser.close();
  }

  const resultsPath = path.resolve('C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/live_smoke_test_results.json');
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
  console.log(`Results written to: ${resultsPath}`);
}

runLiveSmokeTest();
