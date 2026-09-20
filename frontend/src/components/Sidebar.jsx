import React, { useState, useRef } from 'react';
import { 
  FileText, Upload, Clock, Trash2, ChevronRight, 
  Layers, Image as ImageIcon, Table as TableIcon, Hash, CheckCircle2, AlertCircle, Loader2,
  MessageSquare, MessageSquarePlus
} from 'lucide-react';
import { uploadDocument, clearAllSessions } from '../services/api';

export default function Sidebar({
  activeDoc,
  documentId,
  setDocumentId,
  onDocumentLoaded,
  onDeleteDocument,
  sessions = [],
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onSessionsCleared,
  user,
  onOpenAuth,
}) {
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [docInput, setDocInput] = useState('');
  const fileInputRef = useRef(null);

  const handleFileUpload = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Only PDF documents are supported');
      return;
    }

    setUploading(true);
    setUploadError('');
    try {
      const data = await uploadDocument(file);
      setDocumentId(data.document_id);
      if (onDocumentLoaded) onDocumentLoaded(data.document_id);
    } catch (err) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDocIdSubmit = (e) => {
    e.preventDefault();
    const trimmed = docInput.trim();
    if (!trimmed) return;
    setDocumentId(trimmed);
    if (onDocumentLoaded) onDocumentLoaded(trimmed);
    setDocInput('');
  };

  const handleClearSessions = async () => {
    if (!user) return;
    const confirmClear = window.confirm('Are you sure you want to clear all chat sessions?');
    if (!confirmClear) return;
    try {
      await clearAllSessions(user.id);
      if (onSessionsCleared) onSessionsCleared();
    } catch (err) {
      console.warn('Failed to clear sessions:', err);
    }
  };

  const handleDeleteDoc = async () => {
    if (!documentId) return;
    const confirmDelete = window.confirm(
      'Are you sure you want to delete this document? All vector embeddings and chunks will be permanently removed.'
    );
    if (!confirmDelete) return;

    setDeleting(true);
    try {
      await onDeleteDocument(documentId);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <aside className="workspace-sidebar glass-panel">
      {/* Active Document Status */}
      <div className="sidebar-section">
        <div className="section-label">Active Document</div>
        {activeDoc ? (
          <div className="doc-card glass-panel-elevated">
            <div className="doc-header">
              <div className="doc-icon-wrapper">
                <FileText size={18} className="text-blue" />
              </div>
              <div className="doc-meta">
                <span className="doc-title" title={activeDoc.filename}>
                  {activeDoc.filename || 'Document'}
                </span>
                <span className="doc-id-pill">ID: {String(documentId).slice(0, 8)}...</span>
              </div>
              <button
                type="button"
                className="btn-delete-doc"
                title="Delete Document & Chunks"
                onClick={handleDeleteDoc}
                disabled={deleting}
              >
                {deleting ? <Loader2 size={15} className="animate-spin text-muted" /> : <Trash2 size={15} />}
              </button>
            </div>

            <div className="doc-stats-grid">
              <div className="stat-pill">
                <Hash size={12} />
                <span>{activeDoc.total_pages || activeDoc.page_count || 0} Pages</span>
              </div>
              <div className="stat-pill">
                <Layers size={12} />
                <span>{activeDoc.text_chunks || 0} Chunks</span>
              </div>
              <div className="stat-pill">
                <TableIcon size={12} />
                <span>{activeDoc.table_chunks || 0} Tables</span>
              </div>
              <div className="stat-pill">
                <ImageIcon size={12} />
                <span>{activeDoc.images || 0} Images</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="doc-empty-card">
            <AlertCircle size={18} className="text-muted" />
            <p>No document selected. Upload a PDF or enter an ID below.</p>
          </div>
        )}

        {/* Enter ID */}
        <form onSubmit={handleDocIdSubmit} className="doc-id-form">
          <input
            type="text"
            placeholder="Enter Document ID..."
            value={docInput}
            onChange={(e) => setDocInput(e.target.value)}
          />
          <button type="submit" className="btn btn-secondary btn-sm">Load</button>
        </form>

        {/* Upload Zone */}
        <div 
          className="upload-dropzone" 
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]);
          }}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            accept=".pdf" 
            style={{ display: 'none' }} 
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
            }} 
          />
          {uploading ? (
            <div className="upload-loading">
              <Loader2 className="animate-spin text-blue" size={24} />
              <span>Processing PDF Layout & Vectors...</span>
            </div>
          ) : (
            <div className="upload-prompt">
              <Upload size={20} className="text-muted" />
              <span>Drop research paper (.pdf) or click to upload</span>
            </div>
          )}
        </div>
        {uploadError && <div className="field-error">{uploadError}</div>}
      </div>

      <hr className="sidebar-divider" />

      {/* Chat Sessions Section */}
      <div className="sidebar-section history-section">
        <div className="section-label-row">
          <span className="section-label">Chats</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {user && (
              <button 
                className="btn btn-primary btn-new-chat" 
                onClick={onNewChat}
                title="Start a new isolated chat"
              >
                <MessageSquarePlus size={13} />
                <span>New Chat</span>
              </button>
            )}
            {user && sessions.length > 0 && (
              <button 
                className="btn-link text-danger" 
                onClick={handleClearSessions}
                title="Clear all chats"
              >
                <Trash2 size={13} />
              </button>
            )}
          </div>
        </div>

        {user ? (
          sessions.length > 0 ? (
            <div className="history-list">
              {sessions.map((s) => {
                const isActive = s.id === activeSessionId;
                return (
                  <div 
                    key={s.id} 
                    className={`history-item glass-panel ${isActive ? 'history-item-active' : ''}`}
                    onClick={() => onSelectSession(s)}
                  >
                    <div className="history-icon">
                      <MessageSquare size={14} className={isActive ? 'text-blue' : 'text-muted'} />
                    </div>
                    <div className="history-text">
                      <div className="history-query">{s.title || 'Untitled Chat'}</div>
                      <div className="history-time">
                        {s.updated_at ? new Date(s.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''}
                        {s.message_count ? ` • ${s.message_count} msgs` : ''}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn-delete-session"
                      title="Delete chat"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Delete this chat?')) {
                          onDeleteSession(s.id);
                        }
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="history-empty">
              <MessageSquare size={16} className="text-muted" />
              <p>No chats yet. Start querying the active paper!</p>
              <button className="btn btn-secondary btn-sm" onClick={onNewChat}>
                <MessageSquarePlus size={13} /> Start First Chat
              </button>
            </div>
          )
        ) : (
          <div className="history-auth-prompt glass-panel">
            <p>Sign in to save multiple conversations and prevent context mixing.</p>
            <button className="btn btn-primary btn-sm btn-block" onClick={() => onOpenAuth('signin')}>
              Sign In to Save Chats
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
