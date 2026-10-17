import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ── WCAG Relative Luminance & Contrast Ratio Implementation ─────────────────
function hexToRgb(hex) {
  const sanitized = hex.replace('#', '');
  return {
    r: parseInt(sanitized.substring(0, 2), 16),
    g: parseInt(sanitized.substring(2, 4), 16),
    b: parseInt(sanitized.substring(4, 6), 16),
  };
}

function sRgbToLinear(c) {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

function getRelativeLuminance(rgb) {
  const r = sRgbToLinear(rgb.r);
  const g = sRgbToLinear(rgb.g);
  const b = sRgbToLinear(rgb.b);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function getContrastRatio(hex1, hex2) {
  const lum1 = getRelativeLuminance(hexToRgb(hex1));
  const lum2 = getRelativeLuminance(hexToRgb(hex2));
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  return (brightest + 0.05) / (darkest + 0.05);
}

describe('UI-01: UI Accessibility Audit and Contrast/Focus Remediation', () => {
  const tailwindPath = path.resolve(__dirname, '../../tailwind.config.cjs');
  const tailwindConfig = fs.readFileSync(tailwindPath, 'utf8');

  // Parse color tokens from tailwind.config.cjs
  const primaryMatch = tailwindConfig.match(/primary:\s*'([^']+)'/);
  const secondaryMatch = tailwindConfig.match(/secondary:\s*'([^']+)'/);
  const mutedMatch = tailwindConfig.match(/muted:\s*'([^']+)'/);

  const bgMatch = tailwindConfig.match(/bg:\s*'([^']+)'/);
  const cardMatch = tailwindConfig.match(/card:\s*'([^']+)'/);
  const elevatedMatch = tailwindConfig.match(/elevated:\s*'([^']+)'/);
  const overlayMatch = tailwindConfig.match(/overlay:\s*'([^']+)'/);
  const brand400Match = tailwindConfig.match(/400:\s*'([^']+)',\s*\/\/\s*Acid Lime/);

  const tokens = {
    contentPrimary: primaryMatch ? primaryMatch[1] : null,
    contentSecondary: secondaryMatch ? secondaryMatch[1] : null,
    contentMuted: mutedMatch ? mutedMatch[1] : null,
    surfaceBg: bgMatch ? bgMatch[1] : null,
    surfaceCard: cardMatch ? cardMatch[1] : null,
    surfaceElevated: elevatedMatch ? elevatedMatch[1] : null,
    surfaceOverlay: overlayMatch ? overlayMatch[1] : null,
    brand400: brand400Match ? brand400Match[1] : '#d4f237',
  };

  test('Design tokens exist and parse correctly', () => {
    assert.ok(tokens.contentPrimary, 'content.primary token must exist');
    assert.ok(tokens.contentSecondary, 'content.secondary token must exist');
    assert.ok(tokens.contentMuted, 'content.muted token must exist');
    assert.ok(tokens.surfaceBg, 'surface.bg token must exist');
    assert.ok(tokens.surfaceCard, 'surface.card token must exist');
    assert.ok(tokens.surfaceElevated, 'surface.elevated token must exist');
    assert.ok(tokens.surfaceOverlay, 'surface.overlay token must exist');
  });

  test('content.primary satisfies WCAG AAA contrast (>= 7.0:1) across all surfaces', () => {
    const surfaces = [tokens.surfaceBg, tokens.surfaceCard, tokens.surfaceElevated, tokens.surfaceOverlay];
    surfaces.forEach((surf) => {
      const ratio = getContrastRatio(tokens.contentPrimary, surf);
      assert.ok(
        ratio >= 7.0,
        `content.primary (${tokens.contentPrimary}) on ${surf} must be >= 7.0:1, got ${ratio.toFixed(2)}:1`
      );
    });
  });

  test('content.secondary satisfies WCAG AA contrast (>= 4.5:1) across all surfaces', () => {
    const surfaces = [tokens.surfaceBg, tokens.surfaceCard, tokens.surfaceElevated, tokens.surfaceOverlay];
    surfaces.forEach((surf) => {
      const ratio = getContrastRatio(tokens.contentSecondary, surf);
      assert.ok(
        ratio >= 4.5,
        `content.secondary (${tokens.contentSecondary}) on ${surf} must be >= 4.5:1, got ${ratio.toFixed(2)}:1`
      );
    });
  });

  test('content.muted satisfies WCAG AA contrast (>= 4.5:1) across all surfaces (fixes UI-01 defect)', () => {
    const surfaces = [tokens.surfaceBg, tokens.surfaceCard, tokens.surfaceElevated, tokens.surfaceOverlay];
    surfaces.forEach((surf) => {
      const ratio = getContrastRatio(tokens.contentMuted, surf);
      assert.ok(
        ratio >= 4.5,
        `content.muted (${tokens.contentMuted}) on ${surf} must be >= 4.5:1, got ${ratio.toFixed(2)}:1`
      );
    });
  });

  test('brand-400 focus indicator satisfies WCAG non-text UI contrast (>= 3.0:1) against dark surfaces', () => {
    const surfaces = [tokens.surfaceBg, tokens.surfaceCard, tokens.surfaceElevated, tokens.surfaceOverlay];
    surfaces.forEach((surf) => {
      const ratio = getContrastRatio(tokens.brand400, surf);
      assert.ok(
        ratio >= 3.0,
        `brand-400 (${tokens.brand400}) on ${surf} must be >= 3.0:1, got ${ratio.toFixed(2)}:1`
      );
    });
  });

  test('index.css declares global *:focus-visible outline', () => {
    const indexCssPath = path.resolve(__dirname, '../index.css');
    const indexCss = fs.readFileSync(indexCssPath, 'utf8');
    assert.match(indexCss, /\*:focus-visible\s*\{[^}]*outline:\s*2px solid/);
  });

  test('AIInsightsSection accordion header button has visible focus styling', () => {
    const filePath = path.resolve(__dirname, '../components/Insights/AIInsightsSection.jsx');
    const code = fs.readFileSync(filePath, 'utf8');
    assert.match(code, /focus-visible:ring-2/);
    assert.match(code, /focus-visible:ring-brand-400/);
  });

  test('Filters.jsx contains focus-visible styling on interactive controls and avoids low-opacity muted text', () => {
    const filePath = path.resolve(__dirname, '../components/Filters/Filters.jsx');
    const code = fs.readFileSync(filePath, 'utf8');
    assert.match(code, /focus-visible:ring-2 focus-visible:ring-brand-400/);
    assert.doesNotMatch(
      code,
      /placeholder:text-content-muted\/70/,
      'Must not dilute muted text opacity in placeholder below WCAG AA'
    );
    assert.doesNotMatch(
      code,
      /text-content-muted\/70/,
      'Must not dilute muted text opacity in helper text below WCAG AA'
    );
  });

  test('AdvancedDataTable.jsx provides accessible focus-visible rings and aria-labels on controls', () => {
    const filePath = path.resolve(__dirname, '../components/Dashboard/AdvancedDataTable.jsx');
    const code = fs.readFileSync(filePath, 'utf8');
    assert.match(code, /aria-label="Rows per page"/);
    assert.match(code, /focus-visible:ring-2 focus-visible:ring-brand-400/);
  });

  test('Chatbot.jsx provides accessible focus-visible rings on input and buttons', () => {
    const filePath = path.resolve(__dirname, '../components/Chatbot/Chatbot.jsx');
    const code = fs.readFileSync(filePath, 'utf8');
    assert.match(code, /aria-label="Ask AI Copilot about dataset"/);
    assert.match(code, /focus-visible:ring-2 focus-visible:ring-brand-400/);
  });

  test('WorkspaceHero.jsx dropzone and samples declare focus-visible keyboard styling', () => {
    const filePath = path.resolve(__dirname, '../components/Upload/WorkspaceHero.jsx');
    const code = fs.readFileSync(filePath, 'utf8');
    assert.match(code, /role="button"/);
    assert.match(code, /tabIndex=\{0\}/);
    assert.match(code, /focus-visible:ring-brand-400/);
  });
});
