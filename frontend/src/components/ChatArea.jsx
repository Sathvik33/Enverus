import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, BookOpen, Copy, Check, Bot, User as UserIcon, Loader2, ArrowUpRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const STARTER_PROMPTS = [
  'Summarize the core methodology and main conclusions of this document.',
  'What do the figures and architectural diagrams illustrate?',
  'Extract the key performance metrics and quantitative data from the tables.',
  'What are the primary findings and experimental results?',
];

export default function ChatArea({
  messages,
  onSendMessage,
  loading,
  documentId,
  onOpenSources,
}) {
  const [input, setInput] = useState('');
  const [copiedIdx, setCopiedIdx] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <main className="chat-main-area">
      {/* Messages Scroll Container */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="chat-welcome-card glass-panel animate-fade-in">
            <div className="welcome-icon-circle">
              <Sparkles size={28} className="text-blue" />
            </div>
            <h2>Multimodal Paper Intelligence</h2>
            <p>
              Ask any factual, quantitative, table-oriented, or visual question about the active paper.
              Answers are strictly grounded with neural citations.
            </p>

            <div className="starters-section">
              <span className="starters-label">Try asking:</span>
              <div className="starters-grid">
                {STARTER_PROMPTS.map((prompt, i) => (
                  <button
                    key={i}
                    className="starter-btn glass-panel-elevated"
                    onClick={() => onSendMessage(prompt)}
                  >
                    <span>{prompt}</span>
                    <ArrowUpRight size={14} className="starter-icon" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`chat-message-wrapper ${msg.role === 'user' ? 'user' : 'assistant'} animate-fade-in`}
              >
                <div className="message-avatar">
                  {msg.role === 'user' ? (
                    <div className="avatar user-avatar">
                      <UserIcon size={16} />
                    </div>
                  ) : (
                    <div className="avatar bot-avatar">
                      <Bot size={16} />
                    </div>
                  )}
                </div>

                <div className="message-bubble glass-panel-elevated">
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                        {msg.isStreaming && <span className="streaming-cursor">▍</span>}
                      </>
                    ) : (
                      msg.content
                    )}
                  </div>

                  {msg.role === 'assistant' && (
                    <div className="message-actions-bar">
                      {(msg.citations?.length > 0 || msg.evidence?.length > 0) && (
                        <button
                          className="btn-action-source"
                          onClick={() => onOpenSources(msg)}
                          title="View verified citations and retrieved evidence"
                        >
                          <BookOpen size={14} />
                          <span>Sources ({msg.citations?.length || msg.evidence?.length || 0})</span>
                        </button>
                      )}

                      <button
                        className="btn-action-icon"
                        onClick={() => handleCopy(msg.content, idx)}
                        title="Copy Answer"
                      >
                        {copiedIdx === idx ? <Check size={14} className="text-emerald" /> : <Copy size={14} />}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="chat-message-wrapper assistant animate-fade-in">
                <div className="message-avatar">
                  <div className="avatar bot-avatar">
                    <Bot size={16} />
                  </div>
                </div>
                <div className="message-bubble glass-panel-elevated loading-bubble">
                  <div className="loading-dots">
                    <Loader2 size={16} className="animate-spin text-blue" />
                    <span>Searching multimodal embeddings & generating structured answer...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="chat-input-wrapper">
        <form onSubmit={handleSubmit} className="chat-input-form glass-panel-elevated">
          <textarea
            rows={1}
            placeholder={documentId ? "Ask a question about this research paper..." : "Load or upload a paper first..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading || !documentId}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!input.trim() || loading || !documentId}
            title="Send (Enter)"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </form>
        <div className="input-subtext">
          <span>Press <strong>Enter</strong> to submit • Responses strictly grounded in research paper evidence</span>
        </div>
      </div>
    </main>
  );
}
