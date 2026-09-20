const API_BASE = '/api';

export const authStorage = {
  getToken: () => localStorage.getItem('token'),
  getUser: () => {
    const raw = localStorage.getItem('user');
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  getExpiresAt: () => localStorage.getItem('expires_at'),
  isExpired: () => {
    const exp = localStorage.getItem('expires_at');
    if (!exp) return true;
    return new Date(exp).getTime() <= Date.now();
  },
  setAuth: (data) => {
    if (data.token) localStorage.setItem('token', data.token);
    if (data.user) localStorage.setItem('user', JSON.stringify(data.user));
    if (data.expires_at) localStorage.setItem('expires_at', data.expires_at);
  },
  clear: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('expires_at');
  },
};

const authHeaders = () => {
  const token = authStorage.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export async function signUp(email, password) {
  const resp = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || 'Sign up failed');
  authStorage.setAuth(data);
  return data;
}

export async function signIn(email, password) {
  const resp = await fetch(`${API_BASE}/auth/signin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || 'Sign in failed');
  authStorage.setAuth(data);
  return data;
}

export async function fetchMe() {
  if (authStorage.isExpired()) {
    authStorage.clear();
    return null;
  }
  try {
    const resp = await fetch(`${API_BASE}/auth/me`, {
      headers: authHeaders(),
    });
    if (!resp.ok) {
      authStorage.clear();
      return null;
    }
    return await resp.json();
  } catch {
    return null;
  }
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || 'Upload failed');
  return data;
}

export async function getDocument(documentId) {
  const resp = await fetch(`${API_BASE}/documents/${documentId}`);
  if (!resp.ok) throw new Error('Document not found');
  return await resp.json();
}

export async function deleteDocument(documentId) {
  const resp = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to delete document');
  }
  return await resp.json();
}

export async function sendChat(documentId, query, userId = null) {
  const payload = { document_id: documentId, query };
  if (userId) payload.user_id = userId;

  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || 'Chat query failed');
  return data;
}

export async function sendChatStream(
  documentId,
  query,
  userId = null,
  sessionId = null,
  { onMetadata, onToken, onDone, onError }
) {
  const payload = { document_id: documentId, query };
  if (userId) payload.user_id = userId;
  if (sessionId) payload.session_id = sessionId;

  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Streaming failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;
        const jsonStr = trimmed.slice(5).trim();
        if (!jsonStr) continue;

        try {
          const evt = JSON.parse(jsonStr);
          if (evt.type === 'metadata' && onMetadata) {
            onMetadata(evt);
          } else if (evt.type === 'token' && onToken) {
            onToken(evt.token);
          } else if (evt.type === 'done' && onDone) {
            onDone(evt);
          } else if (evt.type === 'error' && onError) {
            onError(new Error(evt.error || 'Stream error'));
          }
        } catch (parseErr) {
          console.error('SSE parse error:', parseErr, jsonStr);
        }
      }
    }
  } catch (err) {
    if (onError) onError(err);
    else throw err;
  }
}

export async function getSessions(userId) {
  if (!userId) return [];
  try {
    const resp = await fetch(`${API_BASE}/sessions?user_id=${userId}`, {
      headers: authHeaders(),
    });
    if (!resp.ok) return [];
    return await resp.json();
  } catch {
    return [];
  }
}

export async function getSessionDetail(sessionId) {
  if (!sessionId) return null;
  try {
    const resp = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      headers: authHeaders(),
    });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

export async function createSession(documentId, userId, title = "New Chat") {
  const resp = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({ document_id: documentId, user_id: userId, title }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create chat session');
  }
  return await resp.json();
}

export async function deleteSession(sessionId) {
  if (!sessionId) return;
  await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
}

export async function clearAllSessions(userId) {
  if (!userId) return;
  await fetch(`${API_BASE}/sessions?user_id=${userId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
}

export async function getHistory(userId) {
  if (!userId) return [];
  try {
    const resp = await fetch(`${API_BASE}/history?user_id=${userId}`, {
      headers: authHeaders(),
    });
    if (!resp.ok) return [];
    const data = await resp.json();
    return data.items || [];
  } catch {
    return [];
  }
}

export async function clearHistory(userId) {
  if (!userId) return;
  await fetch(`${API_BASE}/history?user_id=${userId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
}
