import React from 'react';
import {
  LayoutDashboard, Sparkles, LineChart, PieChart,
  Table, Bot, FileText, Settings, Filter,
  ChevronDown, ChevronRight, Lock,
} from 'lucide-react';
import Filters from '../Filters/Filters';

const NAV_SECTIONS = [
  {
    label: 'Navigation',
    items: [
      { id: 'overview',       label: 'Overview',       icon: LayoutDashboard },
      { id: 'ai-insights',    label: 'AI Insights',    icon: Sparkles,  badge: 'AI' },
      { id: 'analytics',      label: 'Analytics',      icon: LineChart  },
      { id: 'visualizations', label: 'Visualizations', icon: PieChart   },
      { id: 'dataset',        label: 'Dataset',        icon: Table      },
      { id: 'copilot',        label: 'AI Copilot',     icon: Bot        },
    ],
  },
  {
    label: 'Coming soon',
    items: [
      { id: 'reports',  label: 'Reports',  icon: FileText, disabled: true },
      { id: 'settings', label: 'Settings', icon: Settings, disabled: true },
    ],
  },
];

export default function Sidebar({ activeTab, setActiveTab }) {
  const [filtersOpen, setFiltersOpen] = React.useState(true);

  return (
    <aside
      className="hidden md:flex w-60 lg:w-64 shrink-0 flex-col
                 border-r border-surface-border bg-surface-card
                 h-[calc(100vh-4rem)] sticky top-16 overflow-hidden"
    >
      {/* ── Navigation Groups ─────────────────────────────── */}
      <div className="overflow-y-auto custom-scrollbar">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="p-3 pb-1">
            <p className="label-caps px-2 mb-1.5">{section.label}</p>
            <nav className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    disabled={item.disabled}
                    onClick={() => !item.disabled && setActiveTab(item.id)}
                    className={`
                      w-full flex items-center justify-between
                      px-2.5 py-2 rounded-lg body-xs font-medium
                      transition-all duration-100
                      ${isActive
                        ? 'bg-brand-500/12 text-brand-400 border border-brand-500/25'
                        : item.disabled
                        ? 'text-content-muted opacity-40 cursor-not-allowed'
                        : 'text-content-secondary hover:bg-surface-elevated hover:text-content-primary'
                      }
                    `}
                  >
                    <span className="flex items-center gap-2.5 min-w-0">
                      <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-brand-400' : ''}`} />
                      <span className="truncate">{item.label}</span>
                    </span>
                    {item.badge && (
                      <span className="ml-1 shrink-0 px-1.5 py-px text-[9px] font-extrabold
                                       bg-brand-500 text-white rounded tracking-wide">
                        {item.badge}
                      </span>
                    )}
                    {item.disabled && (
                      <Lock className="w-2.5 h-2.5 shrink-0 text-content-muted ml-1" />
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        ))}

        {/* ── Divider ──────────────────────────────────────── */}
        <div className="mx-3 my-2 border-t border-surface-border" />

        {/* ── Filter Panel ─────────────────────────────────── */}
        <div className="p-3">
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className="w-full flex items-center justify-between
                       px-2.5 py-2 rounded-lg body-xs font-semibold text-content-primary
                       hover:bg-surface-elevated transition-colors"
          >
            <span className="flex items-center gap-2.5">
              <Filter className="w-3.5 h-3.5 text-brand-400 shrink-0" />
              Dataset Filters
            </span>
            {filtersOpen
              ? <ChevronDown className="w-3.5 h-3.5 text-content-muted" />
              : <ChevronRight className="w-3.5 h-3.5 text-content-muted" />
            }
          </button>

          {filtersOpen && (
            <div className="mt-2">
              <Filters />
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
