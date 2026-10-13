import React from 'react';

/**
 * DataLens Brand Identity Logo Component
 *
 * Distinctive geometric optical lens enclosing graduated data prism bars,
 * symbolizing clarity, focus, and multi-dimensional dataset exploration.
 *
 * @param {'sm' | 'md' | 'lg'} size - Size variant
 * @param {'full' | 'mark' | 'stacked'} variant - Display variant
 * @param {string} className - Additional CSS classes
 */
export default function DataLensLogo({ size = 'md', variant = 'full', className = '' }) {
  const sizeMap = {
    sm: { mark: 28, text: 'text-sm', sub: 'text-[8px]', gap: 'gap-2' },
    md: { mark: 34, text: 'text-base', sub: 'text-[9px]', gap: 'gap-2.5' },
    lg: { mark: 44, text: 'text-xl', sub: 'text-[10px]', gap: 'gap-3' },
  };

  const config = sizeMap[size] || sizeMap.md;
  const markSize = config.mark;

  const Mark = (
    <svg
      width={markSize}
      height={markSize}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="shrink-0 transition-transform duration-200 group-hover:scale-105"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="dlBgGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#181A1F" />
          <stop offset="100%" stopColor="#111215" />
        </linearGradient>
        <linearGradient id="dlRimGrad" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#D4F237" />
          <stop offset="65%" stopColor="#A3C415" />
          <stop offset="100%" stopColor="#E06D53" />
        </linearGradient>
        <linearGradient id="dlBar1" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FAF8F5" />
          <stop offset="100%" stopColor="#D6D3CB" />
        </linearGradient>
        <linearGradient id="dlBar2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#D4F237" />
          <stop offset="100%" stopColor="#92B80F" />
        </linearGradient>
        <linearGradient id="dlBar3" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#EA826B" />
          <stop offset="100%" stopColor="#C8573D" />
        </linearGradient>
        <filter id="dlGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="1" stdDeviation="2.5" floodColor="#D4F237" floodOpacity="0.25" />
        </filter>
      </defs>

      {/* Outer Squircle Container */}
      <rect width="48" height="48" rx="12" fill="url(#dlBgGrad)" />
      <rect width="48" height="48" rx="12" stroke="rgba(255, 255, 255, 0.1)" strokeWidth="1.2" />

      {/* Optical Focusing Ring */}
      <circle
        cx="24"
        cy="24"
        r="16.5"
        stroke="url(#dlRimGrad)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="82 22"
        filter="url(#dlGlow)"
      />

      {/* Reticle / Aperture Inner Guide */}
      <circle
        cx="24"
        cy="24"
        r="11.5"
        stroke="rgba(161, 161, 170, 0.3)"
        strokeWidth="1"
        strokeDasharray="2 3"
      />

      {/* Data Prism Bars (Refracted through the lens) */}
      <rect x="16" y="24" width="3.5" height="10" rx="1.75" fill="url(#dlBar1)" />
      <rect x="22.25" y="16" width="3.5" height="18" rx="1.75" fill="url(#dlBar2)" />
      <rect x="28.5" y="20" width="3.5" height="14" rx="1.75" fill="url(#dlBar3)" />

      {/* Optical Focal Dot */}
      <circle cx="24" cy="11.5" r="1.5" fill="#D4F237" />
    </svg>
  );

  if (variant === 'mark') {
    return <div className={`inline-flex items-center ${className}`}>{Mark}</div>;
  }

  return (
    <div className={`group inline-flex items-center ${config.gap} select-none ${className}`}>
      {Mark}
      <div className="flex flex-col leading-none">
        <div className="flex items-center tracking-tight">
          <span className={`font-semibold text-content-primary ${config.text}`}>Data</span>
          <span className={`font-extrabold text-brand-400 ${config.text}`}>
            Lens
          </span>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-brand-400 ml-1 mb-0.5" />
        </div>
        <span className={`font-mono uppercase font-semibold text-content-muted tracking-[0.2em] ${config.sub} mt-0.5`}>
          Analytics
        </span>
      </div>
    </div>
  );
}
