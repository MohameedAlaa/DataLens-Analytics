import React, { useState, useCallback, useEffect, useRef } from 'react';
import Navbar from './components/Navigation/Navbar';
import Sidebar from './components/Navigation/Sidebar';
import AIInsightsSection from './components/Insights/AIInsightsSection';
import Dashboard from './components/Dashboard/Dashboard';
import Chatbot from './components/Chatbot/Chatbot';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [externalPrompt, setExternalPrompt] = useState(null);
  const isClickNavigating = useRef(false);

  const handlePromptSelect = useCallback((promptText) => {
    setExternalPrompt(promptText);
    setTimeout(() => setExternalPrompt(null), 150);
  }, []);

  // Update active tab based on scroll position
  useEffect(() => {
    const main = document.querySelector('main');
    if (!main) return;
    
    let timeout;
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
      const input = document.querySelector('aside form input');
      if (input) input.focus();
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
      <Navbar activeTab={activeTab} setActiveTab={handleNavClick} />

      {/* 3-Column App Shell */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar activeTab={activeTab} setActiveTab={handleNavClick} />

        {/* Center Main Canvas */}
        <main
          className="flex-1 min-w-0 overflow-y-auto custom-scrollbar
                     px-4 py-5 md:px-6 lg:px-7 space-y-5"
        >
          <div id="overview" className="h-0 w-full" />
          <div id="ai-insights">
            <AIInsightsSection onPromptSelect={handlePromptSelect} />
          </div>
          <Dashboard />
        </main>

        {/* Right AI Copilot Panel */}
        <Chatbot externalPrompt={externalPrompt} />
      </div>
    </div>
  );
}
