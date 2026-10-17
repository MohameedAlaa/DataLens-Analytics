#!/usr/bin/env node
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, '..');
const DIST_DIR = path.join(FRONTEND_DIR, 'dist');

console.log('================================================================');
console.log('DATALENS ANALYTICS — BROWSER E2E TEST SUITE (PLAYWRIGHT)');
console.log('================================================================');

// 1. Verify that production bundle exists
if (!fs.existsSync(DIST_DIR) || !fs.existsSync(path.join(DIST_DIR, 'index.html'))) {
  console.log('[E2E Runner] Production build not found in dist/. Triggering build first...');
  const buildProc = spawn('npm', ['run', 'build'], {
    cwd: FRONTEND_DIR,
    stdio: 'inherit',
    shell: true,
  });

  buildProc.on('close', (code) => {
    if (code !== 0) {
      console.error(`[E2E Runner] Build failed with exit code ${code}. Aborting E2E tests.`);
      process.exit(code);
    }
    runTests();
  });
} else {
  console.log('[E2E Runner] Verified existing production bundle in dist/ (no rebuild needed).');
  runTests();
}

function runTests() {
  console.log('[E2E Runner] Executing Playwright E2E suite under node:test runner...');
  const testProc = spawn(process.execPath, ['--test', 'e2e/e2e.test.js'], {
    cwd: FRONTEND_DIR,
    stdio: 'inherit',
    env: {
      ...process.env,
      NODE_ENV: 'production',
    },
  });

  testProc.on('close', (code) => {
    if (code === 0) {
      console.log('\n================================================================');
      console.log('✔ ALL E2E BROWSER USER JOURNEYS PASSED CLEANLY');
      console.log('================================================================\n');
    } else {
      console.error(`\n✖ E2E tests failed with exit code ${code}\n`);
    }
    process.exit(code);
  });
}
