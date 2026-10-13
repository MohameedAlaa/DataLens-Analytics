import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  LineChart,
  PieChart,
  Table,
  Bot,
  FileText,
  Settings,
  Lock,
  X
} from 'lucide-react';
import Filters from '../Filters/Filters';

const MAIN_NAV_ITEMS = [
  { id: 'overview',       label: 'Overview',       icon: LayoutDashboard },
  { id: 'ai-insights',    label: 'AI Insights',    icon: Sparkles, badge: 'AI' },
  { id: 'analytics',      label: 'Analytics',      icon: LineChart },
  { id: 'visualizations', label: 'Visualizations', icon: PieChart },
  { id: 'dataset',        label: 'Dataset',        icon: Table },
  { id: 'copilot',        label: 'AI Copilot',     icon: Bot, badge: '2.5' },
];

const SECONDARY_NAV_ITEMS = [
  { id: 'reports',  label: 'Reports',  icon: FileText, disabled: true },
  { id: 'settings', label: 'Settings', icon: Settings, disabled: true },
];

/**
 * Professional SaaS Sidebar
 * Information Architecture:
 * 1. Primary Workspace Navigation (Overview, AI Insights, Analytics, Visualizations, Dataset, AI Copilot)
 * 2. Dataset Filters Control Center
 * 3. Secondary / Coming Soon (Reports, Settings)
 */
export default function Sidebar({ activeTab, setActiveTab, isOpenMobile = false, onCloseMobile }) {
  const sidebarContent = (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Scrollable Navigation & Filter Center */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-3 space-y-3">
        {/* ── Main Navigation ─────────────────────────────── */}
        <div>
          <p className="label-caps px-2 mb-1.5">Workspace</p>
          <nav className="space-y-0.5" aria-label="Workspace Navigation">
            {MAIN_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setActiveTab(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`
                    w-full flex items-center justify-between
                    px-2.5 py-1.5 rounded-lg text-xs font-medium
                    transition-all duration-150 ease-out active:scale-[0.98] text-left
                    ${isActive
                      ? 'bg-brand-500/10 text-brand-400 border border-brand-500/30 font-semibold shadow-sm'
                      : 'text-content-secondary hover:bg-surface-elevated/70 hover:text-content-primary border border-transparent'
                    }
                  `}
                >
                  <span className="flex items-center gap-2.5 min-w-0">
                    <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-brand-400' : 'text-content-muted'}`} />
                    <span className="truncate">{item.label}</span>
                  </span>
                  {item.badge && (
                    <span
                      className={`ml-1 shrink-0 px-1.5 py-px text-[9px] font-mono font-bold rounded ${
                        item.badge === 'AI'
                          ? 'bg-brand-400 text-[#111215]'
                          : 'bg-surface-elevated text-brand-400 border border-brand-500/25'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* ── Divider ────────────────────────────────────── */}
        <div className="border-t border-surface-border/70" />

        {/* ── Filter Control Center ──────────────────────── */}
        <div>
          <Filters />
        </div>

        {/* ── Divider ────────────────────────────────────── */}
        <div className="border-t border-surface-border/70" />

        {/* ── Coming Soon / Platform ─────────────────────── */}
        <div>
          <p className="label-caps px-2 mb-1.5">Platform</p>
          <nav className="space-y-0.5" aria-label="Platform Navigation">
            {SECONDARY_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.id}
                  className="w-full flex items-center justify-between
                             px-2.5 py-1.5 rounded-lg text-xs font-medium
                             text-content-muted/60 opacity-60 cursor-not-allowed select-none"
                >
                  <span className="flex items-center gap-2.5 min-w-0">
                    <Icon className="w-3.5 h-3.5 shrink-0 text-content-muted/60" />
                    <span className="truncate">{item.label}</span>
                  </span>
                  <Lock className="w-2.5 h-2.5 shrink-0 text-content-muted/60 ml-1" />
                </div>
              );
            })}
          </nav>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className="hidden md:flex w-60 lg:w-64 shrink-0 flex-col
                   border-r border-surface-border bg-surface-card/60 backdrop-blur-sm
                   h-full max-h-full overflow-hidden select-none"
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {isOpenMobile && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Mobile Navigation Drawer"
          className="fixed inset-0 z-50 flex md:hidden bg-black/70 backdrop-blur-sm"
        >
          <aside className="w-72 max-w-[85vw] h-full h-[100dvh] max-h-[100dvh] bg-surface-card border-r border-surface-border flex flex-col shadow-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between shrink-0">
              <span className="text-xs font-semibold text-content-primary">Menu & Filters</span>
              <button
                type="button"
                onClick={onCloseMobile}
                aria-label="Close menu"
                className="p-1 rounded-lg text-content-muted hover:text-content-primary hover:bg-surface-elevated transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            {sidebarContent}
          </aside>
          <div className="flex-1" onClick={onCloseMobile} aria-hidden="true" />
        </div>
      )}
    </>
  );
}
