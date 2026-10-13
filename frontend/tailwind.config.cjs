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
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        accent: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
        },
        surface: {
          bg: '#020617',          // Void / Canvas background
          card: '#0b1222',        // Obsidian glass card background
          elevated: '#111c35',    // Raised surface / Hover / Drawer
          overlay: '#162343',     // Modal / Dropdown / Popover
          border: 'rgba(255, 255, 255, 0.08)',       // Subtle inner border
          borderSubtle: 'rgba(255, 255, 255, 0.05)',
          borderStrong: 'rgba(255, 255, 255, 0.16)',
        },
        content: {
          primary: '#f8fafc',     // High-emphasis white
          secondary: '#94a3b8',   // Medium-emphasis slate
          muted: '#64748b',       // Low-emphasis muted text
        },
        navy: {
          DEFAULT: '#020617',
          light: '#0b1222',
        },
        electric: '#38bdf8',
        slate: '#94a3b8',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'monospace'],
      },
      boxShadow: {
        'card': '0 4px 20px -2px rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
        'elevated': '0 12px 32px -4px rgba(0, 0, 0, 0.65), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
        'glow-brand': '0 0 25px -4px rgba(14, 165, 233, 0.3)',
      },
    },
  },
  plugins: [],
};