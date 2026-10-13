import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useChat } from '../../hooks/useChat';
import { useData } from '../../context/DataContext';
import ReactMarkdown from 'react-markdown';
import {
  Bot,
  Send,
  Trash2,
  Sparkles,
  HelpCircle,
  FileText,
  Database,
  ChevronRight,
  RefreshCw,
  Zap,
  Activity,
  Layers,
  X,
  AlertCircle,
  MessageSquare,
  CornerDownLeft
} from 'lucide-react';

export default function Chatbot({
  isOpen,
  onToggle,
  onClose,
  externalPrompt,
  isOpenMobile, // backward compatibility
  onCloseMobile // backward compatibility
}) {
  const { messages, sendMessage, resetChat, loading, error } = useChat();
  const { datasetInfo } = useData();
  const [internalOpen, setInternalOpen] = useState(false);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);
  const chatPanelRef = useRef(null);

  // Controlled vs uncontrolled open state
  const isChatOpen = isOpen !== undefined ? isOpen : (isOpenMobile !== undefined ? isOpenMobile : internalOpen);
  const handleToggle = onToggle || (() => setInternalOpen((prev) => !prev));
  const handleClose = onClose || onCloseMobile || (() => setInternalOpen(false));

  // Smooth slide in/out transition lifecycle
  const [shouldRender, setShouldRender] = useState(isChatOpen);
  const [isTransitioningIn, setIsTransitioningIn] = useState(false);

  useEffect(() => {
    if (isChatOpen) {
      setShouldRender(true);
      const rAF = requestAnimationFrame(() => {
        setIsTransitioningIn(true);
      });
      return () => cancelAnimationFrame(rAF);
    } else {
      setIsTransitioningIn(false);
      const timer = setTimeout(() => {
        setShouldRender(false);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [isChatOpen]);

  // Auto-send external prompt (e.g. clicked from AI Insights)
  useEffect(() => {
    if (!externalPrompt) return;
    if (!isChatOpen) {
      if (onToggle) onToggle();
      else setInternalOpen(true);
    }
    const timer = setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.value = externalPrompt;
        handleSend();
      }
    }, 120);
    return () => clearTimeout(timer);
  }, [externalPrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    if (isChatOpen && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, loading, isChatOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isChatOpen) {
      const focusTimer = setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 150);
      return () => clearTimeout(focusTimer);
    }
  }, [isChatOpen]);

  // Escape key closes the chat
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isChatOpen) {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isChatOpen, handleClose]);

  const handleSend = async (e) => {
    if (e?.preventDefault) e.preventDefault();
    const text = inputRef.current?.value?.trim();
    if (!text || loading) return;
    inputRef.current.value = '';
    await sendMessage(text);
  };

  // Context-aware dynamic suggested questions
  const suggestedQuestions = useMemo(() => {
    if (!datasetInfo) return [];
    const questions = [];
    const numCols = Array.isArray(datasetInfo?.numeric_columns) ? datasetInfo.numeric_columns : [];
    const catCols = Array.isArray(datasetInfo?.categorical_columns) ? datasetInfo.categorical_columns : [];
    const dateCols = Array.isArray(datasetInfo?.date_columns) ? datasetInfo.date_columns : [];

    questions.push({
      text: `Give me an executive summary of ${datasetInfo?.filename || 'the dataset'}.`,
      icon: Sparkles
    });

    if (numCols.length > 0) {
      questions.push({
        text: `What are the average, min, and max values of ${numCols[0]}?`,
        icon: Activity
      });
    }
    if (numCols.length >= 2) {
      questions.push({
        text: `Is there any correlation between ${numCols[0]} and ${numCols[1]}?`,
        icon: Zap
      });
    } else if (catCols.length > 0) {
      questions.push({
        text: `How are records distributed across ${catCols[0]}?`,
        icon: Layers
      });
    }

    if (dateCols.length > 0) {
      questions.push({
        text: `What trend is visible across ${dateCols[0]}?`,
        icon: Activity
      });
    }

    return questions.slice(0, 4);
  }, [datasetInfo]);

  return (
    <>
      {/* ── Persistent Floating AI Copilot Trigger Button ──────────────── */}
      <div className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-40">
        <button
          type="button"
          onClick={handleToggle}
          aria-expanded={isChatOpen}
          aria-label="Toggle AI Copilot"
          title="AI Copilot (Gemini 2.5)"
          className={`
            relative group flex items-center justify-center
            w-12 h-12 sm:w-13 sm:h-13 rounded-2xl
            border transition-all duration-200 shadow-xl
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-bg
            ${isChatOpen
              ? 'bg-brand-400 text-[#111215] border-brand-300 shadow-glow-brand rotate-0 scale-95'
              : 'bg-surface-card/90 backdrop-blur-md text-brand-400 border-surface-border hover:border-brand-500/40 hover:bg-surface-elevated hover:scale-105 hover:shadow-glow-subtle'
            }
          `}
        >
          <div className="relative flex items-center justify-center">
            {isChatOpen ? (
              <X className="w-5 h-5 text-[#111215] transition-transform duration-200" />
            ) : (
              <Bot className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
            )}
            {/* Live status dot */}
            <span
              className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-brand-400 border-2 border-surface-card"
              title="Gemini 2.5 Online"
              aria-hidden="true"
            />
          </div>

          {/* Hover Tooltip */}
          {!isChatOpen && (
            <span
              className="pointer-events-none absolute right-full mr-3 px-3 py-1.5 rounded-xl
                         bg-surface-card/95 backdrop-blur-md border border-surface-border text-xs font-medium text-content-primary
                         shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 hidden sm:flex items-center gap-1.5"
            >
              <span>AI Copilot</span>
              <span className="w-1 h-1 rounded-full bg-content-muted" />
              <span className="text-[10px] text-brand-400 font-mono font-semibold">Gemini 2.5</span>
            </span>
          )}
        </button>
      </div>

      {/* ── Floating Chat Panel ────────────────────────────────────────── */}
      {shouldRender && (
        <div
          ref={chatPanelRef}
          role="dialog"
          aria-label="DataLens AI Copilot"
          className={`
            fixed z-50 flex flex-col overflow-hidden
            inset-x-3 bottom-20 top-20 sm:inset-auto sm:bottom-22 sm:right-6
            sm:w-[410px] sm:h-[580px] sm:max-h-[calc(100vh-7.5rem)]
            bg-surface-card/95 backdrop-blur-xl border border-surface-border
            rounded-2xl sm:rounded-3xl shadow-2xl
            transition-all duration-200 ease-out motion-reduce:transition-none
            ${isTransitioningIn
              ? 'opacity-100 translate-y-0 scale-100'
              : 'opacity-0 translate-y-3 sm:translate-y-4 scale-[0.97] pointer-events-none'
            }
          `}
        >
          {/* ── Header ── */}
          <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between shrink-0 bg-surface-card/80 backdrop-blur-sm">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="p-1.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/25 shrink-0 shadow-inner">
                <Bot className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-xs font-bold text-content-primary tracking-tight">AI Copilot</h2>
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded-full text-[9px] font-mono font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
                    Gemini 2.5
                  </span>
                </div>
                <p className="text-[10px] text-content-muted truncate">
                  {datasetInfo ? datasetInfo.filename : 'Upload a dataset to query'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1 shrink-0">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={resetChat}
                  className="p-1.5 rounded-lg border border-surface-border text-content-muted hover:text-content-primary hover:bg-surface-elevated transition-colors"
                  title="Clear chat history"
                  aria-label="Clear chat history"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                type="button"
                onClick={handleClose}
                className="p-1.5 rounded-lg border border-surface-border text-content-muted hover:text-content-primary hover:bg-surface-elevated transition-colors"
                title="Close AI Copilot"
                aria-label="Close AI Copilot"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* ── Context Info Pill (When dataset is loaded) ── */}
          {datasetInfo && (
            <div className="px-3.5 py-1.5 bg-surface-elevated/40 border-b border-surface-border/60 flex items-center justify-between text-[10px] font-mono text-content-secondary shrink-0">
              <span className="flex items-center gap-1.5 truncate">
                <Database className="w-3 h-3 text-brand-400 shrink-0" />
                <span className="truncate">{datasetInfo.filename}</span>
              </span>
              <span className="text-content-muted shrink-0 ml-2">
                {(datasetInfo.shape?.[0] ?? 0).toLocaleString()} rows • {datasetInfo.shape?.[1] ?? 0} cols
              </span>
            </div>
          )}

          {/* ── Messages & Scrollable Area ── */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-3.5 custom-scrollbar"
          >
            {messages.length === 0 ? (
              /* Compact, Elegant Empty State */
              <div className="py-6 px-2 space-y-4 text-center">
                <div className="w-10 h-10 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mx-auto shadow-inner">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-xs font-bold text-content-primary">Ask anything about your data</h3>
                  <p className="text-[11px] text-content-secondary leading-relaxed max-w-[280px] mx-auto">
                    Compute metrics, analyze distributions, detect outliers, and discover patterns.
                  </p>
                </div>

                {/* Contextual Suggested Questions Chips */}
                {suggestedQuestions.length > 0 && (
                  <div className="pt-2 space-y-1.5 text-left">
                    <p className="text-[10px] font-semibold text-content-muted uppercase tracking-wider px-1">
                      Suggested Questions
                    </p>
                    <div className="space-y-1.5">
                      {suggestedQuestions.map((q, idx) => {
                        const QIcon = q.icon;
                        return (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              if (inputRef.current) {
                                inputRef.current.value = q.text;
                                handleSend();
                              }
                            }}
                            className="w-full text-left p-2.5 rounded-xl border border-surface-border bg-surface-elevated/40 hover:bg-surface-elevated hover:border-brand-500/30 transition-all flex items-start gap-2.5 group"
                          >
                            <QIcon className="w-3.5 h-3.5 text-brand-400 shrink-0 mt-0.5" />
                            <span className="text-[11px] text-content-secondary group-hover:text-content-primary transition-colors flex-1 leading-snug">
                              {q.text}
                            </span>
                            <ChevronRight className="w-3.5 h-3.5 text-content-muted group-hover:text-brand-400 transition-colors shrink-0 mt-0.5" />
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Conversation Messages */
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`p-3 rounded-2xl text-xs leading-relaxed max-w-[90%] shadow-sm ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white rounded-br-none font-medium'
                        : 'bg-surface-elevated/90 border border-surface-border text-content-primary rounded-tl-none space-y-2'
                    }`}
                  >
                    <ReactMarkdown
                      components={{
                        p: ({ node, ...props }) => <p className="mb-1.5 last:mb-0 leading-relaxed" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc pl-4 space-y-1 my-1" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal pl-4 space-y-1 my-1" {...props} />,
                        li: ({ node, ...props }) => <li className="text-[11px]" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-bold text-brand-300" {...props} />,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>

                    {/* Deterministic Analytics Badge */}
                    {msg.analytics && (
                      <div className="mt-2 p-2 rounded-xl bg-brand-500/10 border border-brand-500/25 text-[11px] space-y-1">
                        <div className="flex items-center justify-between text-brand-400 font-bold uppercase tracking-wider text-[10px]">
                          <span className="flex items-center gap-1">
                            <Zap className="w-3 h-3 text-brand-400" /> Deterministic Analytics
                          </span>
                          <span className="font-mono">{msg.analytics.operation || 'Calculation'}</span>
                        </div>
                        <div className="text-content-primary font-mono font-semibold">
                          {msg.analytics.group_value ? `${msg.analytics.group_value}: ` : ''}
                          {typeof msg.analytics.value === 'number'
                            ? msg.analytics.value.toLocaleString()
                            : String(msg.analytics.value ?? '')}
                          {msg.analytics.column ? ` (${msg.analytics.column})` : ''}
                        </div>
                      </div>
                    )}

                    {/* Verifiable Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-surface-border/50 text-[10px]">
                        <details className="group/cit">
                          <summary className="text-brand-400 hover:text-brand-300 cursor-pointer flex items-center justify-between font-medium select-none">
                            <span className="flex items-center gap-1">
                              <FileText className="w-3 h-3 text-brand-400" />
                              {msg.citations.length} Verified Citation{msg.citations.length > 1 ? 's' : ''}
                            </span>
                            <ChevronRight className="w-3 h-3 transition-transform group-open/cit:rotate-90" />
                          </summary>
                          <div className="mt-2 space-y-1.5 pl-2 border-l border-brand-500/30 text-[10px] text-content-secondary max-h-36 overflow-y-auto custom-scrollbar">
                            {msg.citations.map((c, cIdx) => (
                              <div key={cIdx} className="bg-surface-card p-2 rounded-lg border border-surface-border font-mono">
                                <span className="font-semibold text-brand-300">
                                  Row {c.row_index ?? cIdx + 1}:
                                </span>{' '}
                                <span className="text-content-secondary">{c.snippet || JSON.stringify(c)}</span>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}

                    {/* Footnote */}
                    {msg.role === 'assistant' && !msg.analytics && (!msg.citations || msg.citations.length === 0) && (
                      <div className="mt-1.5 pt-1 border-t border-surface-border/40 text-[9px] text-content-muted flex items-center gap-1">
                        <Bot className="w-3 h-3 text-brand-400" /> Synthesized from dataset context
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Loading Indicator */}
            {loading && (
              <div className="flex items-center gap-2 p-3 bg-surface-elevated border border-surface-border rounded-2xl rounded-tl-none w-fit text-xs text-content-secondary shadow-sm animate-pulse">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-400" />
                <span>Analyzing dataset with Gemini…</span>
              </div>
            )}

            {/* Error Banner */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span className="flex-1">{error}</span>
              </div>
            )}
          </div>

          {/* ── Fixed Bottom Input Form ── */}
          <div className="p-3 border-t border-surface-border bg-surface-card/90 shrink-0">
            <form onSubmit={handleSend} className="relative flex items-center">
              <input
                ref={inputRef}
                type="text"
                disabled={loading || !datasetInfo}
                placeholder={datasetInfo ? 'Ask AI Copilot about dataset...' : 'Upload dataset to start querying'}
                aria-label="Ask AI Copilot about dataset"
                className="w-full bg-surface-elevated border border-surface-border text-content-primary text-xs rounded-xl pl-3 pr-10 py-2.5 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 placeholder:text-content-muted disabled:opacity-50 transition-colors"
              />
              <button
                type="submit"
                disabled={loading || !datasetInfo}
                aria-label="Send message"
                className="absolute right-1.5 p-1.5 rounded-lg bg-brand-400 text-[#111215] hover:bg-brand-500 active:scale-95 disabled:opacity-40 transition-all"
              >
                {loading ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
