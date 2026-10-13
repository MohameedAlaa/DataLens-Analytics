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
  MessageSquare,
  X,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';

export default function Chatbot({ externalPrompt, isOpenMobile = false, onCloseMobile }) {
  const { messages, sendMessage, resetChat, loading, error } = useChat();
  const { datasetInfo } = useData();
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!externalPrompt) return;
    const timer = setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.value = externalPrompt;
        handleSend();
      }
    }, 50);
    return () => clearTimeout(timer);
  }, [externalPrompt]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, loading]);

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

    questions.push({ text: `Give me an executive summary of ${datasetInfo?.filename || 'the uploaded dataset'}.`, icon: Sparkles });

    if (numCols.length > 0) {
      questions.push({ text: `What are the average, min, and max values of ${numCols[0]}?`, icon: Activity });
    }
    if (numCols.length >= 2) {
      questions.push({ text: `Is there any correlation between ${numCols[0]} and ${numCols[1]}?`, icon: Zap });
    }
    if (catCols.length > 0) {
      questions.push({ text: `How are records distributed across ${catCols[0]}?`, icon: Layers });
    }
    if (dateCols.length > 0) {
      questions.push({ text: `What time trend is visible across ${dateCols[0]}?`, icon: Activity });
    }
    questions.push({ text: `Identify any data quality issues or missing values in this dataset.`, icon: HelpCircle });

    return questions.slice(0, 5);
  }, [datasetInfo]);

  // Quick Action Buttons
  const quickActions = [
    { label: 'Summarize Trends', prompt: 'Summarize the key trends and patterns in this dataset.' },
    { label: 'Find Outliers', prompt: 'Are there any statistical outliers or anomalies in the dataset?' },
    { label: 'Check Quality', prompt: 'Perform a data quality audit and report missing or zero values.' },
  ];

  return (
    <aside
      className={`
        bg-surface-card flex flex-col overflow-hidden border-surface-border transition-all
        ${
          isOpenMobile
            ? 'fixed inset-0 z-50 flex lg:hidden bg-surface-bg'
            : 'hidden lg:flex w-80 xl:w-96 shrink-0 border-l h-[calc(100vh-4rem)] sticky top-16'
        }
      `}
    >
      {/* ── Header ── */}
      <div className="p-3.5 border-b border-surface-border flex items-center justify-between shrink-0 bg-surface-card/80 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-gradient-to-br from-brand-500/20 to-accent-500/20 text-brand-400 border border-brand-500/30 shadow-inner">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h2 className="heading-xs text-content-primary">AI Copilot</h2>
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Gemini 2.5
              </span>
            </div>
            <p className="text-[11px] text-content-muted">Natural Language RAG Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {messages.length > 0 && (
            <button
              onClick={resetChat}
              className="p-1.5 rounded-lg border border-surface-border text-content-muted hover:text-content-primary hover:bg-surface-elevated transition-colors"
              title="Clear Chat History"
              aria-label="Clear Chat History"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          {isOpenMobile && onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="p-1.5 rounded-lg border border-surface-border text-content-muted hover:text-content-primary hover:bg-surface-elevated transition-colors lg:hidden"
              title="Close Copilot"
              aria-label="Close Copilot"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* ── Dataset Context Summary Card ── */}
      {datasetInfo ? (
        <div className="p-3 bg-surface-elevated/40 border-b border-surface-border text-xs space-y-1.5 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <Database className="w-3.5 h-3.5 text-brand-400 shrink-0" />
              <span className="font-semibold text-content-primary truncate">{datasetInfo?.filename || 'Uploaded dataset'}</span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-500/10 text-brand-400 border border-brand-500/20 shrink-0">
              {(datasetInfo?.shape?.[0] ?? 0).toLocaleString()} rows × {datasetInfo?.shape?.[1] ?? 0} cols
            </span>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-content-secondary font-mono">
            <span>{Array.isArray(datasetInfo?.numeric_columns) ? datasetInfo.numeric_columns.length : 0} numeric</span>
            <span>•</span>
            <span>{Array.isArray(datasetInfo?.categorical_columns) ? datasetInfo.categorical_columns.length : 0} categorical</span>
            {Array.isArray(datasetInfo?.date_columns) && datasetInfo.date_columns.length > 0 && (
              <>
                <span>•</span>
                <span>{datasetInfo.date_columns.length} date</span>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="p-3 bg-surface-elevated/20 border-b border-surface-border text-xs text-content-muted flex items-center gap-2">
          <Database className="w-3.5 h-3.5 opacity-50 shrink-0" />
          <span>No dataset context loaded</span>
        </div>
      )}

      {/* ── Main Conversation & Recommendations Scroll Area ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3.5 space-y-4 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl border border-surface-border bg-surface-card/60 text-center space-y-2 shadow-inner">
              <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mx-auto">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-xs font-bold text-content-primary">Conversational Analytics Engine</h3>
              <p className="text-[11px] text-content-secondary leading-relaxed">
                Ask natural-language questions to compute metrics, identify correlations, and extract verifiable insights.
              </p>
            </div>

            {/* Quick Actions */}
            {datasetInfo && (
              <div className="space-y-2">
                <p className="label-caps flex items-center gap-1.5">
                  <Zap className="w-3 h-3 text-brand-400" />
                  Quick Actions
                </p>
                <div className="grid grid-cols-3 gap-1.5">
                  {quickActions.map((act, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        if (inputRef.current) {
                          inputRef.current.value = act.prompt;
                          handleSend();
                        }
                      }}
                      className="p-2 rounded-xl border border-surface-border bg-surface-elevated/50 hover:bg-surface-elevated hover:border-brand-500/30 text-[10px] font-semibold text-content-secondary hover:text-content-primary transition-all text-center"
                    >
                      {act.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Context-aware Suggested Questions */}
            <div className="space-y-2">
              <p className="label-caps flex items-center gap-1.5">
                <HelpCircle className="w-3 h-3 text-brand-400" />
                Suggested Questions
              </p>
              <div className="space-y-1.5">
                {suggestedQuestions.length > 0 ? (
                  suggestedQuestions.map((q, idx) => {
                    const QIcon = q.icon;
                    return (
                      <button
                        key={idx}
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
                  })
                ) : (
                  <p className="text-[11px] text-content-muted text-center py-2">
                    Upload a dataset to generate context-aware questions.
                  </p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Conversation History turns header */}
            <div className="flex items-center justify-between pb-1 border-b border-surface-border/50">
              <span className="label-caps flex items-center gap-1">
                <MessageSquare className="w-3 h-3 text-brand-400" />
                Conversation History ({messages.length} message{messages.length !== 1 ? 's' : ''})
              </span>
            </div>

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`p-3.5 rounded-2xl text-xs leading-relaxed max-w-[92%] shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white rounded-br-none font-medium'
                      : 'bg-surface-card border border-surface-border text-content-primary rounded-tl-none space-y-2'
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
                    <div className="mt-2 p-2.5 rounded-xl bg-brand-500/10 border border-brand-500/25 text-[11px] space-y-1">
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

                  {/* Real Citations Breakdown */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-surface-border/50 text-[10px]">
                      <details className="group/cit">
                        <summary className="text-brand-400 hover:text-brand-300 cursor-pointer flex items-center justify-between font-medium">
                          <span className="flex items-center gap-1">
                            <FileText className="w-3 h-3 text-brand-400" />
                            {msg.citations.length} Verified Citation{msg.citations.length > 1 ? 's' : ''}
                          </span>
                          <ChevronRight className="w-3 h-3 transition-transform group-open/cit:rotate-90" />
                        </summary>
                        <div className="mt-2 space-y-1.5 pl-2 border-l border-brand-500/30 text-[10px] text-content-secondary max-h-40 overflow-y-auto custom-scrollbar">
                          {msg.citations.map((c, cIdx) => (
                            <div key={cIdx} className="bg-surface-elevated/70 p-2 rounded-lg border border-surface-border font-mono">
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

                  {/* Standard Footnote if neither analytics nor citations */}
                  {msg.role === 'assistant' && !msg.analytics && (!msg.citations || msg.citations.length === 0) && (
                    <div className="mt-2 pt-1 border-t border-surface-border/40 text-[10px] text-content-muted flex items-center gap-1">
                      <Bot className="w-3 h-3 text-brand-400" /> Synthesized from dataset context
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-2 p-3 bg-surface-elevated border border-surface-border rounded-2xl rounded-tl-none w-fit body-xs text-content-secondary shadow-sm">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-400" />
            <span>Analyzing dataset with Gemini…</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl body-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="flex-1">{error}</span>
          </div>
        )}
      </div>

      {/* ── Input Area ── */}
      <div className="p-3 border-t border-surface-border shrink-0 bg-surface-card/90">
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            ref={inputRef}
            disabled={loading || !datasetInfo}
            placeholder={datasetInfo ? 'Ask AI Copilot about dataset...' : 'Upload dataset to start querying'}
            aria-label="Ask AI Copilot about dataset"
            className="flex-1 bg-surface-elevated border border-surface-border text-content-primary body-xs rounded-xl px-3 py-2.5 focus:outline-none focus:border-brand-500 placeholder:text-content-muted disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !datasetInfo}
            aria-label="Send message"
            className="btn-primary px-3.5 py-2.5"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </aside>
  );
}
