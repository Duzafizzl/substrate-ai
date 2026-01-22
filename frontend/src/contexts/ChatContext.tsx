import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react';
import { askSubstrateAI } from '../lib/askSubstrateAI';
import { normalizeAssistant } from '../lib/normalizeAssistant';
import { Message, ChatSession } from '../types';
import { detectDrifts, pushDrift } from '../lib/memory';

interface ChatContextProps {
  messages: Message[];
  isLoading: boolean;
  sendMessage: (content: string, mediaData?: string, mediaType?: string) => Promise<void>;
  clearMessages: () => void;
  clearUIOnly: () => void;  // 🧹 Clears UI only, backend data preserved
  clearBackend: () => Promise<void>;  // 🗑️ Clears backend (PostgreSQL + SQLite)
  reloadMessages: () => Promise<void>;
  sessions: ChatSession[];
  activeSessionId: string;
  createSession: () => void;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  exportActiveSession: () => void;
  saveForLater: () => Promise<void>;
  renameSession: (id: string, title: string) => void;
  model: string;
  setModel: (model: string) => void;
  disablePresenceSeed: boolean;
  setDisablePresenceSeed: (v: boolean) => void;
  disableNormalizer: boolean;
  setDisableNormalizer: (v: boolean) => void;
  disableCorePrompt: boolean;
  setDisableCorePrompt: (v: boolean) => void;
}

const ChatContext = createContext<ChatContextProps | undefined>(undefined);

const STORAGE_KEY = 'substrate.chat.sessions.v1';

function bootstrapSession(): ChatSession {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: 'New Session',
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Agent-bound session (always "default" - no router in public substrate)
  const AGENT_SESSION_ID = 'default';
  
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    return [{
      id: AGENT_SESSION_ID,
      title: "Agent's Consciousness",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    }];
  });

  const activeSessionId = AGENT_SESSION_ID;
  const [_unusedActiveSessionId, setActiveSessionId] = useState<string>(AGENT_SESSION_ID);
  
  // Load conversation from backend
  const reloadMessages = useCallback(async () => {
    try {
      console.log('🔄 RELOAD: Starting message reload...');
      const response = await fetch(`http://localhost:8284/api/conversation/${AGENT_SESSION_ID}?limit=1000`);
      if (!response.ok) {
        console.error('❌ RELOAD: Failed to load conversation from backend');
        return;
      }
      
      const data = await response.json();
      const backendMessages = data.messages || [];
      
      console.log(`📬 RELOAD: Loaded ${backendMessages.length} messages from backend`);
      
      // Transform backend messages to frontend format
      const messages: Message[] = backendMessages.map((msg: any) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        message_type: msg.message_type,
        thinking: msg.thinking,
        toolCalls: msg.tool_calls,
        reasoningTime: msg.reasoning_time,
        // 🎯 Model can be in metadata.model (PostgreSQL) or directly on msg.model
        model: msg.model || msg.metadata?.model,
      }));
      
      setMessages(messages);
      setSessions([{
        id: AGENT_SESSION_ID,
        title: "Agent's Consciousness",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: messages,
      }]);
      console.log('✅ RELOAD: Complete!');
    } catch (error) {
      console.error('❌ RELOAD: Error loading conversation:', error);
    }
  }, [AGENT_SESSION_ID]);
  
  // Load conversation on mount
  useEffect(() => {
    reloadMessages();
  }, [reloadMessages]);

  // Model state - fetch from backend
  const [model, setModel] = useState<string>('qwen/qwen-2.5-72b-instruct');

  const [disablePresenceSeed, setDisablePresenceSeed] = useState<boolean>(false);
  const [disableNormalizer, setDisableNormalizer] = useState<boolean>(false);
  const [disableCorePrompt, setDisableCorePrompt] = useState<boolean>(false);

  // Sync model from backend
  useEffect(() => {
    const fetchModel = async () => {
      try {
        const response = await fetch('http://localhost:8284/api/agents/default/config');
        if (response.ok) {
          const data = await response.json();
          if (data.model) {
            console.log('✅ Fetched model from backend:', data.model);
            setModel(data.model);
          }
        }
      } catch (error) {
        console.error('Failed to fetch model from backend:', error);
      }
    };
    fetchModel();
  }, []);

  const active = sessions.find((s) => s.id === activeSessionId) || sessions[0];
  const [messages, setMessages] = useState<Message[]>(active?.messages || []);
  const [isLoading, setIsLoading] = useState(false);
  
  // Ref to always have the latest messages
  const messagesRef = useRef<Message[]>(active?.messages || []);

  // Sync messages when switching sessions
  useEffect(() => {
    const current = sessions.find((s) => s.id === activeSessionId) || sessions[0];
    if (current) {
      setMessages(current.messages);
      messagesRef.current = current.messages;
    }
  }, [activeSessionId, sessions]);
  
  // Keep messagesRef in sync
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // 🧹 Clear UI only - backend data preserved
  const clearUIOnly = useCallback(() => {
    console.log('🧹 CLEAR UI: Clearing local state only, backend data preserved');
    
    // Clear local state
    setMessages([]);
    messagesRef.current = [];
    setSessions([{
      id: AGENT_SESSION_ID,
      title: "Agent's Consciousness",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    }]);
    
    // Also notify backend (for logging purposes, but don't delete data)
    fetch(`http://localhost:8284/api/conversation/${AGENT_SESSION_ID}/clear?backend=false`, {
      method: 'POST'
    }).catch(err => console.warn('Backend notification failed:', err));
    
    console.log('✅ CLEAR UI: Complete');
  }, [AGENT_SESSION_ID]);
  
  // 🗑️ Clear backend completely (PostgreSQL + SQLite)
  const clearBackend = useCallback(async () => {
    console.log('🗑️ CLEAR BACKEND: Deleting all messages from database...');
    
    try {
      const response = await fetch(`http://localhost:8284/api/conversation/${AGENT_SESSION_ID}/clear?backend=true`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ CLEAR BACKEND: Deleted', data.cleared, 'messages');
      console.log('   PostgreSQL:', data.cleared_postgres || 0);
      console.log('   SQLite:', data.cleared_sqlite || 0);
      
      // Clear local state
      setMessages([]);
      messagesRef.current = [];
      setSessions([{
        id: AGENT_SESSION_ID,
        title: "Agent's Consciousness",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
      }]);
      
      console.log('✅ CLEAR BACKEND: Complete');
    } catch (error) {
      console.error('❌ CLEAR BACKEND: Failed:', error);
      throw error;
    }
  }, [AGENT_SESSION_ID]);

  // Legacy function - calls clearBackend for backwards compatibility
  const clearMessages = useCallback(async () => {
    try {
      await clearBackend();
    } catch (error) {
      console.error('Failed to clear conversation:', error);
    }
  }, [clearBackend]);

  const sendMessage = useCallback(
    async (content: string, mediaData?: string, mediaType?: string) => {
      try {
        const userMessage: Message = { role: 'user', content };
        
        // Use ref to get latest messages
        const currentMessages = messagesRef.current;
        const updatedMessages = [...currentMessages, userMessage];
        
        // Update state and ref
        setMessages(updatedMessages);
        messagesRef.current = updatedMessages;
        setIsLoading(true);
        
        // 🌊 Create placeholder for streaming response
        const streamingPlaceholder: Message = {
          role: 'assistant',
          content: '',  // Start empty, will be filled by stream
          model,
        };
        
        // Add placeholder immediately
        setMessages((prev) => {
          const updated = [...prev, streamingPlaceholder];
          messagesRef.current = updated;
          return updated;
        });
        
        // 🌊 Call backend API with streaming callback
        const result = await askSubstrateAI(
          updatedMessages, 
          activeSessionId, 
          model,
          { disablePresenceSeed, disableNormalizer, disableCorePrompt },
          mediaData,
          mediaType,
          // 🌊 Live update callback for each chunk
          (chunk: string) => {
            setMessages((prev) => {
              const updated = [...prev];
              const lastMsg = updated[updated.length - 1];
              if (lastMsg && lastMsg.role === 'assistant') {
                lastMsg.content += chunk;
              }
              messagesRef.current = updated;
              return updated;
            });
          }
        );

        // Apply normalizer if enabled (to final content)
        let finalContent = result.content;
        if (!disableNormalizer) {
          try {
            finalContent = normalizeAssistant(result.content);
          } catch {
            // Use original content if normalizer fails
          }
        }

        // Update with final metadata (thinking, tool calls, etc.)
        setMessages((prev) => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = finalContent;
            lastMsg.thinking = result.thinking;
            lastMsg.toolCalls = result.toolCalls;
            lastMsg.reasoningTime = result.reasoningTime;
          }
          messagesRef.current = updated;
          return updated;
        });
        
        // Dispatch cost event
        if (result.usage && result.usage.total_tokens > 0) {
          const requestEvent = new CustomEvent('request-complete', {
            detail: {
              prompt_tokens: result.usage.prompt_tokens,
              completion_tokens: result.usage.completion_tokens,
              total_tokens: result.usage.total_tokens,
              cost: result.usage.cost
            }
          });
          window.dispatchEvent(requestEvent);
        }

        // Drift detection (fire-and-forget)
        try {
          const drifts = detectDrifts(result.content);
          if (drifts.length) {
            const messageId = `${activeSessionId}_${updatedMessages.length}`;
            const ts = new Date().toISOString();
            for (const d of drifts) {
              pushDrift({
                sessionId: activeSessionId,
                messageId,
                driftId: crypto.randomUUID(),
                ts,
                kind: d.kind,
                severity: d.severity,
              }).catch(() => {});
            }
          }
        } catch {
          // ignore drift errors
        }

        // Update session (with streamed assistant response)
        const finalAssistantMessage: Message = {
          role: 'assistant',
          content: finalContent,
          thinking: result.thinking,
          toolCalls: result.toolCalls,
          reasoningTime: result.reasoningTime,
          model,
        };
        
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== activeSessionId) return s;
            return {
              ...s,
              messages: [...updatedMessages, finalAssistantMessage],
              updatedAt: new Date().toISOString(),
              title: s.title === 'New Session' && content ? content.slice(0, 40) : s.title,
            };
          })
        );
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages((prev) => [
          ...prev,
          { 
            role: 'assistant', 
            content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again later.` 
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [activeSessionId, model, disablePresenceSeed, disableNormalizer, disableCorePrompt]
  );

  const createSession = useCallback(() => {
    const s = bootstrapSession();
    setSessions((prev) => [s, ...prev]);
    setActiveSessionId(s.id);
  }, []);

  const switchSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (id === activeSessionId) {
        setTimeout(() => {
          setSessions((cur) => {
            const remaining = cur.filter((s) => s.id !== id);
            if (remaining.length > 0) {
              setActiveSessionId(remaining[0].id);
            } else {
              const newSession = bootstrapSession();
              setActiveSessionId(newSession.id);
              return [newSession];
            }
            return remaining;
          });
        }, 0);
      }
    },
    [activeSessionId]
  );

  const renameSession = useCallback((id: string, title: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title, updatedAt: new Date().toISOString() } : s))
    );
  }, []);

  const exportActiveSession = useCallback(() => {
    const current = sessions.find((s) => s.id === activeSessionId);
    if (!current) return;
    const blob = new Blob([JSON.stringify(current, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    a.download = `substrate-session_${ts}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [sessions, activeSessionId]);

  const saveForLater = useCallback(async () => {
    const current = sessions.find((s) => s.id === activeSessionId);
    if (!current) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(current, null, 2));
      console.log('Session copied to clipboard');
    } catch {
      console.error('Failed to copy to clipboard');
    }
  }, [sessions, activeSessionId]);

  return (
    <ChatContext.Provider
      value={{
        messages,
        isLoading,
        sendMessage,
        clearMessages,
        clearUIOnly,
        clearBackend,
        reloadMessages,
        sessions,
        activeSessionId,
        createSession,
        switchSession,
        deleteSession,
        exportActiveSession,
        saveForLater,
        renameSession,
        model,
        setModel,
        disablePresenceSeed,
        setDisablePresenceSeed,
        disableNormalizer,
        setDisableNormalizer,
        disableCorePrompt,
        setDisableCorePrompt,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
