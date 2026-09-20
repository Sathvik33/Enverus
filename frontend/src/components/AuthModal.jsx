import React, { useState } from 'react';
import { X, Lock, Mail, Loader2, Sparkles } from 'lucide-react';
import { signIn, signUp } from '../services/api';

export default function AuthModal({ initialMode = 'signin', onClose, onSuccess }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password.trim()) {
      setError('Please provide both email and password');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    setLoading(true);
    try {
      let data;
      if (mode === 'signup') {
        data = await signUp(email.trim(), password);
      } else {
        data = await signIn(email.trim(), password);
      }
      onSuccess(data.user);
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay animate-fade-in" onClick={onClose}>
      <div className="auth-modal glass-panel-elevated" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose}>
          <X size={18} />
        </button>

        <div className="auth-header">
          <div className="auth-icon-circle">
            <Sparkles size={22} className="text-blue" />
          </div>
          <h2>{mode === 'signup' ? 'Create an Account' : 'Welcome Back'}</h2>
          <p>{mode === 'signup' ? 'Access persistent history and paper analytics' : 'Sign in to access your chat history and uploaded papers'}</p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === 'signin' ? 'active' : ''}`}
            onClick={() => { setMode('signin'); setError(''); }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
            onClick={() => { setMode('signup'); setError(''); }}
          >
            Sign Up
          </button>
        </div>

        {error && (
          <div className="auth-error-banner animate-fade-in">
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label>Email Address</label>
            <div className="input-with-icon">
              <Mail size={16} className="input-icon" />
              <input
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Password</label>
            <div className="input-with-icon">
              <Lock size={16} className="input-icon" />
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {mode === 'signup' && <span className="field-hint">Minimum 6 characters</span>}
          </div>

          <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={loading}>
            {loading ? <Loader2 size={18} className="animate-spin" /> : null}
            <span>{mode === 'signup' ? 'Create Account' : 'Sign In'}</span>
          </button>
        </form>

        <div className="auth-footer">
          {mode === 'signin' ? (
            <p>Don't have an account? <span className="auth-link" onClick={() => setMode('signup')}>Sign up</span></p>
          ) : (
            <p>Already have an account? <span className="auth-link" onClick={() => setMode('signin')}>Sign in</span></p>
          )}
        </div>
      </div>
    </div>
  );
}
