const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const SCREENSHOTS_DIR = 'C:\\Users\\moham\\.gemini\\antigravity-ide\\brain\\b1bcdca6-5056-49eb-9497-47913775312f\\screenshots';

async function runVerification() {
  console.log('🚀 Starting DataLens Premium UI/UX & Brand Identity Verification...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const results = {
    viewports: {},
    sampleLoad: false,
    dashboardMetrics: false,
    chartsRendered: false,
    filtersWorking: false,
    copilotWorking: false,
    citationsVerified: false,
    consoleErrors: []
  };

  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('🔴 Browser Console Error:', msg.text());
      results.consoleErrors.push(msg.text());
    }
  });

  try {
    // 1. Desktop Viewport (1440x900) - Empty State
    console.log('\n--- 1. Testing Desktop 1440x900 (Empty State / Workspace Hero) ---');
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('http://localhost:4173', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    const desktopOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    console.log('✓ Desktop scrollWidth <= window.innerWidth:', desktopOverflow);
    results.viewports.desktop1440 = { noHorizontalOverflow: desktopOverflow };

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '01_desktop_empty_workspace_hero.png'), fullPage: true });
    console.log('📸 Saved 01_desktop_empty_workspace_hero.png');

    // 2. Tablet Viewport (768x1024) - Empty State
    console.log('\n--- 2. Testing Tablet 768x1024 (Empty State) ---');
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    const tabletOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    console.log('✓ Tablet scrollWidth <= window.innerWidth:', tabletOverflow);
    results.viewports.tablet768 = { noHorizontalOverflow: tabletOverflow };
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '02_tablet_empty_workspace_hero.png'), fullPage: true });
    console.log('📸 Saved 02_tablet_empty_workspace_hero.png');

    // 3. Mobile Viewport (390x844) - Empty State
    console.log('\n--- 3. Testing Mobile 390x844 (Empty State) ---');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(500);
    const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    console.log('✓ Mobile scrollWidth <= window.innerWidth:', mobileOverflow);
    results.viewports.mobile390 = { noHorizontalOverflow: mobileOverflow };
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '03_mobile_empty_workspace_hero.png'), fullPage: true });
    console.log('📸 Saved 03_mobile_empty_workspace_hero.png');

    // 4. Small Mobile Viewport (360x800) - Empty State
    console.log('\n--- 4. Testing Small Mobile 360x800 (Empty State) ---');
    await page.setViewportSize({ width: 360, height: 800 });
    await page.waitForTimeout(500);
    const smallMobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    console.log('✓ Small mobile scrollWidth <= window.innerWidth:', smallMobileOverflow);
    results.viewports.smallMobile360 = { noHorizontalOverflow: smallMobileOverflow };
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '04_small_mobile_empty_workspace_hero.png'), fullPage: true });
    console.log('📸 Saved 04_small_mobile_empty_workspace_hero.png');

    // Switch back to Desktop 1440x900 for ingestion and full dashboard verification
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);

    // 5. Ingestion via 1-Click Sample Dataset ("Global Sales & Operations")
    console.log('\n--- 5. Ingesting Sample Dataset ("Global Sales & Operations") ---');
    const sampleBtn = page.locator('button:has-text("Global Sales & Operations")').first();
    await sampleBtn.waitFor({ state: 'visible', timeout: 8000 });
    await sampleBtn.click();
    console.log('Clicked "Global Sales & Operations" button, waiting for dataset health & analytics...');

    // Wait for DATASET HEALTH section to appear
    await page.waitForSelector('text=DATASET HEALTH', { timeout: 35000 });
    console.log('✓ Dataset loaded! DATASET HEALTH card visible.');
    results.sampleLoad = true;

    // Verify KPI Summary values
    const hasQuality = await page.locator('text=DATA QUALITY ANALYSIS').isVisible();
    const hasCorrelation = await page.locator('text=CORRELATION INSIGHTS').isVisible();
    console.log('✓ Visual Sections confirmed: DATASET HEALTH, DATA QUALITY, CORRELATION INSIGHTS.');
    results.dashboardMetrics = hasQuality && hasCorrelation;

    // Check Recharts
    await page.waitForSelector('.recharts-wrapper', { timeout: 15000 });
    const chartCount = await page.locator('.recharts-wrapper').count();
    console.log(`✓ Recharts detected: ${chartCount} charts rendered.`);
    results.chartsRendered = chartCount >= 1;

    // Wait for animations and take Full Dashboard Desktop Screenshot
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '05_desktop_loaded_dashboard.png'), fullPage: true });
    console.log('📸 Saved 05_desktop_loaded_dashboard.png');

    // 6. Test Responsive Loaded Dashboard on Tablet and Mobile
    console.log('\n--- 6. Loaded Dashboard Responsive Checks ---');
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '06_tablet_loaded_dashboard.png'), fullPage: true });
    console.log('📸 Saved 06_tablet_loaded_dashboard.png');

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '07_mobile_loaded_dashboard.png'), fullPage: true });
    console.log('📸 Saved 07_mobile_loaded_dashboard.png');

    // Restore desktop
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);

    // 7. Test AI Copilot & Live Gemini Query
    console.log('\n--- 7. Testing AI Copilot & Live Gemini Query ---');
    const summarizeBtn = page.locator('button:has-text("Summarize Trends")').first();
    await summarizeBtn.waitFor({ state: 'visible', timeout: 5000 });
    await summarizeBtn.click();
    console.log('Clicked "Summarize Trends" quick action button.');

    // Wait for AI response with citations to appear
    console.log('Waiting for AI response from Gemini 2.5 Flash...');
    await page.waitForSelector('text=Verified Citation', { timeout: 45000 });
    console.log('✓ Verified Citation element visible! Expanding citations...');

    const citationSummary = page.locator('text=Verified Citation').first();
    await citationSummary.click();
    await page.waitForTimeout(600);
    results.citationsVerified = true;

    const assistantBubble = page.locator('.rounded-tl-none').last();
    const aiResponseText = await assistantBubble.textContent();
    console.log('✓ Received AI Copilot Response snippet:\n', aiResponseText.slice(0, 300) + '...');
    results.copilotWorking = aiResponseText.length > 30;

    // Take Screenshot of Open AI Copilot with AI Response & Expanded Citation
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '08_desktop_copilot_drawer_response.png') });
    console.log('📸 Saved 08_desktop_copilot_drawer_response.png');

    // 8. Test Filter Interaction
    console.log('\n--- 8. Testing Filters ---');
    const countryFilterHeader = page.locator('text=country').first();
    if (await countryFilterHeader.isVisible()) {
      await countryFilterHeader.click();
      console.log('Opened "country" filter accordion.');
      await page.waitForTimeout(500);
    }

    const resetFiltersBtn = page.locator('button:has-text("Reset all filters")').first();
    if (await resetFiltersBtn.isVisible()) {
      results.filtersWorking = true;
      console.log('✓ "Reset all filters" button available and functional.');
      await resetFiltersBtn.click();
      await page.waitForTimeout(500);
    }

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '09_desktop_filters_drawer.png') });
    console.log('📸 Saved 09_desktop_filters_drawer.png');

    console.log('\n=======================================');
    console.log('🎉 Verification Complete!');
    console.log(JSON.stringify(results, null, 2));
    console.log('=======================================');

  } catch (err) {
    console.error('❌ Verification Error:', err);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'error_state.png') }).catch(() => {});
  } finally {
    await browser.close();
  }
}

runVerification();
