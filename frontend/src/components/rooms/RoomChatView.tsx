import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ArrowLeft, Hash, Copy, Check, ChevronRight, Plus } from 'lucide-react';
import { motion } from 'framer-motion';
import ChatBubble from '../ChatBubble';
import ChatInput from '../ChatInput';

interface Channel {
  id: string;
  name: string;
  description: string;
  parent_id: string | null;
  discord_channel_id: string | null;
  discord_webhook_url: string | null;
  created_at: string;
  updated_at: string;
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  id?: string;
  created_at?: string;
  metadata?: Record<string, any>;
}

interface RoomChatViewProps {
  channel: Channel;
  onBack: () => void;
  agentId?: string;
  onNavigateToChannel?: (channelId: string) => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8284';

const RoomChatView: React.FC<RoomChatViewProps> = ({ channel, onBack, agentId = 'default', onNavigateToChannel }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [copiedId, setCopiedId] = useState(false);
  const [subChannels, setSubChannels] = useState<Channel[]>([]);
  const [showCreateSubRoomModal, setShowCreateSubRoomModal] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentAgentId = agentId;
  
  // Check if this is the task channel (no chatting allowed!)
  const isTaskChannel = channel.name === '📋 task' || channel.name.includes('task');
  
  // Load messages and sub-channels
  useEffect(() => {
    loadMessages();
    loadSubChannels();
    
    // Poll for new messages every 2 seconds
    const interval = setInterval(() => {
      loadMessages();
      loadSubChannels();
    }, 2000);
    return () => clearInterval(interval);
  }, [channel.id, currentAgentId]);
  
  const loadSubChannels = async () => {
    try {
      const response = await fetch(`${API_URL}/api/channels?agent_id=${currentAgentId}&parent_id=${channel.id}`);
      if (response.ok) {
        const data = await response.json();
        setSubChannels(data.channels || []);
      }
    } catch (error) {
      console.error('Error loading sub-channels:', error);
    }
  };
  
  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [messages]);
  
  const loadMessages = async () => {
    try {
      const response = await fetch(`${API_URL}/api/channels/${channel.id}/messages?limit=100`);
      if (response.ok) {
        const data = await response.json();
        // Convert to Message format (include metadata for tasks)
        const formattedMessages: Message[] = (data.messages || []).map((msg: any) => ({
          role: msg.role as 'user' | 'assistant' | 'system',
          content: msg.content,
          id: msg.id,
          created_at: msg.created_at,
          metadata: msg.metadata || {}
        }));
        setMessages(formattedMessages);
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSendMessage = useCallback(async (content: string) => {
    if (!content.trim() || sending) return;
    
    try {
      setSending(true);
      
      // Optimistically add user message
      const userMessage: Message = {
        role: 'user',
        content: content.trim(),
        id: `temp-${Date.now()}`
      };
      setMessages(prev => [...prev, userMessage]);
      
      // Send to backend
      const response = await fetch(`${API_URL}/api/channels/${channel.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: content.trim(),
          role: 'user'
        })
      });
      
      if (response.ok) {
        // Reload messages to get the actual saved message (and any agent response)
        await loadMessages();
      } else {
        // Remove optimistic message on error
        setMessages(prev => prev.filter(m => m.id !== userMessage.id));
        const error = await response.json();
        alert(`Failed to send message: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  }, [channel.id, sending]);
  
  const copyId = async () => {
    try {
      await navigator.clipboard.writeText(channel.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    } catch (error) {
      console.error('Failed to copy ID:', error);
    }
  };
  
  return (
    <div className="flex-1 flex h-full overflow-hidden">
      {/* Sidebar: Sub-Channels - Always visible */}
      <div className="w-64 bg-gray-900/50 border-r border-gray-800 flex flex-col">
        <div className="p-3 border-b border-gray-800 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Sub-Rooms
          </h3>
          <button
            onClick={() => setShowCreateSubRoomModal(true)}
            className="p-1.5 hover:bg-gray-800/50 rounded transition-colors"
            title="Create sub-room"
          >
            <Plus className="w-4 h-4 text-gray-400 hover:text-violet-400 transition-colors" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {subChannels.length === 0 ? (
            <div className="text-center text-gray-500 py-8 text-xs">
              <p>No sub-rooms yet</p>
              <button
                onClick={() => setShowCreateSubRoomModal(true)}
                className="mt-2 text-violet-400 hover:text-violet-300 text-xs"
              >
                Create one
              </button>
            </div>
          ) : (
            subChannels.map((subChannel) => (
              <button
                key={subChannel.id}
                onClick={() => onNavigateToChannel?.(subChannel.id)}
                className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-gray-800/50 transition-colors text-left group"
              >
                <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-violet-400 transition-colors" />
                <Hash className="w-4 h-4 text-violet-400/70 flex-shrink-0" />
                <span className="text-sm font-medium text-gray-300 flex-1 truncate group-hover:text-white transition-colors">
                  {subChannel.name}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
      
      {/* Create Sub-Room Modal */}
      {showCreateSubRoomModal && (
        <CreateSubRoomModal
          parentId={channel.id}
          onClose={() => setShowCreateSubRoomModal(false)}
          onCreated={() => {
            loadSubChannels();
            setShowCreateSubRoomModal(false);
          }}
          agentId={currentAgentId}
        />
      )}
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="bg-gray-900/50 border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            title="Back to rooms"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          
          {/* Copy ID Button - Links */}
          <button
            onClick={copyId}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors flex items-center gap-2 text-sm text-gray-400 hover:text-white"
            title="Copy room ID"
          >
            {copiedId ? (
              <>
                <Check className="w-4 h-4 text-green-400" />
                <span className="text-green-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span className="font-mono text-xs">{channel.id.slice(0, 8)}...</span>
              </>
            )}
          </button>
          
          <div className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-violet-400" />
            <div>
              <h2 className="text-lg font-bold text-white">{channel.name}</h2>
              {channel.description && (
                <p className="text-xs text-gray-400">{channel.description}</p>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto bg-gray-950">
        <div className="max-w-4xl mx-auto p-4">
          {loading ? (
            <div className="text-center text-gray-400 py-8">Loading messages...</div>
          ) : messages.length === 0 ? (
            <div className="text-center text-gray-400 py-12">
              <Hash className="w-12 h-12 mx-auto mb-4 text-gray-600" />
              <p className="text-sm">No messages yet. Start the conversation!</p>
            </div>
          ) : (
            <div className="space-y-4 py-4">
              {messages.map((message, index) => (
                <ChatBubble
                  key={message.id || index}
                  message={message}
                  isLast={index === messages.length - 1 && message.role === 'assistant'}
                />
              ))}
              <div ref={messagesEndRef} className="h-32" />
            </div>
          )}
        </div>
      </div>
      
      {/* Chat Input (disabled for task channel) */}
      {!isTaskChannel && (
        <div className="border-t border-gray-800 bg-gray-900/50">
          <div className="max-w-4xl mx-auto p-4">
            <ChatInput onSendMessage={handleSendMessage} />
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

// Simple Create Sub-Room Modal Component
interface CreateSubRoomModalProps {
  parentId: string;
  onClose: () => void;
  onCreated: () => void;
  agentId: string;
}

const CreateSubRoomModal: React.FC<CreateSubRoomModalProps> = ({ parentId, onClose, onCreated, agentId }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/channels`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          name: name.trim(),
          description: description.trim() || null,
          parent_id: parentId
        })
      });
      
      if (response.ok) {
        onCreated();
      } else {
        const error = await response.json();
        alert(`Failed to create sub-room: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error creating sub-room:', error);
      alert('Failed to create sub-room');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-gray-800 rounded-lg border border-gray-700 p-6 max-w-md w-full"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white">Create Sub-Room</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            aria-label="Close"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400 rotate-90" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Sub-Room Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Enter sub-room name..."
              autoFocus
            />
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Enter description..."
              rows={3}
            />
          </div>
          
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || loading}
              className="flex-1 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

export default RoomChatView;

