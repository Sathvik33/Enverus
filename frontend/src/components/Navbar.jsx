import React from 'react';
import { Sparkles, FileText, User, LogOut, LogIn } from 'lucide-react';

export default function Navbar({ currentView, setCurrentView, user, onOpenAuth, onLogout, activeDoc }) {
  return (
    <header className="navbar">
      <div className="navbar-left">
        <div className="navbar-brand" onClick={() => setCurrentView('landing')}>
          <div className="logo-icon">
            <Sparkles size={20} className="text-blue-400" />
          </div>
          <div className="brand-text">
            <span className="brand-title">Multimodal RAG</span>
          </div>
        </div>

        {activeDoc && currentView === 'workspace' && (
          <div className="active-doc-badge">
            <FileText size={14} />
            <span className="doc-name">{activeDoc.filename || 'Active Document'}</span>
          </div>
        )}
      </div>

      <nav className="navbar-right">
        {currentView === 'landing' ? (
          <button className="btn btn-secondary btn-sm" onClick={() => setCurrentView('workspace')}>
            Open Workspace
          </button>
        ) : (
          <button className="btn btn-secondary btn-sm" onClick={() => setCurrentView('landing')}>
            About Engine
          </button>
        )}

        {user ? (
          <div className="user-profile-menu">
            <div className="user-avatar-pill">
              <User size={15} />
              <span className="user-email">{user.email}</span>
            </div>
            <button className="btn btn-danger btn-sm" onClick={onLogout} title="Sign Out">
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <button className="btn btn-primary btn-sm" onClick={() => onOpenAuth('signin')}>
            <LogIn size={15} />
            <span>Sign In</span>
          </button>
        )}
      </nav>
    </header>
  );
}
