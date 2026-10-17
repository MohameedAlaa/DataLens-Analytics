import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const VERCEL_JSON_PATH = path.resolve(__dirname, '../../vercel.json');
const INDEX_HTML_PATH = path.resolve(__dirname, '../../index.html');

describe('SEC-01: Security Headers and Content Security Policy Audit', () => {
  it('vercel.json exists, parses as valid JSON, and defines headers array', () => {
    assert.ok(fs.existsSync(VERCEL_JSON_PATH), 'vercel.json must exist');
    const raw = fs.readFileSync(VERCEL_JSON_PATH, 'utf-8');
    const config = JSON.parse(raw);
    assert.ok(Array.isArray(config.headers), 'vercel.json must define a headers array');
    assert.ok(config.headers.length > 0, 'headers array must not be empty');
  });

  it('vercel.json configures comprehensive security headers on all routes', () => {
    const raw = fs.readFileSync(VERCEL_JSON_PATH, 'utf-8');
    const config = JSON.parse(raw);
    const globalRule = config.headers.find(h => h.source === '/(.*)');
    assert.ok(globalRule, 'A header rule matching /(.*) must be defined');

    const headerMap = {};
    for (const hdr of globalRule.headers) {
      headerMap[hdr.key.toLowerCase()] = hdr.value;
    }

    assert.equal(headerMap['x-content-type-options'], 'nosniff');
    assert.equal(headerMap['x-frame-options'], 'DENY');
    assert.equal(headerMap['referrer-policy'], 'strict-origin-when-cross-origin');
    assert.ok(headerMap['strict-transport-security']?.includes('max-age=31536000'));
    assert.ok(headerMap['strict-transport-security']?.includes('includeSubDomains'));
    assert.ok(headerMap['permissions-policy']?.includes('geolocation=()'));
    assert.ok(headerMap['permissions-policy']?.includes('camera=()'));
    assert.ok(headerMap['permissions-policy']?.includes('microphone=()'));
    assert.ok(headerMap['content-security-policy'], 'Content-Security-Policy must be defined');
  });

  it('Content-Security-Policy contains all required and restrictive directives', () => {
    const raw = fs.readFileSync(VERCEL_JSON_PATH, 'utf-8');
    const config = JSON.parse(raw);
    const globalRule = config.headers.find(h => h.source === '/(.*)');
    const cspHeader = globalRule.headers.find(h => h.key === 'Content-Security-Policy')?.value;
    assert.ok(cspHeader, 'CSP header value must be present');

    // Parse directives into a map
    const directives = {};
    cspHeader.split(';').map(d => d.trim()).filter(Boolean).forEach(d => {
      const [name, ...sources] = d.split(/\s+/);
      directives[name] = sources;
    });

    // 1. default-src
    assert.ok(directives['default-src']?.includes("'self'"), "default-src must include 'self'");

    // 2. script-src: strict 'self' only, no unsafe-inline or unsafe-eval
    assert.ok(directives['script-src']?.includes("'self'"), "script-src must include 'self'");
    assert.ok(!directives['script-src']?.includes("'unsafe-inline'"), "script-src must NOT include 'unsafe-inline'");
    assert.ok(!directives['script-src']?.includes("'unsafe-eval'"), "script-src must NOT include 'unsafe-eval'");
    assert.ok(!directives['script-src']?.includes('*'), 'script-src must NOT include wildcard *');

    // 3. style-src: self, unsafe-inline for React/Recharts/Framer styles, and Google Fonts
    assert.ok(directives['style-src']?.includes("'self'"), "style-src must include 'self'");
    assert.ok(directives['style-src']?.includes("'unsafe-inline'"), "style-src must include 'unsafe-inline' for chart and UI styles");
    assert.ok(directives['style-src']?.includes('https://fonts.googleapis.com'), 'style-src must allow Google Fonts CSS');

    // 4. font-src: self and fonts.gstatic.com
    assert.ok(directives['font-src']?.includes("'self'"), "font-src must include 'self'");
    assert.ok(directives['font-src']?.includes('https://fonts.gstatic.com'), 'font-src must allow Google Fonts woff2 files');

    // 5. img-src: self, data:, blob:
    assert.ok(directives['img-src']?.includes("'self'"), "img-src must include 'self'");
    assert.ok(directives['img-src']?.includes('data:'), 'img-src must include data:');
    assert.ok(directives['img-src']?.includes('blob:'), 'img-src must include blob:');

    // 6. connect-src: self and canonical Render backend
    assert.ok(directives['connect-src']?.includes("'self'"), "connect-src must include 'self'");
    assert.ok(directives['connect-src']?.includes('https://datalens-backend-jt3p.onrender.com'), 'connect-src must allow Render backend');

    // 7. object-src: none (blocks plugins)
    assert.ok(directives['object-src']?.includes("'none'"), "object-src must be 'none'");

    // 8. base-uri and form-action: self
    assert.ok(directives['base-uri']?.includes("'self'"), "base-uri must be 'self'");
    assert.ok(directives['form-action']?.includes("'self'"), "form-action must be 'self'");

    // 9. frame-ancestors: none (clickjacking protection)
    assert.ok(directives['frame-ancestors']?.includes("'none'"), "frame-ancestors must be 'none'");
  });

  it('external resources in index.html are permitted by CSP', () => {
    const html = fs.readFileSync(INDEX_HTML_PATH, 'utf-8');
    const raw = fs.readFileSync(VERCEL_JSON_PATH, 'utf-8');
    const config = JSON.parse(raw);
    const globalRule = config.headers.find(h => h.source === '/(.*)');
    const csp = globalRule.headers.find(h => h.key === 'Content-Security-Policy')?.value;

    if (html.includes('https://fonts.googleapis.com')) {
      assert.ok(csp.includes('https://fonts.googleapis.com'), 'fonts.googleapis.com in index.html must be in CSP');
    }
    if (html.includes('https://fonts.gstatic.com')) {
      assert.ok(csp.includes('https://fonts.gstatic.com'), 'fonts.gstatic.com in index.html must be in CSP');
    }
  });
});
