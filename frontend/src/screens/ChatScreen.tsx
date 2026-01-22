import React, { useRef, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import ChatBubble from '../components/ChatBubble';
import ChatInput from '../components/ChatInput';
import { TokenCounter } from '../components/TokenCounter';
import CostCounter from '../components/CostCounter';
import AgentSelector from '../components/agent/AgentSelector';
import ModelSettings from '../components/agent/ModelSettings';
import MemoryBlocksPanel from '../components/agent/MemoryBlocksPanel';
import ResizablePanels from '../components/ui/ResizablePanels';
import { useChat } from '../contexts/ChatContext';
import SummarizeButton from '../components/SummarizeButton';
import { MessageSquare, Calendar, Heart, Settings, Trash2 } from 'lucide-react';
import HeartbeatConfigModal from '../components/agent/HeartbeatConfigModal';
import ClearChatModal from '../components/ClearChatModal';
import LanguageSwitcher from '../components/LanguageSwitcher';

interface ChatScreenProps {
  onNavigateToRooms?: () => void;
  onNavigateToTasks?: () => void;
  onOpenSettings?: () => void;
}

const ChatScreen: React.FC<ChatScreenProps> = ({ onNavigateToRooms, onNavigateToTasks, onOpenSettings }) => {
  const { t } = useTranslation();
  const { messages, isLoading, sendMessage, clearUIOnly, clearBackend } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Get agent ID from URL parameter, fallback to 'default'
  const getAgentIdFromURL = () => {
    const params = new URLSearchParams(window.location.search);
    return params.get('agent') || 'default';
  };
  
  const [currentAgentId, setCurrentAgentId] = useState(getAgentIdFromURL());
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  const [heartbeatModalOpen, setHeartbeatModalOpen] = useState(false);
  const [clearChatModalOpen, setClearChatModalOpen] = useState(false);
  
  // Update URL when agent ID changes
  const handleAgentChange = (newAgentId: string) => {
    setCurrentAgentId(newAgentId);
    const params = new URLSearchParams(window.location.search);
    if (newAgentId && newAgentId !== 'default') {
      params.set('agent', newAgentId);
    } else {
      params.delete('agent');
    }
    const newURL = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
    window.history.pushState({}, '', newURL);
    console.log(`🔄 Agent ID updated in URL: ${newAgentId}`);
  };
  
  // Load agent ID from URL on mount
  useEffect(() => {
    const agentId = getAgentIdFromURL();
    if (agentId !== currentAgentId) {
      setCurrentAgentId(agentId);
      console.log(`📖 Loaded agent ID from URL: ${agentId}`);
    }
  }, []);
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    // Immediate scroll to ensure we're always at the bottom
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end',
        inline: 'nearest'
      });
    }
  }, [messages, isLoading]);
  
  return (
    <div className="h-screen flex flex-col bg-gray-950 overflow-hidden">
      {/* Skip to main content link for keyboard users */}
      <a 
        href="#main-content" 
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-purple-600 focus:text-white focus:rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2 focus:ring-offset-gray-950"
      >
        Skip to main content
      </a>
      
      {/* TOP BAR - Agent Selector + Token Counter */}
      <header className="h-16 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4" role="banner">
        {/* Left: Agent Selector */}
        <div className="flex items-center gap-4">
          {/* Logo/Home */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center" aria-hidden="true">
              <span className="text-white font-bold text-sm">S</span>
            </div>
            <span className="text-gray-300 text-sm">Substrate AI</span>
          </div>

          {/* Agent Selector */}
          <AgentSelector onAgentChange={handleAgentChange} />
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-3">
          {/* Rooms Button */}
          {onNavigateToRooms && (
            <button
              onClick={onNavigateToRooms}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-purple-600/30 text-gray-300 hover:text-purple-300 transition-colors"
              title={t('header.rooms')}
            >
              <MessageSquare className="w-4 h-4" />
              <span className="text-sm">{t('header.rooms')}</span>
            </button>
          )}
          
          {/* Tasks Button */}
          {onNavigateToTasks && (
            <button
              onClick={onNavigateToTasks}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-violet-600/30 text-gray-300 hover:text-violet-300 transition-colors"
              title={t('header.tasks')}
            >
              <Calendar className="w-4 h-4" />
              <span className="text-sm">{t('header.tasks')}</span>
            </button>
          )}

          {/* Heartbeat Config Button */}
          <button
            onClick={() => setHeartbeatModalOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-pink-900/50 text-pink-300 hover:bg-pink-800 border border-pink-700 hover:border-pink-600 transition-colors text-xs font-semibold flex items-center gap-1.5"
            title={t('header.heartbeat')}
          >
            <Heart className="w-3.5 h-3.5" />
            <span>{t('header.heartbeat')}</span>
          </button>
          
          {/* Settings Button */}
          {onOpenSettings && (
            <button
              onClick={onOpenSettings}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition-colors"
              title={t('header.settings')}
            >
              <Settings className="w-4 h-4" />
              <span className="text-sm">{t('header.settings')}</span>
            </button>
          )}
          
          {/* Language Switcher */}
          <LanguageSwitcher />
          
          {/* Cost Counter */}
          <CostCounter />
          
          {/* New Chat Button (Archive & Summarize) */}
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              
              if (!window.confirm('📦 New Chat?\n\nCurrent conversation will be archived and summarized.')) return;
              
              // Archive and summarize
              fetch('http://localhost:8284/api/agents/default/new-chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
              })
                .then(res => res.json())
                .then(data => {
                  console.log('✅ Chat archived:', data);
                  
                  // Clear localStorage
                  try {
                    const STORAGE_KEY = 'substrate.chat.sessions.v1';
                    const raw = localStorage.getItem(STORAGE_KEY);
                    if (raw) {
                      const parsed = JSON.parse(raw);
                      parsed.sessions = parsed.sessions.map((s: any) => ({ ...s, messages: [] }));
                      localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
                    }
                  } catch (e) {
                    console.error('Failed to clear localStorage:', e);
                  }
                  
                  if (data.summary) {
                    // Show summary briefly
                    alert('📦 Previous chat archived!\n\n' + data.summary);
                  }
                  
                  // Reload to start fresh
                  window.location.reload();
                })
                .catch(error => {
                  console.error('❌ Failed to archive:', error);
                  alert('Failed to create new chat. Check console.');
                });
            }}
            type="button"
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-green-400 transition-colors focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-offset-2 focus:ring-offset-gray-900"
            title="New Chat (Archive & Summarize)"
            aria-label="New Chat (Archive & Summarize)"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>

          {/* Clear Chat Button - Opens Danger Zone Modal */}
          <button
            onClick={() => setClearChatModalOpen(true)}
            type="button"
            className="p-2 rounded-lg text-gray-400 hover:bg-red-900/30 hover:text-red-400 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 focus:ring-offset-gray-900"
            title={t('header.clearChat')}
            aria-label={t('header.clearChat')}
          >
            <Trash2 className="w-4 h-4" />
          </button>
          
          {/* Sidebar Toggle Buttons */}
          <button
            onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
            className={`p-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2 focus:ring-offset-gray-900 ${leftSidebarOpen ? 'bg-gray-800 text-purple-400' : 'text-gray-400 hover:bg-gray-800'}`}
            title={t('header.toggleSettings')}
            aria-label={t('header.toggleSettings')}
            aria-expanded={leftSidebarOpen}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>

          <button
            onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
            className={`p-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2 focus:ring-offset-gray-900 ${rightSidebarOpen ? 'bg-gray-800 text-purple-400' : 'text-gray-400 hover:bg-gray-800'}`}
            title={t('header.toggleMemory')}
            aria-label={t('header.toggleMemory')}
            aria-expanded={rightSidebarOpen}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
        </div>
      </header>

      {/* 3-COLUMN RESIZABLE LAYOUT - Everything scrollable, Input fixed */}
      <div className="flex-1 flex overflow-hidden">
        <ResizablePanels
          leftPanelVisible={leftSidebarOpen}
          rightPanelVisible={rightSidebarOpen}
          leftPanel={<ModelSettings agentId={currentAgentId} />}
          rightPanel={<MemoryBlocksPanel agentId={currentAgentId} />}
          centerPanel={
            <div className="h-full flex flex-col">
              {/* Token Counter + Summary Button */}
              <div className="bg-gray-900/50 border-b border-gray-800/50 px-4 py-2 flex-shrink-0 flex items-center justify-between gap-4">
                <TokenCounter sessionId="default" />
                <SummarizeButton sessionId="default" />
              </div>

              {/* Messages - Scrollable (auto-scroll to bottom) */}
              <main 
                id="main-content"
                className="flex-1 overflow-y-auto scroll-smooth"
                role="main"
                aria-label="Chat messages"
                aria-live="polite"
                aria-atomic="false"
              >
                <div className="max-w-4xl mx-auto p-4">
                  <div className="py-4 min-h-full flex flex-col">
                    {messages.map((message, index) => (
                      <ChatBubble 
                        key={index} 
                        message={message} 
                        isLast={index === messages.length - 1 && message.role === 'assistant'}
                      />
                    ))}
                    
                    {/* Loading indicator */}
                    {isLoading && (
                      <motion.div
                        className="flex justify-start mb-4"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        role="status"
                        aria-live="polite"
                        aria-label="Loading response"
                      >
                        <div className="bg-violetGlow/20 rounded-2xl px-4 py-3 flex space-x-2">
                          <div className="w-2 h-2 rounded-full bg-violetGlow/70 animate-pulse" style={{ animationDelay: '0ms' }} aria-hidden="true"></div>
                          <div className="w-2 h-2 rounded-full bg-violetGlow/70 animate-pulse" style={{ animationDelay: '300ms' }} aria-hidden="true"></div>
                          <div className="w-2 h-2 rounded-full bg-violetGlow/70 animate-pulse" style={{ animationDelay: '600ms' }} aria-hidden="true"></div>
                        </div>
                      </motion.div>
                    )}
                    
                    {/* Scroll anchor - ALWAYS at the very bottom with padding for fixed input */}
                    <div ref={messagesEndRef} className="h-32 flex-shrink-0" aria-hidden="true" />
                  </div>
                </div>
              </main>
            </div>
          }
        />
      </div>

      {/* FIXED CHAT INPUT - Fixed at bottom, over scrollable content */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-gray-950" role="complementary" aria-label="Chat input">
        <ChatInput onSendMessage={sendMessage} />
      </div>

      {/* HEARTBEAT MODAL */}
      <HeartbeatConfigModal
        isOpen={heartbeatModalOpen}
        onClose={() => setHeartbeatModalOpen(false)}
        agentId={currentAgentId}
      />

      {/* CLEAR CHAT MODAL - Danger Zone */}
      <ClearChatModal
        isOpen={clearChatModalOpen}
        onClose={() => setClearChatModalOpen(false)}
        onClearUIOnly={clearUIOnly}
        onClearBackend={clearBackend}
      />
    </div>
  );
};

export default ChatScreen;
