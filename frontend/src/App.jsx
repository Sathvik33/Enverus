import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LandingPage from './components/LandingPage';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import SourcesDrawer from './components/SourcesDrawer';
import AuthModal from './components/AuthModal';
import { 
  authStorage, fetchMe, getDocument, deleteDocument, sendChatStream, 
  getSessions, getSessionDetail, deleteSession 
} from './services/api';
import './App.css';

export default function App() {
  const [currentView, setCurrentView] = useState('landing');
  const [user, setUser] = useState(authStorage.getUser());
  const [authModal, setAuthModal] = useState(null); // 'signin' | 'signup' | null
  
  const [documentId, setDocumentId] = useState(null);
  const [activeDoc, setActiveDoc] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sourcesMessage, setSourcesMessage] = useState(null);

  // Check auth session validity on mount
  useEffect(() => {
    async function checkAuth() {
      const me = await fetchMe();
      if (me) {
        setUser(me);
      } else {
        setUser(null);
      }
    }
    checkAuth();
  }, []);

  // Fetch document details whenever documentId changes
  useEffect(() => {
    if (!documentId) {
      setActiveDoc(null);
      return;
    }
    async function loadDoc() {
      try {
        const doc = await getDocument(documentId);
        setActiveDoc(doc);
      } catch {
        setActiveDoc(null);
      }
    }
    loadDoc();
  }, [documentId]);

  // Fetch user chat sessions whenever user changes
  useEffect(() => {
    if (!user) {
      setSessions([]);
      setActiveSessionId(null);
      return;
    }
    async function loadSessions() {
      const list = await getSessions(user.id);
      setSessions(list);
    }
    loadSessions();
  }, [user]);

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setSourcesMessage(null);
  };

  const handleSelectSession = async (sessionItem) => {
    try {
      setActiveSessionId(sessionItem.id);
      if (sessionItem.document_id && sessionItem.document_id !== documentId) {
        setDocumentId(sessionItem.document_id);
      }
      const detail = await getSessionDetail(sessionItem.id);
      if (detail && detail.messages) {
        setMessages(
          detail.messages.map((m) => ({
            role: m.role,
            content: m.content,
            citations: m.citations || [],
            evidence: m.evidence || [],
            trace: {},
          }))
        );
      }
    } catch (err) {
      console.error('Failed to load session details:', err);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) {
        handleNewChat();
      }
      if (user) {
        const list = await getSessions(user.id);
        setSessions(list);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleSendMessage = async (queryText) => {
    if (!documentId) return;

    const userMessage = { role: 'user', content: queryText };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      await sendChatStream(
        documentId,
        queryText,
        user?.id,
        activeSessionId,
        {
          onMetadata: (metadata) => {
            setLoading(false);
            if (metadata.session_id && !activeSessionId) {
              setActiveSessionId(metadata.session_id);
            }
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: '',
                citations: metadata.citations || [],
                evidence: metadata.evidence || [],
                trace: metadata.retrieval_trace || {},
                isStreaming: true,
              },
            ]);
          },
          onToken: (token) => {
            setLoading(false);
            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const lastIdx = prev.length - 1;
              const lastMsg = prev[lastIdx];
              if (lastMsg.role !== 'assistant') {
                return [
                  ...prev,
                  {
                    role: 'assistant',
                    content: token,
                    citations: [],
                    evidence: [],
                    trace: {},
                    isStreaming: true,
                  },
                ];
              }
              const updated = [...prev];
              updated[lastIdx] = {
                ...lastMsg,
                content: lastMsg.content + token,
                isStreaming: true,
              };
              return updated;
            });
          },
          onDone: async (doneEvt) => {
            setLoading(false);
            if (doneEvt.session_id) {
              setActiveSessionId(doneEvt.session_id);
            }
            setMessages((prev) => {
              if (prev.length === 0) return prev;
              const lastIdx = prev.length - 1;
              const updated = [...prev];
              const lastMsg = updated[lastIdx];
              if (lastMsg.role === 'assistant') {
                updated[lastIdx] = {
                  ...lastMsg,
                  content: doneEvt.final_answer || lastMsg.content,
                  citations: doneEvt.citations || lastMsg.citations,
                  evidence: doneEvt.evidence || lastMsg.evidence,
                  isStreaming: false,
                };
              }
              return updated;
            });

            if (user) {
              const updatedSessions = await getSessions(user.id);
              setSessions(updatedSessions);
            }
          },
          onError: (err) => {
            setLoading(false);
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: `Error: ${err.message || 'Failed to stream answer'}`,
                citations: [],
                evidence: [],
                isStreaming: false,
              },
            ]);
          },
        }
      );
    } catch (err) {
      setLoading(false);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.message || 'Failed to generate answer'}`,
          citations: [],
          evidence: [],
          isStreaming: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    authStorage.clear();
    setUser(null);
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
  };

  const handleDeleteDocument = async (idToDelete) => {
    const targetId = idToDelete || documentId;
    if (!targetId) return;
    try {
      await deleteDocument(targetId);
    } catch (err) {
      console.warn('Document delete warning:', err);
    }
    setDocumentId(null);
    setActiveDoc(null);
    setMessages([]);
    setActiveSessionId(null);
    if (user) {
      const userSessions = await getSessions(user.id);
      setSessions(userSessions);
    }
  };

  return (
    <div className="app-container">
      <Navbar
        currentView={currentView}
        setCurrentView={setCurrentView}
        user={user}
        onOpenAuth={(mode) => setAuthModal(mode)}
        onLogout={handleLogout}
        activeDoc={activeDoc}
      />

      {currentView === 'landing' ? (
        <LandingPage
          onLaunchApp={() => setCurrentView('workspace')}
          onOpenAuth={(mode) => setAuthModal(mode)}
          user={user}
        />
      ) : (
        <div className="workspace-layout">
          <Sidebar
            activeDoc={activeDoc}
            documentId={documentId}
            setDocumentId={setDocumentId}
            onDocumentLoaded={(id) => {
              setDocumentId(id);
              handleNewChat();
            }}
            onDeleteDocument={handleDeleteDocument}
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onNewChat={handleNewChat}
            onDeleteSession={handleDeleteSession}
            onSessionsCleared={() => {
              setSessions([]);
              setActiveSessionId(null);
              setMessages([]);
            }}
            user={user}
            onOpenAuth={(mode) => setAuthModal(mode)}
          />

          <ChatArea
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={loading}
            documentId={documentId}
            onOpenSources={(msg) => setSourcesMessage(msg)}
          />
        </div>
      )}

      {/* On-Demand Sources Drawer */}
      {sourcesMessage && (
        <SourcesDrawer
          message={sourcesMessage}
          onClose={() => setSourcesMessage(null)}
        />
      )}

      {/* Authentication Modal */}
      {authModal && (
        <AuthModal
          initialMode={authModal}
          onClose={() => setAuthModal(null)}
          onSuccess={(loggedInUser) => {
            setUser(loggedInUser);
            setAuthModal(null);
          }}
        />
      )}
    </div>
  );
}

