import React, { useState, useRef } from 'react';
import { 
  FileText, Upload, Clock, Trash2, ChevronRight, 
  Layers, Image as ImageIcon, Table as TableIcon, Hash, CheckCircle2, AlertCircle, Loader2
} from 'lucide-react';
import { uploadDocument, clearHistory } from '../services/api';

export default function Sidebar({
  activeDoc,
  documentId,
  setDocumentId,
  onDocumentLoaded,
  onDeleteDocument,
  history,
  onSelectHistory,
  onHistoryCleared,
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
    }
  };

  const handleDocIdSubmit = (e) => {
    e.preventDefault();
    if (docInput.trim()) {
      setDocumentId(docInput.trim());
      if (onDocumentLoaded) onDocumentLoaded(docInput.trim());
      setDocInput('');
    }
  };

  const handleClearHistory = async () => {
    if (!user) return;
    if (window.confirm('Clear all your chat history?')) {
      await clearHistory(user.id);
      if (onHistoryCleared) onHistoryCleared();
    }
  };

  const handleDeleteDoc = async (e) => {
    e.stopPropagation();
    if (!documentId) return;
    const confirmed = window.confirm(
      `Are you sure you want to delete "${activeDoc?.filename || 'this document'}"?\nThis will remove the document and its indexed chunks from the database.`
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      if (onDeleteDocument) {
        await onDeleteDocument(documentId);
      }
    } catch (err) {
      alert(err.message || 'Failed to delete document');
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
            onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
          />
          {uploading ? (
            <div className="upload-loading">
              <Loader2 size={24} className="animate-spin text-blue" />
              <span>Ingesting & Embedding PDF...</span>
            </div>
          ) : (
            <div className="upload-prompt">
              <Upload size={20} className="text-blue" />
              <span><strong>Click to Upload</strong> or drag PDF here</span>
              <span className="upload-hint">Extracts text, tables, and SigLIP images</span>
            </div>
          )}
        </div>
        {uploadError && <div className="field-error">{uploadError}</div>}
      </div>

      <hr className="sidebar-divider" />

      {/* Chat History Section */}
      <div className="sidebar-section history-section">
        <div className="section-label-row">
          <span className="section-label">Chat History</span>
          {user && history.length > 0 && (
            <button 
              className="btn-link text-danger" 
              onClick={handleClearHistory}
              title="Clear all history"
            >
              <Trash2 size={13} />
              <span>Clear</span>
            </button>
          )}
        </div>

        {user ? (
          history.length > 0 ? (
            <div className="history-list">
              {history.map((item) => (
                <div 
                  key={item.id} 
                  className="history-item glass-panel"
                  onClick={() => onSelectHistory(item)}
                >
                  <div className="history-icon">
                    <Clock size={14} className="text-muted" />
                  </div>
                  <div className="history-text">
                    <div className="history-query">{item.query}</div>
                    <div className="history-time">
                      {item.created_at ? new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </div>
                  </div>
                  <ChevronRight size={14} className="history-arrow" />
                </div>
              ))}
            </div>
          ) : (
            <div className="history-empty">
              <Clock size={16} className="text-muted" />
              <p>No questions asked yet. Start querying the active paper!</p>
            </div>
          )
        ) : (
          <div className="history-auth-prompt glass-panel">
            <p>Sign in to save and review past questions and structured evidence.</p>
            <button className="btn btn-primary btn-sm btn-block" onClick={() => onOpenAuth('signin')}>
              Sign In to Save History
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
