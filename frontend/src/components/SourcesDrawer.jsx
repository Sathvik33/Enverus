import React, { useState } from 'react';
import { X, BookOpen, Layers, Sparkles, Image as ImageIcon, ExternalLink, Activity } from 'lucide-react';

export default function SourcesDrawer({ message, onClose }) {
  const [activeTab, setActiveTab] = useState('evidence');
  const [previewImage, setPreviewImage] = useState(null);

  if (!message) return null;

  const citations = message.citations || [];
  const evidence = message.evidence || [];
  const trace = message.trace || {};

  return (
    <div className="sources-modal-backdrop" onClick={onClose}>
      <div className="sources-drawer glass-panel-elevated animate-fade-in" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <BookOpen size={20} className="text-blue" />
            <div>
              <h3>Retrieved Grounding & Sources</h3>
              <p>Audited evidence items and neural retrieval trace</p>
            </div>
          </div>

          <div className="drawer-actions">
            <div className="drawer-tabs">
              <button
                className={`drawer-tab ${activeTab === 'evidence' ? 'active' : ''}`}
                onClick={() => setActiveTab('evidence')}
              >
                Evidence Snippets ({evidence.length})
              </button>
              <button
                className={`drawer-tab ${activeTab === 'citations' ? 'active' : ''}`}
                onClick={() => setActiveTab('citations')}
              >
                Citations ({citations.length})
              </button>
              {trace && Object.keys(trace).length > 0 && (
                <button
                  className={`drawer-tab ${activeTab === 'trace' ? 'active' : ''}`}
                  onClick={() => setActiveTab('trace')}
                >
                  Retrieval Trace
                </button>
              )}
            </div>

            <button className="btn-icon-close" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Drawer Body */}
        <div className="drawer-body">
          {/* Tab 1: Evidence Snippets */}
          {activeTab === 'evidence' && (
            <div className="evidence-tab-content">
              {evidence.length > 0 ? (
                evidence.map((item, idx) => (
                  <div key={idx} className="evidence-card glass-panel">
                    <div className="evidence-card-header">
                      <div className="evidence-card-badges">
                        <span className="badge badge-primary">
                          {item.source_type?.toUpperCase() || 'TEXT'}
                        </span>
                        <span className="badge badge-secondary">
                          Page {item.page_number || '?'}
                        </span>
                        {item.section && (
                          <span className="evidence-section-name">
                            {item.section}
                          </span>
                        )}
                      </div>
                      <span className="evidence-score-pill">
                        Score: <strong>{(item.score || 0).toFixed(4)}</strong>
                      </span>
                    </div>

                    <div className="evidence-card-content">
                      {item.content}
                    </div>

                    {item.source_type === 'image' && item.image_path && (
                      <div className="evidence-image-preview">
                        <img
                          src={`/${item.image_path.replace(/\\/g, '/')}`}
                          alt={item.caption || 'Figure preview'}
                          onClick={() => setPreviewImage(`/${item.image_path.replace(/\\/g, '/')}`)}
                        />
                        {item.caption && <span className="image-caption">{item.caption}</span>}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="drawer-empty-state">
                  <p>No raw evidence attached to this message.</p>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Citations */}
          {activeTab === 'citations' && (
            <div className="citations-tab-content">
              {citations.length > 0 ? (
                <div className="citations-grid">
                  {citations.map((c, i) => (
                    <div key={i} className="citation-card glass-panel">
                      <div className="citation-badge-row">
                        <span className="citation-page-badge">Page {c.page_number}</span>
                        <span className="badge badge-secondary">{c.source_type || 'text'}</span>
                      </div>
                      {c.section && <h4 className="citation-section">{c.section}</h4>}
                      {c.content_preview && (
                        <p className="citation-preview-text">"{c.content_preview}..."</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="drawer-empty-state">
                  <p>No specific citations generated for this response.</p>
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Retrieval Trace */}
          {activeTab === 'trace' && (
            <div className="trace-tab-content">
              <div className="trace-card glass-panel">
                <div className="trace-header">
                  <Activity size={18} className="text-cyan" />
                  <h4>Query Analysis & Modality Routing</h4>
                </div>
                <div className="trace-metrics-grid">
                  <div className="trace-metric">
                    <span className="label">Query Type</span>
                    <span className="val">{trace.query_analysis?.query_type || 'Mixed'}</span>
                  </div>
                  <div className="trace-metric">
                    <span className="label">Needs Text</span>
                    <span className="val">{String(trace.query_analysis?.needs_text ?? true)}</span>
                  </div>
                  <div className="trace-metric">
                    <span className="label">Needs Table</span>
                    <span className="val">{String(trace.query_analysis?.needs_table ?? false)}</span>
                  </div>
                  <div className="trace-metric">
                    <span className="label">Needs Image</span>
                    <span className="val">{String(trace.query_analysis?.needs_image ?? false)}</span>
                  </div>
                </div>
              </div>

              <div className="trace-stages-list">
                <div className="trace-stage-item">
                  <span className="stage-name">Dense Text Vector Search</span>
                  <span className="stage-count">{trace.text_results?.length || 0} candidates</span>
                </div>
                <div className="trace-stage-item">
                  <span className="stage-name">Okapi BM25 Lexical Search</span>
                  <span className="stage-count">{trace.bm25_results?.length || 0} candidates</span>
                </div>
                <div className="trace-stage-item">
                  <span className="stage-name">Atomic Table Search</span>
                  <span className="stage-count">{trace.table_results?.length || 0} candidates</span>
                </div>
                <div className="trace-stage-item">
                  <span className="stage-name">SigLIP Image Vector Search</span>
                  <span className="stage-count">{trace.image_results?.length || 0} candidates</span>
                </div>
                <div className="trace-stage-item">
                  <span className="stage-name">Reciprocal Rank Fusion (RRF)</span>
                  <span className="stage-count">{trace.rrf_results?.length || 0} fused</span>
                </div>
                <div className="trace-stage-item highlight">
                  <span className="stage-name">CrossEncoder Neural Reranking</span>
                  <span className="stage-count">{trace.final_evidence?.length || evidence.length} final selected</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Image Full-Size Modal */}
        {previewImage && (
          <div className="image-zoom-overlay" onClick={() => setPreviewImage(null)}>
            <div className="image-zoom-content" onClick={(e) => e.stopPropagation()}>
              <button className="image-zoom-close" onClick={() => setPreviewImage(null)}>
                <X size={20} />
              </button>
              <img src={previewImage} alt="Expanded preview" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
