import React from 'react';
import { ArrowRight, Layers, Cpu, Eye, ShieldCheck, Database, CheckCircle2 } from 'lucide-react';

export default function LandingPage({ onLaunchApp, onOpenAuth, user }) {
  const features = [
    {
      icon: <Eye className="text-cyan" size={24} />,
      title: 'Multimodal Vision & Text',
      desc: 'High-fidelity multimodal representation utilizing Google SigLIP (768-dim) for diagrams/figures and MPNet for academic prose.',
    },
    {
      icon: <Layers className="text-blue" size={24} />,
      title: 'Hybrid RRF Fusion',
      desc: 'Combines dense semantic search, Okapi BM25 lexical matching, and specialized table extractors with Reciprocal Rank Fusion.',
    },
    {
      icon: <Cpu className="text-purple" size={24} />,
      title: 'CrossEncoder Reranking',
      desc: 'Precision MS-MARCO neural cross-attention scores top candidates with figure/table caption preservation.',
    },
    {
      icon: <ShieldCheck className="text-emerald" size={24} />,
      title: 'Strict Evidence Grounding',
      desc: 'Double-guardrail architecture detects PII, audits grounding ratios, and enforces strict factual attribution.',
    },
  ];

  return (
    <div className="landing-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-badge animate-fade-in">
          <span className="badge-dot"></span>
          <span>Multimodal RAG • Text, Images, Tables & Charts</span>
        </div>

        <h1 className="hero-title animate-fade-in">
          Deep Multimodal Intelligence, <br />
          <span className="gradient-text">Grounded in Evidence.</span>
        </h1>

        <p className="hero-subtitle animate-fade-in">
          Query complex documents across dense text, structured data tables, and visual charts or figures.
          Get structured metrics, direct answers, and on-demand citations.
        </p>

        <div className="hero-actions animate-fade-in">
          <button className="btn btn-primary btn-lg" onClick={onLaunchApp}>
            <span>Launch Workspace</span>
            <ArrowRight size={18} />
          </button>
          {!user && (
            <button className="btn btn-secondary btn-lg" onClick={() => onOpenAuth('signup')}>
              Create Free Account
            </button>
          )}
        </div>

        {/* Live Architecture Teaser Card */}
        <div className="hero-preview-card glass-panel-elevated animate-fade-in">
          <div className="preview-header">
            <div className="window-dots">
              <span className="dot red"></span>
              <span className="dot yellow"></span>
              <span className="dot green"></span>
            </div>
            <span className="preview-label">Live Multimodal RAG Execution</span>
            <span className="preview-status">Ollama qwen2.5:7b • CUDA</span>
          </div>
          <div className="preview-body">
            <div className="preview-query">
              <span className="tag">QUERY</span>
              <span>"What are the key findings comparing the models in Table 2 and Figure 4?"</span>
            </div>
            <div className="preview-response">
              <span className="tag tag-success">STRUCTURED ANSWER</span>
              <p>
                The multimodal pipeline synthesizes structured metrics from <strong>Table 2</strong> alongside visual trend data from <strong>Figure 4</strong>:
              </p>
              <div className="preview-bullets">
                <div>• <strong>Structured Data Extraction:</strong> High-precision parsing of tabular cells, headers, and statistical values <span className="citation-pill">Table 2</span></div>
                <div>• <strong>Visual Representation:</strong> SigLIP embeddings index charts, flowcharts, and architecture diagrams <span className="citation-pill">Figure 4</span></div>
                <div>• <strong>Strict Attribution:</strong> Every answer is grounded directly in document passages with verifiable source links.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="features-section">
        <div className="section-header">
          <h2>Engineered for Scientific Accuracy</h2>
          <p>Overcoming hallucinations with multimodal hybrid retrieval and verified citations.</p>
        </div>

        <div className="features-grid">
          {features.map((f, i) => (
            <div key={i} className="feature-card glass-panel">
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Database & Specs Banner */}
      <section className="specs-banner glass-panel">
        <div className="specs-item">
          <Database size={24} className="text-blue" />
          <div>
            <h4>pgvector Storage</h4>
            <p>768-dim HNSW Cosine Index on Neon PostgreSQL</p>
          </div>
        </div>
        <div className="specs-item">
          <CheckCircle2 size={24} className="text-emerald" />
          <div>
            <h4>Deterministic Grounding</h4>
            <p>Direct page, section, and table attribution</p>
          </div>
        </div>
        <div className="specs-item">
          <Layers size={24} className="text-cyan" />
          <div>
            <h4>On-Demand Evidence</h4>
            <p>Inspect snippets, raw images, and retrieval traces</p>
          </div>
        </div>
      </section>
    </div>
  );
}
