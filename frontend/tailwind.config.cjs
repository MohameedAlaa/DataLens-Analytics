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
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
        },
        accent: {
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
        },
        surface: {
          bg: '#020617',         // App main background
          card: '#0f172a',       // Card background
          elevated: '#1e293b',   // Hover/Elevated card background
          border: '#334155',     // Border subtle
          borderStrong: '#475569',
        },
        content: {
          primary: '#f8fafc',
          secondary: '#94a3b8',
          muted: '#64748b',
        },
        navy: '#0F172A',
        electric: '#3B82F6',
        slate: '#94A3B8',
        darkbg: '#1E293B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};