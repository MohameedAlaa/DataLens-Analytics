import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../hooks/useChat';
import { useData } from '../../context/DataContext';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { 
  Send, 
  X, 
  MessageSquare, 
  Trash2, 
  Bot, 
  User, 
  Sparkles,
  ChevronRight
} from 'lucide-react';

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const { messages, sendMessage, resetChat, loading, error } = useChat();
  const { datasetInfo } = useData();
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

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

  const suggestions = [];
  if (datasetInfo) {
    const cat = datasetInfo.categorical_columns?.[0];
    const num = datasetInfo.numeric_columns?.[0];
    if (cat) suggestions.push(`What are the top 5 values in ${cat}?`);
    if (num) suggestions.push(`What is the average of ${num}?`);
    suggestions.push('Summarize this dataset');
  }

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-xl shadow-cyan-500/25 transition-all hover:scale-110 z-50"
            onClick={() => setOpen(true)}
            aria-label="Open DataLens Assistant"
          >
            <MessageSquare size={24} fill="currentColor" />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ y: '100%', opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed bottom-6 right-6 w-[calc(100vw-3rem)] max-w-[400px] h-[600px] max-h-[calc(100vh-6rem)] bg-[#1A202C] rounded-[2rem] shadow-2xl z-50 flex flex-col overflow-hidden border border-slate-700/50"
          >
            {/* Header */}
            <header className="flex items-start justify-between gap-4 p-6 pb-2">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-3xl bg-slate-900/80 text-cyan-300 shadow-inner shadow-cyan-500/10">
                  <Sparkles size={20} />
                </div>
                <div>
                  <p className="text-slate-300 text-sm uppercase tracking-[0.35em]">DataLens Assistant</p>
                  <p className="mt-2 text-sm text-slate-400">Instant analytics guidance for your dataset.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {messages.length > 0 && (
                  <button
                    onClick={resetChat}
                    className="rounded-2xl border border-slate-700/70 bg-slate-900/70 px-3 py-2 text-xs text-slate-300 transition-colors hover:bg-slate-800"
                  >
                    <Trash2 size={14} className="inline-block mr-2" />
                    Clear
                  </button>
                )}
                <button
                  onClick={() => setOpen(false)}
                  className="rounded-2xl border border-slate-700/70 bg-slate-900/70 p-2 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
                  aria-label="Close assistant"
                >
                  <X size={20} />
                </button>
              </div>
            </header>

            {/* Chat Area */}
            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-6 space-y-4 scroll-smooth custom-scrollbar"
            >
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center space-y-6 opacity-90">
                  <Bot size={44} className="text-cyan-400" />
                  <div className="space-y-2">
                    <p className="text-lg font-semibold text-slate-100">Ready to analyze your dataset</p>
                    <p className="max-w-sm text-sm text-slate-400">Ask about trends, averages, top values, or request a concise summary.</p>
                  </div>
                  <div className="grid gap-3 px-4 w-full">
                    {suggestions.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          inputRef.current.value = s;
                          handleSend();
                        }}
                        className="w-full rounded-3xl border border-slate-700/60 bg-slate-900/80 px-4 py-3 text-left text-sm text-slate-200 transition hover:border-cyan-400/40 hover:bg-slate-800"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, idx) => (
                <motion.div
                  key={idx}
                  initial={{ y: 10, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  className={`flex ${msg.role === 'assistant' ? 'justify-start' : 'justify-end'}`}
                >
                  <div className={`px-5 py-4 rounded-[1.75rem] text-sm leading-relaxed max-w-[85%] shadow-sm ${
                    msg.role === 'assistant'
                      ? 'bg-slate-900/90 text-slate-100 ring-1 ring-slate-700/50 rounded-tl-none'
                      : 'bg-gradient-to-r from-emerald-400 to-cyan-300 text-slate-950 font-semibold rounded-br-none'
                  }`}>
                    <ReactMarkdown className="prose prose-invert prose-sm max-w-none">
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </motion.div>
              ))}

              {loading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                  <div className="px-5 py-3 bg-[#2D3748] rounded-[1.75rem] rounded-tl-none flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
                  </div>
                </motion.div>
              )}

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-xs text-center">
                  {error}
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="p-6 pt-2">
              <form onSubmit={(e)=>{e.preventDefault(); handleSend();}} className="flex gap-3">
                <div className="relative flex-1">
                  <input
                    ref={inputRef}
                    disabled={loading || !datasetInfo}
                    placeholder={datasetInfo ? 'Ask about insights, averages, trends, or categories...' : 'Upload a dataset first to start querying'}
                    className="w-full bg-slate-900/90 border border-slate-800 text-slate-100 text-sm rounded-[1.5rem] px-5 py-4 focus:outline-none focus:ring-2 focus:ring-cyan-400/40 transition-all placeholder:text-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={loading || !datasetInfo}
                  className={`inline-flex items-center gap-2 whitespace-nowrap rounded-[1.5rem] border border-cyan-400/20 px-5 py-3 text-sm font-semibold transition-all ${
                    loading || !datasetInfo
                      ? 'bg-slate-800 text-slate-500 border-slate-700'
                      : 'bg-gradient-to-r from-cyan-400 to-sky-500 text-slate-950 shadow-lg shadow-cyan-500/20 hover:scale-[1.01]'
                  }`}
                >
                  {loading ? 'Sending...' : <><Send size={16} /> Send</>}
                </button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

