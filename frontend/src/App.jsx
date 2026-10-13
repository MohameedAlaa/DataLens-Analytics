import React, { useState, useCallback, useEffect, useRef, lazy, Suspense } from 'react';
import Navbar from './components/Navigation/Navbar';
import Sidebar from './components/Navigation/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import WorkspaceHero from './components/Upload/WorkspaceHero';
import { useData } from './context/DataContext';

const AIInsightsSection = lazy(() => import('./components/Insights/AIInsightsSection'));
const Dashboard = lazy(() => import('./components/Dashboard/Dashboard'));
const Chatbot = lazy(() => import('./components/Chatbot/Chatbot'));

function SectionLoadingFallback({ title, height = 'h-36' }) {
  return (
    <div
      className={`p-5 rounded-2xl border border-surface-border bg-surface-card/50
                 flex items-center justify-center ${height} animate-pulse`}
      aria-busy="true"
      aria-label={`Loading ${title}`}
    >
      <span className="body-xs text-content-muted">{title ? `Loading ${title}...` : 'Loading...'}</span>
    </div>
  );
}

function CopilotLoadingFallback() {
  return (
    <aside
      className="w-80 lg:w-96 border-l border-surface-border bg-surface-card/40
                 items-center justify-center p-6 animate-pulse hidden lg:flex"
      aria-busy="true"
      aria-label="Loading AI Copilot"
    >
      <span className="body-xs text-content-muted">Loading AI Copilot...</span>
    </aside>
  );
}

export default function App() {
  const { datasetInfo } = useData();
  const [activeTab, setActiveTab] = useState('overview');
  const [externalPrompt, setExternalPrompt] = useState(null);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isMobileCopilotOpen, setIsMobileCopilotOpen] = useState(false);
  const isClickNavigating = useRef(false);
  const promptTimerRef = useRef(null);

  const handlePromptSelect = useCallback((promptText) => {
    setExternalPrompt(promptText);
    // Auto-open Copilot on mobile if prompt selected from AI Insights
    if (window.innerWidth < 1024) {
      setIsMobileCopilotOpen(true);
    }
    if (promptTimerRef.current) clearTimeout(promptTimerRef.current);
    promptTimerRef.current = setTimeout(() => setExternalPrompt(null), 150);
  }, []);

  useEffect(() => {
    return () => {
      if (promptTimerRef.current) clearTimeout(promptTimerRef.current);
    };
  }, []);

  // Update active tab based on scroll position
  useEffect(() => {
    const main = document.querySelector('main');
    if (!main) return;
    
    const handleScroll = () => {
      if (isClickNavigating.current) return;
      
      // If at bottom
      if (Math.abs(main.scrollHeight - main.clientHeight - main.scrollTop) < 10) {
        setActiveTab('dataset');
        return;
      }

      const sections = ['overview', 'ai-insights', 'analytics', 'visualizations', 'dataset'];
      const mainRect = main.getBoundingClientRect();
      let current = sections[0];
      
      for (const id of sections) {
        const el = document.getElementById(id);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= mainRect.top + 150) {
            current = id;
          }
        }
      }
      
      setActiveTab((prev) => {
        if (prev === 'copilot') return prev; // Preserve copilot active state
        return current;
      });
    };

    main.addEventListener('scroll', handleScroll, { passive: true });
    return () => main.removeEventListener('scroll', handleScroll);
  }, []);

  // Handle smooth scroll when a sidebar item is clicked
  const handleNavClick = useCallback((id) => {
    setActiveTab(id);
    if (id === 'copilot') {
      if (window.innerWidth < 1024) {
        setIsMobileCopilotOpen(true);
      } else {
        const input = document.querySelector('aside form input');
        if (input) input.focus();
      }
      return;
    }
    
    const el = document.getElementById(id);
    if (el) {
      isClickNavigating.current = true;
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // Re-enable scroll spy after smooth scroll duration
      setTimeout(() => {
        isClickNavigating.current = false;
      }, 800);
    }
  }, []);

  return (
    <div className="min-h-screen bg-surface-bg text-content-primary flex flex-col font-sans">
      {/* Top Application Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={handleNavClick}
        onToggleMobileSidebar={() => setIsMobileSidebarOpen(prev => !prev)}
        onToggleMobileCopilot={() => setIsMobileCopilotOpen(prev => !prev)}
      />

      {/* 3-Column App Shell */}
      <div className="flex flex-1 min-h-0 overflow-hidden relative">
        {/* Left Sidebar (Desktop + Mobile Drawer) */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={handleNavClick}
          isOpenMobile={isMobileSidebarOpen}
          onCloseMobile={() => setIsMobileSidebarOpen(false)}
        />

        {/* Center Main Canvas */}
        <main
          className="flex-1 min-w-0 overflow-y-auto custom-scrollbar
                     px-4 py-5 md:px-6 lg:px-7 space-y-5"
        >
          {!datasetInfo ? (
            <WorkspaceHero />
          ) : (
            <>
              <div id="overview" className="h-0 w-full" />
              <div id="ai-insights">
                <ErrorBoundary title="AI Insights Section">
                  <Suspense fallback={<SectionLoadingFallback title="AI Insights" height="h-28" />}>
                    <AIInsightsSection onPromptSelect={handlePromptSelect} />
                  </Suspense>
                </ErrorBoundary>
              </div>
              <ErrorBoundary title="Analytics Dashboard">
                <Suspense fallback={<SectionLoadingFallback title="Dashboard" height="h-64" />}>
                  <Dashboard />
                </Suspense>
              </ErrorBoundary>
            </>
          )}
        </main>

        {/* Right AI Copilot Panel (Desktop + Mobile Drawer) */}
        <ErrorBoundary title="AI Copilot">
          <Suspense fallback={<CopilotLoadingFallback />}>
            <Chatbot
              externalPrompt={externalPrompt}
              isOpenMobile={isMobileCopilotOpen}
              onCloseMobile={() => setIsMobileCopilotOpen(false)}
            />
          </Suspense>
        </ErrorBoundary>
      </div>
    </div>
  );
}
