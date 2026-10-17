/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f7fee7',
          100: '#ecfccb',
          200: '#d9f99d',
          300: '#bef264',
          400: '#d4f237', // Acid Lime - Primary Action & Focus Accent
          500: '#c2e424',
          600: '#a3c415',
          700: '#7f9c10',
          800: '#647c12',
          900: '#526613',
          DEFAULT: '#d4f237',
        },
        terracotta: {
          300: '#f49d88',
          400: '#ea826b',
          500: '#e06d53', // Warm Terracotta - Restrained Secondary Accent
          600: '#c8573d',
          700: '#a23f28',
          DEFAULT: '#e06d53',
        },
        accent: {
          400: '#e06d53',
          500: '#c8573d',
          600: '#a23f28',
        },
        surface: {
          bg: '#111215',          // Deep Graphite / Charcoal canvas
          card: '#181a1f',        // Architectural Charcoal card surface
          elevated: '#20242c',    // Raised surface / Hover / Drawer
          overlay: '#262b35',     // Modal / Dropdown / Popover
          border: 'rgba(255, 255, 255, 0.08)',       // Crisp structural divider
          borderSubtle: 'rgba(255, 255, 255, 0.04)',
          borderStrong: 'rgba(255, 255, 255, 0.16)',
        },
        content: {
          primary: '#f5f4ef',     // Warm Ivory - High contrast, soft on eyes
          secondary: '#b0b0bb',   // Flint neutral gray (exceeds 4.5:1 on all surfaces)
          muted: '#9494a3',       // Architectural stone gray (exceeds 4.5:1 on all surfaces)
        },
        ivory: {
          DEFAULT: '#f5f4ef',
          muted: '#d6d3cb',
          soft: '#faf8f5',
        },
        charcoal: {
          DEFAULT: '#111215',
          light: '#181a1f',
          surface: '#20242c',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'monospace'],
      },
      boxShadow: {
        'card': '0 4px 20px -2px rgba(0, 0, 0, 0.6), inset 0 1px 0 0 rgba(255, 255, 255, 0.04)',
        'elevated': '0 12px 32px -4px rgba(0, 0, 0, 0.75), inset 0 1px 0 0 rgba(255, 255, 255, 0.06)',
        'glow-brand': '0 0 20px -2px rgba(212, 242, 55, 0.22)',
      },
    },
  },
  plugins: [],
};