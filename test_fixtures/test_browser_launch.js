import { chromium } from 'playwright';

async function main() {
  try {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    console.log('Successfully launched msedge with Playwright!');
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:5173');
    console.log('Title:', await page.title());
    await browser.close();
  } catch (err) {
    console.error('Launch failed:', err.message);
  }
}

main();
